# PoultryGuard AI — Implementation Plan

**Last reviewed:** 13 November 2026  
**Planning basis:** Active `feature/gta-mvp` branch and current repository implementation.

## Purpose

This plan sequences work from the current prototype toward a validated poultry farm intelligence product. It supersedes the former ADTC offline/llama.cpp sprint plan as the primary delivery plan. Historical ADTC design documents remain historical references and must not be treated as descriptions of the current runtime.

## Current baseline

Implemented in the active branch:

- Streamlit knowledge assistant at `app/frontend/main.py`.
- Markdown knowledge content and automated content validators.
- Heading-aware Markdown chunking, local Sentence Transformer embeddings, FAISS indexing and retrieval.
- Groq-backed answer generation with source metadata.
- SQLite schema for farms, flocks and daily records.
- Farm, flock and daily-record repositories and application services.
- Flock summary and daily analytics service.
- Latest local test run reported by the developer: 62 tests passed.

Not yet implemented as user workflows:

- Farm Intelligence Streamlit screens and navigation.
- Health, vaccination, treatment, biosecurity and task records.
- Farm-aware AI summaries.
- Formal farmer pilot and professional validation.
- Production authentication, API, PostgreSQL and cloud deployment.

## Delivery sequence

| Phase | Name | Priority | Dependencies |
|---|---|---|---|
| 0 | Engineering baseline and repository accuracy | Maintain | None |
| 1 | Poultry knowledge content and quality | High | Phase 0 |
| 2 | RAG and knowledge assistant | High | Phase 1 |
| 3 | Farm data and analytics foundation | High | Phase 0 |
| 4 | Farm Intelligence UI | **Current next phase** | Phase 3 |
| 5 | Health and operational records | High | Phase 4, schema migrations |
| 6 | Farm-aware AI summaries and expert workflow | Medium | Phases 2, 4 and 5 |
| 7 | Field validation and localisation | High | Usable end-to-end workflows |
| 8 | Production/cloud architecture | Later | Validated workflows and multi-user need |
| 9 | Environmental integrations and predictive intelligence | Later | Reliable longitudinal data and validation |

## Phase 0 — Engineering baseline and documentation

**Objective:** Keep the repository reproducible, tested and accurately described.

Tasks:
- Maintain Python 3.11 development environment and a deliberate dependency-management strategy.
- Keep secrets, local SQLite databases, FAISS artefacts and model files out of Git.
- Retain CI for lint, formatting, tests and knowledge-base validation.
- Keep runtime and deployment instructions aligned with implemented code.
- Maintain clear branch and pull-request practices.

Exit criteria:
- Fresh environment setup is documented and verified.
- CI matches commands developers run locally.
- No live credentials or local runtime artefacts are tracked.
- README and roadmap describe the active architecture.

## Phase 1 — Poultry knowledge base

**Objective:** Maintain a traceable, reviewable poultry knowledge corpus.

Tasks:
- Maintain metadata and source references for all knowledge documents.
- Continue coverage across diseases, vaccination, climate, biosecurity, feeding, management, emergency guidance and FAQs.
- Conduct qualified poultry/veterinary review of high-risk content.
- Review Hausa content with fluent local reviewers before publication.

Exit criteria:
- Knowledge-base validators pass.
- Sources are traceable.
- Critical guidance has professional review status and review dates.
- Known content gaps are documented.

## Phase 2 — RAG knowledge assistant

**Objective:** Retrieve relevant knowledge and generate answers that distinguish evidence from uncertainty.

Tasks:
- Preserve Markdown chunking and FAISS indexing.
- Use the implemented `scripts/build_index.py` command and document model-cache setup; validate the command on a clean Python 3.11 environment.
- Test retrieval relevance and source attribution.
- Add answer-quality tests, insufficient-evidence cases and safety regression cases.
- Handle missing index, missing embedding model and provider/API failures clearly.
- Document that Groq generation requires internet connectivity and an API key.

Exit criteria:
- Index can be built reproducibly from the tracked knowledge base.
- Retriever returns expected relevant passages for a curated evaluation set.
- Answers show source traceability and abstain when evidence is inadequate.
- No treatment/dosage or diagnostic overclaim is introduced.

## Phase 3 — Farm data and analytics foundation

**Objective:** Store and compute basic farm-level production information.

Existing entities:
- Farm
- Flock
- DailyRecord

Existing operations:
- Create/list/get farms.
- Create/list/get flocks.
- Create daily records and retrieve records.
- Calculate flock-level summary and daily metrics.

Remaining quality gates:
- Test chronological and cumulative-mortality calculations using unsorted repository fixtures.
- Define duplicate-date handling and record correction semantics.
- Validate numeric fields and flock relationships.
- Add database migrations before future schema expansion.
- Test persistence and foreign-key cascade behaviour.

