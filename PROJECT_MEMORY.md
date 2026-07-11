# Project Memory

**Last Updated:** 11 July 2026  
**Repository:** `zulyadainimuhammad/poultryguard-ai`  
**Default Branch:** `main`  
**Current Development Branch:** `feature/knowledge-base`

---

## Project Overview

PoultryGuard AI is an offline AI-powered poultry health, vaccination, climate, biosecurity, and farm management advisory assistant built for the Africa Deep Tech Challenge (ADTC) 2026.

**Mission:** Demonstrate a practical, locally deployable AI system that helps smallholder poultry farmers, agricultural extension officers, veterinary workers, and farm managers in sub-Saharan Africa without requiring internet access, cloud APIs, or GPU hardware.

**Key Characteristics:**
- Runs entirely on ADTC Standard Laptop (Intel i5/AMD Ryzen 5, 8 GB RAM, CPU-only)
- Ubuntu 22.04 LTS compatible
- Zero network dependency at runtime
- Offline-first architecture with local FAISS vector store
- Curated Markdown knowledge base (7 domains minimum)
- Local inference via llama.cpp with Qwen2.5-1.5B-Instruct Q4_K_M
- Streamlit desktop UI
- MIT open-source license

**Repository Structure:**
```
poultryguard-ai/
├── app/                    # Frontend, backend, services, config, utils
├── rag/                    # Chunking, embeddings, indexing, retrieval, prompts
├── models/                 # llama.cpp inference boundary
├── knowledge_base/         # Curated Markdown knowledge base (10 domains)
├── vector_store/           # Generated FAISS indexes (git-ignored)
├── datasets/               # Evaluation and synthetic datasets
├── evaluation/             # Answer quality evaluation
├── benchmarks/             # Performance benchmarks
├── profiler/               # Runtime profiling helpers
├── scripts/                # Developer utility scripts
├── notebooks/              # Research notebooks
├── tests/                  # pytest test suite
├── docs/                   # Architecture, API, deployment documentation
├── report/                 # ADTC submission materials
├── demo/                   # Demo scripts
└── assets/                 # Branding and static assets
```

---

## Current Sprint

**Sprint 2 — Knowledge Engineering** (In Progress)

**Branch:** `feature/knowledge-base`

**Objectives:**
- Establish authoritative knowledge engineering standards ✅
- Implement knowledge base schema and validator ✅
- Curate minimum 35 documents across 10 domains (10 of 35 completed)
- Ensure factual accuracy and source traceability ✅

**Target Completion:** End of Sprint 2

**Deliverables:**
- ✅ `docs/knowledge_engineering.md` — complete writing style, citation, chunking standards
- ✅ `docs/knowledge_base_schema.md` — authoritative schema and document template
- ✅ Knowledge base directory structure (10 domains ready)
- ✅ `scripts/validate_knowledge_base.py` — automated schema validator
- ✅ `scripts/validate_metadata.py` — metadata quality validator
- ✅ `scripts/validate_references.py` — citation validator
- ✅ `scripts/validate_links.py` — link validator (offline safety)
- ✅ `scripts/build_index_preview.py` — lightweight RAG chunking preview
- ✅ CI integration — validator runs on every PR
- ⏳ Knowledge base documents (10 of 35 completed)

---

## Completed Milestones

### Repository Scaffold (v0.0.0) ✅
- Production-quality Python project structure
- Makefile, Docker Compose, CI/CD pipeline template
- pyproject.toml with Ruff, pytest configuration
- requirements.txt and requirements-dev.txt
- Open-source governance: LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
- .github/workflows/ci.yml for linting and testing

### Sprint 1 — System Design ✅

**Branch:** `feature/system-design`

**Architecture Documents Created:**
1. `docs/architecture/system_overview.md` — high-level system description, component map, Mermaid diagram
2. `docs/architecture/software_architecture.md` — layered architecture, module map, sequence diagrams
3. `docs/architecture/data_flow.md` — indexing pipeline, query pipeline, logging flow
4. `docs/architecture/model_selection.md` — LLM/embedding model rationale
5. `docs/architecture/rag_design.md` — complete RAG pipeline design
6. `docs/architecture/deployment.md` — system requirements, environment setup, Docker Compose
7. `docs/architecture/adtc_alignment.md` — ADTC hardware compliance mapping
8. `docs/architecture/README.md` — architecture index and reading order

