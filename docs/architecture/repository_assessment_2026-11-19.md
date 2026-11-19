# PoultryGuard AI — Repository Assessment

**Assessment date:** 19 November 2026  
**Repository:** \`zulyadainimuhammad/poultryguard-ai\`  
**Inspected ref:** \`main\` at \`d17c4705b658f0f1bc9aa21159d8305e33d0b40a\`  
**Scope:** Read-only inspection of committed repository content  
**Status:** Initial remote-code assessment; local SQLite database not inspected

## 1. Executive summary

The current repository is a modular local Streamlit MVP with Python services, SQLite repositories, local Sentence Transformer/FAISS retrieval and Groq-based answer generation. The existing implementation should be extended incrementally, not replaced wholesale.

The inspected code already enables SQLite foreign-key enforcement in its connection factory. Two engineering risks need attention before provenance and audit features are introduced:

1. Repository methods use SQLite connection context managers without explicitly closing the connections. The SQLite connection context manager handles transaction commit/rollback but does not close the connection.
2. The current schema uses \`ON DELETE CASCADE\` from farms to flocks and from flocks to daily records. A repository-level delete can therefore remove historical operational data.

The assessment is not an approval to change the schema or runtime.

## 2. Repository baseline

- The remote \`main\` branch was inspected at commit \`d17c4705b658f0f1bc9aa21159d8305e33d0b40a\`.
- The user's local VS Code checkout reported the same commit, on local branch \`docs/measurement-provenance-implementation-plan\`.
- The user's local checkout reported three untracked documentation items. Those files were not part of the inspected remote \`main\` tree.
- GitHub Actions reported the CI run for this \`main\` commit as completed successfully. The workflow runs Ruff lint, Ruff format checking, Pytest, knowledge-base validators and an index-preview build.
- This inspection reads committed GitHub content. It does not read the user's local uncommitted files or SQLite database.

## 3. Current application structure

| Area | Current responsibility |
|---|---|
| \`app/frontend/main.py\` | Streamlit Knowledge Assistant and Farm Intelligence UI |
| \`app/services/farm_service.py\` | Farm, flock and daily-record use cases and validation |
| \`app/services/analytics_service.py\` | Flock and environmental analytics |
| \`app/services/answer_generator.py\` | Groq-backed answer generation |
| \`app/database/connection.py\` | SQLite path, connection creation and initial schema |
| \`app/database/models.py\` | Plain \`Farm\`, \`Flock\` and \`DailyRecord\` dataclasses |
| \`app/database/repositories.py\` | Parameterised SQL persistence operations |
| \`rag/\` | Local retrieval, embedding and indexing components |
| \`tests/unit/\` | Service, analytics, retrieval and validation tests |

The inspected runtime does not yet provide production authentication, multi-user authorisation, farm memberships, farm-level tenant isolation or a production API.

## 4. Database findings

### 4.1 Connection path and foreign-key enforcement

The connection module sets \`DATABASE_PATH\` to \`PROJECT_ROOT / "data" / "poultryguard.db"\`. Its \`get_connection()\` function creates the data directory, opens SQLite, configures \`sqlite3.Row\` and executes \`PRAGMA foreign_keys = ON\` before returning the connection.

**Finding:** Foreign-key enforcement is already enabled for connections created through this factory. Add a regression test so the behaviour remains protected.

**Boundary:** The remote inspection cannot establish whether the user's local database file exists or what data it contains. No attempt was made to access or modify it.

### 4.2 Connection lifetime

Repository methods generally use \`with get_connection() as connection:\`. SQLite's connection context manager controls commit/rollback; it does not itself close the connection. The inspected methods do not explicitly close connections.

**Recommendation:** Introduce an explicit connection-lifecycle API or a consistent \`try/finally\` close pattern, with tests. Do this as a separately reviewed change so transaction semantics remain stable.

### 4.3 Existing tables and deletion behaviour

The initial schema creates:

- \`farms\`;
- \`flocks\`, with \`farm_id REFERENCES farms(id) ON DELETE CASCADE\`;
- \`daily_records\`, with \`flock_id REFERENCES flocks(id) ON DELETE CASCADE\`.

The repositories expose delete methods for farms, flocks and daily records. The inspected \`FarmService\` does not expose corresponding deletion use cases, and the inspected Streamlit UI does not present delete controls.

**Finding:** Cascading deletion is currently a repository/database capability, not a confirmed user-facing workflow. It is nevertheless unsafe as the future default once measurement provenance and audit history are introduced.

**Recommendation:** Define archive/retention behaviour and a migration strategy before changing foreign-key delete policies. Do not run a destructive migration against the user's working database.

## 5. Service and transaction findings

- Repository methods open their own connections through \`get_connection()\`.
- \`FarmService.create_daily_record()\` validates the flock, checks duplicate dates unless explicitly bypassed, reads prior records to check remaining flock population, then delegates insertion to \`DailyRecordRepository.create()\`.
- The insert is a single repository transaction, but the overall use case performs validation reads and insertion through separate repository calls/connections.
- \`allow_duplicate=True\` bypasses the service-level duplicate check. No unique constraint on \`(flock_id, record_date)\` was found in the inspected schema.
- There is no daily-record edit method in the inspected repository/service layer. Repository update methods exist for farms and flocks, but the inspected \`FarmService\` does not expose those update use cases.
- No measurement-observation dual-write exists yet.

**Implication:** When daily records and observation rows are eventually written together, participating repositories must share one connection/transaction or an equivalent unit-of-work mechanism. Otherwise partial writes could leave the daily record and observations inconsistent.

Future concurrent multi-user workflows also require a review of duplicate and mortality checks for race behaviour.

## 6. Measurement and UI findings

The current models are plain dataclasses, consistent with the preference to avoid introducing an ORM solely for the first provenance increment.

Optional feed, water, weight, temperature and humidity measurements preserve \`None\`; analytics include genuine numeric zero values. Mortality is non-null and defaults to zero.

The Streamlit mortality input defaults to zero, but the application does not separately record whether the operator explicitly confirmed zero or simply left the default unchanged.

**Recommendation:** Do not automatically interpret every historical mortality zero as an explicitly observed zero during backfill until product semantics are settled.

The current UI supports farm, flock and daily-record creation, listings, analytics and environmental summaries. Environmental values are manually entered; the UI states that live sensor monitoring is not connected. The UI calls \`initialise_database()\` at application startup, so future schema evolution requires a versioned migration path rather than relying on initial table creation alone.

## 7. Tests and CI

The repository contains unit tests for farm service, analytics, answer-generator configuration, knowledge-base validation, chunking and quality validators. Test fixtures use in-memory SQLite and enable foreign keys.

The CI workflow performs Ruff lint, Ruff format checks, Pytest and knowledge-base validation.

No migration framework or migration test suite was found in the inspected tree. Before provenance work is enabled, add tests for connection closure/foreign-key enforcement, empty and populated database migrations, idempotency, preservation/reconciliation, backfill, transaction rollback, rejected-correction resubmission and append-only audit history.

## 8. Recommended implementation order

1. Confirm the authoritative local working tree and database path before any local database operation.
2. Finalise architecture and product decisions, including the no-recurring-cost development constraint, provider deferral, assigned-flock Staff scope and unresolved farm-ownership policy.
3. Define and test explicit SQLite connection lifecycle and shared transaction handling.
4. Decide migration tooling and archive/retention rules; rehearse additive migrations against a database copy.
5. Implement the observation model and insert-only repository operations after schema review.
6. Rehearse historical backfill on a verified copy before enabling dual-write or corrections on existing records.
7. Design correction attempts, review events and accepted supersession relationships so rejected attempts do not block resubmission.
8. Preserve current analytics until a separate parity-tested cutover is approved.

## 9. Explicit limitations

This assessment did not inspect the user's local \`data/poultryguard.db\`, run tests on the user's PC, modify runtime code, install dependencies, apply migrations, inspect credentials or approve architecture decisions. The CI result is the GitHub Actions status for the inspected commit, not a new test run performed during this review.

**Conclusion:** The MVP has a sound modular starting point and existing foreign-key enforcement. The next safe engineering work is connection/transaction lifecycle hardening and a reviewed migration/data-preservation design—not a wholesale rewrite, hosted-service integration or destructive database migration.
