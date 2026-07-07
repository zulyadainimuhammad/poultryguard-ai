# PoultryGuard AI

Offline AI-powered poultry health, vaccination, climate, biosecurity, and farm management assistant for the Africa Deep Tech Challenge (ADTC) 2026.

PoultryGuard AI is designed to run entirely on the ADTC Standard Laptop without cloud APIs, internet access, or dedicated GPU hardware. This repository currently contains the production-grade project structure, documentation skeleton, and development tooling needed to grow the system safely through the competition lifecycle.

> Status: repository scaffold only. The AI assistant, RAG pipeline, model inference, and application features are intentionally not implemented yet.

## Project Overview

PoultryGuard AI will support poultry farmers, extension officers, students, and farm managers with local-first guidance across:

- Poultry disease awareness and early symptom triage
- Vaccination schedule assistance
- Farm climate and housing recommendations
- Biosecurity checklists
- Feeding and flock management guidance
- Market and operational record support

The system is planned around a small local instruction model, a curated Markdown knowledge base, and retrieval-augmented generation that can operate offline on modest laptop hardware.

## Features

Planned capabilities include:

- Offline Streamlit MVP for farmer-facing workflows
- Local llama.cpp inference using Qwen2.5-1.5B-Instruct in GGUF format
- Retrieval-Augmented Generation over a Markdown knowledge base
- FAISS-backed local vector search
- Poultry health, vaccination, climate, biosecurity, feeding, and management modules
- Benchmarking for CPU latency, RAM usage, startup time, and answer quality
- Reproducible developer tooling with tests, linting, formatting, and CI
- Documentation suitable for open-source collaboration and ADTC submission review

## Architecture Overview

The intended architecture follows clean architecture principles:

```text
User Interface
  -> Application Services
  -> Domain/Workflow Logic
  -> RAG Retrieval Layer
  -> Local Knowledge Base + Vector Store
  -> Local LLM Inference Runtime
```

Key boundaries:

- `app/frontend`: Streamlit UI and presentation-layer components.
- `app/backend`: request orchestration and application entry points.
- `app/services`: use-case services that coordinate business workflows.
- `rag`: indexing, embedding, retrieval, and prompt assembly.
- `models`: local model configuration and llama.cpp integration boundaries.
- `knowledge_base`: versioned Markdown source material for offline retrieval.
- `evaluation`, `benchmarks`, and `profiler`: quality, performance, and hardware compatibility checks.

## Technology Stack

- Language: Python 3.11
- Local inference: llama.cpp via `llama-cpp-python` planned
- Model target: Qwen2.5-1.5B-Instruct GGUF
- Retrieval: FAISS planned
- Knowledge base: Markdown files
- MVP UI: Streamlit
- Testing: pytest
- Linting and formatting: Ruff and Black
- CI: GitHub Actions
- Deployment: local Ubuntu 22.04 LTS, optional Docker Compose

## Installation

Installation commands are placeholders until the MVP is implemented.

```bash
git clone https://github.com/your-org/poultryguard-ai.git
cd poultryguard-ai
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make test
```

Model files are intentionally excluded from Git. Future setup documentation will explain how to place GGUF files under `models/gguf/` for offline use.

## Repository Structure

```text
poultryguard-ai/
├── app/                 # Application UI, backend orchestration, services, utilities, and config
├── knowledge_base/      # Curated offline Markdown knowledge base
├── rag/                 # Embeddings, retrieval, indexing, and prompt assets
├── models/              # Local model configs, GGUF storage path, and inference boundaries
├── vector_store/        # Generated FAISS/vector indexes excluded from Git
├── datasets/            # Raw, processed, and synthetic datasets
├── benchmarks/          # Benchmark scripts and results documentation
├── evaluation/          # Answer quality and safety evaluation assets
├── profiler/            # Runtime profiling helpers
├── scripts/             # Developer and maintenance scripts
├── notebooks/           # Research notebooks and experiments
├── tests/               # Unit and structure tests
├── docs/                # Architecture, API, design, deployment, and benchmark documentation
├── report/              # ADTC reports, writeups, and final submission material
├── demo/                # Demo scripts, walkthroughs, and presentation assets
└── assets/              # Branding, images, icons, and static assets
```

## Roadmap

The project roadmap is tracked in [ROADMAP.md](ROADMAP.md).

High-level phases:

1. Repository setup
2. Knowledge base curation
3. Local LLM integration
4. RAG pipeline
5. Desktop UI
6. Optimization
7. ADTC benchmarking
8. Final submission

## ADTC Compatibility

PoultryGuard AI is designed for the ADTC Standard Laptop target:

- Intel Core i5 10th-12th Gen or AMD Ryzen 5
- 8 GB RAM
- Integrated graphics only
- Ubuntu 22.04 LTS
- Fully offline operation
- No cloud APIs
- No internet dependency at runtime

All future implementation decisions should preserve this compatibility target.

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.