**Key Architecture Decisions:**
- **LLM:** Qwen2.5-1.5B-Instruct Q4_K_M GGUF (fits 8 GB RAM target, ~1.5 GB model)
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (fast, CPU-efficient)
- **Vector Store:** FAISS IndexFlatIP (CPU-only, no network overhead)
- **Inference Engine:** llama.cpp (local, offline-first)
- **Frontend:** Streamlit (rapid prototyping, local deployment)
- **Config Management:** Pydantic-based settings with environment loading
- **Testing:** pytest with unit, integration, and smoke test targets
- **Logging:** Structured JSON logging for observability

**Documentation Updated:**
- README.md — architecture diagram, technology stack, ADTC constraints
- ROADMAP.md — sprint-based roadmap with performance targets
- CHANGELOG.md — detailed changelog of all changes

### Sprint 1.5 — Architecture Refinement ✅

**Branch:** `feature/system-design`

**Query Classification Layer Introduced:**
- `app/backend/classifier.py` — routes queries to `emergency`, `faq`, or `rag` paths
- Priority-based classification: emergency keywords (sub-ms) → FAQ patterns → full RAG
- QueryClass enum with three typed outputs

**Emergency Advisory Module Formalized:**
- Rule-based, deterministic design (independent of LLM)
- Severity levels: `CRITICAL`, `WARNING`, `INFO`
- No hallucination risk; grounded in knowledge base keywords
- Fast response path for life-threatening situations

**Knowledge Base Schema Implemented:**
- `docs/knowledge_base_schema.md` — authoritative reference
- YAML front matter fields: title, domain, tags, reviewed, sources, confidence, severity, language
- 10 valid domain values: diseases, vaccination, climate, biosecurity, feeding, management, market, emergency, faq, hausa
- Domain-specific required section sets
- Filename conventions (lowercase, underscores, .md)

**Validator Implemented:**
- `scripts/validate_knowledge_base.py` — pure Python, stdlib-only
- Checks metadata, domain, sections, sources, duplicate titles, filename conventions
- No external dependencies (no extra pip packages required)
- `tests/unit/test_validate_knowledge_base.py` — 30+ unit tests

**CI Integration:**
- .github/workflows/ci.yml updated to run validator on every PR
- Replaced Black with Ruff for formatting checks
- Validator blocks PR merge if schema validation fails

**Knowledge Base Structure Expanded:**
- `knowledge_base/diseases/` — disease documents (priority: 8)
- `knowledge_base/vaccination/` — vaccination schedules (priority: 4)
- `knowledge_base/climate/` — housing and climate management (priority: 3)
- `knowledge_base/biosecurity/` — farm biosecurity (priority: 3)
- `knowledge_base/feeding/` — nutrition and feed management (priority: 4)
- `knowledge_base/management/` — flock records and farm operations (priority: 3)
- `knowledge_base/market/` — market pricing and economics (priority: 2)
- `knowledge_base/emergency/` — critical alerts for Emergency Advisory Module (priority: 3)
- `knowledge_base/faq/` — frequently asked questions (priority: 5)
- `knowledge_base/hausa/` — Hausa-language documents (Sprint 6 target)
- `knowledge_base/references/` — bibliographic references (not yet implemented)

**Documentation Updated:**
- `docs/architecture/system_overview.md` — added Query Classification Layer
- `docs/architecture/software_architecture.md` — added classifier design section
- `docs/architecture/data_flow.md` — updated query pipeline with three routing paths
- `README.md` — updated status, architecture diagram, documentation index
- `ROADMAP.md` — added Sprint 1.5 entry with completed deliverables
- `CHANGELOG.md` — comprehensive Sprint 1.5 changes

### Sprint 2 — Knowledge Engineering (In Progress) ✅

**Branch:** `feature/knowledge-base`

