# PoultryGuard AI — Repository Assessment

**Assessment date:** 19 November 2026  
**Repository:** `zulyadainimuhammad/poultryguard-ai`  
**Inspected ref:** `main` at `275f60b3b35c88510a2e9c3bf5fd4de54ae91ed3` (`275f60b`)  
**Scope:** Read-only inspection of committed repository content  
**Status:** Updated baseline assessment; local SQLite database not inspected

## 1. Executive summary

The current repository is a modular local Streamlit MVP with Python services, SQLite repositories, local Sentence Transformer/FAISS retrieval and Groq-based answer generation. The current application should be extended incrementally, not replaced wholesale.

The connection-lifecycle concern from the previous assessment has been fixed: the connection factory enables foreign keys per connection and closes connections when their context exits. The change is merged to `main` and has dedicated tests.

The principal preconditions for measurement-provenance work are now: define a shared transaction/unit-of-work boundary, settle archive/retention behaviour for existing cascading foreign keys, and resolve the correction-attempt/accepted-supersession model. No schema change is authorised by this assessment.

## 2. Repository baseline and limits

- The inspected remote `main` ref is `275f60b3b35c88510a2e9c3bf5fd4de54ae91ed3`.
- This assessment covers committed GitHub files at that ref.
- It does not inspect the user's local SQLite database, local credentials, uncommitted working-tree content or local-only files.
- The user reported that, after fast-forwarding the local checkout to `main`, `python -m pytest` completed with **112 passed** and `ruff check .` reported **All checks passed**. These are user-reported local results, not commands independently run by this assessment.

## 3. Current application structure

| Area | Current responsibility |
|---|---|
| `app/frontend/main.py` | Streamlit Knowledge Assistant and Farm Intelligence UI |
| `app/services/farm_service.py` | Farm, flock and daily-record use cases and validation |
| `app/services/analytics_service.py` | Flock and environmental analytics |
| `app/services/answer_generator.py` | Groq-backed answer generation |
| `app/database/connection.py` | SQLite path, connection creation and initial schema |
| `app/database/models.py` | Plain `Farm`, `Flock` and `DailyRecord` dataclasses |
| `app/database/repositories.py` | Parameterised SQLite persistence operations |
| `rag/` | Local retrieval, embedding and indexing components |
| `tests/unit/` | Service, analytics, retrieval, validation and connection tests |

The inspected runtime does not provide production authentication, multi-user authorisation, farm memberships, farm-level tenant isolation, a production API or sensor ingestion.

## 4. Database findings

### 4.1 Connection lifecycle and foreign keys

`app/database/connection.py` defines `_ClosingSQLiteConnection`; its context-manager exit delegates to SQLite's commit/rollback behaviour and closes the connection in a `finally` block. `get_connection()` enables `PRAGMA foreign_keys = ON` immediately after opening each connection.

`tests/unit/test_connection.py` verifies that the pragma returns 1, successful context use commits, exceptional context use rolls back, and the connection is closed after exit.

**Finding:** connection lifetime and per-connection foreign-key enforcement are now covered by the merged connection fix. Do not repeat the earlier recommendation to implement connection closure.

### 4.2 Existing tables and deletion behaviour

The initial schema creates:

- `farms`;
- `flocks`, with `farm_id REFERENCES farms(id) ON DELETE CASCADE`; and
- `daily_records`, with `flock_id REFERENCES flocks(id) ON DELETE CASCADE`.

Repositories expose delete methods for farms, flocks and daily records. The inspected `FarmService` does not expose corresponding farm/flock/daily-record deletion use cases, and the inspected Streamlit UI does not present delete controls.

**Finding:** cascading deletion is a database/repository capability, not evidence of a confirmed user-facing workflow. Define archive, retention and history-preservation rules before changing foreign-key policies or introducing observations/audit history.

## 5. Service, repository and transaction findings

- Repository methods acquire their own connection through `get_connection()`.
- `FarmService.create_daily_record()` reads the flock, checks for an existing flock/date record unless `allow_duplicate=True`, reads prior records to check cumulative mortality, builds a `DailyRecord` and delegates insertion.
- Those reads and the insert occur through separate repository calls/connections. The insert operation has its own transaction, but the entire service use case does not currently share one connection.
- `allow_duplicate=True` bypasses service-level duplicate-date validation. No unique constraint on `(flock_id, record_date)` was found in the inspected schema.
- No daily-record edit method was found in the inspected `FarmService` or `DailyRecordRepository`.
- No measurement-observation dual-write exists.

**Implication:** daily-record and observation persistence must share one SQLite connection/transaction (or an equivalent explicit unit-of-work) before dual-write is introduced. The service's validation reads should be included in the chosen consistency boundary where needed. Do not add a unique daily-record constraint until existing duplicates and intended override semantics are reviewed.

## 6. Measurement and UI findings

- The current models are plain dataclasses; an ORM is not required by the existing model pattern.
- Optional feed, water, average weight, temperature and humidity measurements can be `NULL`; analytics preserve genuine numeric zero values.
- Mortality is non-null and defaults to zero in the model/schema and Streamlit input.
- The UI does not separately record whether the operator explicitly confirmed zero or left the default unchanged.
- The current daily-record UI supports creating entries; no edit/correction workflow was found in the inspected application path.
- Environmental values are manually entered. The UI does not claim live sensor monitoring is connected.

**Recommendation:** Do not infer that historical mortality zero was explicitly measured. Do not manufacture historical observation timestamps, user identities, sensor sources or calibration details.

## 7. Current AI and connectivity boundary

Knowledge-base retrieval, embeddings and FAISS search are local components. Answer generation calls the Groq API through the configured client and therefore requires internet connectivity and configured API access.

**Recommendation:** Do not describe the current assistant as fully offline. The project's zero-recurring-infrastructure-cost development constraint does not itself establish that an external API is free, unlimited or guaranteed to remain on a free tier.

## 8. Tests and CI

The repository includes unit tests for farm service, analytics, answer-generator configuration, knowledge-base validation, markdown chunking, quality validators and SQLite connection lifecycle. The CI workflow runs Ruff, formatting checks, Pytest and knowledge-base validation/build checks.

The user's reported local run after syncing `main` was 112 passing tests and a successful Ruff lint check. A separate local database migration suite does not yet exist. No migration framework was found in the inspected repository.

Before provenance work is enabled, add tests for empty and populated-copy migration, migration-ledger adoption, idempotency, row/value preservation, backfill, foreign-key validation, shared-transaction rollback, rejected-correction resubmission and append-only review/audit history.

## 9. Recommended engineering order

1. Review and reconcile the product requirements, correction report, implementation plan and current architecture register.
2. Finalise the correction-attempt, review-event and accepted-supersession design, including daily-record grouping.
3. Design a small shared SQLite connection/unit-of-work boundary without changing the schema.
4. Decide migration tooling and the archive/retention policy.
5. Rehearse an additive observation migration against disposable empty and populated database copies.
6. Reconcile deterministic historical backfill and zero/missing semantics.
7. Add observation dual-write only after atomic rollback tests pass.
8. Keep existing analytics on `daily_records` until a separate parity-tested cutover is approved.

## 10. Explicit limitations

This assessment did not inspect the user's local `data/poultryguard.db`, execute tests on the user's PC, modify runtime code, install dependencies, apply migrations, inspect credentials or approve architecture decisions.

**Conclusion:** The MVP has a sound modular starting point. The SQLite connection lifecycle fix is complete on the reviewed baseline. The next safe engineering work is transaction-boundary design and correction/migration reconciliation—not hosted-service integration, a wholesale rewrite or a destructive database migration.
