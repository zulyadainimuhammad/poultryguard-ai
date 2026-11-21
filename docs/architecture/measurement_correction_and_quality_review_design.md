# PoultryGuard AI — Measurement Correction Requests and Quality Review Design

**Status:** Proposed design for review; no application implementation authorised  
**Stage:** 3.2.4 — correction and measurement-quality workflow design  
**Base:** `main` at `a0ada899bc9e2fec7a815528d8ef9bcc135fcacc`  
**Depends on:** PR #21 (merged schema migration) and PR #22 (merged manual observation model/repository/service)  
**Scope:** Append-only workflow design, logical data model, state semantics, transaction boundaries, query rules and acceptance tests. No schema migration, runtime service, UI, or live database operation.

---

## 1. Executive recommendation

Implement correction requests and quality review as **separate append-only workflows**, while retaining `measurement_observations` as the immutable record of measured or candidate values.

The observation table already contains the accepted-correction relationship:

- `supersedes_observation_id` identifies the observation replaced by an accepted correction.
- `correction_reason` records why that accepted correction exists.
- A partial unique index permits at most one accepted successor for a target observation.
- Database triggers prevent updates, deletes and replacement of observation rows.

That structure is suitable for an accepted correction, but it is not a request/review workflow. A pending or rejected request is not itself a measurement and must not be inserted as a correction observation. The observation-table CHECK constraint requires a populated supersession link, a non-empty reason and `quality_status = 'observed'` whenever correction metadata is present. The accepted-successor index would also reserve the target too early if a pending request were stored there.

**Recommended separation:**

1. `measurement_observations`: immutable original and accepted measurement/correction values.
2. `measurement_correction_requests`: immutable proposals to replace the value of an accepted observation.
3. `measurement_correction_request_events`: immutable terminal decisions for each request.
4. `measurement_quality_review_events`: immutable decisions on observations initially stored as `pending_validation`.

The current value and effective quality status are derived from the observation row plus its immutable events. No status field on an existing observation is updated.

This design deliberately starts with a narrow manual-entry workflow. Sensor, import and system-generated correction policies; multi-role authorisation; reopening decisions; linked daily-record synchronisation; dual-write; analytics cutover; and backfill remain separate work packages.

## 2. Current implementation baseline

The following are implemented on `main`:

| Capability | Current state |
|---|---|
| Versioned SQLite migration runner and ledger | Implemented in PR #21 |
| Additive `measurement_observations` schema | Implemented in PR #21 |
| Observation constraints, indexes and append-only triggers | Implemented in PR #21 |
| Frozen `MeasurementObservation` dataclass | Implemented in PR #22 |
| Insert/read-only `MeasurementObservationRepository` | Implemented in PR #22 |
| Unit-of-Work access to the observation repository | Implemented in PR #22 |
| Manual observed-value creation for six metrics | Implemented in PR #22 |
| UTC recording timestamp, optional timezone-aware observation time | Implemented in PR #22 |
| Append-only accepted correction creation | Schema relationship reserved; no correction service yet |
| Correction requests, approvals and rejections | Not implemented |
| Quality-review decisions for pending observations | Not implemented |
| Daily-record dual-write, historical backfill or analytics cutover | Not implemented |

The manual-entry service currently writes `source_type = 'manual_entry'` and `quality_status = 'observed'`. It does not expose correction or review transitions. It does not run migrations. Existing analytics continue to read `daily_records`.

The first observation service is deliberately not a production multi-user authorisation boundary. The application currently has no authentication or role system; user identity fields remain nullable. A service method named “approve” must not be presented as secure multi-user approval until authentication, authorisation and farm-level access control are implemented.

## 3. Workflow principles

### 3.1 Preserve raw observations

An observation is a historical fact as received or entered. It is never edited or deleted to express a later decision. Its original `quality_status`, numeric candidate, unit, reporting date, source and timestamps remain unchanged.

### 3.2 Separate measurement from intention and decision

A correction request expresses an intention to replace an accepted value. It is not a measurement and has no effect on analytics or the current accepted value.

