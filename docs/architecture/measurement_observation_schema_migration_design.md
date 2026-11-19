# PoultryGuard AI — Measurement Observation Schema and Migration Design

**Status:** Historical design basis; initial schema/migration implementation merged in PR #21; the manual observation service is under review in PR #22  
**Stage:** 3.2.3 — schema, migration and first application-service increments  
**Reviewed baseline:** `main` at `a3794b8e031523439b5a30e003b1ae720d2e8a3e`  
**Source specifications:** `measurement_provenance.md` (Stage 3.2.2) and `measurement_provenance_implementation_plan.md`  
**Scope:** Records the design rationale and remaining decision gates. Current runtime behaviour is documented in `sqlite_migrations.md` and `measurement_observation_service.md`.

## 1. Executive recommendation

Add a new `measurement_observations` table without changing the existing `farms`, `flocks` or `daily_records` tables. Each row represents one metric observation, linked to a flock and optionally to the daily-record row from which it originated.

Keep the existing daily-record layer as the farmer-facing operational summary and the current analytics source. The observation layer initially supports validated `manual_entry` writes only. Sensor ingestion, file import, system-generated observations, quality-review UI and analytics cutover remain outside the first implementation increment.

Use the merged SQLite Unit-of-Work for future daily-record/observation dual-writes. The daily record and every required observation must commit or roll back together.

The migration runner and additive observation schema have since been implemented and merged in PR #21. The first manual-entry observation model, repository and service are proposed separately in PR #22. The unresolved mortality-zero semantics and correction/review lifecycle still gate daily-record dual-write, historical backfill and correction writers. A live database migration remains a separate approval step.

## 2. Source-derived requirements

The Stage 3.2.2 specification and Stage 3.2.3 implementation plan establish the following requirements:

