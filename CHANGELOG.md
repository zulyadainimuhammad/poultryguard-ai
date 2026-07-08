# Changelog

All notable changes to PoultryGuard AI are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses semantic versioning after the first release.

---

## [Unreleased]

### Added — Sprint 1: System Design (`feature/system-design`)

- `docs/architecture/system_overview.md` — high-level system description, component map, Mermaid architecture diagram, and key constraints
- `docs/architecture/software_architecture.md` — layered architecture design, full module map, sequence diagram, emergency module design, configuration management, logging strategy, and testing strategy
- `docs/architecture/data_flow.md` — indexing pipeline, query pipeline, prompt structure, configuration loading flow, logging flow, benchmarking flow, and data-at-rest inventory
- `docs/architecture/model_selection.md` — LLM candidate evaluation table, Qwen2.5-1.5B-Instruct Q4_K_M selection rationale, GGUF quantisation reference, embedding model selection, and llama.cpp runtime configuration
- `docs/architecture/rag_design.md` — complete RAG pipeline design including chunking strategy, embedder interface, FAISS index builder, retriever with similarity threshold filtering, prompt builder with context budget management, knowledge base structure, and retrieval quality strategy
- `docs/architecture/deployment.md` — system requirements, deployment architecture diagram, environment setup guide, Makefile targets reference, Docker Compose design, ADTC competition deployment checklist, offline distribution package design, and environment variables reference
- `docs/architecture/adtc_alignment.md` — ADTC hardware compliance table, offline operation verification strategy, impact alignment mapping, technical requirements checklist, evaluation criteria mapping, performance targets, localisation roadmap, and risk register
- `docs/project_plan.md` — eight-sprint implementation roadmap with deliverables, acceptance criteria, dependencies, Gantt chart, and definition of done
- `docs/architecture/README.md` — index of all architecture documents with reading order and architecture principles
- Updated `README.md` — full rewrite with architecture diagram, technology stack table, ADTC hardware target, quick start, repository structure, documentation index, and development commands
- Updated `ROADMAP.md` — sprint-based roadmap replacing phase-based roadmap; includes performance targets table
- Updated `CHANGELOG.md` — this entry

### Architecture Decisions Made in Sprint 1

- Selected Qwen2.5-1.5B-Instruct Q4_K_M GGUF as primary language model
- Selected `sentence-transformers/all-MiniLM-L6-v2` as embedding model
- Selected FAISS `IndexFlatIP` as vector store
- Defined layered architecture with strict inward dependency rule
- Defined rule-based Emergency Advisory Module as deterministic, LLM-independent component
- Defined Pydantic-based configuration management
- Defined structured JSON logging strategy
- Defined prompt template using Qwen2.5 chat format with context budget management
- Defined offline distribution package strategy for end-user deployment

---

## [0.0.0] — Repository Scaffold

### Added

- Initial production-quality repository scaffold
- Documentation skeleton for architecture, deployment, benchmarks, and contribution workflows
- Placeholder CI workflow for linting, formatting, and tests
- Placeholder benchmark, profiler, and test files
- `pyproject.toml` with Ruff, Black, and pytest configuration
- `requirements.txt` and `requirements-dev.txt`
- `Makefile`, `Dockerfile`, `docker-compose.yml`
- Open-source governance files: `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