A review event expresses a decision about a pending candidate. It does not rewrite the candidate observation. The effective state is derived from the immutable event.

### 3.3 Only accepted corrections supersede

A correction observation is inserted only when a correction request is approved. The insert and approval event must commit in one transaction. A rejected or invalidated request creates no observation and consumes no `supersedes_observation_id` slot.

### 3.4 Decisions are final in the first release

For the first workflow release, every correction request can receive exactly one terminal outcome: `approved`, `rejected` or `invalidated`. Every pending-quality observation can receive exactly one terminal decision: `accepted` or `rejected`.

Reopening, appeals, amended decisions and second-level review require an explicit future event model. Do not update or delete a prior event to reverse it.

### 3.5 Preserve source precision and provenance

Do not infer an observation timestamp, reviewer identity, request author or source from unrelated fields. Missing identity remains NULL until authenticated identity exists. A correction approval timestamp is not the original measurement time.

## 4. Correction request workflow

### 4.1 First-release scope

The initial correction workflow should support a **value-only correction** of an accepted manual-entry observation.

A request proposes a replacement numeric value and requires a non-empty reason. It inherits the target's:

- `flock_id`;
- `record_date`;
- `metric_name`;
- canonical `unit`;
- `observed_at` (which may remain NULL).

The requester cannot change the flock, metric, reporting date or unit through a correction request. This prevents a correction from silently becoming a different measurement.

Only a current accepted `manual_entry` observation may be targeted in the first release. Corrections to sensor, imported or system-generated observations need source-specific policy and provenance handling and are deferred.

### 4.2 Request submission

At submission, the service must:

1. Validate the requester's positive target identifier and parse the proposed number as finite.
2. Load the target observation inside a `BEGIN IMMEDIATE` Unit-of-Work transaction.
3. Confirm the target exists, has `source_type = 'manual_entry'`, and is an accepted current value.
4. Confirm that the target is not already referenced by an accepted successor.
5. Validate the proposed value using the target metric's canonical validation rules.
6. Require a non-blank correction reason.
7. Create one immutable request with a generated UUID and UTC `requested_at`.
8. Commit without inserting a new observation and without changing the current accepted value.

A request can exist while the original observation remains the current accepted value. Request submission alone must not affect analytics.

### 4.3 Request review

A reviewer may approve or reject a request. At decision time the service must re-read the target and request under one `BEGIN IMMEDIATE` transaction.

**On approval:**

- Confirm the request has no terminal event.
- Confirm the target remains the current accepted leaf.
- Revalidate the proposed value against the target metric.
- Insert a new `measurement_observations` row.
- Set its `supersedes_observation_id` to the target ID and provide the request's correction reason.
- Use a new observation ID and a new UTC `recorded_at`.
- Keep the same flock, metric, reporting date, unit and original `observed_at`.
- Set `source_type = 'manual_entry'` because the proposed corrected value was manually supplied in this first-release workflow.
- Set `quality_status = 'observed'`.
- Preserve the requester identity, if known, in `entered_by_user_id`; do not invent it. Record the reviewer identity on the decision event, not as the submitting actor.
- Insert an `approved` request event that references the new observation.
- Invalidate other still-pending requests targeting the same observation, so they cannot later branch the accepted correction history.
- Commit the observation, approval event and sibling invalidation events atomically.

The correction observation's `observed_at` refers to the time of the measurement being corrected, not the time the reviewer approved it. The new `recorded_at` is the time the accepted correction was persisted.

**On rejection:**

- Insert a `rejected` request event with a required decision reason and UTC event time.
- Do not insert an observation.
- Do not change the target or current accepted value.
- Permit a later new request against the same target, subject to the target still being current.

**On invalidation:**

If another request has already produced an accepted successor for the same target, a pending sibling request is no longer eligible for approval. Insert an `invalidated` event explaining that the target was superseded before this request was decided. Do not insert an observation.

### 4.4 Multiple pending requests and concurrency

