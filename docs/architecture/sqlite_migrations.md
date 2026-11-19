# SQLite Schema Migration Operations

**Status:** Implemented on the feature branch; review and merge required  
**Scope:** Migration runner and the initial additive `measurement_observations` schema only

## 1. Operating principles

- Schema migrations are explicit maintenance operations. They are not called from Streamlit startup or `initialise_database()`.
- The runner accepts only an idle SQLite connection with `PRAGMA foreign_keys = ON`.
- The runner verifies the existing farms/flocks/daily-record baseline before adopting a populated database that predates the migration ledger.
- The migration ledger and schema DDL are written in one `BEGIN IMMEDIATE` transaction.
- An already-applied migration is a no-op only when its name and SHA-256 checksum match the recorded version.
- Unexpected baseline schemas, partial observation tables, unknown migration versions and checksum mismatches fail closed.
- A failed migration rolls back the ledger and schema work together.
- The migration ledger and observation rows have append-only triggers.

## 2. Existing database baseline adoption

The current application predates a schema migration ledger. On first migration, the runner checks the exact expected column names, types, nullability, defaults and primary-key positions for `farms`, `flocks` and `daily_records`. It also checks the expected cascading foreign keys, required CHECK constraints and `PRAGMA foreign_key_check`.

Only after this verification does the runner record baseline version `0000`. It fingerprints the three baseline table definitions at adoption time. Subsequent migrations may add independent tables and indexes without rewriting the historical baseline marker.

A blank or differently structured database is not automatically initialised or adopted by the migration runner. Use the application's existing database initialisation path for a new test database first. A partially-created observation table without a ledger is rejected for manual inspection.

## 3. Explicit command-line operations

The command requires an existing, already-initialised database path. It does not guess or default to the user's database.

Read-only status:

```powershell
python scripts/migrate_database.py --database "C:\path\to\poultryguard.db" --status
```

Apply pending migrations:

```powershell
python scripts/migrate_database.py --database "C:\path\to\poultryguard.db" --apply --backup-to "C:\path\to\backups\poultryguard-before-observations.db"
```

The apply command requires a new backup path that does not already exist, and its parent directory must already exist. It uses SQLite's online backup API, then verifies the backup's integrity and the row counts of `farms`, `flocks` and `daily_records` before applying the migration. It refuses to overwrite an existing backup.

If migration application fails, the command reports the error and preserves the verified backup for recovery. The migration itself is atomic; the backup is not automatically restored because the source database transaction is rolled back on failure.

**The command examples document the operator interface; they are not an instruction to run the migration against a live local database now.** A separate approval gate is required after CI, PR review, populated-copy rehearsal and explicit owner approval.

## 4. Initial migration `0001`

The initial migration adds:

- A unique supporting index on `daily_records(id, flock_id)` to support the composite source reference without changing existing rows.
- `measurement_observations` with canonical metric/unit pairing, quality-status/value compatibility, source metadata fields, date shape validation, metric-specific checks for accepted values and correction-link checks.
- Composite foreign keys to ensure an observation's daily-record reference belongs to the same flock and a correction targets the same flock, metric and reporting date.
- `ON DELETE RESTRICT` relationships to preserve observation history.
- Indexes for flock/metric/date, flock/metric/observation time, daily-record linkage and accepted correction successors.
- Triggers rejecting direct UPDATE and DELETE of observation rows.

No legacy observation rows are created by this migration. It does not backfill `daily_records`, change analytics, add observation services, add a UI, or enable sensor/import/system-generated writers. Those remain separate implementation stages.

## 5. Correction representation

The initial observation table supports only an already-accepted correction link: a row with `supersedes_observation_id` must be `observed`, have a non-empty correction reason, and target the same flock, metric and record date. The partial unique index prevents two accepted observations from superseding the same predecessor.

Pending/rejected correction requests and quality-review transitions are not implemented by this migration. They must be represented separately in a later append-only request/review model so rejected attempts do not consume the accepted supersession link.

## 6. Testing boundary

Automated tests use temporary SQLite files and cover:

- Exact baseline recognition and fail-closed rejection of unexpected schemas.
- First adoption, idempotent reruns and checksums.
- Populated legacy row preservation with no backfill.
- Atomic rollback after injected migration failure.
- Foreign-key and CHECK constraints.
- Metric/unit and quality/value compatibility.
- Same-flock daily-record references and parent-delete restrictions.
- Linear correction chains and append-only triggers.
- Read-only status, required backup path and backup refusal/verification in the CLI.

The tests must never locate or open the user's real `data/poultryguard.db`. No application startup path invokes the migration runner.

---
*This document describes the implementation on the feature branch. It does not authorise a live migration or historical backfill.*
