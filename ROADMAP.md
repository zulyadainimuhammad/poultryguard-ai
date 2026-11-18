# PoultryGuard AI — Product & Engineering Roadmap

**Last reviewed:** 18 November 2026  
**Current baseline:** `main`, including merged PR #11 (Farm Intelligence MVP)

This roadmap separates implemented capabilities from planned work. A feature is marked implemented only where corresponding code and a usable workflow exist. A successful local test run or CI check is not a substitute for farmer, veterinary or field validation.

## Current product status

PoultryGuard AI is a working local MVP with two connected product areas:

1. **AI Knowledge Assistant:** curated poultry Markdown content, local Sentence Transformer embeddings, FAISS retrieval and Groq-backed answer generation with source visibility.
2. **Farm Intelligence:** Streamlit workflows for farm profiles, flock management, daily production records and flock-level analytics, backed by SQLite and application services.

The Farm Intelligence MVP was merged into `main` through PR #11 on 18 November 2026. The 98-test local suite and the PR's GitHub Actions CI pipeline passed. Manual local checks covered farm and flock creation, daily record entry, analytics display and record persistence across a Streamlit restart.

The product is not yet a production multi-user cloud service. Automated sensor ingestion, automated alerts, AI-generated farm insights and expert-referral workflows are not implemented. Formal farmer and veterinary/extension validation remains outstanding.

## Product architecture and capability map

The intended product has these connected capabilities:

| Capability | Intended responsibility | Current state |
|---|---|---|
| AI Knowledge Assistant | Search poultry knowledge and generate source-grounded answers | Working prototype |
| Farm and Flock Records | Organise farms, flocks and daily production records | Implemented MVP |
| Farm Analytics | Summarise flock population, mortality, feed, water, weight and recorded environmental values | Implemented MVP |
| Farm Monitoring | Monitor operating conditions and changes over time | Partial foundation through manually entered daily records; Environmental Monitoring Overview implemented for temperature and humidity coverage and statistics; measurement provenance and data semantics specification completed (Stage 3.2.2 — documentation only; runtime provenance implementation planned) |
| Environmental Data | Capture and manage reliable environmental measurements | Manual temperature/humidity fields exist; Environmental Monitoring Overview shows recorded coverage and statistics; measurement provenance model and proposed data contract defined (Stage 3.2.2 — documentation only); runtime provenance fields, sensor ingestion and device registry planned |
| AI Farm Intelligence | Turn trustworthy farm and environmental data into useful insights | Planned |
| Alerts | Notify farmers about conditions requiring attention | Planned |
| Expert Support | Support escalation and communication with qualified veterinary/agricultural professionals | Planned |
| Cloud Engineering | Provide secure, reliable shared infrastructure across the platform | Planned |

The target architecture, including the cross-cutting Cloud Engineering layer, is described in [Target Architecture](docs/architecture/target_architecture.md).

## Product phases

| Stage | Capability | State | Exit evidence |
|---|---|---|---|
| 0 | Repository and engineering foundation | In place; maintain | Reproducible setup, clean checks, current documentation |
| 1 | Poultry knowledge base and RAG Knowledge Assistant | Working prototype | Reproducible indexing, retrieval tests, source display and safety checks |
| 2 | Farm data foundation and Farm Intelligence UI | Implemented local MVP | Farm → flock → daily record → analytics workflow; persistence and tests |
| 3 | Farm Monitoring and Environmental Intelligence | In progress | Defined monitoring workflow, data-quality rules, trend visibility and reviewed thresholds |
| 4 | AI Farm Intelligence insights and alerts | Planned | Evidence-linked insight rules, alert lifecycle, evaluation and human review |
| 5 | Veterinary and expert support workflows | Planned | Qualified expert roles, consent, referral and auditable communication |
| 6 | Cloud Engineering and production foundations | Planned | API boundary, identity, access control, production database, backups, CI/CD and secure deployment |
| 7 | Farmer pilot, professional validation and localisation | Not completed | Farmer usability evidence, veterinary/extension review and localisation testing |
| 8 | Sensor integrations and predictive intelligence | Longer term | Validated telemetry, sufficient representative data and independently reviewed model evaluation |

