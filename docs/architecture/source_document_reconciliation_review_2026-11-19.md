# PoultryGuard AI — Source Document Reconciliation Review

**Review date:** 19 November 2026  
**Target repository:** `zulyadainimuhammad/poultryguard-ai`  
**Reviewed baseline:** `main` at `275f60b3b35c88510a2e9c3bf5fd4de54ae91ed3` (`275f60b`)  
**Status:** Documentation review; proposed findings, not approvals  
**Scope:** Reconcile the uploaded product requirements, architecture correction report, measurement-provenance specification and implementation plan against the current committed repository.

## 1. Purpose and evidence boundary

This review accompanies three source documents added to the repository:

- `docs/product/product_requirements_ui_ux.md`
- `docs/architecture/adr_v2_2_correction_report.md`
- `docs/architecture/measurement_provenance_implementation_plan.md`

The source documents are preserved as supplied. This review records reconciliation findings; it does not silently rewrite their original recommendations or approve unresolved architecture decisions.

The repository inspection covers committed GitHub content at the reviewed baseline. It does not inspect the user's local SQLite database, credentials, or uncommitted local files. The user's separate local test result is recorded only as user-reported evidence.

## 2. Current repository facts

### 2.1 SQLite connection lifecycle

The current `app/database/connection.py`:

- creates a connection through a custom `_ClosingSQLiteConnection` factory;
- enables `PRAGMA foreign_keys = ON` for each connection before returning it; and
- closes the connection when its context manager exits, while preserving commit/rollback behaviour.

The fix is covered by `tests/unit/test_connection.py`, which checks the foreign-key pragma, commit persistence, exception rollback and closed-connection behaviour.

**Reconciliation:** The earlier repository assessment written against `d17c470` is stale on connection lifetime. Connection closure is now implemented and tested on the reviewed `main` baseline. Foreign-key enforcement was already present and remains enabled.

### 2.2 Current schema and deletion behaviour

The current initial schema has `farms`, `flocks` and `daily_records`. The `flocks.farm_id` foreign key cascades on farm deletion, and `daily_records.flock_id` cascades on flock deletion. Repository delete methods exist for farms, flocks and daily records. The reviewed service/UI does not expose an equivalent general daily-record edit workflow or deletion controls.

**Reconciliation:** This is a schema/repository capability, not evidence of a farmer-facing delete workflow. Do not alter these foreign keys or run a live migration until archive, retention and audit-history policy is approved.

### 2.3 Daily-record writes and duplicate scope

`FarmService.create_daily_record()` performs validation and reads through repository methods before inserting through `DailyRecordRepository.create()`. Those repository methods each open their own connection. The insert itself is transactional, but the complete use case does not yet share one connection for all reads and writes.

The service's `allow_duplicate=True` option bypasses the service-level duplicate check. The inspected schema does not impose a unique constraint on `(flock_id, record_date)`. No daily-record edit method was found in the reviewed service/repository.

**Reconciliation:** A future dual-write to daily records and measurement observations requires an explicit shared-connection transaction/unit-of-work. Do not add a unique daily-record constraint without inspecting existing data and approving duplicate semantics.

### 2.4 Measurement semantics

Optional numeric measurements preserve `NULL` separately from numeric zero. Mortality is non-null with a default of zero. The Streamlit mortality input also defaults to zero; the current workflow does not separately record whether the operator explicitly confirmed that zero.

**Reconciliation:** Do not backfill every historical mortality zero as an explicitly observed value until the input semantics are resolved. Do not infer observation timestamps from record dates or row-creation timestamps.

### 2.5 Current product/runtime boundary

The current app remains a local Streamlit MVP backed by SQLite and Python services/repositories. The knowledge retrieval pipeline uses local Sentence Transformers/FAISS components, while answer generation uses the Groq API and therefore requires internet connectivity and configured API access. The repository does not yet provide production authentication, farm memberships, tenant isolation, sensor ingestion or a production multi-user API.

**Reconciliation:** Preserve the working MVP and label proposed features accurately. A zero-recurring-infrastructure-cost development goal does not itself prove that external API usage is free, offline or guaranteed by a free tier.

## 3. Cross-document corrections and clarifications

### 3.1 Decision numbering

The PRD identifies ADR-01 through ADR-07 and assigns ADR-07 to deployment, backup, monitoring and recovery. The correction report also uses ADR-07 for measurement-correction state transitions and refers to legacy ADR-09, ADR-10, ADR-11 and ADR-15.

The original complete v2.1 decision register and approval history were not available during this review.

**Required treatment:** retain the PRD's source-verified ADR-01–ADR-07 topics. Keep measurement correction and other legacy references as supplementary/working topics until the original register is recovered or a controlled reconstruction is explicitly approved. Do not silently renumber decisions or transfer approval status.

### 3.2 Accepted corrections versus rejected attempts

The correction report recommends a unique partial index on `supersedes_observation_id` and permits accepted correction chains. However, a pending or rejected correction attempt must not reserve the supersession link and prevent a later valid correction.

A unique index directly on every attempted correction row would conflict with that requirement if rejected attempts remain in the same table with the same target reference.

**Recommended design direction for a later schema decision:**

