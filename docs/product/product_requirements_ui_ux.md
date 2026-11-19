# PoultryGuard AI — Product Requirements and UI/UX Specification

**Product direction:** Premium modern SaaS combined with a distinctive Agritech identity  
**Document status:** Product requirements baseline — for architecture and UX discovery  
**Version:** 1.0  
**Date:** 18 November 2026  
**Product:** PoultryGuard AI  
**Primary initial market context:** Poultry farmers and farm operators in Northern Nigeria, with a design intended to serve users internationally

> **Purpose:** Define the product experience, user model, functional requirements, security expectations and delivery sequence for evolving PoultryGuard AI from its current local MVP into a professional, secure, multi-farm platform. This specification is a planning artefact. It does not authorise code changes, database migrations, deployment or the transfer of existing farm data.

---

## 1. Executive summary

PoultryGuard AI is intended to become an intelligent poultry farm management and decision-support platform. It should help farm owners and authorised teams manage farm operations, monitor flock performance, maintain traceable records and access evidence-grounded poultry knowledge.

The product must make a strong first impression through a polished, consistent and trustworthy interface. It must also support real operational work: a farm owner should be able to manage one or more farms, invite staff, assign permissions and see what is happening across the farms they are authorised to access. A staff member should be able to record assigned farm activities without gaining access to settings, financial or administrative information unless explicitly permitted.

The agreed product direction is:

- **Visual identity:** premium modern SaaS combined with Agritech imagery, language and context.
- **User experience:** clear, attractive, responsive, accessible and easy to learn.
- **Account model:** one user account may belong to multiple farms.
- **Authentication:** support both email/password and Google sign-in in the target product.
- **Farm ownership:** every farm has an owner; farm-level roles and permissions control access.
- **Team access:** owners can invite staff and grant or revoke access.
- **Security:** enforce authorisation in backend services and data-access queries, not only by hiding interface controls.
- **Product integrity:** preserve existing farm records and keep measurement provenance, corrections and audit history as first-class design concerns.

## 2. Product vision, goals and non-goals

### 2.1 Product vision

Make PoultryGuard AI a trusted, attractive and professionally engineered poultry farm intelligence platform that farmers, farm managers, staff, agricultural advisers, partners and investors can confidently use and showcase.

### 2.2 Product goals

1. Create a memorable, professional interface that communicates trust, clarity and agricultural expertise.
2. Allow an individual user to belong to multiple farms, with a different role on each farm where appropriate.
3. Give farm owners practical control over invitations, membership, staff permissions and farm settings.
4. Make routine farm operations — farm setup, flock management and daily record entry — straightforward on desktop, tablet and mobile.
5. Present farm performance and environmental information clearly without implying that missing or unverified measurements are known values.
6. Retain the current AI knowledge assistant direction, including retrieved evidence and visible sources.
7. Establish an architecture that can evolve towards secure multi-user operation, reliable auditability and future sensor and decision-support capabilities.
8. Preserve existing data during all future migrations and upgrades.

### 2.3 Success measures

Targets should be set after baseline usability testing. Initial measures to instrument include:

- Time for a new owner to register, create a farm and add a first flock.
- Time and completion rate for a staff member to accept an invitation and submit a daily record.
- Number of failed or abandoned critical workflows.
- Rate of data-entry errors and corrections.
- Percentage of active farms with complete owner and membership information.
- Frequency of permission-denied events and cross-farm access test failures (the latter must remain zero).
- Dashboard load time and key workflow response time under an agreed pilot load.
- User-reported ease of use, trust and visual clarity.

### 2.4 Non-goals for the first multi-user release

- Autonomous veterinary diagnosis or treatment prescription.
- Unreviewed medicine dosages, chemical concentrations or clinical protocols.
- Automated sensor ingestion before device, calibration and data-quality requirements are approved.
- Predictive alerts presented as validated without appropriate farm data, domain review and evaluation.
- Full accounting, payroll, ERP or supply-chain functionality.
- Public access to farm records or a public farm directory by default.
- A billing/subscription system until commercial packaging is decided.

## 3. Product principles

