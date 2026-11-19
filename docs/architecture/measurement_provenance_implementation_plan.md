# PoultryGuard AI — Stage 3.2.3 Measurement Provenance Implementation Plan

**Document status:** Proposed implementation plan — planning milestone only  
**Stage:** 3.2.3  
**Depends on:** Stage 3.2.2 — Measurement Provenance and Data Semantics  
**Source architecture specification:** `docs/architecture/measurement_provenance.md`  
**Target repository:** `zulyadainimuhammad/poultryguard-ai`  
**Date:** 18 November 2026

---

## 1. Purpose

Stage 3.2.2 approved the measurement provenance and data semantics contract. Stage 3.2.3 turns that contract into an implementation-ready engineering plan before any application code or SQLite data is changed.

The implementation must add a traceable observation layer while preserving the existing `farms`, `flocks` and `daily_records` data and the behaviour of the current Streamlit MVP.

**This document does not implement the schema, migrations, services, UI or runtime behaviour.** It is a technical plan and a review gate. Implementation should begin only after the repository structure, existing transaction behaviour and local database have been inspected.

## 2. Desired outcome

At the end of the planned implementation sequence, PoultryGuard AI should be able to:

1. Represent one measurement as one traceable observation.
2. Record the metric, value, unit, flock, farm reporting date, source and recording timestamp.
3. Preserve the distinction between a genuine numeric zero and a missing value.
4. Keep observation time (`observed_at`) distinct from platform recording time (`recorded_at`).
5. Link observations to their originating daily record where applicable.
6. Preserve corrections as new observations rather than overwriting historical values.
7. Query the latest accepted value and retrieve the complete observation history.
8. Migrate historical data without deleting or rewriting existing daily records.
9. Keep current Farm Intelligence and Environmental Monitoring screens working until a later, separately tested analytics integration.

## 3. Scope boundaries

### 3.1 In scope for the first implementation increment

- A versioned, additive SQLite migration.
- A new `measurement_observations` table and supporting indexes/constraints.
- A repository for creating and querying immutable observations.
- Service-layer validation and UTC timestamp generation.
- Manual-entry provenance for values originating in the existing daily-record workflow.
- A controlled, idempotent backfill of eligible existing `daily_records` values.
- Transaction-safe observation creation when daily records are created or edited, after the current write paths have been inspected.
- Append-only correction support for accepted measurements.
- Unit, integration, migration, data-preservation and regression tests.
- Documentation of implementation decisions and limitations.

### 3.2 Explicitly out of scope for the first implementation increment

- IoT device connectivity, sensor protocols or live sensor ingestion.
- File/CSV import workflows.
- Authentication, user accounts or farm-level authorisation.
- Device registry and calibration management.
- New biological thresholds, warning rules or predictive models.
- Replacing `daily_records` as the existing dashboard/analytics source.
- PostgreSQL migration or cloud deployment.
- A full review/approval UI for pending observations.

The provenance contract may reserve fields for future sources, but only the manual-entry path should be enabled in the first release.

## 4. Verified baseline from Stage 3.2.2

The approved architecture specification records the following current state:

- The application is a local Streamlit MVP backed by SQLite.
- The existing tables are `farms`, `flocks` and `daily_records`.
- `daily_records` contains `flock_id`, `record_date`, `feed_kg`, `water_litres`, `mortality`, `average_weight_kg`, `temperature_c`, `humidity_percent`, `notes` and `created_at`.
- Optional numeric fields use `NULL` when not entered. The analytics layer excludes `None` from averages and preserves real zero values.
- `mortality` is required and defaults to zero.
- `created_at` is the database insertion time; it is not the time a measurement was observed.
- There is currently no observation table, provenance metadata, authenticated user identity, sensor ingestion or correction history.
- Daily records are retrieved in `record_date, id` order for the existing analytics.

Before implementation, Amazon Q or the developer must confirm these facts against the current `main` branch rather than assume the source files have not changed since Stage 3.2.2.

## 5. Recommended architecture

### 5.1 Retain the two-layer model