1. Keep the original measurement observation immutable.
2. Represent a correction request/attempt separately from the accepted correction relationship, or use an equivalent model in which pending/rejected attempts do not populate the unique accepted-supersession edge.
3. Record review decisions append-only.
4. Create the accepted supersession edge atomically only when a correction is accepted.
5. Enforce at most one accepted successor per observation and allow a new correction to supersede the current chain head.
6. Define whether review decisions are final; an erroneous accepted value should normally be corrected by a subsequent accepted observation rather than mutating history.

This is a design recommendation only. The exact relational model and effective-status query must be reviewed before implementation.

### 3.3 Multiple daily records on one flock/date

The current service can explicitly bypass duplicate-day validation. An observation scope consisting only of `flock_id + metric_name + record_date` may therefore combine separate daily-record entries.

**Required treatment:** retain a reference to the originating `daily_record_id` when observations originate from a daily record, and define how independent sensor/high-frequency observations are grouped. Do not assume one daily record per flock/date or introduce a unique constraint without a data review.

### 3.4 Identity mapping should allow multiple sign-in providers

The PRD requires email/password and Google sign-in in the target product, while the identity provider remains undecided. A single provider-subject field directly on an internal user row can make future account linking unnecessarily restrictive.

**Recommended direction:** separate the internal application user from one-or-more external identity mappings. Enforce uniqueness on `(provider_name, provider_subject_id)`; internal memberships, audit events and measurement provenance refer to the internal user ID. Email is display/contact data and not a durable security identity key. Provider-specific claims and verification behaviour must wait until ADR-04 is resolved.

### 3.5 Migration tooling and SQLite behaviour

The custom migration runner remains a reasonable low-dependency candidate, but it is not approved. Its design must handle transaction boundaries explicitly, recognise existing populated databases that predate the migration ledger, validate expected schema state, and fail safely. Python SQLite `executescript()` has transaction semantics that must be considered; do not assume it behaves like a sequence of ordinary statements inside an already-open transaction.

Alembic batch mode is relevant for SQLite operations that require table recreation; it should not be described as mandatory for every possible SQLite schema alteration. The actual migration operations and minimum SQLite version must determine the approach.

### 3.6 Farm timezones

Use UTC for stored machine timestamps and a farm-configured IANA timezone for local display and reporting-date interpretation. `Africa/Lagos` is a suitable initial default for farms in Nigeria, not a global hard-coded timezone.

### 3.7 Farm ownership and Staff permissions

Retain the invariant that every active farm must have at least one active Owner. Whether multiple Owners may coexist remains open.

Staff assigned-flock-only access is a selected proposal pending final approval. The exact capabilities (viewing aggregates, creating/editing records, correcting older data, and access after assignment revocation) still need a permission catalogue and negative-access tests.

### 3.8 Platform administrator bootstrap and audit

Platform administration is separate from farm ownership. If a platform-admin role is retained, bootstrap must bind to an authenticated provider subject/internal user mapping, not email alone. Do not put bootstrap secrets in source code, shell history or logs. Audit records should not contain plaintext secrets.

The common audit-event model, failed security-event handling, retention, actor attribution and atomicity with successful business writes remain design work.

## 4. Recommended decisions to keep open

| Topic | Review disposition |
|---|---|
| Identity provider and production account linking | Deferred until validation/funding and ADR-04 review |
| Custom migration runner versus Alembic | Open; custom runner is a low-dependency candidate |
| Multiple active farm Owners | Open; preserve at-least-one-owner invariant |
| Staff assigned-flock permission catalogue | Proposed; final approval pending |
| Correction-request/review/accepted-link schema | Open; correct before schema design is frozen |
| Daily-record duplicate semantics | Open; inspect existing data and usage |
| Archive/retention and parent delete policy | Open; no live FK changes |
| Mortality zero meaning | Open; no automatic historical interpretation |
| Historical backfill of null optional measurements | Defer explicit missing rows until denominator/coverage semantics are agreed |
| Analytics cutover to observations | Defer until parity and reconciliation tests pass |
| Farm-specific AI access and data isolation | Required target design; not implemented |
| Recurring infrastructure/provider expenditure | No paid or recurring service without product-owner approval during validation |

## 5. Safe implementation sequence after documentation review

1. Review and approve this reconciliation and the product/architecture decision statuses.
2. Confirm the local checkout, local uncommitted documents and live database path without opening the database for writes.
3. Design and test a shared SQLite connection/unit-of-work boundary for multi-repository writes, without changing the schema.
4. Decide the archive/retention policy and migration approach.
5. Finalise the observation, correction-attempt, quality-review and accepted-supersession data model.
6. Implement schema changes only on a disposable copy/fresh test database first.
7. Rehearse deterministic historical backfill on a verified copy and reconcile all source row counts/values.
8. Add daily-record dual-write only after transaction rollback tests prove the two layers commit atomically.
9. Keep existing analytics on `daily_records` until a separate parity-tested cutover is approved.

## 6. Validation and safety boundary

The user reported running `python -m pytest` after syncing the local checkout to `main`, with **112 tests passing**, and `ruff check .` with **All checks passed**. This review did not run those commands on the user's PC and did not inspect the local SQLite database.

This change is documentation-only. It adds source documents and records a review of their consistency with current committed code. It does not implement authentication, multi-farm access, measurement observations, corrections, migrations, new dependencies, hosted services or any database change.

---
*End of review. No architecture decision is marked Approved by this document.*
