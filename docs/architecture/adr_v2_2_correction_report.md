# PoultryGuard AI — Architecture Decision Register v2.2 Correction Report

**Document status:** Technical correction report — review gate before v2.2 ADR revision  
**Preceding version:** Architecture Decision Register v2.1  
**Stage:** v2.2 final correction  
**Date:** 18 November 2026  
**Scope:** Five blocking issues identified for resolution before v2.2 is drafted  
**Restriction:** Read-only analysis. No code changes, schema migrations, commits or session restarts.  
**Decision statuses preserved:** All existing decision statuses from v2.1 are unchanged. Nothing is marked Approved by this report.

---

## Purpose

This report documents the exact defect in v2.1 for each of the five blocking issues, provides the technically correct design, identifies related ADRs that must be updated when v2.2 is written, defines acceptance tests required to verify the correction, and flags assumptions that need documentation verification before implementation.

---

## Issue 1 — ADR-10: Secure first-administrator bootstrap and identity binding

### 1.1 Exact defect in v2.1

ADR-10 as stated in v2.1 does not define the mechanism by which the very first platform administrator account is created and bound to a verified identity before any user-facing authentication flow is available. The gap has two parts.

**Part A — Bootstrap gap.** The first administrator cannot arrive through the normal invitation flow because that flow requires an existing owner to initiate an invitation. There is no prior owner when the system is first deployed. v2.1 does not specify how this circular dependency is broken, leaving an implicit assumption that someone will create the account out-of-band (for example, directly in the database or through a provider console), without defining how that action is audited or who may perform it.

**Part B — Identity binding gap.** The product requirements distinguish a user account (a person and their sign-in identity) from a farm membership (the link from that person to a specific farm with a role). ADR-10 in v2.1 does not define how the administrator identity created during bootstrap is durably bound to a specific sign-in credential in the chosen identity provider. Without this binding, a bootstrap-created administrator row is an unowned record: any person who later registers with an email that matches, or any support engineer with database access, could silently acquire platform-administrator privilege.

The product requirements document (PRD §4.3, AUTH-05, AUTH-06) requires email ownership verification before sensitive account actions are fully activated, and explicitly prohibits creating duplicate or incorrectly merged identities. v2.1 does not carry these requirements through to the bootstrap procedure.

**Root cause.** The ADR assumes the deployment will start with an existing verified user, skipping the case where no such user exists yet.

### 1.2 Technically correct design

The bootstrap procedure must be a one-time, explicitly gated operation that cannot be triggered again once a platform administrator exists.

**Recommended design:**

1. **Deployment-time bootstrap secret.** Generate a time-limited, single-use secret token at deployment time (not committed to source code and not stored in plaintext). The token is delivered to the deploying operator through a secure out-of-band channel (for example, as a secret in the deployment environment, printed to a secure deploy log, or passed as a one-time environment variable).

2. **Bootstrap endpoint or CLI command.** A distinct, separately authenticated bootstrap path (a one-shot API endpoint or a server-side CLI command accessible only from the host) accepts the secret token plus the intended administrator's verified email address. The endpoint:
   - Validates the token (expiry, single-use, not already consumed).
   - Calls the identity provider to confirm that an account with that email already exists and has a verified email address.
   - Creates the platform administrator record bound to the identity provider's subject identifier (UID/UUID) for that account, not to the email address alone.
   - Marks the bootstrap token as consumed.
   - Writes an audit event: timestamp, actor (the deploying operator identity where available), action `platform_admin_bootstrapped`, outcome.
   - Disables the bootstrap path permanently once a platform administrator record exists.

3. **Guard against re-entry.** On every subsequent startup, the application checks whether a platform administrator record exists. If one does, the bootstrap path returns a permanent error and writes no further records.

4. **Identity binding is to the provider subject ID.** The administrator record stores the identity provider's subject identifier (for Supabase Auth this is `auth.users.id`, a UUID). It does not store the email string as the binding key. Email addresses can change; subject IDs are stable.

5. **Separation from farm ownership.** The platform administrator role is a separate privilege from farm ownership. Creating a platform administrator does not automatically create a farm or farm membership. The two paths must remain independent.

### 1.3 Related ADRs that must be updated

- **ADR-04** (identity provider selection): must document the subject identifier scheme used for binding and confirm that the provider exposes a stable, immutable subject ID.
- **ADR-10** (this ADR): rewrite to include the bootstrap procedure, token lifecycle, guard condition and audit requirement.
- **MIG-08** (product requirements §11): the prohibition on fabricating historical user identities applies equally to the bootstrap: the administrator identity must not be invented or guessed from existing local data.

