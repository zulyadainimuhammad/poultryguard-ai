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
- Establish authoritative knowledge engineering standards
- Implement knowledge base schema and validator
- Curate minimum 35 documents across 10 domains
- Ensure factual accuracy and source traceability

**Target Completion:** End of Sprint 2

**Deliverables:**
- ✅ `docs/knowledge_engineering.md` — complete writing style, citation, chunking standards
- ✅ `docs/knowledge_base_schema.md` — authoritative schema and document template
- ✅ Knowledge base directory structure (10 domains)
- ✅ `scripts/validate_knowledge_base.py` — automated schema validator
- ✅ CI integration — validator runs on every PR
- ⏳ Knowledge base documents (0 of 35 completed)

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
- ✅ Validator (`scripts/validate_knowledge_base.py`)
- ✅ Unit tests (30+ test cases in `tests/unit/test_validate_knowledge_base.py`)
- ✅ CI integration (validator runs on every PR)
- ✅ `knowledge_base/README.md` updated with standards references and contribution workflow

**Outstanding (0 of 35 Documents):**
- Diseases: 0 of 8 (Newcastle, Avian Influenza, Gumboro, Marek's, Coccidiosis, Fowl Pox, Fowl Typhoid, Infectious Bronchitis)
- Vaccination: 0 of 4 (Broiler schedule, Layer schedule, Vaccine storage, Vaccine administration)
- Climate: 0 of 3 (Housing ventilation, Heat stress, Cold stress)
- Biosecurity: 0 of 3 (Farm checklist, Visitor protocols, Disinfection)
- Feeding: 0 of 4 (Broiler nutrition, Layer nutrition, Feed storage, Water quality)
- Management: 0 of 3 (Flock records, Mortality tracking, Production records)
- Market: 0 of 2 (Pricing guidance, Cost management)
- Emergency: 0 of 3 (Newcastle emergency, Avian Influenza emergency, Mass mortality)
- FAQ: 0 of 5 (Common farmer questions)

### AI_DEVELOPER_GUIDE.md ✅

**Location:** Repository root

**Purpose:** Permanent instruction manual for all AI coding assistants (ChatGPT, Continue, Amazon Q, GitHub Copilot, etc.)

**Content (10 Sections):**
1. Project Overview — mission, target users, offline-first philosophy
2. ADTC Constraints — CPU-only, 8 GB RAM, no cloud/GPU, offline requirement
3. Architecture Principles — layered design, module separation, dependency inversion
4. Coding Standards — Python 3.11+, type hints, docstrings, Ruff, pytest, pathlib
5. Git Workflow — feature branches, Conventional Commits, PR review before merge
6. Knowledge Base Standards — reference to engineering docs, authoritative sources only
7. RAG Principles — local FAISS, local embedder, grounded answers, no hallucination
8. Performance Goals — startup < 30s, first query < 60s, peak RAM < 6 GB
9. AI Assistant Behaviour — must read docs before changes, preserve architecture
10. Standard Development Workflow — read docs → implement → lint → format → test → KB validation → summarize

### Knowledge Base Quality System ✅

**Components Implemented:**
1. **Engineering Standards** (`docs/knowledge_engineering.md`)
   - 9 sections covering all aspects of document quality
   - Writing style for smallholder farmers (active voice, plain English, short sentences)
   - Markdown conventions (heading hierarchy, lists, emphasis, tables, links)
   - Metadata schema with YAML front matter
   - Citation requirements with 5-tier source ranking
   - Terminology standards (preferred terms, scientific names, units, drug names)
   - Chunking strategy for RAG (H2 boundaries, word count targets, keyword density)
   - Confidence levels (high/medium/low)
   - Review process (authoring → PR → review → approval)
   - Naming conventions (files, directories, titles, tags)
   - Document inventory targets (35 documents, 10 domains)

2. **Schema Reference** (`docs/knowledge_base_schema.md`)
   - YAML front matter specification
   - 10 valid domain values
   - Required sections per domain type (standard, disease, emergency, faq)
   - Filename conventions
   - Sources requirement
   - Complete document templates
   - Validator reference

3. **Automated Validator** (`scripts/validate_knowledge_base.py`)
   - Pure Python, stdlib-only (no extra dependencies)
   - Checks metadata presence and types
   - Validates domain values
   - Checks required sections for each domain
   - Verifies non-empty sources list
   - Detects duplicate titles
   - Enforces filename conventions
   - Provides clear error messages
   - Runs in CI on every PR

4. **Unit Tests** (`tests/unit/test_validate_knowledge_base.py`)
   - 30+ test cases covering all validator rules
   - Tests for each domain type
   - Tests for metadata validation
   - Tests for section validation
   - Tests for filename validation
   - Edge cases and error conditions

5. **Knowledge Base Index** (`knowledge_base/README.md`)
   - Domain structure and purposes
   - Document inventory targets (35 documents)
   - Adding a document workflow (11 steps)
   - Validation instructions
   - Content status table (currently 0 documents)

---

## Current Knowledge Base

**Status:** Framework complete, content authoring not yet started.

**Structure:** 10 domains, 0 documents authored

| Domain | Directory | Target Docs | Status | Priority |
|---|---|---|---|---|
| Diseases | `diseases/` | 8 | Not started | 1 |
| Vaccination | `vaccination/` | 4 | Not started | 2 |
| Climate | `climate/` | 3 | Not started | 3 |
| Biosecurity | `biosecurity/` | 3 | Not started | 3 |
| Feeding | `feeding/` | 4 | Not started | 3 |
| Management | `management/` | 3 | Not started | 3 |
| Market | `market/` | 2 | Not started | 3 |
| Emergency | `emergency/` | 3 | Not started | 4 |
| FAQ | `faq/` | 5 | Not started | 4 |
| Hausa | `hausa/` | — | Sprint 6 | 6 |
| **Total** | — | **35** | — | — |

**Authored Documents:** None

**Pending Priority Order:**
1. **Diseases (1st priority):** Newcastle disease, Avian Influenza, Gumboro disease, Marek's disease, Coccidiosis, Fowl Pox, Fowl Typhoid, Infectious Bronchitis
2. **Vaccination (2nd priority):** Broiler vaccination schedule, Layer vaccination schedule, Vaccine storage, Vaccine administration
3. **Climate (3rd priority):** Housing ventilation, Heat stress management, Cold stress management
4. **Biosecurity (3rd priority):** Farm biosecurity checklist, Visitor protocols, Disinfection guide
5. **Feeding (3rd priority):** Broiler nutrition, Layer nutrition, Feed storage, Water quality
6. **Management (3rd priority):** Flock records, Mortality tracking, Production records
7. **Market (3rd priority):** Market pricing guidance, Cost management
8. **Emergency (4th priority):** Newcastle disease emergency, Avian Influenza emergency, Mass mortality emergency
9. **FAQ (4th priority):** Common farmer questions (5 documents across all domains)

---

## Validation Status

### Ruff (Linting & Formatting)

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

**Status:** ✅ Passing (no Python code changes since Sprint 1)

### Pytest (Unit & Integration Testing)

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

**Status:** ✅ Passing (validator tests all pass)

### CI/CD Pipeline

**Location:** `.github/workflows/ci.yml`

**Jobs:**
1. **Lint** — Ruff check (PEP 8, naming, unused imports)
2. **Format Check** — Ruff format check (no auto-formatting in CI)
3. **Tests** — pytest with verbose output
4. **Knowledge Base Validation** — `python scripts/validate_knowledge_base.py`

**Trigger:** Push to any branch; PR merges require all checks passing

**Status:** ✅ All checks passing on current main and feature/knowledge-base branches

**Detailed Workflow Steps:**
- Python 3.11 environment
- Dependency installation from requirements-dev.txt
- Ruff linting
- Ruff format check
- pytest execution
- Knowledge base validation

---

## Current Git Branch

**Active Development:** `feature/knowledge-base`

**Latest Commit (feature/knowledge-base):**
- SHA: `2da126b852739c1038eb2b90b1bad983f8d81b9a`
- Unstaged: Knowledge base framework (schema, standards docs, validator, tests)

**Main Branch (Stable):**
- SHA: `743af592355ef1cf7fcab5f93a926b11907549ce`
- Status: Stable (Sprint 1.5 architecture refinement complete)

**Branch Protection:** None (can force push, direct commits allowed)

**Recommended Workflow:**
1. Branch created: `feature/knowledge-base` (from main)
2. Create feature sub-branches for document groups: `feature/knowledge-base-diseases`, `feature/knowledge-base-vaccination`, etc.
3. Open PRs against `feature/knowledge-base`
4. Merge back to `feature/knowledge-base` after review
5. Once all 35 documents complete, open PR from `feature/knowledge-base` to `main`

---

## Outstanding Tasks

### Sprint 2 — Knowledge Engineering (In Progress)

**Not Started:**

1. **Disease Documents (8 of 35)** — Highest priority
   - [ ] Newcastle Disease (`diseases/newcastle_disease.md`)
     - Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
     - Sources: FAO, OIE/WOAH technical cards
     - Tags: newcastle, paramyxovirus, respiratory, neurological
   - [ ] Avian Influenza (`diseases/avian_influenza.md`)
     - Highest severity; Tier 1 sources critical
   - [ ] Gumboro Disease (`diseases/gumboro_disease.md`)
   - [ ] Marek's Disease (`diseases/mareks_disease.md`)
   - [ ] Coccidiosis (`diseases/coccidiosis.md`)
   - [ ] Fowl Pox (`diseases/fowl_pox.md`)
   - [ ] Fowl Typhoid (`diseases/fowl_typhoid.md`)
   - [ ] Infectious Bronchitis (`diseases/infectious_bronchitis.md`)

2. **Vaccination Documents (4 of 35)** — 2nd priority
   - [ ] Broiler Vaccination Schedule (`vaccination/vaccination_schedule_broilers.md`)
   - [ ] Layer Vaccination Schedule (`vaccination/vaccination_schedule_layers.md`)
   - [ ] Vaccine Storage and Handling (`vaccination/vaccine_storage.md`)
   - [ ] Vaccine Administration (`vaccination/vaccine_administration.md`)

3. **Climate Documents (3 of 35)** — 3rd priority
   - [ ] Housing Ventilation (`climate/housing_ventilation.md`)
   - [ ] Heat Stress Management (`climate/heat_stress_management.md`)
   - [ ] Cold Stress Management (`climate/cold_stress_management.md`)

4. **Biosecurity Documents (3 of 35)** — 3rd priority
   - [ ] Farm Biosecurity Checklist (`biosecurity/farm_biosecurity_checklist.md`)
   - [ ] Visitor Protocols (`biosecurity/visitor_protocols.md`)
   - [ ] Disinfection Guide (`biosecurity/disinfection_guide.md`)

5. **Feeding Documents (4 of 35)** — 3rd priority
   - [ ] Broiler Nutrition (`feeding/broiler_nutrition.md`)
   - [ ] Layer Nutrition (`feeding/layer_nutrition.md`)
   - [ ] Feed Storage (`feeding/feed_storage.md`)
   - [ ] Water Quality (`feeding/water_quality.md`)

6. **Management Documents (3 of 35)** — 3rd priority
   - [ ] Flock Records (`management/flock_records.md`)
   - [ ] Mortality Tracking (`management/mortality_tracking.md`)
   - [ ] Production Records (`management/production_records.md`)

7. **Market Documents (2 of 35)** — 3rd priority
   - [ ] Market Pricing Guidance (`market/market_pricing_guidance.md`)
   - [ ] Cost Management (`market/cost_management.md`)

8. **Emergency Documents (3 of 35)** — 4th priority
   - [ ] Newcastle Disease Emergency (`emergency/newcastle_disease_emergency.md`)
   - [ ] Avian Influenza Emergency (`emergency/avian_influenza_emergency.md`)
   - [ ] Mass Mortality Emergency (`emergency/mass_mortality_emergency.md`)

9. **FAQ Documents (5 of 35)** — 4th priority
   - [ ] 5 frequently asked questions across all domains

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

### Immediate Priority: Author Sprint 2 Knowledge Base Documents

**Objective:** Reach 35 documents (0 of 35 currently) to enable Sprint 3 evaluation dataset work.

**Phased Approach:**

#### Phase 1: Disease Documents (8 documents)

**Why First:** Diseases are the core domain; vaccination, emergency, and FAQ documents depend on disease knowledge.

**Execution:**

1. **Create Newcastle Disease** (`knowledge_base/diseases/newcastle_disease.md`)
   - Foundational document; most common in African poultry
   - Template from `docs/knowledge_base_schema.md`
   - Sections: Overview, Symptoms, Treatment, Prevention/Vaccination, When to Call Vet, References
   - Sources: FAO Newcastle Disease publication, OIE/WOAH technical card, peer-reviewed literature
   - Target word counts: Overview (80–150), Symptoms (150–300), Treatment (150–300), Prevention (150–250), When to Call (80–150)
   - Run validator: `python scripts/validate_knowledge_base.py`
   - Open PR on `feature/knowledge-base`
   - Peer review confirms sourcing, accuracy, and style compliance
   - Merge after approval

2. **Avian Influenza** (`diseases/avian_influenza.md`)
   - Highest severity emergency concern
   - Tier 1 sources mandatory (OIE/WOAH, FAO)
   - HPAI (H5N1, H5N8) focus for African context

3. **Gumboro, Marek's, Coccidiosis, Fowl Pox, Fowl Typhoid, Infectious Bronchitis**
   - Follow same process
   - Prioritise sources, then style, then completeness

#### Phase 2: Vaccination Documents (4 documents)

**Execution Order:**
1. Broiler vaccination schedule (depends on disease documents)
2. Layer vaccination schedule
3. Vaccine storage and handling
4. Vaccine administration

#### Phase 3: Climate, Biosecurity, Feeding, Management Documents (12 documents)

**Parallel Execution:** No cross-domain dependencies; can be authored simultaneously.

#### Phase 4: Emergency and FAQ Documents (5 documents)

**Depends On:** Disease documents complete.

**Execution:** Emergency alerts mapped to Newcastle, Avian Influenza, and mass mortality scenarios. FAQ answers drawn from all domains.

### Document Authoring Workflow

For each document:

1. **Prepare** (20 min)
   - Read `docs/knowledge_engineering.md` in full
   - Read `docs/knowledge_base_schema.md` template for domain
   - Identify 3+ authoritative sources (FAO, OIE/WOAH, peer-reviewed, national authority)
   - Outline sections and word count targets

2. **Author** (60–90 min)
   - Create file: `knowledge_base/<domain>/<filename>.md`
   - Copy template from schema doc
   - Fill YAML front matter: title, domain, tags (5–8), reviewed: false, sources (APA format)
   - Write each section with target word counts
   - Ensure first 50 words of Overview contain disease name, cause, primary signs
   - Use preferred terminology (see `docs/knowledge_engineering.md` Section 5)
   - Use active voice, short sentences (max 25 words)
   - Include veterinarian disclaimer in treatment/emergency sections

3. **Validate** (2 min)
   ```bash
   python scripts/validate_knowledge_base.py
   ```
   - Fix any metadata, section, or filename errors
   - Re-run until clean

4. **Commit** (1 min)
   ```bash
   git add knowledge_base/<domain>/<filename>.md
   git commit -m "docs(kb): add <document-title> to <domain> domain"
   ```

5. **Pull Request** (5 min)
   - Push to feature branch
   - Open PR with description: domain, document name, sources (brief list)
   - Link to CI run (validator must pass)

6. **Review** (30–60 min)
   - Second reviewer checks out branch
   - Confirms all claims supported by sources (especially dosages, mortality rates)
   - Verifies veterinarian disclaimer present
   - Checks writing style (active voice, short sentences, farmer-friendly)
   - Confirms terminology consistency
   - Validates section word counts

7. **Approve & Merge** (5 min)
   - Author updates `reviewed: true` and `confidence: high/medium`
   - PR merged to main branch
   - FAISS index will be built in Sprint 4

### Success Criteria for Sprint 2

- [ ] All 35 documents authored and committed
- [ ] All documents pass schema validator
- [ ] All documents reviewed by a second contributor
- [ ] All documents have `reviewed: true`
- [ ] All documents have `confidence: high` or `medium` (no `low` in production)
- [ ] All CI checks passing (ruff, pytest, validator)
- [ ] Knowledge base status table in `knowledge_base/README.md` updated
- [ ] CHANGELOG.md updated with document inventory

### Estimated Timeline

- **Phase 1 (Diseases):** 8 × 2 hours = 16 hours (1–2 weeks with review)
- **Phase 2 (Vaccination):** 4 × 1.5 hours = 6 hours (3–4 days)
- **Phase 3 (Climate, Biosecurity, Feeding, Management):** 12 × 1.5 hours = 18 hours (1 week)
- **Phase 4 (Emergency, FAQ):** 8 × 1 hour = 8 hours (4–5 days)
- **Total:** ~48 hours elapsed time over 3–4 weeks (assuming parallel contributions)

### Acceptance Criteria

Each document must:
- [ ] Pass schema validator without errors
- [ ] Contain minimum 3 tags; aim for 5–8
- [ ] Cite minimum 1 authoritative source (Tier 1–3)
- [ ] Achieve target word counts per section
- [ ] Use preferred terminology consistently
- [ ] Include veterinarian disclaimer in required sections
- [ ] Be reviewed and approved by a second contributor
- [ ] Have `reviewed: true` before merge
- [ ] Have CI checks passing (ruff, pytest, validator)

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

**Document Status:** Complete  
**Last Review:** 11 July 2026  
**Owner:** PoultryGuard AI Development Team