**Layer 1 — `daily_records` (existing):** Keep this as the daily operational summary and the existing farmer-facing input model. Do not rename, drop or repurpose it in this milestone.

**Layer 2 — `measurement_observations` (new):** Add a granular table in which each row represents one metric observation. One daily record can therefore be associated with multiple observation rows, one per metric.

The first implementation should dual-write from the daily-record workflow into the observation layer, but it should not switch existing analytics to the new layer. This isolates schema and data-capture work from analytics behaviour changes.

### 5.2 Relationship to farm and flock

Store `flock_id` as the primary ownership relationship. Derive `farm_id` through the existing `flocks.farm_id` relationship when building response objects or reports. This avoids storing two independently mutable ownership references in the new table. The service must verify the flock exists before accepting an observation.

Add a nullable `daily_record_id` reference so observations created from the existing daily-record workflow can be traced to their parent record. Sensor/import observations in later stages may have no `daily_record_id`.

The exact foreign-key delete policy must be checked against existing farm/flock deletion behaviour. Do not use cascading deletion for observation history. Prefer `RESTRICT`/`NO ACTION` or an explicit archive/soft-delete workflow so deleting a parent cannot silently destroy the audit trail.

### 5.3 Source support

The schema may recognise the four approved source types:

- `manual_entry`
- `file_import`
- `sensor_device`
- `system_generated`

Only `manual_entry` creation is enabled in this increment. Do not create fake import, sensor or calculation provenance merely to populate nullable columns.

### 5.4 Time semantics

- `record_date` remains the farm's local reporting date (`YYYY-MM-DD`).
- `observed_at` is optional for manual observations. Keep it `NULL` where the actual time was not supplied; do not infer it from `record_date` or `created_at`.
- `recorded_at` is mandatory and assigned by the application at the time the observation is persisted.
- Store machine timestamps as timezone-aware UTC ISO 8601 values, preferably normalised to a `Z` suffix.
- Use `Africa/Lagos` as the farm timezone default for Nigeria, including Kano, when local-time conversion is required. Do not store a fixed `+01:00` offset as a substitute for the IANA timezone name.

### 5.5 Immutability and corrections

Treat observation rows as append-only. Do not provide general-purpose update/delete methods in the observation repository.

A correction inserts a new observation with:

- a new `observation_id`;
- the same flock, metric and reporting period as the observation being corrected;
- `supersedes_observation_id` pointing to the currently accepted observation;
- a non-empty `correction_reason`;
- its own provenance and `recorded_at`;
- `quality_status = "observed"` when accepted.

A row is superseded by relationship, not by changing its status. A correction must not overwrite or delete the original row. Only an accepted correction supersedes the referenced observation. Enforce a linear correction chain (each observation can be superseded at most once) unless a future design explicitly supports branching.

### 5.6 Quality-status handling

Persist the seven approved values from Stage 3.2.2:

`observed`, `not_recorded`, `not_measured`, `not_applicable`, `device_unavailable`, `invalid`, `pending_validation`.

Use `observed` for ordinary validated manual values. For statuses representing absence (`not_recorded`, `not_measured`, `not_applicable`, `device_unavailable`), the numeric value must be `NULL`. For `invalid` and `pending_validation`, preserve the received candidate value where one exists; do not use it as an accepted analytics value.

**Important dependency:** the observation row is immutable, but a review workflow may later need to move a candidate from `pending_validation` to `observed` or `invalid`. Do not mutate the original row to achieve that. Before implementing status transitions, design an append-only quality-review/event record (or an equivalent versioned status history). The first increment should not expose a review UI or claim to support review transitions.

## 6. Proposed logical data model

The following is a logical design to guide implementation. It is not production-ready SQL and must be reconciled with the repository's existing SQLite conventions before migration code is written.

### 6.1 `measurement_observations`