### 1.4 Acceptance tests

| ID | Test description | Pass condition |
|---|---|---|
| AT-10-01 | Bootstrap with valid token and verified-email account | Platform administrator record created; token marked consumed; audit event written |
| AT-10-02 | Bootstrap with expired token | Rejected; no administrator record created; descriptive error |
| AT-10-03 | Bootstrap with already-consumed token | Rejected; idempotent; no second administrator record created |
| AT-10-04 | Bootstrap attempted when administrator already exists | Rejected with permanent error; no new record; no mutation of existing administrator |
| AT-10-05 | Bootstrap with unverified-email account | Rejected; email verification is a prerequisite |
| AT-10-06 | Administrator record is bound to provider subject ID | Query administrator by subject ID succeeds; query by email alone does not resolve to privileged access |
| AT-10-07 | Bootstrap path is inaccessible after first administrator exists | Endpoint/command returns permanent rejection on subsequent calls |
| AT-10-08 | Audit event is written on successful bootstrap | Audit log contains timestamp, action, outcome; no plaintext secret in audit entry |

### 1.5 Assumptions requiring documentation verification

- **A-10-01:** The chosen identity provider (not yet selected per ADR-04) must expose a stable, immutable subject identifier. If it does not, the binding model must be revised. Verify after ADR-04 is resolved.
- **A-10-02:** The deployment environment must support passing a one-time secret to the bootstrap command without writing it to source code or a shared log. Confirm the CI/CD and secrets management approach (target architecture §5) is compatible.
- **A-10-03:** The administrator bootstrap secret must be generated and stored through the same secrets management path used for all other application credentials. Confirm this path exists before implementation.
- **A-10-04:** The design assumes a single, non-federated identity provider. If multiple providers are supported at launch, the binding must specify which provider's subject ID is the authoritative identifier.

---

## Issue 2 — ADR-07: Measurement correction state transitions and accepted observation derivation

### 2.1 Exact defect in v2.1

ADR-07 in v2.1 covers deployment, backup, monitoring and recovery. However, the measurement provenance documents (Stage 3.2.2 and Stage 3.2.3) have introduced a correction model whose state-transition rules are not fully defined in v2.1. The specific defects are:

**Defect A — `pending_validation` transition is undefined.** The measurement provenance contract defines seven `quality_status` values including `pending_validation`. The Stage 3.2.3 implementation plan (§5.6) explicitly states: "a review workflow may later need to move a candidate from `pending_validation` to `observed` or `invalid`. Do not mutate the original row to achieve that. Before implementing status transitions, design an append-only quality-review/event record." v2.1 does not define this append-only transition mechanism. The result is that any row assigned `pending_validation` is permanently stuck; there is no approved path to accept or reject it.

**Defect B — `accepted observation` derivation rule is ambiguous.** The correction model states that the current accepted value is "the most recent observation that is not itself referenced by an accepted correction." This relies on the phrase "accepted correction." v2.1 does not define what makes a correction accepted versus pending or rejected. If a correction row itself has `quality_status = "pending_validation"`, the derivation rule is circular: the original observation is neither clearly superseded nor clearly current.

**Defect C — Branching correction is not prohibited by constraint.** The Stage 3.2.3 plan notes that a unique index on `supersedes_observation_id` where non-null should prevent two corrections from superseding the same observation. v2.1 does not confirm whether this constraint is part of the approved schema design or merely a recommendation, leaving an implementation gap that could allow two corrections to independently supersede the same row.

**Defect D — Correction of a correction is not addressed.** The chain structure permits `obs_002` to supersede `obs_001`. v2.1 does not define whether `obs_003` may supersede `obs_002` (a chain extension), or whether only the original observation may be superseded. This ambiguity is consequential for the "current accepted value" query.

### 2.2 Technically correct design

**For Defect A — `pending_validation` transition:**

Design an append-only quality-review event record. When a reviewer accepts or rejects a `pending_validation` observation, a new quality-review event row is inserted (not an update to the observation row). The event carries: `review_event_id`, `observation_id` (the observation being reviewed), `reviewer_user_id`, `review_decision` (`accepted` or `rejected`), `review_recorded_at`, and optional `review_notes`.

The observation row is never mutated. `quality_status` on the original row remains `pending_validation`. The effective status of the observation is derived: check whether a review event exists for this observation. If `review_decision = "accepted"`, treat the observation as `observed` for analytics purposes. If `review_decision = "rejected"`, treat it as `invalid`.

This keeps the observation row immutable while providing a complete, auditable decision trail.

