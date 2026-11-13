# Development and Deployment

**Last reviewed:** 13 November 2026

This document describes how to run the current PoultryGuard prototype. It does not describe a production deployment. The Docker and llama.cpp files currently in the repository are scaffolding from an earlier design and are not the supported runtime path.

## 1. Current runtime

- Python 3.11
- Streamlit entry point: `app/frontend/main.py`
- SQLite local data file: `data/poultryguard.db`
- Local FAISS index: `vector_store/poultryguard.faiss`
- Local chunk metadata: `vector_store/metadata.json`
- Groq generation requires internet access and `GROQ_API_KEY`
- Sentence Transformer embedding model must be available in the local cache

## 2. Windows PowerShell setup

```powershell
git clone https://github.com/zulyadainimuhammad/poultryguard-ai.git
cd poultryguard-ai
git switch feature/gta-mvp

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

Copy-Item .env.example .env
```

Edit `.env` and set:

```dotenv
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Never commit `.env` or real API credentials.

## 3. Build the knowledge index

The retriever expects the generated FAISS index and metadata under `vector_store/`. The indexing implementation is `KnowledgeBaseIndexer` in `rag/indexing/indexer.py`. The Sentence Transformer model is configured for local-only loading; make sure it is available in the local model cache before indexing.

The index builder is exposed through the command-line wrapper:

```powershell
python scripts/build_index.py
```

On a connected development machine, populate the local Sentence Transformers model cache before running the build. The encoder uses local-only loading at runtime.

## 4. Run the application

```powershell
streamlit run app/frontend/main.py
```

The current UI is the poultry knowledge assistant. Farm and analytics services are implemented but the Farm Intelligence screens are not yet integrated.

## 5. Development checks

```powershell
python -m pytest -v
ruff check .
ruff format --check .
python scripts/validate_knowledge_base.py
python scripts/validate_metadata.py
python scripts/validate_references.py
python scripts/validate_links.py
```

## 6. Local data and reset behaviour

The SQLite database is created under `data/` by the database initialisation function. Do not delete it to reset a development environment unless you intend to discard local farm records. FAISS index files can be rebuilt from the version-controlled knowledge base.

## 7. Production deployment — not yet ready

Before any public or multi-farm deployment, complete:

- Authentication and role-based authorisation.
- Farm-level data isolation and privacy controls.
- Database migrations and PostgreSQL deployment.
- Secret management and encryption.
- Backups and tested restore procedures.
- Monitoring, logs, alerting and incident response.
- CI/CD, environment separation and rollback strategy.
- Security and usability validation.

Do not treat the current SQLite/Streamlit prototype or placeholder Docker files as a production-ready hosting setup.
