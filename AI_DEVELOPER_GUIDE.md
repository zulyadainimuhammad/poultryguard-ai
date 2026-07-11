# AI Developer Guide

This guide is the permanent instruction manual for AI coding assistants working on PoultryGuard AI, including ChatGPT, Continue, Amazon Q, GitHub Copilot, and similar tools.

Every AI assistant must read this file before making changes to the repository.

---

## 1. Project Overview

PoultryGuard AI is an offline AI-powered poultry health, vaccination, climate, biosecurity, and farm management assistant.

The project exists to support the Africa Deep Tech Challenge (ADTC) 2026 by demonstrating a practical, locally deployable AI system that can help poultry farmers and extension officers without relying on cloud infrastructure.

Target users include:

- Smallholder poultry farmers
- Agricultural extension officers
- Veterinary support workers
- Poultry farm managers
- Students and researchers working on African agritech systems

The central philosophy is offline-first development. PoultryGuard AI must remain useful in low-connectivity and no-connectivity environments. Runtime inference, retrieval, knowledge access, logging, and evaluation must be designed so they can operate locally on the target machine.

---

## 2. ADTC Constraints

All development decisions must respect the ADTC Standard Laptop target and competition constraints.

Required constraints:

- CPU-only inference.
- Maximum practical RAM target: 8 GB system memory.
- Ubuntu 22.04 LTS compatibility.
- llama.cpp runtime only for local LLM inference.
- GGUF model files only.
- No cloud inference.
- No external API calls during inference.
- No runtime dependency on internet access.
- No GPU, CUDA, ROCm, Metal, or cloud accelerator assumption.

Do not add features, dependencies, or architecture choices that require cloud-hosted models, remote vector databases, managed APIs, or online services during normal operation.

---

## 3. Architecture Principles

PoultryGuard AI follows a clean, layered architecture. Preserve the boundaries defined in `README.md` and `docs/architecture/`.

Core principles:

- Use layered architecture with clear separation between UI, backend orchestration, services, RAG, model inference, configuration, utilities, and storage.
- Keep modules small, modular, and testable.
- Apply single responsibility: each module should have one clear reason to change.
- Use dependency inversion: high-level workflows should depend on interfaces or injected collaborators, not hardcoded concrete implementations.
- Avoid circular imports.
- Prefer composition over inheritance.
- Keep the Query Classification Layer separate from the orchestrator.
- Keep the Emergency Advisory Module deterministic and independent of the LLM.
- Keep RAG, inference, and Streamlit UI concerns separate.

Expected architecture boundaries:

- `app/frontend/`: Streamlit pages and reusable UI components.
- `app/backend/`: entry points, query orchestration, and query classification.
- `app/services/`: use-case services and application workflow coordination.
- `app/config/`: settings, defaults, and configuration loading.
- `app/utils/`: logging, timing, memory, and shared helpers.
- `rag/`: chunking, embeddings, indexing, retrieval, and prompt construction.
- `models/`: llama.cpp inference boundary and model configuration.
- `knowledge_base/`: curated Markdown source documents.
- `vector_store/`: generated FAISS indexes and metadata.

---

## 4. Coding Standards

Use production-quality Python and keep the codebase easy for humans and AI tools to reason about.

Required standards:

- Python 3.11 or newer.
- Type hints for public functions, classes, and service boundaries.
- Clear docstrings for modules, classes, and non-trivial functions.
- `pathlib.Path` instead of `os.path` for filesystem paths.
- PEP 8 naming and readability conventions.
- Ruff for linting and formatting.
- pytest for tests.
- Small, focused modules.
- Deterministic behavior where possible.
- No hidden network calls.
- No unnecessary global state.
- No broad exception swallowing.
- No large binary files committed to Git.

Prefer explicit configuration through `app/config/` and `.env.example` over hardcoded paths or magic numbers.

---

## 5. Git Workflow

Do not commit directly to `main`.

Required workflow:

- Create a feature branch for every change.
- Use descriptive branch names, such as `feature/knowledge-base`, `docs/architecture-update`, or `fix/rag-validator`.
- Use Conventional Commits.
- Open a pull request before merging.
- Keep pull requests focused and reviewable.
- Do not mix unrelated refactors with feature work.
- Do not commit generated FAISS indexes, GGUF models, caches, logs, virtual environments, or local secrets.

