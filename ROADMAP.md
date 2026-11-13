# PoultryGuard AI — Product & Engineering Roadmap

**Last reviewed:** 13 November 2026  
**Current development branch:** `feature/gta-mvp`  
**Repository default branch:** `main`

This roadmap reflects the current codebase. A capability is marked implemented only where corresponding code exists; planned work is clearly separated.

## Current product status

PoultryGuard AI is a working prototype with two foundations:

1. A source-grounded poultry knowledge assistant using local Markdown content, Sentence Transformers, FAISS and Groq answer generation.
2. A farm data and analytics foundation using SQLite, repositories, application services and tests.

The Farm Intelligence user interface is not yet integrated. Formal farmer and veterinary/extension validation has not yet taken place.

## Product phases

| Phase | Capability | State | Exit evidence |
|---|---|---|---|
| 0 | Repository, configuration, tests, CI and engineering practices | In place; improve continuously | Reproducible setup, clean checks, current docs |
| 1 | Poultry knowledge base and content validation | Implemented foundation | Validators pass; sources and expert review maintained |
| 2 | RAG knowledge assistant | Working prototype | Reproducible index, retrieval tests, grounded response checks and source display |
| 3 | Farm data foundation | Implemented at data/service layer | Farm, flock and daily-record operations; analytics tests |
| 4 | Farm Intelligence dashboard | Next | Streamlit screens connected to services; complete workflow tests |
| 5 | Health and operational records | Planned | Health, vaccination, treatment, biosecurity and task workflows |
| 6 | Farm-aware decision support | Planned | Farm-context summaries, auditability, source traceability and safety review |
| 7 | Field validation and localisation | Not started | Farmer interviews, usability pilot, veterinary/extension review and Hausa user research |
| 8 | Cloud and production engineering | Planned | Authentication, API boundary, PostgreSQL migrations, backups, CI/CD and secure deployment |
| 9 | Environmental integrations and predictive intelligence | Long term | Reliable datasets, sensor validation, model evaluation and documented limitations |

## Phase 4 — Farm Intelligence dashboard (next milestone)

**Goal:** Make the existing farm and analytics services usable through Streamlit without placing database logic in the UI.

### Work packages

1. **Dashboard shell and navigation**
   - Introduce navigation for Knowledge Assistant and Farm Intelligence.
   - Preserve current assistant behaviour.
   - Initialise the database safely at startup.

2. **Farm profile**
   - Create, list and view farms using `FarmService`.
   - Validate required fields and handle contact details carefully.

3. **Flock management**
   - Create and list flocks for a selected farm.
   - Validate initial bird count and stocking date.
   - Display flock status and identifiers.

4. **Daily farm records**
   - Record date, feed, water, mortality, average weight, temperature, humidity and notes.
   - Validate non-negative values, mortality and humidity bounds.
   - Define same-flock/same-day duplicate and correction behaviour.

5. **Analytics**
   - Connect `AnalyticsService` to summary metrics and chronological charts.
   - Show current flock size, cumulative mortality, mortality rate, feed, water, weight and environment readings.
   - Ensure records are sorted chronologically before cumulative calculations.
   - Explain metric definitions and missing-data behaviour.

### Phase 4 acceptance criteria

- Existing knowledge assistant remains usable.
- A user can create a farm, add a flock and submit daily records using the UI.
- Data persists after application restart.
- Dashboard requires explicit farm and flock selection.
- Charts and summary values reconcile with stored records and unit tests.
- No hard-coded demonstration metrics are presented as real farm data.
- Input validation and useful error states are present.
- Full tests, Ruff lint and formatting checks pass.

## Phase 5 — Health and operational records

- Introduce schema migrations before expanding the SQLite schema.
- Add health observations and events.
- Add vaccination plans and administration records.
- Add treatment records with product, professional authorisation, dates and withdrawal-period fields where applicable.
- Add biosecurity checklists and task/reminder records.
- Keep veterinary decisions under qualified professional oversight.
- Do not implement unsupported prescriptions or automatic treatment selection.

## Phase 6 — Farm-aware decision support

- Build a controlled context layer that retrieves only the selected farm's permitted records.
- Generate weekly summaries from recorded data, with explicit date ranges and missing-data indicators.
- Keep farm facts separate from general knowledge-base evidence.
- Include references and timestamps in AI summaries.
- Present unusual changes as observations requiring review, not diagnoses.
- Require human review for consequential health recommendations.

## Phase 7 — Field validation and localisation

- Conduct structured discovery interviews with poultry farmers in the initial target region.
- Recruit a small, consent-based pilot cohort.
- Test onboarding, farm setup, flock creation, record entry and dashboard comprehension.
- Seek review from poultry veterinarians and extension professionals.
- Research Hausa terminology and test translated content with fluent reviewers.
- Measure usability, record completeness, repeat usage and decision-support usefulness.
- Document negative findings and product limitations alongside positive findings.

Do not claim reduced mortality, improved productivity or farmer impact without measured and attributable evidence.

## Phase 8 — Cloud and production engineering

Introduce cloud engineering when multi-user access, remote synchronisation, reliability or deployment requires it—not before local workflows are stable.

1. Define stable application/service interfaces and introduce an API boundary.
2. Add authentication, authorisation and farm-level data isolation.
3. Introduce migrations and move production persistence from SQLite to PostgreSQL.
4. Add secrets management, encryption, backups and restore testing.
5. Containerise the app and services with Docker.
6. Add CI/CD, deployment environments, logging, monitoring and alerting.
7. Test availability, security, data isolation and recovery.

SQLite remains suitable for the current local prototype; it is not the intended multi-user production database.

## Phase 9 — Environmental integrations and predictive intelligence

- Start with trustworthy temperature and humidity capture, including manual entry and validated sensors.
- Evaluate calibration, sampling frequency, connectivity gaps and missing data.
- Collect consented, quality-controlled time-series data.
- Establish baseline rules and domain-reviewed thresholds before machine-learning risk indicators.
- Train and evaluate predictive models only after sufficient representative data is available.
- Report uncertainty, false alerts and limits of generalisation.
- Keep expert escalation available.

## Cross-cutting engineering requirements

- Every feature has tests, validation and documented purpose.
- Database changes use explicit migrations and preserve existing data.
- Secrets and personal data are never committed.
- UI code calls services; services call repositories; repositories own persistence queries.
- No diagnostic, predictive or impact claims without validation evidence.
- Update README, roadmap and changelog when implementation changes.

## Immediate next task

Complete Phase 4, beginning with the dashboard shell and navigation. Before charting cumulative performance, verify chronological analytics calculations and add a regression test. Then implement one end-to-end vertical slice at a time:

**Create farm → create flock → add daily record → view analytics.**