Multiple requests may be submitted against the same current observation. This preserves the history of separate proposals and allows one proposal to be rejected while another is considered.

Only one can be approved. The existing unique partial index on `supersedes_observation_id` is the final database guard against branching. The service must also serialise approval decisions with the existing Unit of Work's `BEGIN IMMEDIATE` transaction.

When one request is approved, all other undecided requests targeting that same observation are closed with `invalidated` events in the same transaction. If a conflict or database constraint still occurs, the whole transaction must roll back.

### 4.5 Proposed request state derivation

There is no mutable `status` column on a request.

| Request record | Terminal event | Derived state | Effect on observations |
|---|---|---|---|
| Exists | None | `pending` | None |
| Exists | `approved` | `approved` | New accepted correction exists |
| Exists | `rejected` | `rejected` | None |
| Exists | `invalidated` | `invalidated` | None |

The request row records the proposal. The event records the outcome. The status is a query result, not a mutable field.

## 5. Measurement quality-review workflow

### 5.1 Purpose and initial scope

Quality review handles a candidate observation whose row was initially persisted with `quality_status = 'pending_validation'`. It lets an authorised reviewer accept or reject that candidate without editing the original observation.

The first release supports only two terminal decisions:

- `accepted`: the candidate is approved for use as an accepted measurement;
- `rejected`: the candidate is not accepted and remains excluded from accepted-value analytics.

An observation already stored as `observed` does not need a quality-review event. An observation stored as `invalid` cannot be promoted to observed by this workflow. To correct an invalid raw value, create a new valid observation through a separately defined ingestion or correction path; retain the invalid source row.

### 5.2 Review submission

The service must:

1. Load the target observation inside a write transaction.
2. Confirm its raw `quality_status = 'pending_validation'`.
3. Confirm it has no prior terminal quality-review event.
4. Require a non-empty review reason.
5. Record the decision, reviewer identity (nullable until authentication) and UTC `reviewed_at`.
6. Commit an immutable review event only.

No observation fields are modified. A second terminal decision for the same observation is rejected. Reopening or reversing a final decision is outside the first release.

### 5.3 Effective quality status

The observation's stored `quality_status` remains the immutable ingestion-time value. A query may expose a separately named `effective_quality_status` derived as follows:

| Stored `quality_status` | Review event | Effective status | Eligible as accepted measurement? |
|---|---|---|---|
| `observed` | None | `observed` | Yes, unless superseded |
| `pending_validation` | None | `pending_validation` | No |
| `pending_validation` | `accepted` | `observed` | Yes, unless superseded |
| `pending_validation` | `rejected` | `invalid` | No |
| `invalid` | None | `invalid` | No |
| Absence status (`not_recorded`, `not_measured`, `not_applicable`, `device_unavailable`) | None | Same stored status | No numeric value |

The values in this table are query semantics, not updates to `measurement_observations.quality_status`. The event history remains available for audit.

### 5.4 Quality review and correction interaction

A pending candidate must be reviewed before it can become a correction target. Once accepted, its effective status is `observed` and it can be considered for correction, provided it is still the current accepted leaf and has an eligible source type.

A rejected candidate is effectively invalid and cannot be corrected through the first-release accepted-observation correction workflow. A replacement observation must be entered as a distinct observation with valid provenance, retaining the rejected candidate for audit.

## 6. Proposed logical data model

The following are logical schemas, not migration-ready SQL. Exact SQLite constraints, indexes, trigger definitions, column types and foreign-key declarations must be specified and tested in a later implementation PR.

### 6.1 `measurement_correction_requests`

| Field | Proposed type | Required | Purpose |
|---|---|---:|---|
| `request_id` | TEXT | Yes | UUID primary key |
| `target_observation_id` | TEXT | Yes | FK to the observation being corrected |
| `proposed_value_numeric` | REAL | Yes | Proposed finite replacement value; zero is valid |
| `correction_reason` | TEXT | Yes | Non-empty explanation |
| `requested_by_user_id` | TEXT | No | Authenticated requester when available; otherwise NULL |
| `requested_at` | TEXT | Yes | UTC request-submission timestamp |

