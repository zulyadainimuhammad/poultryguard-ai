# PoultryGuard AI — Measurement Correction Requests and Quality Review Design

**Status:** Workflow decisions reviewed; implementation remains a separate feature-branch change<br>
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

This design deliberately starts with a narrow manual-entry workflow. Sensor, import and system-generated correction policies; authentication and role enforcement; reopening decisions; linked daily-record synchronisation; dual-write; analytics cutover; and backfill remain separate work packages.

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

Do not infer an observation timestamp, reviewer identity, request author or source from unrelated fields. Requester and reviewer IDs remain NULL until authenticated identity and authorisation are implemented. The initial local workflow records an operator-entered decision only; it is not secure independent approval. A correction approval timestamp is not the original measurement time.

## 4. Correction request workflow

### 4.1 First-release scope

The initial correction workflow should support a **value-only correction** of an eligible manual-entry observation, targeted by its exact `observation_id`.

A request proposes a replacement numeric value and requires a non-empty reason. It inherits the target's:

- `flock_id`;
- `record_date`;
- `metric_name`;
- canonical `unit`;
- `observed_at` (which may remain NULL).

The requester cannot change the flock, metric, reporting date or unit through a correction request. This prevents a correction from silently becoming a different measurement.

Correction eligibility is limited to a current accepted `manual_entry` observation. This includes an observation originally stored as `pending_validation` once its quality-review event accepts it, provided it has no accepted successor. Corrections to sensor, imported or system-generated observations need source-specific policy and provenance handling and are deferred.

Multiple independent observations may share the same flock, metric and reporting date. They remain separate records. A request must name the exact observation ID; the service must never select a target by flock/metric/date or infer a winner among duplicates.

### 4.2 Request submission

At submission, the service must:

1. Validate the exact target observation ID and parse the proposed number as finite.
2. Load the target observation inside a `BEGIN IMMEDIATE` Unit-of-Work transaction.
3. Confirm the target exists, has `source_type = 'manual_entry'`, has effective accepted status (`observed`, either raw or accepted by review), and has no accepted successor.
4. Validate the proposed value using the target metric's canonical validation rules.
6. Reject a proposed value exactly equal to the target's existing numeric value: a no-op is not a correction.
7. Require a non-empty correction reason and required request ID/timestamp fields.
8. Create one immutable request with a generated UUID and UTC `requested_at`.
9. Commit without inserting a new observation and without changing the current accepted value.

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
- Invalidate all other still-pending requests targeting this exact observation, so they cannot later branch the accepted correction history.
- Commit the observation, approval event and sibling invalidation events atomically.

The correction observation's `observed_at` refers to the time of the measurement being corrected, not the time the reviewer approved it. The new `recorded_at` is the time the accepted correction was persisted.

**On rejection:**

- Insert a `rejected` request event with a required decision reason and UTC event time.
- Do not insert an observation.
- Do not change the target or current accepted value.
- Permit a later new request against the same target, subject to the target still being current.

A rejection is terminal for that request only. It does not reserve the target or supersession edge and does not prevent a new request against the same still-eligible observation.

**On invalidation:**

If a request remains pending but its exact target has become stale (for example, an accepted successor exists), insert an `invalidated` event explaining why it is no longer eligible. Do not insert an observation. A decision attempt against a request that already has any terminal event is rejected as already decided and creates no additional event.

### 4.4 Multiple pending requests and concurrency

Multiple requests may be submitted against the same current observation. This preserves the history of separate proposals and allows one proposal to be rejected while another is considered.

Only one request can be approved for a given exact target. The existing unique partial index on `supersedes_observation_id` is the final database guard against branching. The service must also serialise approval decisions with the existing Unit of Work's `BEGIN IMMEDIATE` transaction. The first successful approval transaction wins.

When one request is approved, all other pending requests targeting that same observation are closed with `invalidated` events in the same transaction as the correction observation and approval event. A later attempt against one of those requests is rejected as already decided. If a request is still pending but its target is independently found stale, the attempt records an invalidation and no observation. If a conflict or database constraint still occurs, the whole approval transaction must roll back.

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

Quality review handles a candidate observation whose row was initially persisted with `quality_status = 'pending_validation'`. It lets the local operator record an accept/reject decision without editing the candidate observation. This local workflow is not secure independent approval.

The first release supports only two terminal decisions:

- `accepted`: the candidate is approved for use as an accepted measurement;
- `rejected`: the candidate is not accepted and remains excluded from accepted-value analytics.

An observation already stored as `observed` does not need a quality-review event. An observation stored as `invalid` cannot be promoted to observed by this workflow. To correct an invalid raw value, create a new valid observation through a separately defined ingestion or correction path; retain the invalid source row.

### 5.2 Review submission

