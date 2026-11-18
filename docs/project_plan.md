# PoultryGuard AI — Implementation Plan

**Last reviewed:** 18 November 2026  
**Baseline:** `main` at the merge of PR #11 (Farm Intelligence MVP)

## Purpose

This plan sequences the work from the current local MVP toward a validated, secure poultry farm intelligence platform. It supersedes the former ADTC/offline/llama.cpp sprint plan as the primary delivery plan. Historical design material remains historical and must not be treated as a description of the current runtime.

The plan distinguishes implemented capability from planned capability. Passing software tests does not establish farmer impact, veterinary correctness or production readiness.

## Current baseline

Implemented and merged into `main`:

- Streamlit application entry point at `app/frontend/main.py`.
- Knowledge Assistant using curated Markdown, local Sentence Transformer embeddings, FAISS retrieval and Groq-backed answer generation.
- SQLite schema, connection management, models and repositories for farms, flocks and daily records.
- Farm and flock profile workflows.
- Daily production record entry and validation.
- Flock summary and daily analytics, including population, mortality, feed, water, weight and recorded environmental measurements.
- Altair analytics charts with point markers for single observations.
- Automated unit tests, Ruff checks and knowledge-base validation in GitHub Actions.

The Farm Intelligence work was merged through PR #11 on 18 November 2026. The local test run reported 98 passing tests; the PR CI pipeline passed. Manual checks covered farm/flock workflows, record entry, chart display and SQLite persistence after a Streamlit restart.

Not yet implemented:

- Automated environmental sensor ingestion or continuous monitoring.
- Automated farm alerts and AI-generated farm insights.
- Veterinary/expert consultation workflow.
- Health, vaccination, treatment, biosecurity and task modules.
- Production API, multi-user authentication, authorisation and farm-level data isolation.
- Cloud hosting, managed production database, operational monitoring and disaster recovery.
- Formal farmer pilot, veterinary/extension validation or measured impact evaluation.

## Delivery sequence

| Stage | Name | Priority | Dependencies |
|---|---|---|---|
| 0 | Engineering baseline and repository accuracy | Maintain | None |
| 1 | Poultry knowledge content and RAG assistant | Maintain | Stage 0 |
| 2 | Farm data foundation and Farm Intelligence MVP | Implemented | Stage 0 |
| 3 | Farm Monitoring and Environmental Intelligence | In progress | Stage 2; agreed measurement definitions |
| 4 | AI Farm Intelligence insights and alerts | High | Stages 1–3; reviewed evidence and thresholds |
| 5 | Veterinary and expert support workflows | High | Consent, expert role and safety design |
| 6 | Cloud Engineering and production foundations | Later | Stable service contracts, security and deployment requirements |
| 7 | Farmer pilot, professional validation and localisation | High | Usable workflows and domain-reviewed content |
| 8 | Sensor integrations and predictive intelligence | Later | Reliable longitudinal data and validation |

Stages may overlap. Production cloud deployment should be driven by validated multi-user, remote-access and reliability requirements.

## Stage 0 — Engineering baseline and documentation

**Objective:** Keep the repository reproducible, tested, secure and accurately described.

Tasks:
- Maintain Python 3.11 development environment and dependency-management strategy.
- Keep secrets, local SQLite databases, generated FAISS artefacts and model files out of Git.
- Retain CI for lint, formatting, tests and knowledge-base validation.
- Keep runtime and deployment instructions aligned with the merged application.
- Use focused branches and reviewed pull requests.
- Update product and architecture documentation whenever implementation changes.

Exit criteria:
- Fresh environment setup is documented.
- CI matches local development checks.
- No credentials or runtime artefacts are tracked.
- README, roadmap and architecture docs describe the actual runtime and target separately.

## Stage 1 — Poultry knowledge base and RAG assistant

**Objective:** Maintain traceable poultry knowledge and evidence-grounded responses.

Tasks:
- Maintain source metadata and references for knowledge documents.
- Review high-risk poultry content with qualified veterinary/extension professionals.
- Maintain retrieval and answer-quality tests, including inadequate-evidence and unsafe-request cases.
- Verify provider/model configuration with a real chat-completion smoke test when it changes.
- Keep retrieval relevance separate from factual confidence.
- Document that Groq generation requires internet connectivity and an API key.

Exit criteria:
- Index can be built reproducibly from tracked knowledge content.
- Retrieval evaluation uses representative, reviewed questions.
- Answers display source traceability and abstain when evidence is inadequate.
- No diagnostic, treatment or dosage overclaim is introduced.

## Stage 2 — Farm data foundation and Farm Intelligence MVP (implemented)

**Objective:** Make farm and flock records usable through the Streamlit application.