1. Preserve existing `farms`, `flocks` and `daily_records`; add an individual-observation layer.
2. One observation row represents one measurement of one metric. A daily record may be associated with multiple observation rows.
3. Use `flock_id` as the ownership relationship and derive `farm_id` through `flocks`; do not store a second mutable farm reference in the observation.
4. Keep `daily_record_id` nullable because future sensor/import observations may not originate from a daily-record form.
5. Store the farm-local reporting date separately from timestamps: `record_date` is a date, `observed_at` is the actual measurement time when known, and `recorded_at` is the platform recording time.
6. Store machine timestamps in UTC ISO 8601 form. Do not fabricate `observed_at` from `record_date` or the legacy `created_at`.
7. Preserve real numeric zero and preserve `NULL); never coerce one into the other.
8. Preserve the seven quality statuses: `observed`, `not_recorded`, `not_measured`, `not_applicable`, `device_unavailable`, `invalid`, `pending_validation`.
9. Preserve the four source categories: `manual_entry`, `file_import`, `sensor_device`, `system_generated`; enable only `manual_entry` writes initially.
10. Keep observation rows append-only. A correction is a new observation with its own provenance and timestamp, and the old row remains unchanged.
11. Keep current analytics on `daily_records` until a separate parity-tested analytics migration is approved.
12. Backfill is additive and must be deterministic/restart-safe. Do not automatically convert historical mortality zero to an observed zero until its meaning is resolved.

The schema migration in PR #21 implements the observation table, constraints and append-only protections. The manual-only model/service implementation in PR #22 is under review. Dual-write, backfill, corrections, review events, sensor/import writers and analytics cutover remain unimplemented.

## 3. Current repository facts affecting the design

The reviewed repository already contains:

- `app/database/connection.py`: SQLite connection factory, foreign-key pragma and explicit close-on-context-exit behaviour.
- `app/database/unit_of_work.py`: one shared connection, `BEGIN IMMEDIATE`, commit/rollback and close.
- `app/database/repositories.py`: repositories can use an injected shared connection or their existing standalone connection scope.
- `FarmService.create_daily_record()`: flock lookup, duplicate-date validation, cumulative-mortality validation and insert occur within one Unit-of-Work.
- Existing farm, flock and daily-record tables are created by `initialise_database()`; no versioned migration ledger/runner exists.
- `daily_records` supports multiple records for the same flock/date when `allow_duplicate=True`; there is no unique `(flock_id, record_date)` constraint.
- The repositories have delete methods and foreign keys currently cascade from farms to flocks and from flocks to daily records. The current UI/service does not expose a general daily-record delete/edit workflow.

**Implications:** do not add a daily-record uniqueness constraint; use the originating `daily_record_id` to distinguish daily-entry groups; do not make observation history cascade-delete with a flock or daily record; and do not assume a live database has a migration ledger.

This review covers committed repository code only. It does not inspect the user's local SQLite database or working-tree state.

## 4. Recommended logical schema

### 4.1 `measurement_observations`

| Column | Proposed SQLite type | Nullability | Notes |
|---|---|---:|---|
| `observation_id` | TEXT | NOT NULL | UUID for a new observation; deterministic UUID for a legacy backfill row |
| `flock_id` | INTEGER | NOT NULL | FK to `flocks.id`; primary ownership reference |
| `daily_record_id` | INTEGER | NULL | FK to `daily_records.id` when created from a daily record |
| `record_date` | TEXT | NOT NULL | Farm-local reporting date, `YYYY-MM-DD` |
| `metric_name` | TEXT | NOT NULL | One of the six current daily-record metrics |
| `value_numeric` | REAL | NULL | Numeric value; zero remains zero; absence statuses use NULL |
| `unit` | TEXT | NOT NULL | Canonical unit owned by the service's metric dictionary |
| `observed_at` | TEXT | NULL | UTC ISO 8601 measurement timestamp when known |
| `recorded_at` | TEXT | NOT NULL | UTC ISO 8601 platform timestamp, assigned by the service |
| `source_type` | TEXT | NOT NULL | Four approved categories; initial writer accepts manual only |
| `entered_by_user_id` | TEXT | NULL | NULL until authenticated user identity exists |
| `device_id` | TEXT | NULL | Reserved; no device registry in this increment |
| `import_batch_id` | TEXT | NULL | Reserved; no import writer in this increment |
| `source_reference` | TEXT | NULL | Optional external/legacy reference |
| `calibration_reference` | TEXT | NULL | Reserved; no calibration store in this increment |
| `calculation_method` | TEXT | NULL | Reserved for future system-generated observations |
| `calculation_version` | TEXT | NULL | Reserved for future system-generated observations |
| `quality_status` | TEXT | NOT NULL | One of the seven approved statuses |
| `supersedes_observation_id` | TEXT | NULL | Self-reference for an accepted correction only |
| `correction_reason` | TEXT | NULL | Required and non-blank when superseding another observation |
| `notes` | TEXT | NULL | Optional contextual note |

Do not add `farm_id` to this table in the first version. Derive it through `flocks.farm_id`. Do not add `source_observation_ids` as a comma-separated string; it is not required for manual-entry writes. If system-generated observations are later implemented, use a normalised observation-input link table or a separately reviewed structured representation.

### 4.2 Metric and canonical unit mapping

| `metric_name` | Source field | Canonical `unit` | Validation to preserve |
|---|---|---|---|
| `mortality` | `mortality` | `birds` | Integer, >= 0; current remaining-population validation remains |
| `feed_kg` | `feed_kg` | `kg` | >= 0 when present |
| `water_litres` | `water_litres` | `litres` | >= 0 when present |
| `average_weight_kg` | `average_weight_kg` | `kg_per_bird` | > 0 when present; existing suspicious-value warning remains a warning |
| `temperature_c` | `temperature_c` | `degrees_celsius` | No new biological range constraint |
| `humidity_percent` | `humidity_percent` | `percent_relative_humidity` | 0–100 |

The service layer must derive the unit from `metric_name`; callers must not be allowed to pair a metric with an arbitrary unit. The database should also include a CHECK pairing each approved metric with its canonical unit.

A single `REAL` column is proposed for the six numeric metrics. Mortality's integer-only semantics must be enforced in the service and with a database CHECK that rejects non-integral mortality values. Do not change mortality to floating point in the application model.

### 4.3 Quality status/value compatibility

The proposed database CHECK should enforce the contract:

- `not_recorded`, `not_measured`, `not_applicable`, `device_unavailable`: `value_numeric IS NULL`.
- `observed`, `invalid`, `pending_validation`: `value_numeric IS NOT NULL`.

A numeric `0.0` with `quality_status = 'observed'` is a genuine observation. `invalid` and `pending_validation` retain the candidate/raw value but are not accepted values for ordinary analytics. No implicit fill-forward, interpolation or null-to-zero conversion is allowed.

The first write service should create `observed` manual values only. The schema may recognise the other approved source/status values, but there must be no callable sensor/import/system writer or claim that quality review is implemented yet.

## 5. Referential integrity and deletion protection

Recommended foreign-key policy:

- `flock_id → flocks.id`: `ON DELETE RESTRICT` (or the SQLite-equivalent `NO ACTION` with explicit tests).
- `daily_record_id → daily_records.id`: `ON DELETE RESTRICT`.
- `supersedes_observation_id → measurement_observations.observation_id`: `ON DELETE RESTRICT`.

Do not cascade-delete observations. Once observations exist, a farm/flock/daily-record hard delete may be blocked by the observation references. This is intentional protection for provenance history, but it means archive/retention policy must be agreed before enabling observation writes in workflows where parent deletion remains possible.

The correction relationship should be checked for the same `flock_id`, `metric_name` and `record_date`. A composite self-reference to a unique tuple `(observation_id, flock_id, metric_name, record_date)` is a candidate for enforcing this at SQLite level; otherwise enforce it in the correction service and tests. Confirm the exact SQLite DDL against the supported runtime version before committing the migration.

## 6. Correction-chain constraints and the review-attempt problem

The source correction model requires an append-only, linear chain:

- Original observations are never updated or deleted.
- A correction inserts a new observation with a new ID and a non-empty reason.
- Only an accepted correction supersedes an existing accepted observation.
- An observation can have at most one accepted successor.
- A correction may extend a chain by superseding its current accepted leaf.
- A correction must target the same flock, metric and reporting date.

A partial unique index on `supersedes_observation_id` where non-NULL is appropriate **only if that column is populated by accepted correction observations**. A pending or rejected correction attempt must not occupy that unique link.

**Recommended separation:** record correction attempts/requests separately from the accepted observation chain. A rejected request remains available for review/audit but has no `supersedes_observation_id` edge. When a request is accepted, the same Unit-of-Work should insert a new `observed` correction observation with the accepted supersession link and append the review decision. This avoids a rejected attempt preventing a later valid correction.

The Stage 3.2.2 specification also says a `pending_validation` observation cannot be mutated into `observed` or `invalid` without violating immutability. A later quality-review phase should use append-only review events and an explicitly defined effective-status query. Do not implement in-place status updates. The exact correction-request/review-event table shape remains a decision gate, not part of the first table-only migration.

## 7. Index design

Recommended minimum indexes for the observation table:

1. `(flock_id, metric_name, record_date)` for daily/reporting-period lookups.
2. `(flock_id, metric_name, observed_at)` for future time-series retrieval.
3. `(daily_record_id)` for finding observations belonging to a daily record.
4. Partial unique `(supersedes_observation_id)` where non-NULL, once the accepted-correction-only invariant is implemented.

Do not add a uniqueness constraint on `(flock_id, metric_name, record_date)`: multiple observations per day are an explicit future requirement, and duplicate daily records are currently supported. Use `daily_record_id` to associate manual daily-record observations with their source row.

## 8. Migration runner design

### 8.1 Approach

A small project-owned migration runner is the recommended candidate because the repository uses direct `sqlite3`, dataclasses and repositories rather than an ORM. This is a proposal, not a selected/approved migration tool.

Suggested structure (exact names may change during implementation):

```text
app/database/
  migrations/
    __init__.py
    runner.py
    versions/
      0001_add_measurement_observations.py
