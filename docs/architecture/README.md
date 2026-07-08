# Architecture Documentation

This directory contains the complete software architecture documentation for PoultryGuard AI.

## Documents

| Document | Description |
|---|---|
| [system_overview.md](system_overview.md) | High-level system description, component map, and key constraints |
| [software_architecture.md](software_architecture.md) | Layered architecture, module map, interaction diagrams, and testing strategy |
| [data_flow.md](data_flow.md) | Indexing pipeline, query pipeline, prompt structure, and data at rest |
| [model_selection.md](model_selection.md) | LLM and embedding model selection rationale and configuration |
| [rag_design.md](rag_design.md) | Complete RAG pipeline design including chunking, retrieval, and prompt construction |
| [deployment.md](deployment.md) | Local setup, Docker, ADTC competition deployment, and offline distribution |
| [adtc_alignment.md](adtc_alignment.md) | ADTC 2026 compliance mapping, performance targets, and risk register |

## Reading Order

For a new contributor, read in this order:

1. `system_overview.md` — understand what the system is and why
2. `software_architecture.md` — understand how the code is structured
3. `data_flow.md` — understand how data moves through the system
4. `rag_design.md` — understand the retrieval pipeline in detail
5. `model_selection.md` — understand the model choices
6. `deployment.md` — understand how to run the system
7. `adtc_alignment.md` — understand competition compliance

## Architecture Principles

- Offline-first: zero network calls at runtime
- CPU-only: no GPU dependency
- Layered: outer layers depend on inner layers only
- Modular: each component has a single responsibility
- Testable: all components are injectable and mockable
- Documented: every module has purpose, inputs, outputs, and dependencies
