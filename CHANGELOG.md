# Changelog

All notable changes to PoultryGuard AI are documented here. The project uses the Keep a Changelog structure; semantic versioning will be adopted for tagged releases.

## [Unreleased]

### Added
- Farm Intelligence Streamlit workflows for farm profiles, flock management, daily production records and flock analytics.
- Altair time-series visualisations with explicit point markers so single observations remain visible.
- Farm service validation and analytics/repository regression tests.
- Target architecture documentation for AI Knowledge Assistant, Farm & Flock Records, Farm Monitoring, Environmental Data, AI Farm Intelligence, Insights, Alerts, Expert Support and cross-cutting Cloud Engineering.
- Environmental Monitoring Overview in the Analytics tab: descriptive summary of recorded temperature and humidity observations for the selected flock, including recorded count, missing count, coverage percentage, average, minimum, maximum and latest observation date and value for each measurement. Measurements are manually entered through daily farm records; sensor ingestion is not implemented. No automated warning thresholds or alerts are included.
- Data quality improvements: daily record form fields for feed, water, weight, temperature and humidity now use empty inputs with `value=None` and placeholder text, preventing automatic defaults from being stored as measurements. Genuine zero values are preserved and distinguished from missing observations.
- `get_environmental_summary()` method on `AnalyticsService` returning structured temperature and humidity coverage and statistics per flock.
- `get_metrics_by_date_range()` corrected to preserve `None` for unrecorded feed and water instead of coercing to `0.0`.

### Changed
- Updated README, roadmap and implementation plan to reflect the merged Farm Intelligence MVP and the next development stage.
- Updated system overview, software architecture, data-flow, deployment guidance and architecture index to distinguish current implementation from target capabilities.
- Documented local SQLite persistence and the current manual-entry nature of environmental measurements.
- Clarified production gaps: authentication, farm-level authorisation, API, PostgreSQL, cloud hosting, monitoring, backup/recovery and field validation remain future work.

### Fixed
- Corrected the current-bird mortality delta presentation so a reduction in flock population is shown as a negative change.
- Improved analytics charts for one or many observations and enforced a zero-based, non-negative population scale.
- Set the Groq answer-generation default to `qwen/qwen3.8-27b`, verified by the project owner to return text for the configured account.
- Added tests for Groq model default and environment/constructor overrides.

## Historical development notes

### Product and architecture realignment — 13 November 2026
- Repositioned the project from an ADTC-specific offline assistant proposal to a poultry farm intelligence product direction.
- Documented the active Streamlit, local RAG, Groq and SQLite architecture.
- Separated prototype capabilities from planned operational records, decision support, validation and cloud engineering.

### Earlier engineering milestones
- Added curated knowledge-base metadata and source validation.
- Added Markdown parsing/chunking, Sentence Transformer embeddings, FAISS indexing and retrieval.
- Added the initial SQLite farm, flock and daily-record data foundation.
- Added CI for linting, formatting, tests and knowledge-base validation.
- Historical ADTC/local-LLM design notes remain historical references and do not describe the active Groq-backed runtime.

## [0.0.0] — Repository Scaffold

### Added
- Initial repository structure and documentation scaffold.
- Initial CI, benchmark and test placeholders.
- Python project configuration, dependency files and developer utilities.
- Open-source governance files.