1. **Trust before decoration.** Every displayed metric must have a clear meaning, date range, unit and data freshness context.
2. **Clarity over density.** Show the most useful information first; put detailed tables and advanced controls behind clear navigation.
3. **Farm-scoped access.** A user's permissions are evaluated for the selected farm, not assumed globally from their account role.
4. **Safe defaults.** New members receive the minimum permission set needed for their assigned work.
5. **Traceable records.** Preserve who entered or changed information, when it happened and the reason where relevant.
6. **Honest data semantics.** Missing values must not be displayed as zero. Manual, imported, sensor and system-generated observations must be distinguishable when provenance is implemented.
7. **Responsive by design.** Critical workflows must work on smaller screens, not only on a desktop dashboard.
8. **Progressive disclosure.** Keep novice workflows simple while allowing experienced managers to access detailed analytics and configuration.
9. **Accessible interaction.** Use readable typography, adequate contrast, keyboard operation, labels and non-colour-only status indicators.
10. **Evidence-aware AI.** AI answers must show supporting sources and clearly communicate when evidence is insufficient.

## 4. Users, accounts and farm membership

### 4.1 User account versus farm membership

A **user account** represents a person and their sign-in identity. A **farm membership** links that user to a specific farm with a role and permissions. The same user may have memberships in several farms and may hold different roles in each farm.

Example: a person can be an owner of Farm A and a manager of Farm B. Access to Farm A must not automatically grant access to Farm B, and membership in one farm must not reveal another farm's records.

### 4.2 User types

| User type | Purpose | Typical access |
|---|---|---|
| Platform administrator | Operates the PoultryGuard service itself | Platform configuration and support functions; farm data access only through explicitly authorised support procedures |
| Farm owner | Owns or is accountable for a farm workspace | Full control of that farm, its membership and settings; can transfer ownership using a controlled process |
| Farm manager | Runs day-to-day operations for a farm | Operational management and selected team functions delegated by the owner |
| Farm staff / record keeper | Enters or maintains assigned operational records | Restricted operational access, normally focused on assigned flocks and permitted record actions |
| Read-only viewer / adviser | Reviews information without changing it | Read-only access to explicitly shared areas; suitable for an adviser or auditor where approved |

The platform administrator is not the same as a farm owner. Platform administration must not silently create unrestricted access to private farm records.

### 4.3 Account registration and sign-in

The target product should offer both:

- **Email and password:** account registration, verified email, sign-in, password reset and secure session handling.
- **Google sign-in:** an identity-provider flow that creates or links an account according to a documented account-linking policy.

Requirements:

- AUTH-01: A new user can register with an email address and password.
- AUTH-02: A user can sign in using Google.
- AUTH-03: A user can sign out and explicitly end their active session.
- AUTH-04: A user can request a password reset without revealing whether an email address is registered.
- AUTH-05: Email ownership is verified before sensitive account actions and invitations are fully activated.
- AUTH-06: Account linking must avoid creating duplicate or incorrectly merged identities.
- AUTH-07: Sessions must expire according to a documented policy; sensitive actions may require re-authentication.
- AUTH-08: Authentication attempts must be rate-limited and protected against common credential attacks.
- AUTH-09: Multi-factor authentication should be supported or required for privileged roles according to the final security policy.
- AUTH-10: Secrets, password hashes, identity tokens and recovery tokens must never be written to application logs.

The identity provider and implementation approach remain an architecture decision. Authentication proves identity; it does not by itself decide which farms a person may access.

### 4.4 Farm creation and onboarding

- ONB-01: After registration, a user can create a farm workspace and becomes its initial owner.
- ONB-02: Farm creation captures only the information required to start: farm name, location/timezone context and optional production details.
- ONB-03: The owner can add one or more flocks and continue setup later.
- ONB-04: The onboarding flow explains how to invite a manager or staff member.
- ONB-05: The product can show a guided checklist, but users can skip non-essential steps and return later.
- ONB-06: Empty states explain the next useful action instead of showing blank charts or invented sample values.

### 4.5 Multiple farms and farm switching

- FARM-01: A user can belong to more than one farm.
- FARM-02: The application provides a clearly visible farm selector showing only farms where the user has an active membership.
- FARM-03: Switching farms refreshes the displayed dashboard, records, analytics and team context to the selected farm.
- FARM-04: The current farm context is visible on operational pages to reduce accidental data entry into the wrong farm.
- FARM-05: Every backend request and data query checks the user's active membership and permission for the requested farm.
- FARM-06: A user can leave a farm, subject to ownership and outstanding governance rules; the last owner cannot simply leave without transferring ownership.
- FARM-07: Ownership transfer requires explicit confirmation, re-authentication where appropriate and an audit event.

## 5. Roles and permissions

