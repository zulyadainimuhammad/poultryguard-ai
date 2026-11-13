# AI-Assisted Development Guide

This document defines working rules for human developers and any coding assistant used on PoultryGuard AI. It is guidance for the current codebase, not a substitute for reviewing the implementation and tests.

## 1. Product overview

PoultryGuard AI is a developing poultry farm intelligence platform. The current prototype combines:

- A Streamlit poultry knowledge assistant.
- Curated Markdown content, local semantic embeddings and FAISS retrieval.
- Groq-based answer generation using retrieved evidence.
- SQLite persistence for farms, flocks and daily records.
- Farm and analytics application services.

The Farm Intelligence UI, health and vaccination records, farm-aware AI summaries, field validation and production cloud deployment remain planned work. Do not describe planned capabilities as implemented.

## 2. Current architecture

- `app/frontend/`: Streamlit user interface.
- `app/services/`: application services for farm operations, analytics and answer generation.
- `app/database/`: dataclasses, SQLite connection and repositories.
- `rag/`: Markdown parsing/chunking, embeddings, FAISS indexing and retrieval.
- `knowledge_base/`: sourced poultry reference content.
- `vector_store/`: generated index and chunk metadata; do not commit.
- `data/`: local SQLite database; do not commit.
- `tests/`: pytest suite.
- `scripts/`: knowledge-base and development validators.

The intended dependency flow is UI → services → repositories → database. RAG components should remain independent of Streamlit.

## 3. Runtime facts

- Python 3.11 is the supported development runtime.
- Embeddings and FAISS retrieval run locally once the model and index are present.
- Answer generation currently calls Groq and requires internet access and `GROQ_API_KEY`.
- The current application is not fully offline.
- The current Streamlit entry point is `streamlit run app/frontend/main.py`.
- The current farm schema includes farms, flocks and daily_records only.

Do not assume `app/backend/main.py`, Docker Compose or llama.cpp/GGUF scaffolding is the current application entry point or active generation implementation.

## 4. Coding principles

- Keep UI, business workflows, persistence and retrieval concerns separate.
- Add type hints and clear docstrings to public interfaces.
- Use parameterised SQL and validate user input.
- Keep credentials in environment variables, never in source code.
- Make tests deterministic and independent of live external APIs where possible.
- Handle missing index/model/provider errors explicitly.
- Avoid wide refactors while implementing a product vertical slice.
- Preserve existing farmer data when changing the schema.

## 5. Data and analytics rules

- Daily production metrics must be based on dated records.
- Sort records chronologically before cumulative calculations.
- Do not silently convert missing measurements into zero.
- Define duplicate-record and correction semantics before enabling editing.
- Add versioned migrations before introducing new tables.
- Do not expose one farm's records to another farm or user.

## 6. Responsible AI rules

PoultryGuard is a decision-support tool, not a veterinary diagnostic or prescription system.

- Use only relevant retrieved evidence for knowledge answers.
- Acknowledge when evidence is insufficient.
- Never invent drug dosages, prescriptions or treatment protocols.
- Escalate severe illness, suspected outbreaks and high mortality to qualified professionals.
- Distinguish recorded farm measurements from generated interpretation.
- Do not claim prediction accuracy, reduced mortality or productivity impact without formal evaluation.

## 7. Development workflow

Use focused feature branches and descriptive commits. Do not commit directly to `main`.

Before opening a pull request, run:

```powershell
python -m pytest -v
ruff check .
ruff format --check .
python scripts/validate_knowledge_base.py
python scripts/validate_metadata.py
python scripts/validate_references.py
python scripts/validate_links.py
```

Update README, roadmap, project plan and changelog when implementation state changes. Do not rewrite shared history or force-push without explicit approval and a backup plan.
