# Changelog

All notable changes to PoultryGuard AI are documented here. The project uses the Keep a Changelog structure; semantic versioning will be adopted for tagged releases.

## [Unreleased]

### Added
- Farm Intelligence Streamlit workflows for farm profiles, flock management, daily production records and flock analytics.
- Altair time-series visualisations with explicit point markers so single observations remain visible.
- Farm service validation and analytics/repository regression tests.
- Target architecture documentation for AI Knowledge Assistant, Farm & Flock Records, Farm Monitoring, Environmental Data, AI Farm Intelligence, Insights, Alerts, Expert Support and cross-cutting Cloud Engineering.

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