**For Defect B — Accepted correction definition:**

An accepted correction is a correction observation whose effective status is `observed` — either directly (the row was inserted with `quality_status = "observed"`) or indirectly (via a review event with `review_decision = "accepted"`). A correction with `quality_status = "pending_validation"` and no review event does not supersede its target.

The derived current-value query therefore becomes: return the observation for a given flock/metric/record_date whose `observation_id` is not referenced by the `supersedes_observation_id` of any observation that is itself effectively `observed`. This definition is unambiguous.

**For Defect C — Uniqueness constraint:**

The unique partial index on `supersedes_observation_id WHERE supersedes_observation_id IS NOT NULL` is a required schema constraint, not an optional recommendation. It must be listed in the approved schema design and verified by a migration test. The service layer must also check this rule before inserting, because SQLite constraint error messages are not user-friendly and the service should produce a descriptive rejection.

**For Defect D — Chained corrections:**

Permit chain extension. `obs_003` may supersede `obs_002` (where `obs_002` already supersedes `obs_001`). This is natural: a second correction may refine a first. The uniqueness constraint on `supersedes_observation_id` already prevents two rows from superseding the same target, so branching is impossible without lifting that constraint. The "current accepted value" query traverses the chain to its end: the observation that has no accepted-correction row pointing to it.