The request does not duplicate flock, metric, date, unit, source or observation time. Those are inherited from the target observation and checked at approval.

Suggested indexes: `(target_observation_id, requested_at)` and `requested_at`. The target FK must use `ON DELETE RESTRICT` (or equivalent) so a request cannot silently outlive a deleted observation.

### 6.2 `measurement_correction_request_events`

| Field | Proposed type | Required | Purpose |
|---|---|---:|---|
| `event_id` | TEXT | Yes | UUID primary key |
| `request_id` | TEXT | Yes | FK to request |
| `outcome` | TEXT | Yes | `approved`, `rejected` or `invalidated` |
| `outcome_reason` | TEXT | Yes | Non-empty decision/invalidation explanation |
| `reviewed_by_user_id` | TEXT | No | Reviewer identity when authenticated |
| `event_at` | TEXT | Yes | UTC decision time |
| `created_observation_id` | TEXT | Conditional | Required for `approved`; NULL for other outcomes |

A unique constraint on `request_id` allows at most one terminal outcome per request in the first release. The event must reference the new observation on approval and no observation for rejected/invalidated outcomes. Foreign keys must protect request and accepted correction history from deletion.

Suggested index: `(request_id, event_at)`. Since the first release permits one terminal event per request, a unique `request_id` index is the primary lookup/consistency guard.

### 6.3 `measurement_quality_review_events`

| Field | Proposed type | Required | Purpose |
|---|---|---:|---|
| `event_id` | TEXT | Yes | UUID primary key |
| `observation_id` | TEXT | Yes | FK to candidate observation |
| `decision` | TEXT | Yes | `accepted` or `rejected` |
| `review_reason` | TEXT | Yes | Non-empty review justification |
| `reviewed_by_user_id` | TEXT | No | Reviewer identity when authenticated |
| `reviewed_at` | TEXT | Yes | UTC decision time |

A unique constraint on `observation_id` permits at most one terminal review decision in the first release. The service, not a cross-table CHECK, must ensure the target's raw `quality_status` is `pending_validation`.

Suggested index: `(observation_id, reviewed_at)`. The unique target index is the primary guard against repeated final decisions.

### 6.4 Append-only protections

All three proposed tables must be append-only:

- no repository `update` or `delete` methods;
- SQLite `BEFORE UPDATE` and `BEFORE DELETE` triggers;
- protection against `INSERT OR REPLACE` over an existing request or event identifier;
- no mutable request or review status columns;
- all correction/quality outcomes inserted as new event rows.

The exact trigger implementation and migration validators belong in the migration PR, not this design document.

## 7. Accepted-value and audit-query semantics

Queries must expose the difference between raw source history, review state and accepted operational values.

### 7.1 Request status

A request is pending when it has no terminal event. Otherwise the request's derived state is the terminal event's outcome. No request's proposed value is included in measurement analytics before an approved correction observation exists.

### 7.2 Effective quality status

The effective quality status is derived from the immutable observation and, when applicable, its single terminal quality-review event. The stored quality status is always returned separately to preserve the original ingestion result.

### 7.3 Current accepted observation

For one flock, metric and reporting date, a current accepted observation must:

1. Have raw `quality_status = 'observed'`, or raw `pending_validation` with an `accepted` quality-review event.
2. Not have an accepted successor referencing its `observation_id`.
3. Not be rejected or otherwise excluded by the quality-review derivation.
4. Match the requested flock, metric and date.

When several uncorrected observed entries exist for the same measurement/date, this design does not invent a precedence rule. Duplicate/conflict resolution remains an explicit product decision and must be addressed before a UI or analytics consumer relies on a single-value query.

### 7.4 Full audit history

The audit view returns:

- every original and accepted correction observation in the supersession chain;
- every correction request targeting each chain member;
- each request's terminal decision, if any;
- every quality-review event for the observation;
- raw and effective quality statuses;
- requester/reviewer identity where available;
- all UTC event and observation recording times;
- the correction or review reason.