```

Each immutable, ordered migration module should expose a version/name/checksum and an `upgrade(connection)` function. Keep SQL in explicit statements executed on the supplied connection. Do not make migration execution depend on Streamlit.

### 8.2 Migration ledger and existing-database adoption

Add an additive ledger, for example:

```sql
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
```

The repository's existing populated database predates this ledger. The runner must therefore have a separately tested **baseline-adoption** path:

1. Detect whether the ledger exists.
2. If it does not, inspect the known baseline tables and required columns/foreign-key definitions.
3. Confirm that the database matches the expected current schema baseline; do not infer the baseline from a filename or from the presence of one table.
4. Create the ledger and record a baseline version only after successful verification.
5. If the existing schema is unexpected, incomplete or partially migrated, stop without changing business tables and report the discrepancy.

If a migration ledger exists, verify migration checksums and the expected schema state. Do not silently edit a previously applied migration or silently accept a checksum mismatch.

### 8.3 Transaction and execution rules

- Enable and verify `PRAGMA foreign_keys = ON` before beginning the migration transaction.
- Use a single connection and an explicit transaction for the additive table/index migration.
- Execute DDL statements on that connection; avoid transaction helpers that implicitly commit outside the migration runner's control.
- Insert the migration-ledger row in the same transaction as the schema change.
- Run `PRAGMA foreign_key_check` before commit and fail if any violations are returned.
- Roll back the whole migration if any statement, ledger write or validation fails.
- Verify expected tables, columns, indexes and CHECK/foreign-key definitions after the migration.
- Do not run migrations automatically from Streamlit startup. Use an explicit maintenance command with a displayed plan/status and an explicit apply action.

For a first migration that only adds the ledger, observation table and indexes, no existing table rebuild should be needed. If a later migration requires SQLite table reconstruction, design and test that operation separately.

### 8.4 Rollback and forward-recovery policy

Separate **transaction rollback on a failed migration** from **downgrading a migration that has already accepted production observations**.

- If the migration fails before commit, SQLite transaction rollback must leave the previous schema state intact.
- A downgrade that drops `measurement_observations` after the table contains provenance history would destroy data and is not an acceptable routine rollback.
- After observations are written, prefer a forward corrective migration. Preserve a verified backup before every live schema operation.
- Do not advertise a destructive `downgrade` as safe merely because the table was newly created.

## 9. Backfill policy and data-preservation rules

Backfill is a separate controlled operation; it must not run automatically as part of Streamlit startup or the schema migration.

Proposed mapping from each legacy `daily_records` row:

- For each non-NULL optional field, create one observation with the correct metric/unit, `flock_id`, `daily_record_id`, and `record_date`.
- Treat mortality separately. Do not automatically classify stored zero as a confirmed observed zero until the input/default semantics are decided.
- Use `source_type = 'manual_entry'` only after confirming the historical capture path was manual.
- Set `observed_at = NULL`; exact historical measurement time is unknown.
- Set `recorded_at` from legacy `created_at` only as a documented approximation of row-creation time, after confirming timestamp representation and timezone interpretation. Never label it as observation time.
- Set `entered_by_user_id = NULL`; no historical user identity exists.
- Set `quality_status = 'observed'` for accepted, non-NULL historical values.
- Use deterministic UUIDv5 (or another documented deterministic scheme) derived from `daily_record_id + metric_name` so backfill retries cannot create duplicate rows.
- Omit legacy optional NULLs initially; do not create `not_recorded` rows until the expected-measurement schedule/coverage denominator is defined.
- Do not alter, delete or re-key any legacy daily-record row.

The backfill tool must support a dry-run report by metric before writes begin, and a repeat run must produce zero additional rows after the first successful run.

## 10. Daily-record integration using the merged Unit-of-Work

The current Unit-of-Work provides the right transaction boundary. The later integration should:

1. Begin one Unit-of-Work.
2. Perform the current flock, duplicate-date and cumulative-mortality validation.
3. Insert the daily-record row.
4. Insert the corresponding observation rows using the same connection.
5. Commit only after every required observation insert succeeds.

If any observation insert fails, the daily-record insert must roll back too. Do not cut analytics over to observations in this milestone; current dashboards continue to read `daily_records`.

The record-to-observation association is through `daily_record_id`. This supports multiple daily records for the same flock/date without confusing their individual source values. No uniqueness constraint should be added to the legacy daily-record table.

**Mortality decision gate:** because the current mortality input defaults to zero without separate explicit confirmation, decide whether saving a daily record itself constitutes confirmation of a zero report. Until that is agreed, do not claim historical default zeros are observed mortality evidence.

## 11. Test and rehearsal matrix

All tests must use temporary files or in-memory SQLite databases. No test may discover or open the user's live `data/poultryguard.db`.

### Migration tests

- Empty database: baseline/ledger setup and observation-table migration succeed in the intended order.
- Populated baseline copy: existing farms, flocks and daily_records tables/values remain unchanged.
- Unexpected schema: baseline adoption fails closed without changing business tables.
- Migration already applied: second runner invocation is a no-op with no duplicate DDL/data.
- Checksum mismatch: runner refuses to silently accept edited migration content.
- Injected failure: transaction rollback leaves the previous schema and ledger state.
- `PRAGMA foreign_key_check` returns no violations after migration.
- DDL constraints, indexes and FK delete restrictions match the design.

### Observation model/service tests

- All six metric names map to the exact canonical unit.
- Metric/unit mismatch rejected.
- Mortality accepts integer values only and preserves existing population validation.
- Feed/water non-negative; weight positive; humidity 0–100; temperature has no new biological range rule.
- Zero remains a numeric zero; NULL remains NULL.
- Absence status/value combinations enforced.
- Unknown observation time remains NULL.
- Recorded timestamp is service-generated UTC.
- Only manual-entry writes are exposed in the first release.
- No generic update/delete methods for observations.

### Correction tests

- Original observation remains unchanged after a correction.
- Correction reason is mandatory.
- Correction belongs to the same flock, metric and record date.
- A target must be the current accepted chain leaf.
- A target cannot have two accepted successors.
- A correction chain may extend linearly.
- Rejected/pending correction requests do not occupy the accepted supersession link.
- History query returns every observation/request/review entry required by the audit model.

### Integration and backfill tests

- Daily-record + observation insert succeeds atomically.
- Forced failure of any observation insert rolls back the daily-record insert.
- `allow_duplicate=True` remains supported; no new unique daily-record constraint.
- Daily record and observation source linkage is exact.
- Backfill IDs are deterministic and rerunning backfill inserts no duplicates.
- Legacy farms/flocks/daily_records counts and values are unchanged.
- Legacy NULL and zero values are reconciled per the approved mortality policy.
- Existing analytics output remains unchanged because it still reads `daily_records`.

## 12. Implementation sequence and gates

| Order | Deliverable | Exit gate |
|---|---|---|
| 0 | Review this schema/migration design | Open decisions accepted or explicitly deferred |
| 1 | Repository-specific database preflight and migration-runner design | Baseline schema and ledger-adoption checks specified; no live DB write |
| 2 | Migration ledger + additive observation table/index migration on feature branch | Empty/populated-copy tests pass |
| 3 | Observation dataclass, repository and service validation | Unit tests pass; insert-only contract verified |
| 4 | Correction request/review model and accepted correction chain | Append-only and no-branch tests pass |
| 5 | Atomic daily-record/observation dual-write | Rollback integration tests pass; mortality semantics resolved |
| 6 | Dry-run and deterministic historical backfill | Populated-copy rehearsal reconciles |
| 7 | Documentation and PR review | Full CI green; owner reviews before merge |
| 8 | Live local migration/backfill (separate explicit approval) | Verified backup, rehearsed copy, recorded counts and restore plan |

Do not combine all phases into one large PR. Keep schema, service, integration and backfill reviewable and separately gated.

## 13. Decisions that remain open

These are not approved by this document:

1. **Mortality zero:** Does submitting the daily-record form mean the default zero was explicitly confirmed? This must be decided before historical zero backfill or new mortality dual-write.
2. **Correction request and quality-review schema:** Which append-only request/event tables and effective-status query will be used? The recommendation is to separate rejected/pending attempts from accepted supersession links.
3. **Parent deletion/archive policy:** Once observations exist, should farms/flocks/daily records be archived and hard deletion blocked? The recommended immediate protection is RESTRICT/NO ACTION, but the product policy needs approval.
4. **Historical backfill:** Should it run as a separate controlled maintenance command after table creation? Recommended: yes; no automatic startup backfill.
5. **Migration runner:** The custom runner, strict baseline adoption, checksum verification and backup-protected explicit CLI are implemented and documented in `sqlite_migrations.md`. Any future migration changes remain subject to review.
6. **Quality review:** Are `pending_validation` observations excluded from analytics until an append-only review event accepts them? Recommended: exclude until accepted.
7. **Farm timezone storage:** The long-term design specifies an IANA timezone such as `Africa/Lagos`; adding a farm timezone column is outside this additive observation migration.
8. **Observation identifiers:** UUIDv4 for new rows and deterministic UUIDv5 for legacy backfill is recommended, subject to approval.

## 14. Implementation status and safety boundary

The repository now has the following implemented or reviewable increments:

- PR #21 merged the explicit migration runner, ledger, baseline-adoption checks and additive `measurement_observations` schema.
- PR #22 proposes the frozen observation model, insert/read-only repository, Unit-of-Work wiring and validated manual-entry service. It remains subject to review and CI.
- Current analytics continue to read `daily_records`; no dual-write or analytics cutover is included.
- No historical daily records are backfilled.
- No correction-request, quality-review, sensor, import, system-generated or UI workflow is included.
- Mortality-zero semantics, the correction/review model and the parent archive/deletion policy remain unresolved.

Automated migration and service tests use temporary SQLite databases. Neither PR #21 nor PR #22 authorises opening, inspecting, backing up, migrating or writing to the user's local `data/poultryguard.db`. A live migration and any backfill require a separate populated-copy rehearsal, verified backup and explicit owner approval.

---
*End of proposed design.*
