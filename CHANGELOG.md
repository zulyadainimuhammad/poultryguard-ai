# Changelog

All notable changes to PoultryGuard AI are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project uses semantic versioning after the first release.

---

## [Unreleased]

### Added — Sprint 2: Knowledge Engineering (`feature/knowledge-base`)

- `docs/knowledge_engineering.md` — authoritative knowledge engineering standards
  covering writing style, Markdown conventions, metadata schema, citation
  requirements, terminology standards, RAG chunking strategy, confidence levels,
  review process, naming conventions, and Sprint 2 document inventory targets

### Changed — Sprint 2

- `knowledge_base/README.md` — added Standards section linking to
  `docs/knowledge_engineering.md`; expanded Adding a Document workflow to 11
  steps aligned with engineering standards; added Document Inventory Targets
  table for Sprint 2

---

### Added — Sprint 1.5: Architecture Refinement (`feature/system-design`)

- `docs/knowledge_base_schema.md` — authoritative schema for all knowledge base documents; defines required front matter fields, valid domain values, required sections per domain, filename conventions, and sources requirements
- `knowledge_base/emergency/README.md` — emergency domain directory stub
- `knowledge_base/faq/README.md` — FAQ domain directory stub
- `knowledge_base/hausa/README.md` — Hausa-language domain directory stub (Sprint 6 target)
- `knowledge_base/references/README.md` — bibliographic references directory stub
- `scripts/validate_knowledge_base.py` — stdlib-only knowledge base validator; checks metadata, domain, sections, sources, duplicate titles, and filename conventions
- `tests/unit/__init__.py` — unit test package
- `tests/unit/test_validate_knowledge_base.py` — 30+ unit tests covering all validator rules across all domain types

### Changed — Sprint 1.5

- `docs/architecture/system_overview.md` — added Query Classification Layer to design decisions, architecture diagram, and component responsibilities table
- `docs/architecture/software_architecture.md` — added Query Classification Layer section with `QueryClass` enum design, classification priority order, and pure-function design properties; updated layer diagram, module map, and sequence diagram
- `docs/architecture/data_flow.md` — updated query pipeline flowchart to show three routing paths (emergency, faq, rag); updated query pipeline steps table to include classifier step
- `knowledge_base/README.md` — full replacement with domain index, contribution guide, validation instructions, and content status table
- `.github/workflows/ci.yml` — added `Validate knowledge base` step; replaced `black --check` with `ruff format --check`
- `README.md` — updated status, architecture diagram, layer table, documentation index, and sprint status
- `ROADMAP.md` — added Sprint 1.5 entry

### Architecture Decisions Made in Sprint 1.5

- Introduced `QueryClass` enum (`emergency`, `faq`, `rag`) as the typed output of the Query Classification Layer
- Defined classification priority: emergency keywords checked first (sub-ms), then FAQ patterns, then full RAG
- Defined knowledge base schema with 10 valid domains including `emergency`, `faq`, `hausa`, and `references`
- Defined domain-specific required section sets (diseases, emergency, faq, default)
- Implemented validator using Python stdlib only — no additional runtime dependencies

---

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
