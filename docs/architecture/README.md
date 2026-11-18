# Architecture Documentation

This directory documents both the **currently implemented local MVP** and the **target architecture** for PoultryGuard AI. These are deliberately kept distinct so planned infrastructure and product capabilities are not mistaken for deployed functionality.

## Current system documents

| Document | Description |
|---|---|
| [system_overview.md](system_overview.md) | Current product, implemented components, data model and system boundaries |
| [software_architecture.md](software_architecture.md) | Implemented module map, dependency direction, service boundaries and future production boundary |
| [data_flow.md](data_flow.md) | Current knowledge indexing, question-answering and farm-record/analytics flows |
| [rag_design.md](rag_design.md) | Markdown chunking, embeddings, FAISS indexing and retrieval |
| [model_selection.md](model_selection.md) | Current local embedding model and remote answer-generation provider |
| [deployment.md](deployment.md) | Supported local developer setup and production-readiness gaps |

## Target and historical documents

| Document | Description |
|---|---|
| [target_architecture.md](target_architecture.md) | Long-term product architecture: Knowledge Assistant, Farm & Flock Records, Monitoring, Environmental Data, AI Farm Intelligence, Insights, Alerts, Expert Support and cross-cutting Cloud Engineering |
| [adtc_alignment.md](adtc_alignment.md) | Historical ADTC 2026 design/compliance material; not a statement of current runtime behaviour |

## Recommended reading order

1. [System overview](system_overview.md) — understand what is implemented now.
2. [Target architecture](target_architecture.md) — understand the full product vision and Cloud Engineering foundation.
3. [Software architecture](software_architecture.md) — understand code and dependency boundaries.
4. [Data flow](data_flow.md) — understand current data movement and planned flows.
5. [RAG design](rag_design.md) — understand knowledge indexing and retrieval.
6. [Model and provider selection](model_selection.md) — understand the active AI providers.
7. [Development and deployment](deployment.md) — run the local MVP and understand production gaps.

## Architecture principles

- Describe active code accurately; mark planned features as planned.
- Keep Streamlit presentation separate from application services and repositories.
- Keep SQL in repositories and preserve parameterised queries.
- Keep the RAG pipeline independent of Streamlit.
- Keep secrets and generated local data out of source control.
- Add versioned migrations before evolving the farm database schema.
- Preserve provenance, units, timestamps and missing-data semantics.
- Use least-privilege access and farm-level data isolation before multi-user operation.
- Treat AI as decision support, not veterinary diagnosis or prescription.
- Treat Cloud Engineering as a cross-cutting foundation, not an assumed provider choice.
- Add cloud services when validated product, security and operational requirements justify them.