Exit criteria:
- Service and repository contracts are documented.
- Chronological calculations are deterministic.
- Invalid inputs are rejected.
- Existing data can be migrated safely.

## Phase 4 — Farm Intelligence UI

**Objective:** Connect the data foundation to farmer-facing workflows in Streamlit.

Implementation order:

1. Navigation shell separating Knowledge Assistant and Farm Intelligence.
2. Farm profile creation, listing and selection.
3. Flock creation and listing for a selected farm.
4. Daily record entry with field validation.
5. Farm/flock summary cards and chronological charts.
6. Empty states, error handling, confirmation and data-refresh behaviour.

Required analytics:
- Initial/current bird count.
- Total mortality and mortality rate.
- Feed and water totals.
- Average weight.
- Temperature and humidity summaries.

Exit criteria:
- User completes the farm → flock → daily record → analytics path.
- Restarting Streamlit does not lose saved records.
- Dashboard values reconcile with repository data.
- Existing knowledge assistant remains functional.
- Tests cover UI-facing service contracts and core validation.

## Phase 5 — Health and operational records

**Objective:** Expand the data model safely.

Potential entities:
- HealthObservation
- VaccinationEvent
- TreatmentRecord
- BiosecurityCheck
- FarmTask

Tasks:
- Add versioned database migrations.
- Define validation and event-history semantics.
- Record source/author for professional recommendations.
- Add treatment withdrawal-period tracking only with appropriate product and professional data.
- Do not implement unsupported prescriptions or automatic treatment selection.

Exit criteria:
- Migration tests preserve existing farm/flock/record data.
- Every entity has repository, service and validation tests.
- UI presents clear status and audit history.

## Phase 6 — Farm-aware AI and expert workflows

**Objective:** Combine selected farm records with relevant knowledge in an auditable way.

Tasks:
- Define a minimised, permission-checked farm context payload.
- Generate weekly summaries with explicit time range and data coverage.
- Cite knowledge-base sources separately from user-recorded farm measurements.
- Flag unusual changes as observations requiring review, not diagnoses.
- Add expert consultation request and response workflows with clear professional role identity.

Exit criteria:
- Every generated metric traces to stored records.
- AI distinguishes recorded facts, retrieved guidance and uncertain interpretation.
- Safety evaluation includes high-risk poultry-health scenarios.

## Phase 7 — Field validation and localisation

**Objective:** Test usefulness with intended users and domain professionals.

Tasks:
- Conduct farmer interviews and workflow observation.
- Run consent-based usability sessions and a limited pilot.
- Obtain veterinary and extension review.
- Evaluate Hausa labels, help text and content with fluent reviewers.
- Measure task completion, completeness, repeat usage, confidence and usability.
- Record failures and corrective actions.

Exit criteria:
- Validation report includes methods, participants, findings and limitations.
- Claims about impact are supported by measured evidence.
- Product priorities reflect actual farmer feedback.

## Phase 8 — Production and cloud engineering

**Objective:** Support secure multi-user use when remote access and operational reliability are required.

Tasks:
- Separate UI from application services with a stable API contract.
- Add authentication, roles and farm-level authorisation.
- Adopt migrations and PostgreSQL for production.
- Add Docker images, CI/CD and environment-specific configuration.
- Add encryption, secret management, backups, restore drills, observability and incident procedures.
- Validate deployment security and data isolation.

Exit criteria:
- Tested deployment and rollback process.
- Verified backups and restores.
- Farm-level access-control tests pass.
- No secrets are stored in source control.

## Phase 9 — Environmental and predictive features

**Objective:** Add sensor-informed and predictive functionality only when reliable longitudinal data exists.

Tasks:
- Validate manual and sensor-based temperature/humidity readings.
- Monitor calibration, missing data, sampling intervals and device connectivity.
- Build transparent baselines before machine-learning models.
- Evaluate models using representative, independently reviewed data.
- Measure false positives, false negatives, drift and generalisation limits.
- Keep professional review and escalation paths.

Exit criteria:
- Data provenance and quality thresholds are documented.
- Evaluation is reproducible.
- Product language accurately communicates uncertainty and limitations.

## Working method

- Use a focused branch for each coherent feature.
- Make small commits with clear messages.
- Run focused tests after each change and the full suite before merging.
- Update documentation when implementation changes—not before.
- Merge only after review and passing CI.
- Do not mix product claims, planned capabilities and implemented features.

## First work item

Start Phase 4 with the Streamlit navigation shell and Farm Profile page. Before charting cumulative performance, verify chronological ordering in `AnalyticsService.get_daily_metrics` and add a regression test.