Audit ordering should use event timestamps plus stable IDs. A correction's `observed_at` must not be used as the decision timestamp.

### 7.5 Rejected and pending requests do not reserve a correction edge

Only the approved correction observation populates `supersedes_observation_id`. Pending, rejected and invalidated request rows do not write to `measurement_observations` and do not consume the accepted-successor uniqueness constraint.

## 8. Transaction and consistency requirements

The existing `UnitOfWork` starts a `BEGIN IMMEDIATE` transaction and provides one connection to its repositories. All decisions that read a target and write an outcome must use that shared transaction.

**Correction submission:**

- Validate target and proposed candidate in a transaction.
- Insert request row.
- Commit without changing an observation.

**Correction approval:**

- Re-read request and target.
- Derive request state; refuse if already decided.
- Reconfirm target remains current and accepted.
- Validate candidate using the target metric's rules and unit.
- Insert the accepted correction observation.
- Insert approved event.
- Insert invalidation events for other pending requests targeting the same observation.
- Commit all writes atomically.

**Correction rejection:**

- Re-read request and ensure undecided.
- Insert rejected event.
- Commit. No observation insert.

**Quality review:**

- Re-read target and ensure raw status is pending and undecided.
- Insert one accepted/rejected review event.
- Commit. No observation update.

Any failure must roll back every write in the operation. Database unique indexes and FK constraints remain final guards in addition to service validation.

## 9. Authorisation and identity boundary

The current application is a local single-user MVP with no authentication, role management or farm membership model. The event schema reserves nullable user-ID fields but does not create secure reviewer identities.

Before multi-user deployment, define and test:

- who may request a correction;
- who may approve or reject a correction;
- whether a requester may approve their own request;
- who may accept or reject a pending observation;
- farm-level access isolation;
- whether an administrator may review records across farms;
- identity retention and audit access policy.

Until authentication and authorisation are implemented, the proposed workflow is an internal application design only. It must not be described as a secure independent-approver process. Service parameters supplied by a caller are not proof of identity or role.

## 10. Decisions and recommendations

| Decision | Recommended first-release rule | Reason / dependency |
|---|---|---|
| Which observations can be corrected? | Current accepted `manual_entry` observations only | Sensor/import/system correction requires source-specific provenance policy |
| What may a request change? | Numeric value only | Keeps flock, metric, unit and reporting date immutable |
| Can several requests target one observation? | Yes; only one may be approved; siblings are invalidated atomically | Retains proposals without allowing a correction branch |
| Can a rejected request be resubmitted? | Yes, as a new request if the target remains current | Prior request and rejection stay immutable |
| Can a decision be reopened? | No, not in the first release | Avoids mutable or ambiguous terminal states |
| Can a pending candidate be reviewed? | Yes, accept or reject once | Event creates an effective state without editing source row |
| Can an invalid candidate be accepted? | No | Invalid raw input must remain invalid; enter a distinct corrected observation |
| What happens to accepted review candidates? | Effective status becomes observed; raw status remains pending_validation | Preserves ingestion-time state and review history |
| Does approval rewrite daily_records? | No | Daily-record synchronisation is a separate design/work package |
| Does approval imply a reviewer is independent? | No, not until auth/roles enforce this | Current application has no identity boundary |
| Which timestamps are stored? | UTC request/event/recorded times; preserve target observed_at | Avoids confusing measurement time with review time |
| Are sensor and imported values correctable? | Deferred | Need explicit source ownership and correction provenance policy |

## 11. Explicit exclusions

This design does not authorise or implement:

- any new migration or change to the live SQLite database;
- direct observation updates or deletes;
- editing a daily record when a correction is approved;
- dual-write from `FarmService`;
- historical backfill;
- changes to existing analytics or dashboards;
- Streamlit correction/review UI;
- multi-user authentication, authorisation or role enforcement;
- correction of sensor, import or system-generated records;
- quality-review reopening, appeals or multiple decision rounds;
- a single-value precedence policy for unrelated same-day duplicate observations;
- changes to mortality's default-zero semantics.