| Field | Proposed type | Required | Purpose |
|---|---|---:|---|
| `observation_id` | TEXT | Yes | UUID string for a new observation; deterministic ID for legacy backfill rows |
| `flock_id` | INTEGER | Yes | FK to `flocks.id`; parent ownership context |
| `daily_record_id` | INTEGER | No | FK to `daily_records.id` for observations originating from a daily record |
| `record_date` | TEXT | Yes | Farm-local reporting date, `YYYY-MM-DD` |
| `metric_name` | TEXT | Yes | One of the six current daily-record metrics |
| `value_numeric` | REAL | Conditional | Numeric measurement; preserve `0.0` |
| `unit` | TEXT | Yes | Canonical unit for the metric |
| `observed_at` | TEXT | No | Actual observation timestamp; nullable when unknown |
| `recorded_at` | TEXT | Yes | Application-assigned UTC timestamp |
| `source_type` | TEXT | Yes | One of the four approved source types; first release writes `manual_entry` only |
| `entered_by_user_id` | TEXT | No | Nullable until authentication exists |
| `device_id` | TEXT | No | Future sensor provenance |
| `import_batch_id` | TEXT | No | Future file-import provenance |
| `source_reference` | TEXT | No | External source reference where applicable |
| `calibration_reference` | TEXT | No | Future calibration record reference |
| `calculation_method` | TEXT | No | Future calculation provenance |
| `calculation_version` | TEXT | No | Future reproducibility metadata |
| `quality_status` | TEXT | Yes | One of the seven approved statuses |
| `supersedes_observation_id` | TEXT | No | Self-reference to the observation corrected by this row |
| `correction_reason` | TEXT | No | Required for a correction; null for original observation |
| `notes` | TEXT | No | Optional measurement note |

**Normalisation note:** do not store `farm_id` redundantly in this first table; obtain it by joining `flocks`. If a future high-volume reporting requirement justifies denormalisation, add it with a documented consistency rule.

**Source input list note:** `source_observation_ids` is an array in the architecture examples. Do not store an unvalidated comma-separated string. When system-generated observations are implemented, decide between a child link table (recommended for referential integrity) and validated JSON text. This field is not needed for manual-entry-only writes.

### 6.2 Metric and unit mapping

| `metric_name` | Daily-record source field | Canonical unit | Value validation to preserve |
|---|---|---|---|
| `mortality` | `mortality` | `birds` | Integer, >= 0; retain existing remaining-population validation at service layer |
| `feed_kg` | `feed_kg` | `kg` | >= 0 when supplied |
| `water_litres` | `water_litres` | `litres` | >= 0 when supplied |
| `average_weight_kg` | `average_weight_kg` | `kg_per_bird` | > 0 when supplied; existing suspicious-value warning remains a warning |
| `temperature_c` | `temperature_c` | `degrees_celsius` | Preserve current rule: no new domain/schema limit; current UI range is a UI guard only |
| `humidity_percent` | `humidity_percent` | `percent_relative_humidity` | 0–100, preserving existing service and database validation |

The service layer must own metric-to-unit mapping. Callers should not be able to pair `temperature_c` with `litres`, for example.

### 6.3 Recommended indexes and constraints

Subject to confirmation against the installed SQLite version and project conventions:

- Primary key on `observation_id`.
- Foreign keys to `flocks`, optional `daily_records`, and optional self-reference for correction.
- `CHECK` constraint for the approved `metric_name` values.
- `CHECK` constraint for the approved `source_type` values.
- `CHECK` constraint for the seven `quality_status` values.
- A value/status constraint: absence statuses require `value_numeric IS NULL`; `observed`, `invalid` and `pending_validation` require a candidate value.
- A correction constraint: if `supersedes_observation_id` is non-null, `correction_reason` must be non-empty and the new row must be accepted (`observed`).
- Unique index on `supersedes_observation_id` where non-null, to prevent two corrections from independently superseding the same observation.
- Index for `(flock_id, metric_name, record_date)`.
- Index for `(flock_id, metric_name, observed_at)` for time-series queries.
- Index for `daily_record_id`.

Do not rely on SQLite `CHECK` constraints alone for business rules such as same-flock/same-metric correction links; validate these in the service and test them.

## 7. Migration and data-preservation strategy