The service must:

1. Load the target observation inside a write transaction.
2. Confirm its raw `quality_status = 'pending_validation'`.
3. Confirm it has no prior terminal quality-review event.
4. Require a non-empty review reason, event ID and UTC timestamp.
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

The current production `MeasurementObservationService` intentionally writes only observed manual-entry values. Do not expand it solely to create review-test candidates. Quality-review unit/integration tests may insert a valid `pending_validation` row directly through temporary database fixtures. A future ingestion/validation path (for example, a separately designed import or sensor intake service) may create production candidates when its provenance and validation contract is defined.

A rejected candidate is effectively invalid and cannot be corrected through the first-release accepted-observation correction workflow. A replacement observation must be entered as a distinct observation with valid provenance, retaining the rejected candidate for audit.

## 6. Proposed logical data model

The following are logical schemas, not migration-ready SQL. Stage 3.2.5A must translate these rules into explicit SQLite DDL, triggers, indexes and migration validators and test them on temporary databases only.

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

A unique constraint on `request_id` allows at most one terminal outcome per request in the first release. An approved event must reference a newly created observation that supersedes the exact target recorded by the request. Rejected and invalidated events must have `created_observation_id IS NULL`. Foreign keys must protect the request, target and accepted correction history from deletion.

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

A unique constraint on `observation_id` permits at most one terminal review decision in the first release. The service, not a simple cross-table CHECK, must ensure the target's raw `quality_status` is `pending_validation`.

Suggested index: `(observation_id, reviewed_at)`. The unique target index is the primary guard against repeated final decisions.

### 6.4 Append-only protections

All three proposed tables must be append-only:

- no repository `update` or `delete` methods;
- SQLite `BEFORE UPDATE` and `BEFORE DELETE` triggers;
- protection against `INSERT OR REPLACE` over an existing request or event identifier;
- no mutable request or review status columns;
- all correction/quality outcomes inserted as new event rows.

The exact trigger implementation and migration validators belong in the migration PR, not this design document.

### 6.5 Required migration consistency rules

The migration must enforce and validate the following, using CHECK/UNIQUE constraints, foreign keys and triggers as appropriate:

- `ON DELETE RESTRICT` foreign keys from correction requests to their exact target observations, correction events to requests and any created observation, and quality-review events to observations.
- Exactly one terminal correction event per request and exactly one terminal quality-review event per observation. Multiple correction requests per target remain allowed.
- No more than one accepted successor per target observation (the existing partial unique observation index remains the final guard).
- An approved event references a correction observation whose `supersedes_observation_id` equals the target observation ID on that event's request. A robust schema-level implementation may use a trigger or an equivalent composite-key relation; the service must also validate this inside the transaction.
- `created_observation_id` is non-NULL only for `approved`, and is NULL for `rejected` or `invalidated`.
- Valid outcome/decision enumerations; non-empty request, event, observation and actor-independent reason identifiers/text; required UTC timestamp values; finite numeric proposed values; and metric-specific proposed-value checks against the target metric.
- Append-only `BEFORE UPDATE` and `BEFORE DELETE` protection and `INSERT OR REPLACE` protection for every new table.

Simple foreign keys and UNIQUE constraints cannot by themselves ensure that a request targets an eligible current observation or that a candidate has raw `pending_validation` status. Enforce these cross-table state rules in the service under `BEGIN IMMEDIATE`, and test them as transactional invariants. The schema must not add uniqueness on `(flock_id, metric_name, record_date)` or otherwise collapse independent observations.

## 7. Accepted-value and audit-query semantics

Queries must expose the difference between raw source history, review state and accepted operational values.

### 7.1 Request status

A request is pending when it has no terminal event. Otherwise the request's derived state is the terminal event's outcome. No request's proposed value is included in measurement analytics before an approved correction observation exists.

### 7.2 Effective quality status

The effective quality status is derived from the immutable observation and, when applicable, its single terminal quality-review event. The stored quality status is always returned separately to preserve the original ingestion result.

### 7.3 Current accepted observation

For an exact observation ID, eligibility is evaluated independently of other observations sharing its flock, metric and reporting date. An accepted-observation query for a flock/metric/date must return **all eligible leaves**. It must never select one by timestamp, insertion order, or another implicit precedence rule. If a caller requires a single result and receives multiple eligible leaves, return an explicit ambiguity result.

An eligible current accepted observation must:

1. Have raw `quality_status = 'observed'`, or raw `pending_validation` with an `accepted` quality-review event.
2. Not have an accepted successor referencing its `observation_id`.
3. Not be rejected or otherwise excluded by the quality-review derivation.
4. Match the requested flock, metric and date.