Stages may overlap where dependencies allow. Production cloud deployment should be driven by validated multi-user, remote-access and reliability requirements, not by infrastructure novelty.

## Stage 2 — Farm Intelligence MVP (implemented)

**Objective:** Make farm and flock data usable through Streamlit.

Implemented workflows:
- Register, list and select farm profiles.
- Register flocks linked to a selected farm.
- Capture dated daily records, including mortality, feed, water, average bird weight, temperature, humidity and notes.
- Calculate flock summaries and daily metrics.
- Display charts and a detailed daily-metrics table.
- Preserve farm data in local SQLite across application restarts.

Validation recorded for the merged MVP:
- 98 local tests passed.
- Ruff lint and format checks passed.
- GitHub Actions CI for PR #11 passed, including tests and knowledge-base validation.
- Manual checks exercised two sample flocks and confirmed stored records remained available after restarting Streamlit.

These sample records are demonstration data, not measured field results. This validation does not establish production readiness or farmer impact.

## Stage 3 — Farm Monitoring and Environmental Intelligence (in progress)

**Objective:** Turn the current daily-record foundation into a clearer, trustworthy monitoring capability.

### Work packages

1. **Monitoring definitions**
   - Define the operational meaning, units, frequency and source of each measurement.
   - Distinguish manually entered observations from device/sensor readings.
   - Show timestamps, data coverage and missing values clearly.

2. **Environmental monitoring**
   - Improve temperature and relative-humidity views.
   - Define configurable, professionally reviewed thresholds by species, age/stage, housing and relevant context before using warning states.
   - Avoid presenting generic thresholds as universal veterinary or husbandry advice.
   - Record device identity, calibration status and observation source when sensor integration begins.

3. **Production monitoring**
   - Make mortality, population, feed and water trends easy to review.
   - Add rate/normalisation measures only where denominators and units are explicit.
   - Identify missing, implausible or inconsistent observations without silently changing stored values.

4. **Data quality and monitoring history**
   - Handle delayed, duplicate, missing and out-of-order readings.
   - Preserve an auditable history and distinguish corrections from new observations.
   - Add tests for boundary conditions and time-series ordering.

5. **IoT integration preparation**
   - Define a device-agnostic ingestion contract before choosing hardware or protocols.
   - Prototype one sensor data path only after the data model, connectivity assumptions and calibration process are clear.

### Stage 3 exit criteria

- Measurement names, units, provenance and timestamps are explicit.
- Manual data remains distinguishable from sensor data.
- Trend charts work with a single observation and multiple observations.
- Missing and suspicious readings are visible and are not silently converted into valid measurements.
- Any alert threshold has documented provenance and qualified domain review.
- Automated tests cover chronology, gaps, duplicates and invalid measurements.

## Stage 4 — AI Farm Intelligence insights and alerts

**Objective:** Generate transparent decision-support observations from permitted farm data and reviewed evidence.

Potential capabilities:
- Daily or weekly summaries of farm and flock performance.
- Detection of unusual changes in mortality, feed/water use or environmental measurements.
- Explainable rule-based alerts before introducing predictive models.
- Alert severity, source measurements, timestamp, acknowledgement and resolution state.
- Evidence-linked recommendations with explicit uncertainty and missing-data notices.

Safety requirements:
- Describe abnormal patterns as observations that need review, not as disease diagnoses.
- Do not prescribe medication or dosage.
- Use expert-reviewed rules and thresholds.
- Keep a human review and escalation path for consequential decisions.
- Log which records and rules contributed to an insight.

## Stage 5 — Veterinary and expert support

**Objective:** Connect farmers with qualified professionals without positioning AI as a replacement for professional judgement.

Planned work:
- Expert directory and professional-role verification approach.
- Farmer-initiated consultation/referral requests.
- Consent and controlled sharing of relevant farm records.
- Expert response and follow-up workflow.
- Audit trail for recommendations and their authorship.
- Clear distinction between AI-generated content and advice issued by a qualified professional.

## Stage 6 — Cloud Engineering and production foundations