### 5.1 Proposed default role matrix

| Capability | Owner | Manager | Staff / record keeper | Viewer / adviser |
|---|:---:|:---:|:---:|:---:|
| View farm dashboard | Yes | Yes | Limited | Yes, if shared |
| View farm profile | Yes | Yes | Limited | Yes, if shared |
| Edit farm settings | Yes | Delegated | No | No |
| Create and manage flocks | Yes | Yes | No by default | No |
| Create daily records | Yes | Yes | Yes, within assigned scope | No |
| Edit daily records | Yes | Yes, according to policy | Own/assigned records, according to policy | No |
| Delete records | Controlled | Normally restricted | No | No |
| View analytics and reports | Yes | Yes | Limited | Yes, if shared |
| Invite members | Yes | Only when delegated | No | No |
| Change member roles | Yes | Only within delegated limits | No | No |
| Remove members | Yes | Only when delegated | No | No |
| View audit history | Yes | Relevant operational history | Own/assigned activity where appropriate | No by default |
| Transfer farm ownership | Yes, controlled workflow | No | No | No |

This is the proposed starting matrix, not a substitute for a final permission catalogue. Permissions should be defined as named capabilities and checked on every protected action. The interface may hide unavailable actions, but the backend must independently reject unauthorised requests.

### 5.2 Team invitations

- TEAM-01: An owner can invite a person by email to a selected farm.
- TEAM-02: The invitation includes the farm identity, intended role, inviter and expiry information.
- TEAM-03: The invited person must authenticate or register and verify control of the invited email before membership activates.
- TEAM-04: Invitation tokens must be single-use, time-limited, stored safely and revocable.
- TEAM-05: The owner can view pending, accepted, expired and revoked invitations.
- TEAM-06: An owner can revoke a pending invitation and suspend or remove an active member subject to ownership rules.
- TEAM-07: Role changes are audited and take effect promptly.
- TEAM-08: Re-inviting an existing member must not create duplicate memberships.
- TEAM-09: Invitation and role-assignment screens must clearly explain what access the role grants.

### 5.3 Fine-grained permissions

The product should begin with understandable default roles, but the architecture should allow selected capabilities to be delegated later. Examples include record creation, record correction, report export, flock management and inviting team members. Avoid introducing a complex custom-role editor in the first release unless pilot users demonstrate a real need.

## 6. Information architecture and key screens

### 6.1 Global application shell

The authenticated experience should include:

- A left navigation sidebar on desktop, with a clear compact/collapsed state.
- A top bar containing the current farm selector, page context, notifications and user menu.
- A visible page title, short contextual description and primary action.
- A consistent content grid with clear spacing and predictable card/table patterns.
- Breadcrumbs or clear back navigation on nested detail pages.
- A mobile navigation pattern that preserves the farm context and primary actions.

### 6.2 Proposed primary navigation

1. Overview
2. Farms and flocks
3. Daily operations
4. Environmental monitoring
5. Analytics and reports
6. Knowledge assistant
7. Team and access
8. Settings

The navigation must be filtered by membership role. For example, Team and Access should not appear as an actionable management area to ordinary staff without permission.

### 6.3 Screen requirements

| Screen | Main purpose | Key content and actions |
|---|---|---|
| Public landing / sign-in | Explain the product and let users access accounts | Product value, sign-in, create account, Google option, help and privacy links |
| Registration / verification | Create a secure identity | Email, password, Google sign-in, verification and terms acknowledgement |
| Onboarding | Create the first farm | Farm details, location/timezone, first flock, invite team, progress checklist |
| Farm switcher | Change active farm | Searchable list of authorised farms, role label and recent selection |
| Overview dashboard | Summarise the selected farm | Flock population, mortality, recorded feed/water, latest environmental readings, trends, activity and alerts |
| Farm profile | Maintain farm details | Identity, location, production context, timezone and settings |
| Flock list/detail | Manage production groups | Species, production type, stocking date, population, status and flock-specific metrics |
| Daily operations | Capture routine activities | Date, flock, mortality, feed, water, weight, temperature, humidity, notes and record status |
| Environmental monitoring | Review recorded environmental data | Temperature/humidity trends, coverage, latest measurement time/source, missing data and future device status |
| Analytics and reports | Explore performance over time | Date filters, comparable metrics, charts, tables and export actions permitted by role |
| Knowledge assistant | Ask poultry knowledge questions | Question entry, grounded answer, cited passages, evidence limitations and professional referral guidance |
| Team and access | Manage farm members | Members, role, invitation state, last activity where appropriate, invite/revoke/change role actions |
| Audit history | Review important activity | Actor, action, farm, affected object, timestamp, outcome and correction links |
| Settings | Manage personal and farm preferences | Profile, security, notifications, farm settings and membership controls |