**Standards Documents Completed:**
- ✅ `docs/knowledge_engineering.md` (582 lines) — authoritative engineering standards
  - Writing style (audience, voice, tone, sentence/paragraph length)
  - Markdown conventions (headings, lists, emphasis, tables, links, formatting)
  - Metadata schema (required/optional YAML fields, tag conventions)
  - Citation requirements (source tiers, acceptable sources, APA format)
  - Terminology standards (preferred terms, scientific names, units, drug names)
  - Document chunking strategy for RAG (chunk boundaries, word count targets, keyword density)
  - Confidence levels (high/medium/low with definitions)
  - Review process (authoring, PR, content review checklist, approval, update workflow)
  - Naming conventions (filenames, directories, titles, tags)
  - Document inventory targets (35 documents across 10 domains)

- ✅ `docs/knowledge_base_schema.md` (231 lines) — authoritative reference
  - YAML front matter schema with examples
  - 10 valid domain values with descriptions
  - Required section sets per domain (standard, disease, emergency, faq)
  - Filename and directory conventions
  - Sources requirement and acceptable formats
  - Complete document template for all domain types
  - Validator reference

**Framework Completed:**
- ✅ Knowledge base directory structure (10 domains ready)
- ✅ `scripts/validate_knowledge_base.py` — schema validator
- ✅ `scripts/validate_metadata.py` — metadata quality validator
- ✅ `scripts/validate_references.py` — citation validator
- ✅ `scripts/validate_links.py` — offline-safe link validator
- ✅ `scripts/build_index_preview.py` — lightweight RAG chunking preview
- ✅ Unit tests (30+ test cases in `tests/unit/test_validate_knowledge_base.py`)
- ✅ CI integration (validators run on every PR)
- ✅ `knowledge_base/README.md` updated with standards references and contribution workflow