Cloud Engineering is a cross-cutting platform capability, not merely an additional screen. It will support the Knowledge Assistant, Farm Intelligence, monitoring, alerts and expert workflows.

Planned work packages:

| Cloud capability | Purpose |
|---|---|
| Application/API hosting | Make the platform accessible remotely and provide stable service interfaces |
| API boundary | Separate UI clients from application services and define versioned contracts |
| Production database | Move from local SQLite to PostgreSQL using tested migrations |
| Object/document storage | Store approved documents, images, exports and supporting files |
| Identity and access management | Authenticate users and enforce roles and farm-level data isolation |
| Secrets management | Protect Groq credentials, database credentials and service secrets |
| CI/CD | Automate tests, builds, deployment and rollback |
| Observability | Centralised logs, metrics, errors and operational alerts |
| Backup and recovery | Encrypted backups, retention and tested restore procedures |
| Security and privacy | Encryption, least privilege, consent, retention and incident response |

### Cloud engineering sequence

1. Document requirements for multi-user access, hosting, availability, data residency, connectivity and operating cost.
2. Define service boundaries and a stable API contract while retaining the current service/repository separation.
3. Introduce versioned database migrations and test SQLite-to-PostgreSQL data migration.
4. Add authentication, authorisation and farm-level isolation tests.
5. Containerise the supported application runtime.
6. Select a cloud provider and deployment topology using cost, availability, security and operational criteria.
7. Add secrets management, CI/CD, monitoring, backups, recovery drills and rollback.
8. Conduct security and operational readiness reviews before public multi-user launch.

No cloud provider or production hosting design is selected by this roadmap. Selection will follow explicit requirements and a comparative evaluation.

## Stage 7 — Farmer pilot, professional validation and localisation

**Objective:** Validate the product with intended users and domain professionals.

Planned work:
- Conduct structured discovery and usability sessions with poultry farmers in the initial target region.
- Run a limited, consent-based pilot with clearly documented participant selection and data handling.
- Obtain veterinary and agricultural extension review of poultry knowledge, warnings, thresholds and expert workflows.
- Test Hausa terminology and interface copy with fluent local reviewers.
- Measure usability, record completeness, repeated use, workflow completion and decision-support usefulness.
- Document adverse findings, failures and limitations.

Do not claim reduced mortality, increased productivity or other impact without measured, attributable evidence.

## Stage 8 — Sensor integrations and predictive intelligence

**Objective:** Add automated environmental data and predictive capabilities only when data quality and validation support them.

Planned work:
- Evaluate suitable temperature, humidity and other sensor options.
- Validate calibration, placement, sampling frequency, connectivity and device identity.
- Define secure, resilient telemetry ingestion and offline buffering behaviour.
- Collect consented and quality-controlled longitudinal data.
- Establish interpretable baseline rules before machine-learning models.
- Evaluate models on representative data with independent review.
- Report uncertainty, false positives, false negatives and generalisation limits.
- Maintain professional escalation for consequential findings.

## Cross-cutting engineering requirements

- Keep presentation, application services, repositories and infrastructure concerns separated.
- Use versioned migrations for schema evolution; preserve existing user data.
- Keep secrets, local databases, generated indexes and model artefacts out of source control.
- Test chronological calculations, missing data, duplicate handling and boundary conditions.
- Make data provenance, units, timestamp and correction history explicit.
- Use least-privilege access and farm-level data isolation before multi-user operation.
- Do not make veterinary, predictive or product-impact claims without appropriate validation.
- Update README, roadmap, architecture and changelog as implementation changes.

## Immediate next work

Start Stage 3 with discovery and requirements for Farm Monitoring and Environmental Intelligence. Stage 3.1 (data quality), Stage 3.2.1 (Environmental Monitoring Overview) and Stage 3.2.2 (Measurement Provenance and Data Semantics specification) are complete on feature branches. Remaining Stage 3 work includes improving trend views for missing and suspicious values, establishing data-quality rules, and defining a telemetry ingestion contract before adding sensors or automated alerts.

Cloud Engineering should be designed in parallel at the architecture level, but production deployment should follow stable workflows, security requirements and a deliberate provider evaluation.
