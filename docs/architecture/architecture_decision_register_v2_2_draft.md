# PoultryGuard AI — Architecture Decision Register v2.2 (Draft)

**Document status:** Consolidated architecture review draft — not approved for implementation  
**Version:** 2.2-draft  
**Prepared:** 19 November 2026  
**Approval status:** No architecture decision is newly marked Approved by this draft.

## 1. Purpose

This register consolidates the available product requirements, current software architecture, target architecture, measurement-provenance design, implementation plan, correction report and repository assessment. It preserves the internationally ambitious product direction while controlling early-stage costs and protecting the working MVP and its farm data.

This document is a review draft. It does not approve code changes, database migrations, production deployment, paid subscriptions or a production identity provider.

## 2. Evidence and numbering limitations

The original standalone Architecture Decision Register v2.1 and its complete 20-decision approval history have not been recovered from the inspected files or available branches.

The Product Requirements document explicitly identifies ADR-01 through ADR-07. Those titles are treated as the source-verified canonical numbering for this draft. References to ADR-09, ADR-10, ADR-11 and ADR-15 in the correction report are retained as legacy references, but their canonical numbering is unverified.

There is a conflict in the correction report's use of ADR-07: the PRD assigns ADR-07 to deployment, backup, monitoring and recovery, while the correction report also uses ADR-07 for measurement corrections. This draft retains the PRD's ADR-07 title and tracks measurement correction as a supplementary decision topic. No silent renumbering or invented approval status is permitted.

## 3. Product vision and international experience

PoultryGuard AI is intended to evolve from a local poultry-management MVP into an AI-powered poultry farm intelligence platform. The target product includes:

- AI Knowledge Assistant;
- Farm and Flock Records;
- Farm Monitoring and Environmental Data;
- Farm Analytics;
- AI Farm Intelligence;
- explainable Insights and Alerts; and
- farmer-initiated Expert Support involving qualified veterinary and agricultural professionals.

Cloud Engineering is a cross-cutting foundation for APIs, hosting, data, identity, security, CI/CD, observability and recovery.

The international product ambition is retained: a professional, accessible, responsive desktop/tablet/mobile experience, clear farm workspaces, polished analytics, source-attributed AI assistance, explainable insights and future expert workflows. A demo may use sample data only when it is clearly labelled. Simulated functionality must not be presented as implemented or as evidence of validated farmer impact.

## 4. Current implemented baseline