Mortality zero, parent archive/deletion policy, and analytics cutover remain separate decisions. No existing `daily_records` zero or NULL value is reinterpreted here.

## 12. Proposed implementation sequence and release gates

| Order | Deliverable | Required exit gate |
|---|---|---|
| 0 | Review and approve this workflow design | Product decisions recorded; unresolved items explicitly deferred |
| 1 | Implement request and event schema on a feature branch | Migration tests on fresh and populated temporary copies; append-only and FK checks pass |
| 2 | Implement correction-request repository/service | Submission, rejection, approval, stale request invalidation and concurrency tests pass |
| 3 | Implement quality-review repository/service | Pending-only eligibility, single final decision and effective-status tests pass |
| 4 | Implement current-value and full audit queries | Approved-value parity, supersession chain and event-history tests pass |
| 5 | Security/identity gate | No multi-user reviewer claim until role checks and farm isolation exist |
| 6 | Documentation and review PR | Full CI green; review before merge |

Keep schema and service work separately reviewable. Do not combine this with daily-record dual-write, migration of the user's live database, backfill or analytics cutover.

## 13. Acceptance-test matrix for the implementation PR

### Correction request tests

- Request creation stores the proposed finite numeric value and non-empty reason.
- Metric-specific value validation uses the target's metric.
- A request against a non-existent, non-manual, superseded or non-accepted target is rejected.
- Request submission does not insert a measurement observation or change the current accepted value.
- Multiple requests can be recorded against one current target.
- Request status is pending until one terminal event exists.
- Rejected requests create no observation and do not reserve the supersession link.
- A rejected request does not prevent a new request if the target remains current.

### Correction approval tests

- Approval inserts a new observation and leaves the original row unchanged.
- New observation inherits target flock, metric, date, unit and observation time.
- New observation has a new ID and UTC recording timestamp.
- Correction reason is preserved and non-empty.
- Approval event references the new observation.
- Approval and observation insertion are atomic.
- A target that is already superseded cannot be approved again.
- Two concurrent approval attempts cannot create branches.
- Pending sibling requests are invalidated atomically when one request is approved.
- An already decided request cannot be decided again.
- Approval of a stale request inserts no observation.

### Quality-review tests

- Only a raw `pending_validation` observation can be reviewed.
- Observed, invalid and absence-status rows cannot enter this review path.
- Exactly one final decision can be recorded per candidate.
- Acceptance leaves the original row unchanged and derives effective status `observed`.
- Rejection leaves the original row unchanged and derives effective status `invalid`.
- Pending, rejected and invalid candidates remain excluded from accepted-value queries.
- A reviewed accepted candidate can later be corrected if it remains the current leaf.
- Review event insertion is append-only and cannot be replaced, edited or deleted.

### Query and audit tests

- Pending and rejected correction requests do not change the accepted measurement.
- An approved correction becomes current and its target is excluded from current-value results.
- Full audit history returns original observations, accepted corrections, request outcomes and review events.
- Raw quality status and derived effective quality status are both visible.
- Stable ordering is deterministic for equal timestamps.
- Same-day unrelated duplicate observations are not silently collapsed into a single winner.

### Regression and safety tests

- Existing 171-test baseline remains green, with new tests added.
- Ruff lint and formatting pass.
- All schema tests use temporary databases.
- No test opens or writes to `data/poultryguard.db`.
- No existing farm, flock or daily-record row is updated or deleted by this feature.
- No migration command is invoked automatically at application startup.

## 14. Implementation approval boundary

This document is a design proposal only. It does not authorise runtime code, a schema migration, a local backup, a live database migration, a backfill, a UI change or a daily-record integration.

The next implementation branch may be created only after the workflow model and first-release decisions are reviewed. Any eventual migration must be tested against empty and populated temporary databases. Any operation against the user's actual local database remains a separate step requiring a populated-copy rehearsal, verified backup/restore plan and explicit approval.

---

*End of proposed design.*