When several eligible observations exist for the same flock, metric and date, all remain visible as independent leaves. The query layer returns them all; a single-value caller gets an explicit ambiguity result.

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
- Derive request state; reject without another event if already decided.
- Reconfirm target remains current and accepted.
- Validate candidate using the target metric's rules and unit.
- Insert the accepted correction observation.
- Insert approved event.
- Insert invalidation events for all other pending requests targeting the exact same observation.
- Commit all writes atomically.

**Correction rejection:**

- Re-read request and ensure undecided.
- Insert rejected event.
- Commit. No observation insert.
- A later request against the same target remains allowed while the target is eligible.

**Stale request decision:**

- If the request is still pending but its target is no longer eligible, insert one `invalidated` event with a reason.
- Do not insert an observation.
- If the request already has a terminal event, reject the attempt without inserting any further event.

**Quality review:**

- Re-read target and ensure raw status is pending and undecided.
- Insert one accepted/rejected review event.
- Commit. No observation update.

Any failure must roll back every write in the operation. Database unique indexes and FK constraints remain final guards in addition to service validation.

## 9. Authorisation and identity boundary

The current application is a local single-user MVP with no authentication, role management or farm membership model. Requester/reviewer IDs remain nullable until those capabilities exist. The initial implementation records an operator-entered decision only and must not be represented as secure independent approval. A caller-provided actor ID is not proof of identity or role.

When authentication is added, derive the actor from the authenticated session/principal rather than accepting an arbitrary identity string from the UI. A separate authorization policy must check farm access and permitted actions on every request/review. Store stable authenticated principal IDs in `requested_by_user_id` and `reviewed_by_user_id`. Decide and enforce self-approval policy before describing any workflow as independent review.

Before multi-user deployment, define and test:

- who may request a correction;
- who may approve or reject a correction;
- whether a requester may approve their own request;
- who may accept or reject a pending observation;
- farm-level access isolation;
- whether an administrator may review records across farms;
- identity retention and audit access policy.

Until authentication and authorisation are implemented, the workflow is an operator-recorded local decision process only. It must not be described as a secure independent-approver process. Service parameters supplied by a caller are not proof of identity or role.

## 10. Decisions and recommendations

| Decision | Recommended first-release rule | Reason / dependency |
|---|---|---|
| Which observations can be corrected? | Current accepted `manual_entry` observations only | Sensor/import/system correction requires source-specific provenance policy |
| How is a target identified? | Exact `observation_id` | Same-date observations remain independent |
| How are duplicate leaves queried? | Return every eligible leaf; explicit ambiguity for single-result callers | No timestamp or insertion-order winner |
| Can an accepted quality-review candidate be corrected? | Yes, if its source is `manual_entry` and it has no accepted successor | Eligibility is based on effective accepted status and exact target |
| What may a request change? | Numeric value only | Keeps flock, metric, unit and reporting date immutable |
| Can a no-op correction be requested? | No, exact equality with the target value is rejected | A separate measurement is not a correction |
| Can several requests target one observation? | Yes; only one may be approved; siblings are invalidated atomically | Retains proposals without allowing a correction branch |
| Can a rejected request be resubmitted? | Yes, as a new request if the target remains current | Prior request and rejection stay immutable |
| Can a decision be reopened? | No, not in the first release | Avoids mutable or ambiguous terminal states |
| Can a pending candidate be reviewed? | Yes, accept or reject once | Event creates an effective state without editing source row |
| Can an invalid candidate be accepted? | No | Invalid raw input must remain invalid; enter a distinct corrected observation |
| What happens to accepted review candidates? | Effective status becomes observed; raw status remains pending_validation | Preserves ingestion-time state and review history |
| Does approval rewrite daily_records? | No | Daily-record synchronisation is a separate design/work package |
| Does approval imply a reviewer is independent? | No, not until auth/roles enforce this | Current application has no identity boundary |
| How are pending quality candidates tested before an intake writer exists? | Seed valid candidates in temporary database test fixtures | Do not widen the production manual-entry service for tests |
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

| Stage | Deliverable | Required exit gate |
|---|---|---|
| 3.2.5A | Add request/event schema and migration validators on a feature branch | Constraints, exact-target linkage, uniqueness, append-only triggers and `ON DELETE RESTRICT` foreign keys validated on fresh and populated temporary databases |
| 3.2.5B | Implement correction request/decision repository and service | Exact-ID targeting; no-op rejection; rejection/re-request; atomic approval and sibling invalidation; stale-request handling; concurrency tests |
| 3.2.5C | Implement quality-review repository/service and effective-status derivation | Pending-only review and terminal-decision tests; use temporary DB fixtures for candidates, without widening the production manual-entry writer |
| 3.2.5D | Implement accepted-leaf and audit queries | Return every eligible leaf; explicit ambiguity for single-result callers; exact supersession and event-history coverage |
| Release gate | Documentation and review PR | Full CI green; reviewer/identity limitations documented; no live DB operation, dual-write, backfill or analytics cutover included |