**Knowledge Base Documents (10 of 35 completed):**
- ✅ 5 disease documents completed (Newcastle, Avian Influenza, Gumboro, Infectious Bronchitis, Coccidiosis)
- ⏳ 3 disease documents pending (Infectious Coryza, Marek's, Fowl Cholera, Fowl Pox, Pullorum — Sprint 2.3 Batch 2)
- ⏳ 4 vaccination documents pending
- ⏳ 3 climate documents pending
- ⏳ 3 biosecurity documents pending
- ⏳ 4 feeding documents pending
- ⏳ 3 management documents pending
- ⏳ 2 market documents pending
- ⏳ 3 emergency documents pending
- ⏳ 5 FAQ documents pending

### AI Infrastructure & Documentation ✅

**AI_DEVELOPER_GUIDE.md** (10 Sections)
- Permanent instruction manual for all AI coding assistants
- Project overview, ADTC constraints, architecture principles
- Coding standards (Python 3.11+, type hints, docstrings, Ruff, pytest)
- Git workflow (feature branches, Conventional Commits, PR review)
- Knowledge base standards and RAG principles
- Performance goals and AI assistant behaviour
- Standard development workflow with verification steps

**PROJECT_MEMORY.md** (This Document)
- Complete project state snapshot
- Sprint progress and completion status
- Knowledge base inventory and validation status
- Outstanding tasks and recommendations
- Next sprint planning

**Knowledge Engineering Standards** (`docs/knowledge_engineering.md`)
- Writing style for smallholder farmers (active voice, plain English, short sentences)
- Markdown conventions (heading hierarchy, lists, emphasis, tables)
- Metadata schema (YAML front matter, tag conventions)
- Citation requirements (5-tier source ranking, APA format)
- Terminology standards (preferred terms, scientific names, units)
- Document chunking strategy (H2 boundaries, word count targets)
- Confidence levels (high/medium/low)
- Review process and naming conventions

**Knowledge Base Schema** (`docs/knowledge_base_schema.md`)
- YAML front matter specification
- 10 valid domain values
- Required sections per domain type
- Filename conventions
- Complete document templates
- Validator reference

### Knowledge Base Quality System ✅

**Components Implemented:**
1. **Engineering Standards** — Complete writing, sourcing, and structure guidelines
2. **Schema Reference** — Authoritative YAML and section structure specification
3. **Automated Validators:**
   - `validate_knowledge_base.py` — schema compliance
   - `validate_metadata.py` — metadata quality
   - `validate_references.py` — citation accuracy
   - `validate_links.py` — offline-safe links
   - `build_index_preview.py` — RAG chunking preview
4. **Unit Tests** — 30+ test cases covering all validator rules
5. **Knowledge Base Index** — Domain structure and document inventory targets
6. **CI Integration** — Validators run on every PR, block merge if validation fails

---

## Current Knowledge Base

**Status:** Framework complete, 10 of 35 documents authored

**Completed Documents (10 of 35):**

### Diseases (5 of 8 Completed)

| Document | Filename | Status | Sources | Reviewed |
|---|---|---|---|---|
| Newcastle Disease | `newcastle_disease.md` | ✅ Completed | FAO, OIE/WOAH | ✅ |
| Avian Influenza | `avian_influenza.md` | ✅ Completed | FAO, OIE/WOAH, HPAI focus | ✅ |
| Gumboro Disease | `gumboro.md` | ✅ Completed | Peer-reviewed literature | ✅ |
| Infectious Bronchitis | `infectious_bronchitis.md` | ✅ Completed | Veterinary authority sources | ✅ |
| Coccidiosis | `coccidiosis.md` | ✅ Completed | Research literature | ✅ |

### Diseases (3 of 8 Pending — Sprint 2.3 Batch 2)

| Document | Filename | Status | Priority |
|---|---|---|---|
| Infectious Coryza | `infectious_coryza.md` | ⏳ Pending | Sprint 2.3 Batch 2 |
| Marek's Disease | `mareks_disease.md` | ⏳ Pending | Sprint 2.3 Batch 2 |
| Fowl Cholera | `fowl_cholera.md` | ⏳ Pending | Sprint 2.3 Batch 2 |
| Fowl Pox | `fowl_pox.md` | ⏳ Pending | Sprint 2.3 Batch 2 |
| Pullorum Disease | `pullorum_disease.md` | ⏳ Pending | Sprint 2.3 Batch 2 |

### Other Domains (0 of 27 Completed)

| Domain | Target | Completed | Pending |
|---|---|---|---|
| Vaccination | 4 | 0 | 4 |
| Climate | 3 | 0 | 3 |
| Biosecurity | 3 | 0 | 3 |
| Feeding | 4 | 0 | 4 |
| Management | 3 | 0 | 3 |
| Market | 2 | 0 | 2 |
| Emergency | 3 | 0 | 3 |
| FAQ | 5 | 0 | 5 |
| **Total** | **35** | **10** | **25** |

---

## Validation Status

### Knowledge Base Validators

**Primary Validators (Implemented & Active):**

1. **validate_knowledge_base.py** ✅
   - Schema compliance (YAML front matter, sections, filenames)
   - Domain validation (valid domain values)
   - Required section headings
   - Non-empty sources list
   - Duplicate title detection
   - Filename convention checking
   - Pure Python, stdlib-only

2. **validate_metadata.py** ✅
   - Metadata field validation (types, required fields)
   - Tag quality checks (3+ tags, lowercase, underscores)
   - Confidence field validation
   - Severity field validation (emergency domain)
   - Language code validation (ISO 639-1)
   - Front matter structure validation

3. **validate_references.py** ✅
   - Citation format validation (APA compliance)
   - Sources list vs. References section alignment
   - Author and date field validation
   - ISBN/DOI format validation
   - Duplicate reference detection

4. **validate_links.py** ✅
   - External link detection (should not exist in offline system)
   - Internal relative link validation
   - Broken link detection
   - Offline-safe link enforcement
   - Cross-document reference validation

5. **build_index_preview.py** ✅
   - Lightweight RAG chunking simulation
   - H2 boundary chunk detection
   - Word count per chunk analysis
   - Keyword density preview (first 50 words importance)
   - Token budget estimation
   - No embeddings, no FAISS indexing

### Code Quality Validators

**Ruff (Linting & Formatting)**

**Configuration:** `pyproject.toml`

**Checks Enabled:**
- PEP 8 style compliance
- Naming conventions (PEP 8)
- Docstring presence (required for public functions)
- Import ordering
- Unused imports detection
- Complexity checks (cyclomatic, cognitive)
- Type annotation checks (partial)

**Local Usage:**
```bash
make lint          # ruff check .
make format        # ruff format .
```

**CI Integration:** .github/workflows/ci.yml runs `ruff format --check .` on every PR

**Status:** ✅ Passing

**Pytest (Unit & Integration Testing)**

**Configuration:** `pyproject.toml`

**Test Structure:**
- `tests/unit/` — unit tests for individual modules
- `tests/integration/` — integration tests for module interactions
- `tests/smoke/` — smoke tests for end-to-end functionality

**Implemented Tests:**
- `tests/unit/test_validate_knowledge_base.py` — 30+ tests for KB validator
  - Metadata validation (required fields, types)
  - Domain validation (valid domain values)
  - Section validation (required sections per domain)
  - Sources validation (non-empty list)
  - Duplicate title detection
  - Filename convention checking
  - Edge cases and error conditions

**Local Usage:**
```bash
make test          # pytest
pytest -v          # verbose output
```

**CI Integration:** .github/workflows/ci.yml runs `pytest` on every PR

**Status:** ✅ Passing

### CI/CD Pipeline

**Location:** `.github/workflows/ci.yml`

**Jobs:**
1. **Lint** — Ruff check (PEP 8, naming, unused imports)
2. **Format Check** — Ruff format check (no auto-formatting in CI)
3. **Tests** — pytest with verbose output
4. **Knowledge Base Validation** — `python scripts/validate_knowledge_base.py`
5. **Metadata Validation** — `python scripts/validate_metadata.py`
6. **References Validation** — `python scripts/validate_references.py`
7. **Links Validation** — `python scripts/validate_links.py`

**Trigger:** Push to any branch; PR merges require all checks passing

**Status:** ✅ All checks passing on current main and feature/knowledge-base branches

**Detailed Workflow Steps:**
- Python 3.11 environment
- Dependency installation from requirements-dev.txt
- Ruff linting
- Ruff format check
- pytest execution
- All knowledge base validators run sequentially

---

## Current Git Branch

**Active Development:** `feature/knowledge-base`

**Latest Commit (feature/knowledge-base):**
- 5 disease documents authored (Newcastle, Avian Influenza, Gumboro, Infectious Bronchitis, Coccidiosis)
- All validators passing
- All CI checks passing

**Main Branch (Stable):**
- Sprint 1.5 architecture refinement complete
- Status: Stable, ready for knowledge base merges

**Branch Protection:** None (can force push, direct commits allowed)

**Recommended Workflow:**
1. Work on `feature/knowledge-base` branch
2. Create feature sub-branches for document batches: `feature/knowledge-base-batch-2`, etc.
3. Open PRs against `feature/knowledge-base`
4. Merge back to `feature/knowledge-base` after review and validator passes
5. Once all 35 documents complete, open PR from `feature/knowledge-base` to `main`

---

## Outstanding Tasks

### Sprint 2.3 Batch 2 — Disease Documents (5 of 35)

**Status:** In Progress

**Objective:** Complete second batch of disease documents to reach 13 of 35 total documents.

**Documents to Create:**

1. **Infectious Coryza** (`knowledge_base/diseases/infectious_coryza.md`)
   - Bacterial infection causing sinusitis and respiratory disease
   - Key sections: Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
   - Sources: OIE/WOAH technical card, FAO, peer-reviewed veterinary literature
   - Tags: infectious_coryza, respiratory, bacterial, sinusitis, odor

2. **Marek's Disease** (`knowledge_base/diseases/mareks_disease.md`)
   - Herpes virus infection causing immunosuppression and tumors
   - Key sections: Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
   - Sources: OIE/WOAH, FAO, Marek's disease research literature
   - Tags: mareks_disease, herpes_virus, immunosuppression, paralysis, tumors

3. **Fowl Cholera** (`knowledge_base/diseases/fowl_cholera.md`)
   - Acute bacterial disease with high mortality
   - Key sections: Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
   - Sources: OIE/WOAH, national veterinary authorities
   - Tags: fowl_cholera, bacterial, mortality, acute, pasteurella

4. **Fowl Pox** (`knowledge_base/diseases/fowl_pox.md`)
   - Viral disease causing skin lesions and respiratory signs
   - Key sections: Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
   - Sources: OIE/WOAH technical card, FAO
   - Tags: fowl_pox, viral, skin_lesions, diphtheritic_form, wet_form

5. **Pullorum Disease** (`knowledge_base/diseases/pullorum_disease.md`)
   - Bacterial disease affecting chicks, reducing production in adults
   - Key sections: Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
   - Sources: OIE/WOAH, national veterinary authority
   - Tags: pullorum_disease, bacterial, chicks, production_loss, salmonella

**Execution Workflow:**

For each document:

1. **Prepare** (15 min)
   - Confirm 3+ authoritative sources (FAO, OIE/WOAH, peer-reviewed)
   - Outline sections and word count targets
   - Note key clinical signs and epidemiology

2. **Author** (60 min)
   - Create file: `knowledge_base/diseases/<filename>.md`
   - Copy template from `docs/knowledge_base_schema.md`
   - Fill YAML front matter: title, domain: diseases, tags (5–8), reviewed: false, sources
   - Write Overview (80–150 words): disease name, causative agent, primary signs
   - Write Symptoms (150–300 words): observable clinical signs, mortality rates
   - Write Treatment and Management (150–300 words): isolation, supportive care, veterinarian disclaimer
   - Write Prevention and Vaccination (150–250 words): vaccine references, timing
   - Write When to Call a Veterinarian (80–150 words): escalation criteria
   - Write References: APA format, full citations

3. **Validate** (2 min)
   ```bash
   python scripts/validate_knowledge_base.py
   python scripts/validate_metadata.py
   python scripts/validate_references.py
   python scripts/validate_links.py
   python scripts/build_index_preview.py
   ```

4. **Commit & PR**
   ```bash
   git add knowledge_base/diseases/<filename>.md
   git commit -m "docs(kb-diseases): add <disease-name> disease document"
   git push origin feature/knowledge-base
   ```

5. **Review & Merge**
   - CI runs all validators (must pass)
   - Peer review confirms sourcing, accuracy, style
   - Update `reviewed: true` and `confidence: high/medium`
   - Merge to `feature/knowledge-base`

**Estimated Timeline:**
- 5 documents × 80 min (prep + author + validate + commit) = 400 minutes
- Plus review time: 30 min per document = 150 minutes
- **Total: ~9 hours over 2–3 days**

### Sprint 2.2 (Pending) — Vaccination Documents (4 of 35)

**Objective:** Create vaccination schedules and administration guides.

**Documents:**
- Broiler Vaccination Schedule
- Layer Vaccination Schedule
- Vaccine Storage and Handling
- Vaccine Administration

### Sprint 2.4 (Pending) — Climate, Biosecurity, Feeding, Management (13 of 35)

**Objective:** Complete remaining priority domains.

- Climate (3): Housing ventilation, Heat stress, Cold stress
- Biosecurity (3): Farm checklist, Visitor protocols, Disinfection
- Feeding (4): Broiler nutrition, Layer nutrition, Feed storage, Water quality
- Management (3): Flock records, Mortality tracking, Production records

### Sprint 2.5 (Pending) — Emergency & FAQ Documents (8 of 35)

**Objective:** Create emergency alerts and frequently asked questions.

- Emergency (3): Newcastle emergency, Avian Influenza emergency, Mass mortality
- FAQ (5): Common farmer questions across all domains

### Future Sprints (Not Yet Started)

**Sprint 3 — Dataset Preparation**
- Collect 100 reference Q&A pairs from agricultural extension sources
- Generate 200 synthetic Q&A pairs from knowledge base
- Implement evaluation metrics (BLEU, ROUGE, semantic similarity)
- Document dataset provenance

**Sprint 4 — RAG Pipeline**
- Implement markdown chunker (`rag/chunking/markdown_chunker.py`)
- Implement embedder (`rag/embeddings/embedder.py`)
- Implement index builder (`rag/indexing/index_builder.py`)
- Implement retriever (`rag/retrieval/retriever.py`)
- Implement prompt builder (`rag/prompts/prompt_builder.py`)
- Build `scripts/build_index.py`
- Achieve retrieval latency < 500 ms

**Sprint 5 — Local LLM Integration**
- Implement llama.cpp inference wrapper (`models/inference/llm_runner.py`)
- Implement query orchestrator (`app/backend/orchestrator.py`)
- Implement query service (`app/services/query_service.py`)
- Implement emergency service (`app/services/emergency_service.py`)
- Implement settings (`app/config/settings.py`)
- Implement logging, timing, memory utilities
- Validate end-to-end pipeline
- Achieve inference latency < 60 seconds

**Sprint 6 — Desktop Application**
- Build Streamlit multi-page application
- Implement 7 domain pages (disease, vaccination, climate, biosecurity, feeding, records, home)
- Implement emergency alert banner
- Implement chat widget and session history
- Achieve application startup < 30 seconds

**Sprint 7 — Benchmarking and Optimisation**
- Run full benchmark suite on ADTC Standard Laptop
- Profile startup time, inference latency, RAM usage, retrieval latency
- Run answer quality evaluation against dataset
- Optimise bottlenecks
- Produce benchmark report

**Sprint 8 — ADTC Submission**
- Write ADTC competition submission report
- Finalise all documentation
- Freeze model and knowledge base versions
- Tag v1.0.0-adtc release
- Package offline distribution bundle

---

## Recommended Next Task

### Sprint 2.3 Batch 2 — Create 5 Disease Documents

**Objective:** Progress from 10 of 35 to 15 of 35 documents. Complete remaining core disease documents for comprehensive disease coverage.

**Priority Order:**

1. **Infectious Coryza** (60 min) — Respiratory bacterial disease, high impact in tropical regions
2. **Marek's Disease** (60 min) — Herpes virus, major immunosuppression risk
3. **Fowl Cholera** (60 min) — High-mortality acute bacterial infection
4. **Fowl Pox** (60 min) — Viral disease with visible skin manifestations
5. **Pullorum Disease** (60 min) — Affects young chicks, reduces adult production

**Execution:**

For each disease document, follow this workflow:

1. **Research & Source** (15 min)
   - Confirm OIE/WOAH technical card availability
   - Identify FAO or peer-reviewed backup sources
   - Review national veterinary authority guidelines

2. **Draft** (45 min)
   - Use `docs/knowledge_base_schema.md` template
   - Fill YAML front matter (title, domain: diseases, 5–8 tags, sources)
   - Write all required sections with target word counts
   - Ensure key terms in first 50 words of Overview

3. **Validate & Format** (10 min)
   ```bash
   python scripts/validate_knowledge_base.py
   python scripts/validate_metadata.py
   python scripts/validate_references.py
   python scripts/validate_links.py
   ```

4. **Commit & Push**
   ```bash
   git add knowledge_base/diseases/<filename>.md
   git commit -m "docs(kb-diseases): add <disease-name>"
   git push origin feature/knowledge-base
   ```

5. **Request Review**
   - Open PR with disease name and source list
   - CI must pass (all validators)
   - Request peer review (20–30 min)
   - Address feedback if any
   - Merge when approved

**Success Criteria:**
- [ ] All 5 documents authored
- [ ] All pass all validators (schema, metadata, references, links)
- [ ] All CI checks passing
- [ ] All reviewed and approved by second contributor
- [ ] Knowledge base progress: 15 of 35 documents (43%)

**Estimated Timeline:**
- **Total:** ~9 hours (or 2–3 days with parallel reviews)
- **Per document:** 80 minutes (research, draft, validate, commit)
- **Review time:** 30 minutes per document (parallel with next document authoring)

**Next Steps After Batch 2:**
- Sprint 2.2 — Vaccination documents (4 documents)
- Sprint 2.4 — Climate, Biosecurity, Feeding, Management documents (13 documents)
- Sprint 2.5 — Emergency & FAQ documents (8 documents)
- **Target:** All 35 documents complete by end of Sprint 2

---

## References

- **Architecture:** `docs/architecture/`
- **Knowledge Engineering Standards:** `docs/knowledge_engineering.md`
- **Knowledge Base Schema:** `docs/knowledge_base_schema.md`
- **Knowledge Base Index:** `knowledge_base/README.md`
- **AI Developer Guide:** `AI_DEVELOPER_GUIDE.md`
- **Project Plan:** `docs/project_plan.md`
- **Roadmap:** `ROADMAP.md`
- **Changelog:** `CHANGELOG.md`

---

**Document Status:** Updated  
**Last Updated:** 11 July 2026  
**Sprint Progress:** Sprint 2 — 10 of 35 documents (29%)  
**Next Milestone:** Sprint 2.3 Batch 2 — 15 of 35 documents (43%)  
**Owner:** PoultryGuard AI Development Team