Implemented workflows:
1. Register, list and select farm profiles.
2. Register flocks linked to a selected farm.
3. Enter daily records including date, mortality, feed, water, average weight, temperature, humidity and notes.
4. View flock summaries and daily production analytics.
5. Inspect charts and the full daily-metrics table.
6. Persist records locally in SQLite across application restarts.

Quality and validation evidence:
- Service validation covers required fields, supported species, positive initial population, farm/flock relationships, mortality limits and duplicate daily records.
- Analytics and repository tests cover chronological records, cumulative metrics and missing-value behaviour.
- Local test suite: 98 passed on 18 November 2026.
- Ruff lint and format checks passed.
- PR #11 CI passed, including knowledge-base validators.
- Manual local test covered two sample flocks and restart persistence.

Limitations:
- Manual temperature/humidity fields are not automated sensor monitoring.
- Sample data is demonstration data, not field evidence.
- The local SQLite/Streamlit workflow is not a secure multi-user production deployment.
- Farmer and veterinary/extension validation remains outstanding.

## Stage 3 — Farm Monitoring and Environmental Intelligence (in progress)

**Objective:** Build a clear, trustworthy monitoring workflow on top of the current records and analytics foundation.

### Implemented in Stage 3

**Stage 3.1 — Data Quality and Measurement Accuracy**
- Daily record form fields for feed, water, weight, temperature and humidity changed to empty inputs (`value=None`) with placeholder text. Automatic defaults no longer populate as stored measurements.
- Genuine zero values are preserved and distinguished from missing observations throughout the service and analytics layers.
- `get_metrics_by_date_range()` corrected to preserve `None` for unrecorded feed and water.
- Regression tests added for `None` preservation, genuine zero persistence and date-range accuracy.

**Stage 3.2.1 — Environmental Monitoring Overview**
- `get_environmental_summary()` added to `AnalyticsService`. Returns recorded count, missing count, coverage percentage, average, minimum, maximum, latest observation date and latest value for temperature and humidity separately.
- Environmental Monitoring Overview section added to the Analytics tab in the Streamlit interface, above the existing trend charts. Displays Temperature Monitoring and Relative Humidity Monitoring panels with metric cards and latest-observation captions.
- Measurements are manually entered through daily farm records. Sensor ingestion is not implemented. No automated warning thresholds or alerts are included. Veterinary or agricultural professional validation of thresholds remains outstanding.
- 8 unit tests added covering averages, counts, coverage, None exclusion, genuine zero counting, different latest dates per measurement, later-missing-does-not-replace-latest, empty flock and unknown flock.

**Stage 3.2.2 — Measurement Provenance and Data Semantics** *(documentation milestone; no runtime changes)*
- Comprehensive measurement provenance and data semantics specification created at `docs/architecture/measurement_provenance.md`.
- Covers: current data model assessment and its provenance limitations; measurement dictionary for all six daily-record measurements; provenance model with four source categories (`manual_entry`, `file_import`, `sensor_device`, `system_generated`); observation-time and recording-time semantics; missing-value and data-quality status model; data-quality lifecycle; correction and audit model; proposed future measurement data contract with three illustrative JSON examples; recommended future architecture evolution; migration and backward-compatibility considerations; security, privacy and access-control considerations; open design decisions.
- Architecture README, data-flow document and target architecture updated to reference the new specification.
- This milestone is documentation only. No Python code, database schema or application behaviour was changed.

### Remaining Stage 3 work packages

1. Define each measurement's name, unit, timestamp, collection frequency and provenance.
2. Distinguish farmer-entered observations from automated device readings.
3. Improve environmental and production trend views, including missing-data and suspicious-value states.
4. Define configurable, context-aware thresholds only with documented and qualified domain review.
5. Establish data-quality rules for delayed, duplicate, missing, implausible and out-of-order observations.
6. Define a device-agnostic telemetry ingestion contract before choosing hardware or protocols.
7. Prototype sensor ingestion after connectivity, calibration and device identity requirements are known.

Exit criteria:
- Measurements have explicit units, source and timestamps.
- Manual and sensor-originated data are distinguishable.
- Trends display correctly for one or many observations.
- Missing or suspicious values are not silently converted or corrected.
- Alert thresholds have traceable provenance and expert review.
- Tests cover chronological order, gaps, duplicates, invalid values and boundaries.

## Stage 4 — AI Farm Intelligence insights and alerts

**Objective:** Convert permitted farm data and reviewed knowledge into transparent decision-support observations.