Conventional commit examples:

```text
docs(project): add AI developer guide
feat(rag): add markdown chunker
fix(config): validate missing model path
test(kb): add schema validator tests
```

---

## 6. Knowledge Base Standards

All knowledge base work must follow:

- `docs/knowledge_engineering.md`
- `docs/knowledge_base_schema.md`
- `knowledge_base/README.md`

Knowledge base documents must be written in RAG-optimized Markdown. Headings, metadata, section structure, and source fields must remain consistent so the future chunking and retrieval pipeline can produce high-quality context.

Use authoritative veterinary and agricultural sources only, such as:

- FAO publications
- WOAH/OIE technical disease cards
- Peer-reviewed veterinary and poultry science literature
- National veterinary authority guidance
- University extension publications
- Reputable agricultural research institutions

Do not cite Wikipedia, social media, marketing pages, undated blogs, forums, or AI-generated content as sources.

Never invent veterinary advice, drug names, dosages, mortality rates, vaccine schedules, or disease claims. If the source does not support a claim, remove the claim or mark uncertainty clearly.

---

## 7. RAG Principles

PoultryGuard AI uses Retrieval-Augmented Generation to ground model responses in local, curated knowledge.

Required RAG principles:

- Use a local FAISS index.
- Use a local embedding model.
- Build indexes from local Markdown knowledge base files.
- Ground answers using retrieved context.
- Include source metadata where possible.
- Never hallucinate unsupported facts.
- Prefer saying that the knowledge base does not contain enough information over guessing.
- Keep retrieval fast enough for the ADTC Standard Laptop.
- Keep the prompt builder aware of context-window limits.
- Preserve the emergency path as deterministic and independent of RAG or LLM availability.

The local LLM is an answer generator, not an authority. The knowledge base and retrieved context are the factual source of truth.

---

## 8. Performance Goals

Optimize for the ADTC Standard Laptop, not high-end development machines.

Performance goals:

- Low RAM usage under the 8 GB system-memory constraint.
- Peak runtime memory target below 6 GB where practical.
- CPU-only inference through llama.cpp.
- Fast FAISS retrieval.
- Responsive Streamlit UI.
- Application startup target below 30 seconds.
- First query target below 60 seconds.
- Subsequent query target below 30 seconds.
- Retrieval latency target below 500 ms.

Avoid dependencies or design choices that substantially increase RAM usage, startup time, model load time, or offline package size without a documented reason.

---

## 9. AI Assistant Behaviour

Every AI assistant must do the following before making changes:

- Read this file.
- Read `README.md`.
- Read `ROADMAP.md`.
- Read `CHANGELOG.md`.
- Read the files in `docs/architecture/`.
- Read `docs/knowledge_engineering.md`.
- Read `docs/knowledge_base_schema.md`.

Every AI assistant must preserve project architecture:

- Respect existing module boundaries.
- Avoid unnecessary dependencies.
- Avoid application feature implementation when the task is documentation, planning, or scaffolding only.
- Avoid broad rewrites unless explicitly requested.
- Avoid changing generated files, local caches, or large artifacts.
- Keep CI passing.
- Explain major design decisions.
- Summarize what changed and what was verified.

When working with knowledge base content, AI assistants must prioritize factual accuracy, source traceability, and farmer safety over speed or completeness.

When unsure, prefer a smaller, well-documented change that fits the architecture over a large speculative implementation.

---

## 10. Standard Development Workflow

Every task should follow this workflow:

1. Read documentation.
2. Confirm the requested scope.
3. Implement the smallest coherent change.
4. Run Ruff lint:

   ```bash
   ruff check .
   ```

5. Run Ruff format check or formatting:

   ```bash
   ruff format --check .
   ```

   or, when formatting changes are intended:

   ```bash
   ruff format .
   ```

6. Run pytest:

   ```bash
   pytest
   ```

7. Run knowledge base validation when knowledge documents changed:

   ```bash
   python scripts/validate_knowledge_base.py
   ```

8. Summarize changes.
9. Summarize verification.
10. Suggest a Conventional Commit message.

If a task changes only Markdown documentation and no Python files, Ruff and pytest may be unnecessary. In that case, explicitly say that code checks were not run because the change was documentation-only.

Suggested commit for this file:

```text
docs(project): add AI developer guide
```