Keep these increments separately reviewable. No runtime work in this sequence authorises migration of the user's live database. Do not combine this with daily-record dual-write, backfill or analytics cutover. Authentication and authorisation remain a prerequisite for any secure multi-user or independent-review claim.

## 13. Acceptance-test matrix for the implementation PR

### Correction request tests

- Request creation stores the proposed finite numeric value and non-empty reason.
- Non-empty request IDs/reasons and required UTC timestamps are enforced; invalid timestamps and non-finite values are rejected.
- Metric-specific value validation uses the exact target's metric and rejects an exactly equal proposed value.
- A request against a non-existent, non-manual, superseded or non-accepted target is rejected.
- A reviewed-and-accepted `pending_validation` manual-entry observation is request-eligible if it has no accepted successor; other sources remain ineligible.
- Request submission does not insert a measurement observation or change the current accepted value.
- Multiple requests can be recorded against one exact current target, and independent same-date observations remain independent.
- Request status is pending until one terminal event exists.
- Rejected requests create exactly one immutable event, no observation, and do not reserve the supersession link.
- A rejected request does not prevent a new request if the target remains current.

### Correction approval tests

- Approval inserts a new observation and leaves the original row unchanged.
- New observation inherits target flock, metric, date, unit and observation time.
- New observation has a new ID and UTC recording timestamp.
- Correction reason is preserved and non-empty.
- Approval event references the new observation.
- Database consistency rejects an approved event unless its created observation supersedes the exact target recorded by the request.
- Rejected and invalidated events must have no `created_observation_id`; every request has at most one terminal event.
- Approval and observation insertion are atomic.
- A target that is already superseded cannot be approved again.
- Concurrent approvals against requests for the same exact target have one winner; the winning observation, approval event and sibling invalidation events commit atomically.
- Pending sibling requests are invalidated atomically when one request is approved; a later decision attempt against an invalidated request is rejected without another event.
- A still-pending request with an unexpectedly stale target records one invalidation event and inserts no observation.
- An already decided request cannot be decided again or receive another event.
- Multiple independent observations on one flock/metric/date can each be targeted and corrected without cross-target effects.

### Quality-review tests

- Only a raw `pending_validation` observation can be reviewed.
- Observed, invalid and absence-status rows cannot enter this review path.
- Exactly one final decision can be recorded per candidate.
- Acceptance leaves the original row unchanged and derives effective status `observed`.
- Rejection leaves the original row unchanged and derives effective status `invalid`.
- Pending, rejected and invalid candidates remain excluded from accepted-value queries.
- A reviewed accepted candidate can later be corrected if it remains the current leaf.
- Review event insertion is append-only and cannot be replaced, edited or deleted; every candidate has at most one terminal review event.
- Pending candidates are seeded only in temporary test fixtures until an ingestion/validation writer is separately designed.

### Query and audit tests

- Pending and rejected correction requests do not change the accepted measurement.
- An approved correction becomes current and its target is excluded from current-value results.
- Full audit history returns original observations, accepted corrections, request outcomes and review events.
- Raw quality status and derived effective quality status are both visible.
- Stable ordering is deterministic for equal timestamps.
- Same-day independent observations are all returned as eligible leaves; no winner is selected by timestamp or insertion order.
- A caller requiring one result receives explicit ambiguity when multiple eligible leaves are returned.
- A quality-reviewed manual candidate is included only when accepted and not superseded; rejected and pending candidates are excluded.
- Request, event, target and review foreign keys use `ON DELETE RESTRICT` and reject parent deletion.
- Every new table rejects UPDATE, DELETE and `INSERT OR REPLACE`; multiple requests per target remain allowed while each request/event uniqueness rule holds.

### Regression and safety tests

- Existing regression suite remains green, with new workflow tests added.
- Ruff lint and formatting pass.
- All schema tests use temporary databases.
- No test opens or writes to `data/poultryguard.db`.
- No existing farm, flock or daily-record row is updated or deleted by this feature.
- No migration command is invoked automatically at application startup.

## 14. Implementation approval boundary

This document records reviewed workflow decisions and implementation requirements. It does not itself authorise runtime code, a schema migration, a local backup, a live database migration, a backfill, a UI change or a daily-record integration.

Implementation must proceed through the Stage 3.2.5A–3.2.5D feature-branch increments above. Any migration must be tested against empty and populated temporary databases. Any operation against the user's actual local database remains a separate step requiring a populated-copy rehearsal, verified backup/restore plan and explicit approval.

---

*End of proposed design.*
