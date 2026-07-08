# Roadmap

This roadmap tracks the planned development lifecycle for PoultryGuard AI through the Africa Deep Tech Challenge 2026. The detailed sprint plan with deliverables and acceptance criteria is in [`docs/project_plan.md`](docs/project_plan.md).

---

## Sprint 2 — Knowledge Engineering (in progress)

**Branch:** `feature/knowledge-base`

- Created `docs/knowledge_engineering.md` — writing style, Markdown conventions,
  citation requirements, terminology standards, RAG chunking strategy, confidence
  levels, review process, naming conventions, and document inventory targets
- Updated `knowledge_base/README.md` with Standards section and expanded
  contribution workflow
- Disease documents, vaccination schedules, and all other domain content to follow

---

## Sprint 1.5 — Architecture Refinement ✅

**Branch:** `feature/system-design`

- Introduced Query Classification Layer (`app/backend/classifier.py`) with three routing paths: `emergency`, `faq`, `rag`
- Formalised Rule-Based Emergency Advisory Module design with `CRITICAL`/`WARNING`/`INFO` severity levels
- Updated `system_overview.md`, `software_architecture.md`, and `data_flow.md` to reflect revised architecture
- Created `docs/knowledge_base_schema.md` — authoritative schema for all KB documents
- Expanded knowledge base structure: added `emergency/`, `faq/`, `hausa/`, `references/` directories
- Replaced `knowledge_base/README.md` with full domain index and contribution guide
- Implemented `scripts/validate_knowledge_base.py` — stdlib-only validator (no extra dependencies)
- Added `tests/unit/test_validate_knowledge_base.py` — 30+ unit tests covering all validation rules
- Updated CI workflow to run `python scripts/validate_knowledge_base.py` on every PR
- Replaced Black format check with `ruff format --check` in CI

---

## Sprint 1 — System Design ✅

**Branch:** `feature/system-design`

- Designed complete software architecture
- Created seven architecture documents under `docs/architecture/`
- Defined layered module structure across `app/`, `rag/`, `models/`
- Documented RAG pipeline design, model selection, data flow, and deployment
- Mapped all ADTC 2026 requirements to design decisions
- Created sprint roadmap in `docs/project_plan.md`
- Updated `README.md`, `ROADMAP.md`, `CHANGELOG.md`

---

## Sprint 2 — Knowledge Base

**Branch:** `feature/knowledge-base`

- Define Markdown schema for knowledge base documents
- Curate minimum 35 documents across 7 domains:
  - Diseases (Newcastle, Avian Influenza, Gumboro, Marek's, Coccidiosis, Fowl Pox, Fowl Typhoid, Infectious Bronchitis)
  - Vaccination (broiler schedule, layer schedule, vaccine storage, administration)
  - Climate (housing ventilation, heat stress, cold stress, humidity)
  - Biosecurity (farm checklist, visitor protocols, disinfection)
  - Feeding (broiler nutrition, layer nutrition, feed storage, water quality)
  - Management (flock records, mortality tracking, production records)
  - Market (pricing guidance, cost management)
- Add source attribution and review metadata
- Implement `scripts/validate_knowledge_base.py`

---

## Sprint 3 — Dataset Preparation

**Branch:** `feature/datasets`

- Collect reference Q&A pairs from agricultural extension sources
- Build evaluation set of 100 labelled question-answer pairs
- Generate 200 synthetic Q&A pairs from knowledge base documents
- Implement evaluation metrics (BLEU, ROUGE, semantic similarity)
- Document dataset provenance

---

## Sprint 4 — RAG Pipeline

**Branch:** `feature/rag`

- Implement `rag/chunking/markdown_chunker.py`
- Implement `rag/embeddings/embedder.py` with `all-MiniLM-L6-v2`
- Implement `rag/indexing/index_builder.py` with FAISS `IndexFlatIP`
- Implement `rag/retrieval/retriever.py`
- Implement `rag/prompts/prompt_builder.py`
- Build `scripts/build_index.py`
- Write unit and integration tests for all RAG modules
- Achieve retrieval latency < 500 ms on ADTC laptop

---

## Sprint 5 — Local LLM Integration

**Branch:** `feature/local-llm`

- Implement `models/inference/llm_runner.py` with `llama-cpp-python`
- Implement `app/backend/orchestrator.py`
- Implement `app/services/query_service.py`
- Implement `app/services/emergency_service.py` (rule-based triage)
- Implement `app/config/settings.py` with Pydantic settings
- Implement `app/utils/logger.py`, `timer.py`, `memory.py`
- Validate end-to-end pipeline with Qwen2.5-1.5B-Instruct Q4_K_M
- Achieve inference latency < 60 seconds on ADTC laptop

---

## Sprint 6 — Desktop Application

**Branch:** `feature/frontend`

- Build Streamlit multi-page application
- Implement all 7 domain pages (disease, vaccination, climate, biosecurity, feeding, records, home)
- Implement emergency alert banner component
- Implement chat widget and session history
- Achieve application startup < 30 seconds
- Produce demo screenshots for ADTC submission

---

## Sprint 7 — Benchmarking and Optimisation

**Branch:** `feature/benchmarking`

- Run full benchmark suite on ADTC Standard Laptop
- Profile startup time, inference latency, RAM usage, retrieval latency
- Run answer quality evaluation against evaluation dataset
- Optimise bottlenecks to meet all ADTC performance targets
- Produce reproducible benchmark report for competition submission

---

## Sprint 8 — ADTC Submission

**Branch:** `feature/documentation`

- Write ADTC competition submission report
- Finalise all documentation
- Freeze model and knowledge base versions
- Tag `v1.0.0-adtc` release
- Package offline distribution bundle
- Complete ADTC submission checklist

---

## Performance Targets

| Metric | Target |
|---|---|
| Application startup | < 30 seconds |
| First query latency | < 60 seconds |
| Subsequent query latency | < 30 seconds |
| Peak RAM usage | < 6 GB |
| Answer relevance score | > 0.7 |
| Retrieval latency | < 500 ms |