### 7.1 Mandatory preflight

Before writing the migration:

1. Confirm the current branch is `main` and the working tree is clean.
2. Inspect the actual database connection and schema initialisation code.
3. Confirm how SQLite connections enable `PRAGMA foreign_keys`.
4. Inspect transaction boundaries in daily-record create, edit and delete operations.
5. Inspect whether farms/flocks/daily records can be deleted and how the UI handles that.
6. Locate the configured database path without printing or sharing sensitive data.
7. Create a consistent backup using SQLite's backup API (preferred) or a documented stopped-app copy.
8. Record baseline row counts for `farms`, `flocks` and `daily_records` and run the current test suite.

Never use `DROP TABLE`, database reset, fixture initialisation or destructive re-creation against the user's working `data/poultryguard.db`.

### 7.2 Versioned migration runner

The Stage 3.2.2 architecture notes that the project does not yet have a formal migration framework. Add a small, explicit schema migration mechanism before introducing the new table.

Recommended characteristics:

- A migration ledger table recording applied migration version, name and timestamp.
- Ordered, immutable migration files/scripts.
- Each migration runs in a transaction where SQLite permits it.
- Foreign-key enforcement is enabled for every application connection and verified in tests.
- Migration application is idempotent: a previously applied version is not applied twice.
- After migration, run `PRAGMA foreign_key_check` and verify expected schema objects.
- A migration must fail loudly and roll back if any step fails.

The migration runner should be deliberately small; avoid introducing a heavyweight ORM or migration dependency solely for this increment unless the existing codebase has already adopted one.

### 7.3 Legacy backfill policy

Backfill is additive. It must not update or delete the existing `daily_records` rows.

Recommended conversion for each historical daily record:

- Create an observation for each non-null optional value (`feed_kg`, `water_litres`, `average_weight_kg`, `temperature_c`, `humidity_percent`).
- Consider `mortality` separately because it is non-null and defaults to zero. Confirm whether a stored default zero is a value the operator explicitly reported or merely an application default before treating every historical zero as an observed zero.
- Set `flock_id`, `daily_record_id`, `record_date`, metric and canonical unit from the source record.
- Set `source_type = "manual_entry"` only after confirming the historical daily-record workflow was manual.
- Set `observed_at = NULL`; historical observation time is unknown.
- Populate `recorded_at` from the legacy `created_at` value only as an approximation of row creation time. Preserve in documentation that it is not observation time. Parse and normalise the known SQLite timestamp representation as UTC only after confirming how the existing database produced it.
- Set `entered_by_user_id = NULL`, since the current app has no authenticated user identity.
- Set `quality_status = "observed"` for accepted, non-null historical values.
- Set `source_reference` to a traceable reference such as `legacy:daily_records:<id>` if helpful for auditability.
- Use a deterministic observation ID derived from `daily_record_id` and `metric_name` so a backfill can be safely re-run without duplicates.

Do not manufacture precise `observed_at` values from `record_date` or `created_at`. Do not silently convert nulls to zero. Do not invent reasons for historical missing values. Whether to create explicit `not_recorded` rows for historical nulls is a separate decision; the safe default is to omit them until the intended coverage denominator is agreed.

### 7.4 Backfill rehearsal and release gate

Run the migration and backfill against a fresh copy of the real SQLite database first. Compare:

- source daily-record count before and after;
- farms and flocks counts before and after;
- number of expected observation rows by metric;
- zero values retained as zero;
- optional nulls remain absent rather than coerced;
- all observation foreign keys valid;
- deterministic IDs prevent duplicate rows on repeated backfill invocation;
- every backfilled observation links to the correct daily-record row and flock.

Only after this rehearsal is clean should the migration be considered for the live local database. Preserve the pre-migration backup until the new version has been exercised successfully.

## 8. Repository and service implementation sequence

The exact target file paths must be confirmed against the current repository. Likely areas identified in Stage 3.2.2 include `app/database/connection.py`, `app/database/models.py`, the daily-record repository, `FarmService` and the existing analytics service.