The service must reject attempts to supersede an observation that has already been superseded (i.e., whose `observation_id` already appears in another accepted correction's `supersedes_observation_id`), offering the caller the ID of the current accepted observation instead.

### 2.3 Related ADRs that must be updated

- **ADR-07** (measurement correction and state transitions): add the quality-review event model, the accepted-correction definition, the chain-extension policy and the constraint requirement.
- The Stage 3.2.2 measurement provenance document (`measurement_provenance.md` §8) must be updated to reference the quality-review event record and clarify the `accepted correction` definition.
- The Stage 3.2.3 implementation plan (`measurement_provenance_implementation_plan.md` §5.6, §8 Phase D) must be updated to include quality-review event implementation in the correction-support phase.

### 2.4 Acceptance tests

| ID | Test description | Pass condition |
|---|---|---|
| AT-07-01 | Insert observation with `pending_validation`; query current accepted value | Original observation (if one existed) remains current; `pending_validation` row does not appear as current |
| AT-07-02 | Accept `pending_validation` via review event | Review event written; observation treated as `observed` in current-value query |
| AT-07-03 | Reject `pending_validation` via review event | Review event written; observation treated as `invalid` in current-value query |
| AT-07-04 | Correction with `pending_validation` quality_status | Correction does not supersede original; original remains current |
| AT-07-05 | Two corrections attempt to supersede the same observation | Second insert rejected (unique constraint + service check); first correction stands |
| AT-07-06 | Chain extension: obs_003 supersedes obs_002 | Accepted; obs_003 is current; obs_001 and obs_002 appear in audit history only |
| AT-07-07 | Attempt to supersede an already-superseded observation | Rejected with descriptive error; current-chain head is returned |
| AT-07-08 | Current-value query with multi-step chain | Returns the chain-end observation only; full chain available through audit-history query |
| AT-07-09 | History query returns complete chain | All observations in chain returned, ordered by recorded_at ascending |

### 2.5 Assumptions requiring documentation verification

- **A-07-01:** The append-only quality-review event record is a new table. Its schema, foreign keys and query path must be added to the Stage 3.2.3 implementation plan before Phase D work begins.
- **A-07-02:** The derived effective-status rule (observation row + review event → effective status) must be implemented in one place in the service layer, not duplicated across repository queries. Verify the project's service-layer boundary rules before implementation.
- **A-07-03:** SQLite's support for partial indexes (`WHERE supersedes_observation_id IS NOT NULL`) must be confirmed against the SQLite version in use. Test the constraint in a migration test before relying on it.

---

## Issue 3 — ADR-03/09: SQLite foreign-key enforcement and Alembic batch migrations

### 3.1 Exact defect in v2.1

**ADR-03** covers database selection and migration tooling. **ADR-09** (as defined in v2.1) covers the versioned migration mechanism for the measurement observation layer.

The defects in v2.1 are:

**Defect A — SQLite foreign-key enforcement is not guaranteed at every connection.** SQLite does not enforce foreign keys by default. `PRAGMA foreign_keys = ON` must be set for every connection that opens the database, not once at schema creation time. The Stage 3.2.3 implementation plan (§7.1 item 3) identifies this as a preflight check but does not specify where and how the enforcement pragma is to be set in the application connection lifecycle, nor does it define a test that verifies enforcement is active before any write occurs.

**Defect B — Alembic batch-mode requirement for SQLite is not documented.** SQLite does not support `ALTER TABLE … ADD CONSTRAINT`, `ALTER TABLE … DROP COLUMN` (before version 3.35.0), or `ALTER TABLE … RENAME COLUMN` (before 3.25.0). Alembic's standard migration operations fail silently or raise errors on SQLite for these cases unless batch mode is used. v2.1 does not specify whether Alembic is used, and if it is, whether batch mode is required. The Stage 3.2.2 document (§10 and §11.1) notes that a migration tool such as Alembic must be introduced but leaves the choice open. The implementation plan (§7.2) recommends a small custom runner to avoid a heavyweight dependency. This ambiguity means the team may start implementation with incompatible assumptions about the migration approach.

**Defect C — Foreign-key constraint on the `measurement_observations` self-reference is not tested.** The correction chain uses `supersedes_observation_id` as a self-referencing foreign key. SQLite permits deferred self-referencing foreign keys but requires the constraint to be deferred within the transaction in some cases. v2.1 does not define whether this constraint is `DEFERRABLE INITIALLY DEFERRED` and does not include a test for valid and invalid self-reference scenarios.

### 3.2 Technically correct design

**For Defect A — Foreign-key enforcement:**

Set `PRAGMA foreign_keys = ON` in the connection setup code, not in migration scripts. The connection factory (`app/database/connection.py`) must execute this pragma immediately after every connection is opened, before the connection is returned to the caller. Add an integration test that:
1. Opens a connection.
2. Verifies `PRAGMA foreign_keys` returns `1`.
3. Attempts to insert a row with an invalid foreign key.
4. Verifies the insert raises a constraint error.

This test must be part of the migration test suite and must run against both an empty and a populated test database.

**For Defect B — Migration tooling decision:**

Make a binding choice before Phase A work starts. Two options:

- **Option 1 — Alembic with SQLite batch mode.** Use `with op.batch_alter_table(...)` for every migration that modifies an existing table's columns or constraints. This is required for all table alterations on SQLite. Document this requirement in the migration contribution guide. The tradeoff is a dependency on SQLAlchemy and Alembic.

- **Option 2 — Custom versioned migration runner.** Implement a small migration ledger table and ordered migration script files as described in the Stage 3.2.3 plan (§7.2). Each migration file uses raw SQL. The runner records applied versions and runs each migration in a transaction. The tradeoff is that the team maintains the runner; there is no community tooling for edge cases.

Both options are viable. The choice must be documented in ADR-03 or ADR-09 with explicit rationale. The recommendation from the existing implementation plan is Option 2 for the first increment, to avoid introducing a heavyweight ORM dependency solely for this stage. If the project later adopts SQLAlchemy for the ORM layer, revisiting Alembic at that point is rational.

Regardless of choice: every migration that adds a column to an existing table must use `ALTER TABLE … ADD COLUMN` (which SQLite supports for nullable columns without a default or for columns with a constant default). Adding a non-nullable column without a default to an existing table with rows is not directly supported in SQLite and requires a table-rebuild strategy (rename, create, copy, drop). The migration plan must identify which new columns require this strategy and test it.

**For Defect C — Self-referencing foreign key:**

Declare `supersedes_observation_id` with `REFERENCES measurement_observations(observation_id) DEFERRABLE INITIALLY DEFERRED`. The deferred constraint allows inserting a correction row that references an `observation_id` within the same transaction before the referenced row is committed (necessary if both rows are being inserted in one atomic operation, though in this design the original always precedes the correction). Add an integration test for:
1. Valid self-reference (correction pointing to an existing observation in the same flock/metric).
2. Invalid self-reference (correction pointing to a non-existent `observation_id`) — must be rejected.
3. Cycle detection: correction A supersedes B; attempt to make B supersede A — must be rejected at the service layer before the constraint is tested.

### 3.3 Related ADRs that must be updated

- **ADR-03** (database and migration tooling): add the SQLite foreign-key enforcement requirement, the migration-tooling decision, and the batch-mode/table-rebuild constraint.
- **ADR-09** (measurement observation migration): add the self-referencing constraint declaration, the deferral policy, and the migration test requirements.
- `measurement_provenance_implementation_plan.md` §7.1 (preflight) and §7.2 (versioned runner): update to reflect the binding tooling choice and the foreign-key enforcement requirement.

### 3.4 Acceptance tests

| ID | Test description | Pass condition |
|---|---|---|
| AT-03-01 | Open connection; verify `PRAGMA foreign_keys` | Returns `1` |
| AT-03-02 | Insert flock row with non-existent `farm_id` | Rejected with foreign-key constraint error |
| AT-03-03 | Insert `daily_records` row with non-existent `flock_id` | Rejected with foreign-key constraint error |
| AT-03-04 | Insert `measurement_observations` row with non-existent `flock_id` | Rejected with foreign-key constraint error |
| AT-03-05 | Insert `measurement_observations` correction with non-existent `supersedes_observation_id` | Rejected with foreign-key constraint error |
| AT-03-06 | Migration ledger records applied version; re-running returns without error | No duplicate migration applied; ledger entry count matches expected |
| AT-03-07 | Migration on populated database preserves existing row counts | Farms, flocks, daily_records counts unchanged after migration |
| AT-03-08 | `PRAGMA foreign_key_check` after migration | Returns no violations |
| AT-03-09 | Table-rebuild migration (non-nullable column add) on copy of populated DB | Schema change applied; existing data preserved; no row count change |

### 3.5 Assumptions requiring documentation verification

- **A-03-01:** The SQLite version installed in the target development and production environment must be identified. SQLite 3.35.0 or later is required for `DROP COLUMN`; 3.25.0 or later for `RENAME COLUMN`. Confirm the installed version before writing migration scripts that use these operations.
- **A-03-02:** The existing `app/database/connection.py` connection factory must be inspected to confirm whether `PRAGMA foreign_keys = ON` is already set. The Stage 3.2.3 preflight (§7.1 item 3) identifies this as a check to perform. It has not yet been verified as part of this document.
- **A-03-03:** If Alembic is chosen, confirm that SQLAlchemy is not already a dependency. If it is, adoption is lower cost. If it is not, the custom runner is the lower-dependency option.

---

## Issue 4 — ADR-05/15: Active farm ownership invariants and concurrent membership operations

### 4.1 Exact defect in v2.1

**ADR-05** covers the tenant/farm membership and permission enforcement model. **ADR-15** (as defined in v2.1) covers concurrent membership operations and ownership transfer.

The defects in v2.1 are:

**Defect A — The "last owner cannot leave" invariant has no enforcement mechanism.** The product requirements (PRD §4.5, FARM-06) state that "the last owner cannot simply leave without transferring ownership." v2.1 does not define the check that enforces this invariant at the service layer. Without a named, tested guard, the invariant can be violated by a concurrent or rapid sequence of operations: two co-owners resign their ownership simultaneously, leaving the farm ownerless.

**Defect B — Ownership transfer has no atomic isolation.** The product requirements (PRD §4.5, FARM-07) require explicit confirmation, re-authentication where appropriate, and an audit event. v2.1 does not specify how the transfer is made atomic relative to concurrent membership changes. For example: an owner initiates a transfer to Manager A. Before the transfer commits, the owner changes Manager A's role to Staff. The farm could end up with a staff-role owner, which violates the invariant that the owner role has specific privileges.

**Defect C — Membership deduplication is not enforced at the data layer.** The product requirements (PRD §5.2, TEAM-08) state that re-inviting an existing member must not create duplicate memberships. v2.1 does not define a unique constraint or service-layer guard for this case, nor does it specify the behaviour when an invitation is sent to a user who already holds an active membership.

**Defect D — Farm membership queries are not explicitly scoped.** ADR-05 states that farm-level data isolation must be enforced in backend services and data-access queries, not only in the UI. v2.1 does not define the query pattern that ensures a request to read Farm B's data (from a user holding only Farm A membership) is rejected at the data-access layer, not merely hidden in the interface.

### 4.2 Technically correct design

**For Defect A — Last-owner invariant:**

The `FarmMembershipService` must enforce a named invariant check before any membership action that could reduce owner count:

```
INVARIANT: at all times, every active farm must have at least one active member with role = Owner.
```

Before removing a membership, downgrading a role from Owner, or accepting an ownership transfer that removes the current owner, the service must count active owner memberships for the farm. If the count after the proposed operation would be zero, the operation is rejected with a descriptive error. This check must run inside the same transaction as the membership write; it must not be a pre-flight check that another concurrent request can race.

**For Defect B — Atomic ownership transfer:**

Ownership transfer is a two-phase operation:

1. **Initiation:** the current owner nominates a new owner by user ID. A pending transfer record is created: `farm_id`, `from_user_id`, `to_user_id`, `initiated_at`, `token` (single-use, time-limited), `status = pending`. The current owner's role is not yet changed.

2. **Confirmation:** the nominated new owner accepts the transfer by presenting the token and re-authenticating. Inside one database transaction: set the new owner's role to Owner; set the outgoing owner's role to Manager (or the owner may choose to withdraw from the farm entirely, subject to the last-owner invariant). Mark the transfer record `status = completed`. Write audit events for both role changes. No other concurrent membership write may touch either user's role for this farm while the transfer is in `pending` state (use a row-level lock or a serialisable transaction).

A pending transfer record blocks role changes to either participant for that farm until the transfer completes, expires, or is cancelled.

**For Defect C — Membership deduplication:**

Add a unique constraint on `(farm_id, user_id)` in the farm membership table. This prevents duplicate rows at the data layer regardless of race conditions. The service must also check for an existing pending invitation before creating a new one: if an active invitation or active membership exists for `(farm_id, email)`, reject the duplicate invitation with a descriptive message rather than silently creating a second record.

**For Defect D — Farm-scoped query pattern:**

Every repository method that returns farm-scoped data must accept `(farm_id, requesting_user_id)` and include both as conditions in the query. The pattern:

```sql
SELECT ... FROM <table>
WHERE farm_id = :farm_id
  AND EXISTS (
    SELECT 1 FROM farm_memberships
    WHERE farm_id = :farm_id
      AND user_id = :requesting_user_id
      AND status = 'active'
  )
```

This embeds the authorisation check in the data layer. The service layer may additionally perform role-level checks. The UI hiding an element is not a substitute for this query-level check. Integration tests must demonstrate that a query from a user with no membership for the requested farm returns empty or raises a permission error.

### 4.3 Related ADRs that must be updated

- **ADR-05** (membership and permission enforcement): add the last-owner invariant definition, the deduplication constraint, and the farm-scoped query pattern.
- **ADR-15** (concurrent membership and ownership transfer): rewrite to include the two-phase atomic transfer protocol, the pending transfer lock, and the invariant-check transaction requirement.
- PRD §4.5 FARM-06, FARM-07 requirements are already correctly stated; ADR-05 and ADR-15 must be revised to show how the implementation satisfies them.

### 4.4 Acceptance tests

| ID | Test description | Pass condition |
|---|---|---|
| AT-05-01 | Single owner attempts to leave farm | Rejected; descriptive error; membership unchanged |
| AT-05-02 | Single owner attempts to downgrade own role | Rejected; role unchanged |
| AT-05-03 | Two owners simultaneously resign | One succeeds; the second is rejected; farm retains exactly one owner |
| AT-05-04 | Ownership transfer: current owner initiates; new owner confirms | Both role changes occur in one transaction; audit events written; pending transfer marked completed |
| AT-05-05 | Ownership transfer: role of nominee changed during pending state | Role-change rejected while transfer is pending |
| AT-05-06 | Ownership transfer token expires | Confirmation rejected after expiry; both roles unchanged; transfer marked expired |
| AT-05-07 | Re-invite existing active member | Rejected with descriptive error; no duplicate membership or invitation created |
| AT-05-08 | Re-invite user with pending invitation | Rejected or existing invitation reused; no duplicate invitation |
| AT-05-09 | Unique constraint on `(farm_id, user_id)` | Direct insert attempt of duplicate membership rejected at database layer |
| AT-05-10 | User with no membership queries Farm B data | Query returns empty or permission error; no Farm B data returned |
| AT-05-11 | User with Farm A membership queries Farm B | Same result as AT-05-10; farm membership does not bleed across farms |

### 4.5 Assumptions requiring documentation verification

- **A-05-01:** The database supporting the production deployment must support serialisable transactions or row-level locking for the ownership transfer. SQLite supports serialisable isolation for the whole database (WAL mode excepted, where only the writer holds an exclusive lock). Confirm that the last-owner check and role-change write can be executed atomically in the target database. If PostgreSQL is adopted (ADR-03), use `SELECT … FOR UPDATE` on the membership rows.
- **A-05-02:** The pending transfer lock mechanism must be tested under concurrent load. For the SQLite single-writer model this is straightforward; for PostgreSQL concurrent access it requires explicit locking tests.
- **A-05-03:** The unique constraint on `(farm_id, user_id)` assumes one membership row per user per farm. If the design later supports multiple historical membership rows (for audit purposes), the unique constraint must apply only to `status = 'active'` rows. Document this design decision before implementation.

---

## Issue 5 — ADR-11: Correct mapping between internal user IDs and Supabase Auth UUIDs

### 5.1 Exact defect in v2.1

ADR-11 as stated in v2.1 defines the relationship between the application's internal user identity model and Supabase Auth's UUID-based subject identifiers. The defects are:

**Defect A — Identity provider is not yet selected.** The product requirements (PRD §4.3) and target architecture both state that no identity provider has been selected. ADR-04 is explicitly open (not approved). ADR-11 names Supabase Auth specifically. This creates a logical dependency error: ADR-11 makes implementation commitments that depend on a provider-level decision (ADR-04) that has not been made. If ADR-04 resolves to a different provider, ADR-11 is invalid in its current form.

**Defect B — The mapping table design does not enforce referential integrity in both directions.** v2.1 defines an `app_users` table with a `supabase_auth_uuid` column. It does not define what happens when: (a) a Supabase Auth user is deleted; (b) the same Auth UUID appears twice in `app_users` (due to a race condition at registration); or (c) an `app_users` row is created before the corresponding Auth account has completed email verification. Without addressing these cases, the mapping can become inconsistent.

**Defect C — Email address is used as a secondary lookup key in some flows.** v2.1 describes using email to look up an `app_users` record in certain flows (password reset, invitation acceptance). Email addresses are not stable: they can change in the identity provider without necessarily triggering an update to `app_users`. Using email as a lookup key for security-sensitive flows risks matching the wrong account after an email change.

**Defect D — The mapping creation point is not atomic with identity provider account creation.** When a user registers, there is a window between the identity provider creating the Auth account and the application inserting the `app_users` row. If the application crashes or the request fails in this window, the Auth account exists but the `app_users` row does not. v2.1 does not define the reconciliation procedure for this split-brain state.

### 5.2 Technically correct design

**For Defect A — Provider dependency:**

ADR-11 must be explicitly conditioned on ADR-04. The correct approach is to rename or restructure ADR-11 as "Internal user identity model and provider-subject-ID mapping," describe the invariants that must hold regardless of provider, and then add a provider-specific appendix when ADR-04 is resolved. The invariants are:

- Every `app_users` row has exactly one provider subject ID (`provider_subject_id`) from exactly one provider (`provider_name`).
- The `(provider_name, provider_subject_id)` pair is unique in `app_users`.
- Internal application entities (farm memberships, audit events, observation provenance) reference `app_users.id` (the application's internal integer or UUID primary key), not the provider subject ID directly.
- The provider subject ID is used only at authentication time to resolve the `app_users.id`.

This design is provider-agnostic. The provider-specific details (e.g., Supabase's `auth.users.id` schema, JWT claim names) go in an appendix written after ADR-04 is approved.

**For Defect B — Mapping table integrity:**

- Add a `UNIQUE` constraint on `provider_subject_id` in `app_users`.
- Define the behaviour on Auth-side user deletion: the application must not delete the `app_users` row automatically (this would cascade-delete audit history and observation provenance). Instead, mark the row `status = 'deactivated'` and record the deactivation timestamp and reason. Audit events and observation provenance rows that reference this user remain intact and attributable.
- Guard against pre-verification mapping: do not insert the `app_users` row until email verification is confirmed by the identity provider. Use the provider's webhook or JWT claim (`email_verified: true`) as the trigger for `app_users` row creation, not the initial registration event.

**For Defect C — Email as lookup key:**

Remove email as the lookup key for security-sensitive flows. All flows that resolve a user identity must use the provider subject ID (from the authenticated session's JWT claim) or the application's internal `app_users.id`. Email may be displayed for human-readable confirmation but must not be the resolution key. For invitation acceptance (where the invited email must match the authenticated user's email), validate the match at the application layer using the provider's current verified email from the session JWT, not from the `app_users` table, since the table's email could be stale.

**For Defect D — Mapping creation atomicity:**

Use a reconciliation strategy:

1. When a user first authenticates after registration, the application checks whether an `app_users` row exists for the provider subject ID.
2. If it does not exist and the JWT carries `email_verified: true`, insert it now (a "lazy mapping" on first authenticated access).
3. If it does not exist and `email_verified` is false, reject the session with a prompt to verify email.
4. This eliminates the creation-time race: the `app_users` row is created at the first successful authenticated access, which only occurs after the provider has confirmed the account.

Alternatively, use the provider's post-verification webhook to create the `app_users` row. If using Supabase Auth, this is the `auth.users` `AFTER INSERT` trigger path or the Supabase Function webhook. The webhook approach is provider-specific and must be documented in the ADR-04 appendix.

### 5.3 Related ADRs that must be updated

- **ADR-04** (identity provider selection): must be resolved before ADR-11 can be fully specified. ADR-11 currently depends on ADR-04 without declaring this dependency.
- **ADR-11** (internal user ID and provider UUID mapping): rewrite to be provider-agnostic for the invariants section; add a Supabase-specific appendix conditional on ADR-04 resolution; add integrity constraints, deactivation policy, and lazy-mapping reconciliation procedure.
- **ADR-10** (bootstrap): cross-reference — the bootstrap procedure must bind to `app_users.provider_subject_id`, not to email, as established in this correction.
- PRD §4.3, AUTH-05, AUTH-06, AUTH-10: these requirements are already correctly stated; ADR-11 must show how the mapping design satisfies them.

### 5.4 Acceptance tests

| ID | Test description | Pass condition |
|---|---|---|
| AT-11-01 | Unique constraint on `(provider_name, provider_subject_id)` in `app_users` | Duplicate insert rejected at database layer |
| AT-11-02 | First authenticated access after registration (email verified) | `app_users` row created lazily; subsequent access resolves same row |
| AT-11-03 | First authenticated access with unverified email | Session rejected; `app_users` row not created |
| AT-11-04 | Auth-side user deactivated; application access attempted | Session rejected; `app_users` row marked `deactivated`; audit and provenance rows intact |
| AT-11-05 | Email changes in provider; user authenticates | Application resolves user by provider subject ID, not email; correct `app_users` row returned |
| AT-11-06 | Invitation acceptance: authenticated email matches invitation email | Membership activated; resolution uses JWT email claim, not stored `app_users` email |
| AT-11-07 | Invitation acceptance: authenticated email does not match invitation | Rejected; descriptive error; membership not activated |
| AT-11-08 | Concurrent registration with same provider subject ID | Only one `app_users` row created; second insert rejected by unique constraint |
| AT-11-09 | Internal entities reference `app_users.id` not provider subject ID | Spot-check: farm memberships, audit events, observation `entered_by_user_id` carry `app_users.id` or a stable internal identifier |
| AT-11-10 | Bootstrap administrator bound to provider subject ID | Bootstrap test: resolve admin by subject ID succeeds; email-only lookup does not grant privilege |

### 5.5 Assumptions requiring documentation verification

- **A-11-01:** ADR-04 (identity provider selection) is a hard prerequisite for the provider-specific appendix of ADR-11. This report cannot verify the Supabase-specific schema (`auth.users.id`, JWT claim names, webhook availability) without ADR-04 being resolved. All Supabase-specific details in this correction report are illustrative and must be verified against the actual chosen provider's documentation before implementation.
- **A-11-02:** The lazy-mapping strategy requires that every code path that accesses `app_users` can tolerate the row not existing yet, triggering creation on first access. This must be verified against the existing service-layer design to confirm there are no code paths that assume `app_users` always exists for any authenticated session.
- **A-11-03:** "Email verified" must be a verifiable JWT claim from the provider. If the provider does not expose this claim or the claim can be forged, an alternative verification path must be defined. Confirm with the chosen provider's documentation after ADR-04 is resolved.

---

## Cross-cutting notes

The following points apply to two or more of the five issues.

### Audit event consistency

Issues 1, 4 and 5 all require audit events. v2.1 does not define a common audit-event schema. Before implementing any of these flows, define:

- A shared `audit_events` table with: `event_id`, `farm_id` (nullable for platform-level events), `actor_user_id` (nullable for bootstrap events), `action` (enumerated), `target_type`, `target_id`, `outcome` (`success` / `failure`), `recorded_at`, `notes`.
- The `action` enumeration must include at minimum: `platform_admin_bootstrapped`, `farm_created`, `membership_invited`, `membership_accepted`, `membership_revoked`, `role_changed`, `ownership_transfer_initiated`, `ownership_transfer_completed`, `ownership_transfer_cancelled`, `observation_corrected`, `quality_review_accepted`, `quality_review_rejected`.

### ADR dependency ordering

Before detailed implementation can begin, the following ADR dependency chain must be resolved in order:

1. ADR-04 (identity provider) → unblocks ADR-11 (user ID mapping)
2. ADR-11 (user ID mapping) → unblocks ADR-10 (bootstrap) and ADR-05 (membership)
3. ADR-03 (database and migration tooling) → unblocks ADR-09 (observation migration)
4. ADR-07 (correction state transitions) → unblocks Stage 3.2.3 Phase D

### Nothing in this report is Approved

All existing decision statuses from v2.1 are preserved unchanged. This report identifies defects and specifies the correct designs; it does not authorise any ADR as Approved. Each ADR must follow its own review and approval process.

---

*End of technical correction report. Proceed to v2.2 ADR revision only after each section above has been reviewed by the responsible architect and product owner.*