Tasks:
- Produce daily/weekly summaries with explicit date range and data coverage.
- Add explainable rule-based identification of unusual changes before ML prediction.
- Attach supporting measurements, timestamps, data source and rule/version to every insight.
- Design alert severity, acknowledgement, assignment and resolution.
- Include uncertainty and missing-data notices.
- Provide human review for consequential actions.

Exit criteria:
- Every generated metric traces to stored data.
- Insights separate facts, rules, retrieved knowledge and uncertain interpretation.
- High-risk scenarios pass safety regression tests.
- No unsupported diagnosis or prescription is generated.

## Stage 5 — Veterinary and expert support

**Objective:** Connect farmers to qualified veterinary and agricultural professionals.

Tasks:
- Define expert identity, role and qualification verification.
- Add farmer-initiated consultation/referral requests.
- Define explicit consent and controlled sharing of relevant farm records.
- Record professional responses, follow-up and authorship.
- Keep AI-generated suggestions clearly separate from professional advice.
- Maintain an audit trail for consequential recommendations.

Exit criteria:
- Expert roles are clear and verifiable.
- Data sharing is consent-based and scoped.
- Recommendations have clear authorship and history.
- Escalation does not imply that AI replaces professional care.

## Stage 6 — Cloud Engineering and production foundations

**Objective:** Provide secure, reliable shared infrastructure when the product's validated requirements justify remote multi-user use.

Cloud Engineering is cross-cutting. It supports the Knowledge Assistant, Farm Intelligence, monitoring, alerts and expert workflows.

Work packages:
1. Document non-functional requirements: users, availability, connectivity, data residency, privacy, operating cost and recovery objectives.
2. Define stable service interfaces and a versioned API boundary between clients and application services.
3. Introduce versioned database migrations and test moving production persistence from SQLite to PostgreSQL.
4. Add authentication, role-based authorisation and farm-level data isolation.
5. Evaluate cloud providers and deployment options against documented requirements.
6. Containerise the supported runtime and establish separate development/staging/production configuration.
7. Add secrets management, encryption, CI/CD, logs, metrics, operational alerting and rollback.
8. Implement encrypted backups, retention and tested restore procedures.
9. Conduct security, access-control and operational readiness testing.

Exit criteria:
- Repeatable deployment and rollback.
- Verified farm-level access controls.
- Backups and recovery tested.
- Secrets never stored in source control.
- Monitoring and incident-response ownership documented.

No specific cloud provider is preselected by this plan; choose after a comparative requirements and cost evaluation.

## Stage 7 — Farmer pilot, professional validation and localisation

**Objective:** Validate product usefulness and safety with intended users.

Tasks:
- Conduct farmer discovery and usability sessions in the initial target region.
- Run a limited, consent-based pilot with documented data handling.
- Obtain veterinary and extension review of content, thresholds, insights and expert workflows.
- Review Hausa terminology and interface copy with fluent local reviewers.
- Measure usability, task completion, record completeness, repeated usage and decision-support usefulness.
- Publish a validation report including limitations and negative findings.

Exit criteria:
- Participant selection and methods are documented.
- Professional review status is traceable.
- Product changes are linked to observed findings.
- Any impact claim is supported by measured and attributable evidence.

## Stage 8 — Sensor integrations and predictive intelligence

**Objective:** Introduce automated telemetry and predictive models only when data quality and validation justify them.

Tasks:
- Select sensors based on farm context, cost, availability and maintainability.
- Validate calibration, placement, sampling frequency, connectivity and device identity.
- Design secure ingestion and offline buffering.
- Collect consented, quality-controlled longitudinal data.
- Establish domain-reviewed baseline rules before machine learning.
- Evaluate predictive models on representative data with independent review.
- Measure false positives, false negatives, uncertainty and model drift.
- Retain expert escalation.

Exit criteria:
- Data provenance and quality thresholds are documented.
- Evaluation is reproducible and independently reviewed.
- Uncertainty and generalisation limits are visible to users.
- No unsupported performance or impact claim is made.

## Working method

- Use one focused branch per coherent change.
- Make small commits with clear messages.
- Run focused tests after each change and the full suite before merging.
- Keep application logic in services, persistence queries in repositories and presentation in the UI.
- Use migrations for database schema changes and preserve existing records.
- Update docs when implementation changes.
- Merge only after code review and successful CI.
- Keep planned capabilities visibly distinct from working functionality.

## Immediate next work

Stage 3 is in progress. Stage 3.1 (data quality), Stage 3.2.1 (Environmental Monitoring Overview) and Stage 3.2.2 (Measurement Provenance and Data Semantics specification) are implemented on feature branches. Remaining Stage 3 work includes improving trend views for missing and suspicious values, establishing data-quality rules, and defining a telemetry ingestion contract before adding sensors or automated alerts.
