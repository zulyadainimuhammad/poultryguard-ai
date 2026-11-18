# Development and Deployment

**Last reviewed:** 18 November 2026  
**Current runtime:** Local Streamlit MVP; production deployment is not yet supported.

This document describes the supported developer runtime for the merged PoultryGuard AI MVP. It does not describe a production cloud deployment. Historical Docker or llama.cpp scaffolding must not be treated as a verified production path unless separately tested and documented.

## 1. Current runtime

- Python 3.11
- Streamlit entry point: `app/frontend/main.py`
- Local SQLite data file: `data/poultryguard.db`
- Local FAISS index: `vector_store/poultryguard.faiss`
- Local chunk metadata: `vector_store/metadata.json`
- Groq answer generation requires internet access and `GROQ_API_KEY`
- Sentence Transformer embedding model must be available in the local cache
- Altair is used for Farm Intelligence analytics charts

The application currently provides two navigation areas:
- **Knowledge Assistant:** local retrieval and Groq-backed answer generation with source display.
- **Farm Intelligence:** Dashboard, Farm Profiles, Flock Management, Daily Records and Analytics.

Farm records are persisted locally in SQLite. Temperature and humidity are currently manual daily-record fields; automated sensor ingestion is not part of the current runtime.

## 2. Windows PowerShell setup

```powershell
git clone https://github.com/zulyadainimuhammad/poultryguard-ai.git
cd poultryguard-ai
git switch main

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

Copy-Item .env.example .env
```

Edit `.env` and set:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=qwen/qwen3.8-27b
```

Never commit `.env` or real API credentials. The repository's `.env.example` contains placeholders, not secrets.

## 3. Build the knowledge index

The retriever expects the generated FAISS index and metadata under `vector_store/`. The indexing implementation is `KnowledgeBaseIndexer` in `rag/indexing/indexer.py`.

The Sentence Transformer model is configured for local-only loading; ensure it is available in the local model cache before building/querying the index.

On a connected development machine, populate the model cache:

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
```

Build the index:

```powershell
python scripts/build_index.py
```

Generated index files are local runtime artefacts and should not be committed.

## 4. Run the application

```powershell
streamlit run app/frontend/main.py
```

Select Knowledge Assistant or Farm Intelligence from the application sidebar. Farm Intelligence supports farm profiles, flock management, daily production records and flock analytics.

## 5. Development checks

```powershell
python -m pytest
ruff check .
ruff format --check .
python scripts/validate_knowledge_base.py
python scripts/validate_metadata.py
python scripts/validate_references.py
python scripts/validate_links.py
```

The 18 November 2026 local run reported 98 passing tests. GitHub Actions CI for PR #11 also completed successfully. Test success demonstrates software checks for the current suite; it is not evidence of field validation, veterinary correctness or production readiness.

## 6. Local data and reset behaviour

The SQLite database is created under `data/` by the database initialisation function.

**Do not delete the database to reset a development environment unless you intend to discard local farm records.** For demonstrations, prefer a separate copy or explicitly backed-up demo database. Preserve the original database before any migration or destructive test.

FAISS index files can be rebuilt from the version-controlled knowledge base.

## 7. Production deployment — not yet ready

The current Streamlit/SQLite runtime is a local MVP. Before public or multi-user deployment, complete:

### Application and data architecture
- Stable API boundary and versioned service contracts.
- Versioned database migrations.
- Production database selection and tested SQLite-to-PostgreSQL migration.
- Farm-level data isolation and tested data-access rules.
- File/document storage strategy.

### Identity, security and privacy
- Authentication and role-based authorisation.
- Least-privilege access for farmers, staff, administrators and experts.
- Secret management; no credentials in source code or logs.
- Encryption in transit and at rest.
- Consent, retention, privacy and incident-response procedures.

### Cloud operations and reliability
- Cloud-provider and deployment-topology evaluation against documented requirements.
- Containerised and reproducible runtime.
- Separate development, staging and production environments.
- CI/CD, deployment approvals, rollback and release process.
- Centralised logging, metrics, service monitoring and operational alerting.
- Encrypted backups, retention and tested restore procedures.
- Security, load, availability and recovery testing.

### Product and domain validation
- Farmer usability pilot and documented findings.
- Veterinary and agricultural extension review of relevant knowledge and warnings.
- Validation of data definitions, environmental thresholds and any future decision-support rules.
- Clear user communication about limitations and human expert escalation.

No cloud provider is selected by this document. Cloud Engineering is a planned cross-cutting capability; provider selection should follow requirements for cost, availability, connectivity, data residency, security and operational capacity.

See [Target Architecture](target_architecture.md), [ROADMAP.md](../../ROADMAP.md) and [the implementation plan](../project_plan.md).