The inspected repository at \`d17c470\` is a local, single-process Streamlit MVP using Python services, SQLite repositories, farm/flock/daily-record workflows, analytics, local Sentence Transformer/FAISS retrieval and Groq-based answer generation.

The inspected runtime does not yet provide production authentication, multi-user authorisation, farm memberships, farm-level isolation, managed multi-tenant hosting, sensor ingestion, a separate AI insight engine, automated alerts or integrated expert referrals.

The target architecture must evolve the MVP rather than discard it.

## 5. Agreed development and cost constraint

**Agreed product-owner direction (19 November 2026):** target **₦0 recurring infrastructure expenditure** during development and initial product validation. No paid subscription or recurring service is to be introduced without explicit discussion and approval.

Preferred approaches are local development, SQLite for local development/testing, open-source libraries, local test identity adapters, mock/local email delivery, local RAG retrieval and locally runnable demonstrations. Do not make essential development workflows dependent on free-tier services that can pause, expire or force an upgrade.

This is a stage-specific cost constraint, not a permanent limitation on the target architecture. After product validation and a credible funding/revenue plan, evaluate paid providers based on cost, reliability, data export, security, backup/restore, lock-in and migration path.

## 6. Canonical PRD decision gates

| ID | Source-verified decision topic | Draft position | Status |
|---|---|---|---|
| ADR-01 | Frontend: evolve Streamlit for an interim release or introduce a separate frontend | Preserve the current Streamlit MVP. Evaluate React/Next.js and alternatives against usability, accessibility, mobile experience, delivery effort and cost. | Open |
| ADR-02 | Backend/API approach and service boundaries | Preserve Python application services and repository boundaries. FastAPI remains a future API candidate, not selected. | Open |
| ADR-03 | Production database and migration tooling | SQLite remains the local development baseline. PostgreSQL is a production candidate, subject to comparison and tested migration. Migration tooling remains open. | Open |
| ADR-04 | Identity provider and account-linking policy | Defer provider selection. Define provider-neutral identity contracts first. Supabase, Firebase and Clerk are future candidates only; none is selected. | Deferred |
| ADR-05 | Tenant/farm membership and permission enforcement | Enforce farm membership, role and flock-assignment checks in backend/data-access paths. Support multiple farms per user and explicit farm context. | Proposed |
| ADR-06 | Invitation delivery, email verification and notifications | Design single-use, expiring, revocable invitations. Use mock/local email in development. Production email provider deferred. | Open |
| ADR-07 | Deployment, backup, monitoring and recovery | Keep development local. Specify backup/restore and operational requirements before external deployment. Cloud provider/topology not selected. | Open |

## 7. Supplementary architecture decision topics

Final ADR numbering for these topics must be reconciled if the original v2.1 register is recovered.

| Working ID | Topic | Draft position | Status |
|---|---|---|---|
| SUP-01 | Measurement provenance | Retain \`daily_records\`; introduce granular \`measurement_observations\` additively. Existing analytics remain on \`daily_records\` until a separate parity-tested cutover. | Proposed |
| SUP-02 | Correction attempts and accepted supersession | Separate correction attempts/reviews from accepted supersession relationships. A rejected attempt remains auditable but does not supersede or block a later valid attempt. | Proposed |
| SUP-03 | Internal identity mapping | Application-owned internal user IDs are referenced by memberships, audit and provenance. External identities are separate and unique by provider plus stable subject ID. Email is not a permanent identity key. | Proposed |
| SUP-04 | First platform administrator | If a platform-admin role is required, use a one-time, high-entropy, expiring, hashed and atomically consumed bootstrap secret. Bind the administrator to an authenticated provider subject, not email alone. | Proposed |
| SUP-05 | Farm ownership invariant | Every active farm must retain at least one active Owner. Whether multiple simultaneous Owners are allowed remains unresolved. | Open |
| SUP-06 | Staff permission scope | Product-owner-selected proposal: Staff access is limited to assigned flocks in the first multi-farm release. Final approval and the exact read/write capability catalogue remain pending. | Proposed; approval pending |
| SUP-07 | Farm switching and request context | Switching farms changes the complete data context. Every protected operation validates farm membership and relevant permissions. | Required; implementation pending |
| SUP-08 | Farm-aware AI isolation | Separate shared poultry knowledge from farm-specific records. Authorise farm context before retrieval or external AI transmission; isolate histories, caches, logs and derived outputs. | Target requirement |
| SUP-09 | Archive and deletion policy | Do not permit parent deletion to silently cascade into observation/audit history. Define archive, retention and restrictive FK rules before migration. | Proposed |
| SUP-10 | Shared audit events | Define common platform/farm audit events. Successful business writes and their audit entries should be atomic; failed security events need a durable safe logging path. | Proposed |
| SUP-11 | Quality-review transitions | Use append-only quality-review events for pending-validation decisions. Do not mutate original observations to record review outcomes. | Proposed |
| SUP-12 | SQLite connection and transaction lifecycle | Keep foreign-key enforcement enabled per connection; explicitly close connections; share one transaction for logical multi-repository writes. | Required engineering work |
| SUP-13 | Zero-recurring-cost development | No recurring service/subscription without explicit product-owner approval during development and initial validation. | Agreed project constraint |
| SUP-14 | Agriculture-led product evolution | New agricultural ideas may be proposed at any stage and assessed for user value, evidence, safety, cost and architecture impact. | Agreed working principle |

## 8. Staff permissions — selected proposal

The product owner selected **assigned-flock-only access** as the proposed first-release Staff scope, pending final approval.

Under this proposal, Staff membership alone does not grant access to every flock in a farm. Staff permissions must additionally check the user's active assignment to the requested flock. Owners and appropriately delegated Managers administer assignments. Direct API/repository access must enforce the same boundary; hiding UI controls is not security.

The final permission catalogue must specify whether Staff can view farm-level aggregates, which records they can create/edit, how assignment revocation affects historical records and which operations require additional approval.

## 9. Farm ownership — unresolved policy

The required invariant is that every active farm must have at least one active Owner. The ownership workflow must require explicit confirmation, appropriate re-authentication, atomic role changes and audit events.

Whether more than one active Owner may exist is still a product decision. Do not implement an exactly-one-owner or multiple-owner model until that policy is explicitly approved. A pending ownership transfer must not leave the farm without an active Owner or permit conflicting role changes.

## 10. Measurement provenance and correction safeguards

- Preserve existing farms, flocks and daily records.
- Keep original observations immutable.
- Keep \`observed_at\`, \`recorded_at\` and farm-local \`record_date\` semantically distinct.
- Preserve NULL versus numeric zero.
- Never fabricate historical user identity, observation timestamp, sensor source or calibration data.
- Do not interpret historical mortality zero as explicitly observed until the form/default semantics are resolved.
- Backfill only from a verified database copy with deterministic IDs, row-count reconciliation and FK checks.
- Keep current analytics on daily records until a separate cutover is designed and tested.

### 10.1 Correction-state defect

A unique index on \`supersedes_observation_id\` across all correction attempts can block a valid resubmission after an earlier attempt was rejected. Separate correction attempts/review history from accepted supersession relationships. Only acceptance creates the official relationship. The relational model, review reversal policy and concurrency handling remain open.

### 10.2 Database and migration safeguards

The inspected connection factory already runs \`PRAGMA foreign_keys = ON\`. Repository methods currently use SQLite connection context managers without explicit close. The schema uses cascading deletion from farms to flocks and flocks to daily records. These are findings for reviewed remediation, not permission to change the live database.

Choose a small custom migration runner versus Alembic before schema evolution. SQLite table-rebuild/batch operations are required when a requested change is not supported directly; they are not required for every SQLite alteration. Rehearse migrations on a database copy and verify preservation before any live operation.

## 11. Security and AI boundaries

Authentication proves identity; it does not authorise farm access. Use provider-neutral identity interfaces and local-only test adapters during development. Do not build homemade production authentication or connect a hosted identity provider without explicit approval and funding.

The AI assistant remains decision support, not veterinary diagnosis or prescription. Preserve source attribution and uncertainty. Farm-specific data must be authorised before it enters retrieval or an external model request. Professional diagnosis and treatment remain with qualified professionals; farm-data sharing requires consent and auditability.

## 12. Delivery roadmap

| Stage | Focus | Exit gate |
|---|---|---|
| 0 | Repository and local data baseline | Authoritative local tree and DB path confirmed; no data changed |
| 1 | Architecture and product decisions | Numbering conflict documented; open decisions explicitly reviewed |
| 2 | Local architecture foundations | Provider-neutral interfaces and local test adapters specified |
| 3 | Data/migration foundation | Additive schema and migration design approved; populated-copy rehearsal ready |
| 4 | Local identity and multi-farm permissions | Local test identities, memberships and assigned-flock access validated |
| 5 | Provenance and correction | Backfill, dual-write, review events and correction history validated on copied data |
| 6 | Product experience and AI | Responsive product experience and farm-aware AI design; demo/implemented/roadmap status clear |
| 7 | Farmer validation | Feedback from farmers and agricultural professionals; usability and willingness-to-pay evidence |
| 8 | Funding and production readiness | Paid services evaluated only after funding/revenue and explicit approval |

## 13. Agriculture-led idea intake

New ideas from the product owner's agricultural expertise and farmer feedback are welcome at any stage. Each idea should be assessed for:

1. farm problem and target user;
2. field evidence or research basis;
3. operational, economic, welfare or data-quality value;
4. workflow and data requirements;
5. AI/safety implications and professional oversight;
6. privacy and consent;
7. ability to prototype locally at no recurring cost;
8. architecture/security/migration impact; and
9. a small validation experiment.

Classify ideas as MVP candidate, pilot experiment, roadmap differentiator or research/deferred. Do not silently alter an approved decision; record impact, risks, cost, migration and rollback implications.

## 14. Decision status vocabulary

- **Requirement:** stated by an authoritative product source; not a technology approval.
- **Verified current state:** confirmed in inspected code.
- **Proposed:** recommended, not approved.
- **Open:** product policy or alternatives unresolved.
- **Deferred:** postponed until validation, funding or dependency.
- **Approved:** explicitly approved and recorded by the decision authority.
- **Superseded:** replaced by a traceable later decision.

No ADR in this draft is marked Approved. The no-recurring-cost development constraint is agreed by the product owner. Staff assigned-flock scope remains a proposed decision pending final approval. Multiple farm Owners remain unresolved.

## 15. Immediate review gates

1. Recover the original v2.1 register if possible; otherwise approve a controlled reconstruction with the numbering caveat.
2. Reconcile ADR-07 and legacy ADR references.
3. Decide whether farms may have multiple Owners while preserving the at-least-one-active-Owner invariant.
4. Finalise Staff assigned-flock read/write capabilities.
5. Record the agreed zero-recurring-cost constraint and exception/approval process.
6. Keep identity-provider choice deferred; specify the local-only development authentication boundary.
7. Decide migration tooling and the correction/review data model.
8. Review the repository assessment before code or schema changes.
9. Approve additive implementation steps with backup, rehearsal, preservation, testing and rollback gates.

**Current gate:** Review branch and documentation only. No application/database code or production data has been changed by this PR.