### 6.4 Dashboard content rules

The dashboard should prioritise information that supports an immediate operational decision:

- **KPI cards:** current flock population, mortality over a selected period, recorded feed/water totals, average weight where available, and environmental coverage.
- **Trend views:** population and mortality trends; feed/water trends where the underlying records support meaningful comparison.
- **Environmental summary:** latest recorded temperature and humidity, observation date/time if known, source/provenance when available, and coverage percentage.
- **Recent activity:** recent entries and important changes, with actor attribution when identity tracking is implemented.
- **Alerts / attention items:** only validated rules with an explanation, severity, timestamp and recommended next action. Do not invent alert thresholds during the design phase.
- **Filters:** active farm, flock and date range, with clear indication of the scope being displayed.

Do not display illustrative values as if they are live farm data. When data is missing, display “Not recorded” or an equivalent explicit state. Do not convert missing values to zero. Every chart should show units and date range and should offer a useful empty state.

## 7. Visual design system

### 7.1 Design direction

The interface should combine the visual discipline of a premium business SaaS product with authentic Agritech cues. It should feel modern and confident without looking like a generic finance dashboard or a playful consumer app.

### 7.2 Proposed colour tokens

These are initial design tokens for prototyping. They must be checked for contrast and refined during UI implementation.

| Token | Proposed value | Intended use |
|---|---|---|
| Forest green | `#163B2F` | Primary brand, navigation emphasis, strong headings |
| Emerald | `#1F8A5B` | Primary actions and positive states |
| Teal | `#247C7A` | Secondary data accents |
| Mint | `#E8F4EE` | Soft surfaces and selected states |
| Warm white | `#F7F9F7` | Main application canvas |
| Charcoal | `#1F2933` | Primary text |
| Slate grey | `#667085` | Secondary text and labels |
| Amber | `#C78B27` | Caution and needs-attention states |
| Red | `#C43D3D` | Errors and critical status |
| White | `#FFFFFF` | Cards and contrast surfaces |

Do not use colour as the only way to communicate status. Pair status colours with text, icons or patterns. Verify text/background combinations against the agreed accessibility contrast standard before release.

### 7.3 Typography and layout

- Use a contemporary, highly legible sans-serif typeface (Inter or a metrically similar fallback may be evaluated).
- Use a clear type scale for page titles, section headings, card labels, values, helper text and table content.
- Prefer generous whitespace, consistent alignment and a restrained number of font weights.
- Use a consistent spacing scale and a responsive grid; avoid arbitrary per-page padding.
- Use consistent card radii and subtle elevation. Avoid heavy shadows, excessive gradients and decorative borders.
- Use icons from one consistent icon family and pair unfamiliar icons with text labels.

### 7.4 Data visualisation

- Use chart types that fit the question, with readable axes, units, legends and date ranges.
- Distinguish actual values from targets, forecasts and illustrative/demo data.
- Explain gaps and missing measurements rather than connecting or filling them in misleading ways.
- Provide an accessible tabular or textual alternative for important chart information.
- Avoid 3D charts, unnecessary gauge dials and excessive decorative animation.
- Use consistent colours for the same measurement across screens.

### 7.5 Responsive behaviour

- Desktop: full sidebar, multi-column dashboards and detailed tables.
- Tablet: narrower navigation, two-column cards where space permits, usable forms.
- Mobile: compact navigation, single-column KPI cards, stacked forms, horizontally safe tables or card-based record layouts, and large touch targets.
- Critical tasks — sign-in, farm switching, entering a daily record and accepting an invitation — must be usable on mobile.

### 7.6 Interaction states

Every important control and screen must define:

- Default state.
- Hover, focus and pressed states.
- Loading state.
- Empty state.
- Validation error state.
- Permission-denied state.
- Success confirmation.
- Network or service failure state where applicable.

Use confirmation for destructive or high-impact actions such as removing a member, deleting a record where deletion is permitted, changing ownership or revoking access. Prefer reversible actions and soft-deactivation where the business rules require preserving history.

## 8. Functional requirements by module

### 8.1 Farm and flock management