### Phase A — Database foundation

- Add the migration ledger/runner.
- Add the additive migration for `measurement_observations` and its indexes/constraints.
- Add a typed observation model/dataclass consistent with existing models.
- Add migration tests for empty and populated database copies.
- Do not change any Streamlit page yet.

### Phase B — Repository and validation service

- Add `MeasurementObservationRepository` (or follow the existing repository naming pattern).
- Implement insert-only persistence, retrieval by flock/metric/date, current accepted observation lookup, and full audit-history lookup.
- Do not add generic update/delete methods.
- Add `MeasurementObservationService` or extend the existing service layer using project conventions.
- Validate metric names, units, numeric type, metric-specific constraints, source-specific required fields, quality-status/value compatibility, timestamps and correction links.
- Generate `observation_id` and `recorded_at` in the service layer, not in the Streamlit page.
- In the first release, accept `manual_entry` writes only. Keep other source categories reserved and not externally callable.

### Phase C — Daily-record integration

- Inspect create and edit flows before changing them.
- When a daily record is created, write its corresponding observation rows in the same database transaction.
- When a daily record is edited, do not mutate prior observation rows. Append new observations for changed metric values and link them as corrections where the edit represents correction of the same reporting-period measurement.
- If the application currently deletes and recreates daily records during edit, refactor carefully only after tests describe the existing behaviour; do not lose the link to historical observation rows.
- If a dual-write fails, roll back both the daily-record write and observation inserts. A daily record must not appear successfully saved while its required observation writes silently failed.
- Preserve current Streamlit form behaviour and messages unless a separately approved UI change is required.

**Important decision before Phase C:** determine whether a default `mortality = 0` is always an operator-confirmed observation. If it is only a form default, the form may need an explicit confirmation/semantics change in a later UI milestone. Do not infer user intent from a default value.

### Phase D — Correction support

- Implement a dedicated correction method, not a generic update method.
- Require a target observation that is the current accepted value.
- Require same `flock_id`, `metric_name` and `record_date` for the correction.
- Require a non-empty correction reason.
- Insert the correction with its own ID, provenance and `recorded_at`.
- Protect against correcting an already superseded observation or creating a cycle/branch.
- Query the latest accepted observation by excluding any observation referenced by an accepted correction.
- Return complete audit chains for inspection.

### Phase E — Controlled backfill

- Implement a dry-run report showing expected rows by metric before inserting.
- Backfill in a transaction or deterministic batches with restart-safe IDs.
- Store a migration/backfill completion marker.
- Verify row counts and foreign keys after backfill.
- Make the backfill callable only through a controlled migration/maintenance command, not on every Streamlit application startup.

### Phase F — Documentation and handover

- Update architecture documentation to distinguish implemented features from reserved future fields.
- Document migration version, backup location/process, backfill counts and known limitations.
- Update `ROADMAP.md`, `docs/project_plan.md` and `CHANGELOG.md` only when implementation has actually landed.

## 9. Transaction and consistency requirements

The daily-record row and its observations form one logical write. Use one shared SQLite connection/transaction for the full operation.

Required behaviour:

1. Begin a transaction.
2. Validate the flock and daily-record data.
3. Insert/update the daily record using the existing business rules.
4. Insert new observations/corrections for the changed values.
5. Commit only after all writes succeed.
6. Roll back everything if any step fails.

Avoid opening independent repository connections inside one service operation if that breaks atomicity. Confirm the project's current connection lifecycle and dependency-injection pattern before implementation.

## 10. Query semantics

The new repository should provide separate operations for distinct use cases:

- **History query:** returns all observations for a flock/metric/date range, including corrected and invalid entries, ordered by `observed_at` when present and then stable recording/ID fields.
- **Current accepted value:** returns an observation with `quality_status = "observed"` that is not referenced by another accepted correction.
- **Coverage query:** initially reports only what can be safely inferred from recorded observation rows. Do not assume that absence of an observation means a specific missing reason until the expected-observation denominator is defined.
- **Daily record query:** existing dashboards continue to use existing `daily_records` until a separate analytics migration is designed and tested.