- CORE-01: Owners and authorised managers can create and update farm profiles.
- CORE-02: Farms contain one or more flocks.
- CORE-03: Users can only read or modify farms and flocks for which they have explicit permission.
- CORE-04: Flock lists support search, status and production-type filtering where useful.
- CORE-05: Flock detail pages show flock context and linked daily records.

### 8.2 Daily operations and measurement records

- OPS-01: Authorised users can create daily records for a selected flock.
- OPS-02: The entry form clearly identifies the active farm, flock, date and measurement units.
- OPS-03: Optional measurements can remain missing; missing must not become zero.
- OPS-04: Genuine zero values remain valid when the metric permits zero.
- OPS-05: Validation rules communicate the reason for rejection and do not silently rewrite user values.
- OPS-06: The application records the submitting user and recording timestamp when authenticated multi-user operation is implemented.
- OPS-07: Corrections preserve the original record or observation and create an auditable correction relationship according to the approved measurement provenance contract.

### 8.3 Environmental monitoring

- ENV-01: Present recorded temperature and humidity with units, dates and coverage.
- ENV-02: Distinguish manual, imported and sensor data when provenance is available.
- ENV-03: Show the observation time separately from the time a value was recorded by the platform when both are available.
- ENV-04: Do not claim live sensor monitoring until device integration exists.
- ENV-05: Any warning threshold or alert rule must be documented, configurable where appropriate and reviewed by qualified poultry domain experts before use.

### 8.4 Analytics and reporting

- ANA-01: Analytics respect active farm membership and selected flock/date scope.
- ANA-02: Metrics display definitions, units and date ranges.
- ANA-03: Missing measurements are excluded or handled according to an explicit metric definition; they are never silently treated as zero.
- ANA-04: Export actions enforce the same permissions as on-screen reports.
- ANA-05: Reports identify their generation time and the farm/date scope.

### 8.5 Knowledge assistant

- AI-01: Answers are grounded in retrieved knowledge-base passages.
- AI-02: Supporting source files/sections are visible to the user.
- AI-03: The system states when retrieved evidence is insufficient.
- AI-04: Health-related answers retain appropriate veterinary escalation language and do not invent medicine dosages or unsupported treatment instructions.
- AI-05: AI provider availability, latency and failures are presented clearly without exposing API keys or internal secrets.
- AI-06: The assistant's data access scope must be defined before it can use private farm records as context.

### 8.6 Team management and audit

- TEAM-10: Owners can view current and pending memberships for their farm.
- TEAM-11: Membership changes and privileged actions create audit events.
- TEAM-12: Audit events include actor, farm, action, target, timestamp and outcome, while minimising sensitive payload storage.
- TEAM-13: Audit records are protected from ordinary member modification.
- TEAM-14: A user's access is revoked promptly after membership removal or suspension.

## 9. Security, privacy and trust requirements

Security is a product requirement, not a final polish task.

1. Enforce farm-level tenant isolation in the backend and at the data-access layer for every request.
2. Never trust a farm ID, role or user ID supplied by the client without verifying the authenticated user's membership and permissions.
3. Use secure password hashing through a vetted identity solution; never store plaintext passwords.
4. Protect sessions, reset tokens and invitation tokens; make them time-limited and revocable.
5. Use HTTPS in deployed environments and secure handling of secrets through environment or secret-management facilities.
6. Apply rate limits to sign-in, password reset and invitation endpoints.
7. Record security-relevant events such as login failures, role changes, invitation acceptance, access revocation and ownership transfer.
8. Limit platform support access to farm data and make exceptional access explicit, authorised and auditable.
9. Define data retention, account deletion, farm closure, export and ownership-transfer policies before public launch.
10. Back up production data and test restoration; a backup that has never been restored is not a verified recovery plan.
11. Do not expose personal contact details, farm records or AI prompts in public logs or analytics.
12. Conduct dependency, configuration and application security reviews before production release.

## 10. Technical architecture direction and decision gates

### 10.1 Current baseline

The current repository is a local Streamlit MVP using Python services, SQLite repositories, a local Sentence Transformer/FAISS knowledge retrieval pipeline and Groq-based answer generation. It does not yet provide production authentication, multi-user authorisation, farm membership isolation or a production multi-tenant database.

The current implementation is valuable and should be preserved as the functional baseline. The product redesign must not be mistaken for permission to discard or rewrite existing working capabilities.

### 10.2 Candidate target architecture

A candidate production architecture to evaluate is:

- Frontend: a dedicated responsive web frontend (React/Next.js is one candidate).
- Backend: Python API/services (FastAPI is one candidate).
- Database: PostgreSQL or another managed relational database with a clear tenant-isolation model.
- Authentication: an established identity provider supporting email/password and Google sign-in.
- AI services: retain the existing RAG and answer-generation concepts behind service boundaries.
- Background processing: queue/workers for longer-running indexing, imports and future notifications.
- Storage and operations: managed backups, monitoring, secret management and deployment automation.

This is a candidate, not a final technology decision. A documented architecture decision record must compare the cost, delivery effort, maintainability, Streamlit evolution options, accessibility, mobile experience, identity integration and expected scale before selecting a new stack.

### 10.3 Architecture decision gates

- ADR-01: Decide whether to evolve Streamlit for an interim release or introduce a separate frontend.
- ADR-02: Select the backend/API approach and define service boundaries.
- ADR-03: Select PostgreSQL or another production database and migration tooling.
- ADR-04: Select the identity provider and account-linking policy for email/password and Google sign-in.
- ADR-05: Approve the tenant/farm membership and permission enforcement model.
- ADR-06: Define invitation delivery, email verification and notification services.
- ADR-07: Decide deployment, backup, monitoring and recovery arrangements.

No one should start a production migration until these decisions, data mapping and recovery approach are reviewed.

## 11. Data migration and backward compatibility

The existing local SQLite database may contain farm, flock and daily-record data. It must be treated as valuable user data.

- MIG-01: Make a verified backup before any schema migration or data transformation.
- MIG-02: Test migrations against a copy of the database, never the only source database.
- MIG-03: Use versioned, repeatable migration scripts and record the applied migration version.
- MIG-04: Define a rollback or forward-recovery strategy for each migration.
- MIG-05: Reconcile row counts, foreign keys, key relationships and representative values before and after migration.
- MIG-06: Preserve existing farm, flock and daily-record identifiers where technically feasible, or maintain an explicit mapping if identifiers change.
- MIG-07: Do not fabricate historical user identities, observation timestamps, sensor sources or calibration details.
- MIG-08: Historical records with unknown provenance must remain explicitly unknown/legacy rather than being falsely attributed to a newly created user.
- MIG-09: Keep the existing application usable until the new workflow has passed migration tests and acceptance checks.
- MIG-10: Test recovery from backup and confirm that the restored system can read expected farm records.

The future account model must also decide how existing local farms are assigned to an initial owner during onboarding. That mapping must be explicit and confirmed by the data owner; it must not be guessed.

## 12. Accessibility, localisation and international readiness

- Use semantic page structure, visible labels and keyboard-accessible controls.
- Provide visible focus indicators and accessible validation messages.
- Do not rely on colour alone for status or chart interpretation.
- Test common text/background combinations against the agreed contrast criteria.
- Support responsive layouts and zoom/text scaling.
- Keep interface copy concise and avoid unexplained technical jargon.
- Use clear date, time and measurement units; store timestamps with unambiguous timezone semantics and display them in the farm's configured timezone.
- Design for localisation, even if the first release ships in English. Hausa and other languages may be evaluated for later releases.
- Avoid embedding currency, timezone, date format or location assumptions throughout the code.

## 13. Delivery roadmap

| Phase | Focus | Main deliverables | Exit condition |
|---|---|---|---|
| 0. Product and discovery baseline | Confirm requirements and workflows | This specification, user journeys, risk register, open-decision list | Product owner reviews scope and priority |
| 1. UX and visual foundation | Establish look, feel and screen behaviour | Brand tokens, typography, component library, responsive wireframes/prototype, usability review | Core screens and design system approved |
| 2. Architecture decisions | Choose the transition path | ADRs for frontend, backend, identity, database, tenancy, deployment | Architecture and migration approach approved |
| 3. Identity and farm membership foundation | Implement secure accounts and multi-farm model | Registration, email verification, Google sign-in, farm membership, farm selector | Identity and tenant-isolation tests pass |
| 4. Roles, invitations and audit | Enable controlled team access | Owner/manager/staff/viewer permissions, invitations, revocation, audit events | Permission matrix and negative-access tests pass |
| 5. Data migration and provenance | Preserve and extend farm records | Versioned migration, backup/restore tests, observation/provenance and correction implementation | Reconciled data and migration acceptance pass |
| 6. Product UI and workflow rollout | Deliver the approved experience | Dashboard, farm/flock, operations, environmental, analytics, assistant and team screens | Usability and functional acceptance pass |
| 7. Pilot and production readiness | Validate with real users and operations | Security review, performance tests, farmer/extension feedback, monitoring, backups, deployment runbook | Pilot exit criteria and launch approval met |