Late/out-of-order sensor reads are future scope. When sensor ingestion is added, time-series queries must sort by `observed_at`, not arrival/insert order.

## 11. Testing and acceptance criteria

### 11.1 Migration tests

- Migration succeeds on a fresh empty database.
- Migration succeeds against a copy of a populated database.
- Existing farms, flocks and daily-record rows and values remain unchanged.
- Foreign keys are enabled and `PRAGMA foreign_key_check` returns no violations.
- A migration is not applied twice.
- Failure during migration leaves the database at the previous valid version.
- Backfill is deterministic and idempotent.

### 11.2 Model and service tests

- All six metric names map to the correct canonical unit.
- Real `0.0` values are retained and are not treated as missing.
- `None` is never silently converted to zero.
- Mortality remains an integer and respects the existing population rules.
- Feed and water reject negative values.
- Average weight rejects non-positive values while preserving the existing suspicious-value warning behaviour.
- Humidity remains constrained to 0–100.
- Temperature does not acquire an undocumented biological range constraint.
- Invalid metric/source/status/unit combinations are rejected.
- `recorded_at` is always populated by the service in UTC.
- Unknown `observed_at` stays null.
- No user identity is fabricated while authentication is absent.

### 11.3 Correction and audit tests

- Correction inserts a new row and leaves the original row byte-for-byte/logically unchanged.
- Correction reason is mandatory.
- Correction must target the current accepted observation for the same flock, metric and reporting date.
- A superseded observation cannot be superseded twice.
- Cycles and cross-flock/cross-metric correction links are rejected.
- Current-value query returns the accepted correction.
- History query returns the complete chain.
- Invalid or pending corrections do not supersede an accepted observation.
- Generic update/delete methods are absent or explicitly blocked; if database triggers are used, verify they reject updates/deletes.

### 11.4 Integration/regression tests

- Daily record creation and observation creation commit atomically.
- Forced observation insert failure rolls back the daily-record write.
- Editing a daily record appends correction observations for changed metrics rather than mutating historical observations.
- Existing Farm Intelligence and Environmental Monitoring tests remain green.
- Existing analytics output remains unchanged in this milestone.
- The test suite does not require or touch the user's real `data/poultryguard.db`.

### 11.5 Release acceptance criteria

Stage implementation is ready for review only when:

- the migration has passed against a copy of the real local database;
- all historical source rows are preserved and counts reconcile;
- backfill is idempotent and auditable;
- daily-record writes are transaction-safe with observation writes;
- zero/missing semantics are verified;
- correction history is append-only and tested;
- all existing tests plus new tests pass;
- Ruff lint and format checks pass;
- architecture, project plan, roadmap and changelog accurately describe what is implemented;
- a clean PR is opened and CI passes before merge.

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Migration modifies the user's only SQLite database incorrectly | Loss or corruption of farm data | SQLite backup API, populated-copy rehearsal, transactional migration, row-count and foreign-key checks |
| Dual-write is not atomic | Daily record and observations disagree | Shared connection and transaction; explicit rollback integration test |
| Null becomes zero during backfill or mapping | False farm metrics | Preserve nullable semantics; zero/null regression tests |
| `created_at` is misrepresented as observation time | False temporal precision | Backfill only to `recorded_at` with a documented approximation; keep `observed_at` null |
| Default mortality zero is treated as explicitly observed | False mortality evidence | Resolve default-zero semantics before backfill and write integration |
| Parent deletion cascades into audit history | Loss of provenance | No cascade deletion for observations; test parent deletion policy |
| Corrections branch or target another metric/flock | Ambiguous current value | Service validation, unique supersession index and correction-chain tests |
| Pending status is mutated in place | Audit history becomes unreliable | Defer review transitions or add append-only quality-review events |
| Analytics switches too early to the observation table | Existing dashboard regressions | Keep `daily_records` as analytics source until a separate approved milestone |
| Future source types are accepted before their provenance is implemented | Untrustworthy metadata | Enable manual-entry only; keep sensor/import/calculation writers out of scope |