UX prototyping can proceed while architecture decisions are being prepared, but production implementation must respect the approved identity, tenancy and data model. Avoid building a polished interface that relies on insecure or unscoped backend operations.

## 14. Acceptance criteria for the first multi-farm release

The first multi-farm release is not ready until all of the following are true:

1. A person can register using email/password and can sign in using Google, subject to the approved identity policy.
2. A user can create a farm and becomes its initial owner.
3. A user can belong to at least two farms and hold different roles in each.
4. The active farm is clearly visible and switching farms changes the entire data context.
5. An owner can invite a manager or staff member and assign a role.
6. Invitees must authenticate and verify the invited identity before membership becomes active.
7. Owners can review pending and active memberships, change permitted roles and revoke access.
8. Staff can perform only the operations allowed by their membership permissions.
9. Direct API/data-access tests prove that a user from Farm A cannot read or change Farm B data without an explicit membership.
10. Important record creation, correction, membership and permission changes are auditable.
11. Existing farm data is migrated or retained through a tested, reconciled process with a verified recovery path.
12. Dashboard metrics show units, filters, date ranges and missing-data states accurately.
13. Critical workflows work at desktop, tablet and mobile sizes.
14. Keyboard navigation, contrast, labels and error states pass the agreed accessibility checks.
15. Automated tests, dependency checks, security checks and deployment checks pass the release gate.

## 15. Open decisions and assumptions

The following items require explicit decisions before detailed implementation:

- Which identity provider will support both email/password and Google sign-in?
- Will email/password credentials be managed by the identity provider or by an application-owned authentication service?
- Is multi-factor authentication required for owners and platform administrators at launch?
- Can managers invite staff by default, or only when the owner delegates that permission?
- Can staff edit their own records, and within what time window? Who can correct an older record?
- What happens when a farm owner leaves, becomes inactive or loses access to their account?
- How should legacy local farms be assigned to verified owners during migration?
- Which country/timezone and localisation defaults are required for the first release?
- Is mobile web sufficient for the first release, or is a native mobile application a later requirement?
- Which frontend/backend/database architecture provides the best balance of product quality, delivery effort, operating cost and maintainability?
- What are the first pilot farm sizes, number of users per farm and expected concurrent usage?
- Which notifications are required at launch, and which channels (email, in-app, SMS/WhatsApp) are appropriate later?
- What is the commercial model, if any, for farms, seats, usage or premium features?

## 16. Immediate next steps

1. Store this specification in the repository as `docs/product/product_requirements_ui_ux.md`.
2. Ask Kiro Crew to review it against the current repository in read-only mode and identify implementation gaps and contradictions.
3. Convert the key user journeys into wireframes and a clickable UX prototype before production UI coding.
4. Create architecture decision records for frontend, backend, identity, database and tenant isolation.
5. Prepare a separate data migration and backup/restore plan before changing the database.
6. Break the approved plan into small implementation milestones, each with tests and reviewable pull requests.

**Current status:** Product direction agreed; detailed implementation architecture, UX prototype and security model still require review and approval. No application code or database has been changed by producing this specification.

## Appendix A. Key terms

| Term | Meaning in this specification |
|---|---|
| User account | A person's sign-in identity, independent of the farms they can access. |
| Farm membership | The relationship connecting a user account to one farm with a specific role and permissions. |
| Authentication | The process of verifying who is signing in. |
| Authorisation | The process of deciding which actions and data an authenticated user is allowed to access. |
| Tenant isolation | Controls that prevent a user or farm workspace from accessing another farm's private data without explicit permission. |
| Role-based access control (RBAC) | A permission model that assigns named capabilities through roles such as owner, manager, staff and viewer. |
| Provenance | Information about where a measurement came from, who or what produced it and how it was recorded. |
| Observation time | The actual time a measurement was taken, if known. |
| Recording time | The time the platform received and stored a measurement. |
| Audit event | A protected record of an important action, including the actor, target, time and outcome. |
| Responsive design | An interface that adapts its layout and controls to desktop, tablet and mobile screen sizes. |