## 13. Implementation order and review gates

| Order | Work package | Exit gate |
|---|---|---|
| 0 | Inspect current `main`, database, service transactions and delete flows | Baseline findings recorded; no code/data changed |
| 1 | Finalise schema decisions and migration approach | Schema review approved |
| 2 | Implement migration runner and new table | Empty/populated-copy migration tests pass |
| 3 | Implement observation model, repository and service validation | Unit tests pass; insert-only contract verified |
| 4 | Add atomic daily-record dual-write | Integration and rollback tests pass |
| 5 | Add correction and audit queries | Append-only correction tests pass |
| 6 | Rehearse and execute controlled legacy backfill | Counts reconcile; data preservation verified |
| 7 | Update documentation and open implementation PR | Full CI green; PR reviewed before merge |

Do not combine all work into one large unreviewable change. Use small commits or separate feature branches/PRs if the repository's existing workflow favours them.

## 14. Decisions to resolve before implementation

The following items require explicit decisions during the Stage 3.2.3 review. Recommended defaults are included.

1. **Mortality default zero:** confirm whether the current form's default `0` is an operator-confirmed value. Recommended: treat it as observed only if the daily record represents an explicit daily report; otherwise adjust the future form to distinguish “confirmed zero” from “not entered”.
2. **Historical missing optional values:** should the backfill create `not_recorded` rows for null fields? Recommended: no for the initial backfill; omit them until the expected measurement schedule and coverage denominator are defined.
3. **Daily-record edits:** does the current UI update a record in place or delete/recreate it? Recommended: preserve the row and append correction observations for changed measurements, after inspecting the actual write path.
4. **Parent deletion:** what happens when a farm/flock/daily record is deleted after observations exist? Recommended: block destructive deletion or introduce archive/soft delete; never cascade-delete observation history.
5. **Quality review transitions:** how will `pending_validation` become `observed` or `invalid`? Recommended: a future append-only review-event table; no in-place status changes.
6. **Observation ID:** Recommended UUIDv4 for new records and deterministic IDs for backfill rows to guarantee idempotence.
7. **Timezone representation:** Recommended UTC timestamps in storage and IANA `Africa/Lagos` for Nigerian farm-local presentation.
8. **Analytics cutover:** Recommended no cutover in this increment; continue using `daily_records` until parity tests are designed.

## 15. First implementation task for Amazon Q Developer

Use the following prompt only after placing this plan in the repository and creating a dedicated documentation/implementation branch. This is a **read-only repository assessment task**; Amazon Q must not edit code, apply migrations or open the live database for writes.

> Read `docs/architecture/measurement_provenance.md` and `docs/architecture/measurement_provenance_implementation_plan.md` in full. Inspect the current `main` branch implementation, especially SQLite connection creation, schema initialisation, model definitions, repository patterns, daily-record create/edit/delete flows, transaction handling, and test fixtures. Produce a repository-specific implementation assessment that maps each proposed component to actual file paths and functions. Identify any differences between the approved architecture and current code. Explicitly determine how daily-record edits and deletes work, how SQLite foreign keys are enabled, how timestamps are created, whether mortality zero is a form default or an explicitly confirmed report, and how to take a safe SQLite backup. Recommend the smallest additive migration design. Do not modify any files, do not run a migration, do not alter or reset `data/poultryguard.db`, do not install dependencies, and do not commit or push. Return findings, risks, unresolved decisions and a proposed implementation sequence only.

## 16. Completion definition for Stage 3.2.3

Stage 3.2.3 is complete when the repository-specific assessment has been reviewed, the eight decisions above are resolved or explicitly deferred, the migration and rollout plan are approved, and the team has a task-by-task implementation sequence. No database or runtime changes are required to declare this planning milestone complete.

---

*This document is an implementation plan derived from the approved Stage 3.2.2 architecture specification. Proposed schema fields, repository names and code locations must be verified against the current repository before implementation. It does not authorise a database reset, destructive migration or modification of the user's live farm database.*