# Architecture Documentation

This directory contains the current architecture references for PoultryGuard AI. The active system is a Streamlit prototype with local RAG retrieval, Groq answer generation and a SQLite farm-data/service foundation.

## Current architecture documents

| Document | Description |
|---|---|
| [system_overview.md](system_overview.md) | Current product, components, data model and system boundaries |
| [software_architecture.md](software_architecture.md) | Implemented module map, dependency direction and future production boundary |
| [data_flow.md](data_flow.md) | Current knowledge indexing, question-answering and farm-record flows |
| [rag_design.md](rag_design.md) | Implemented Markdown chunking, embeddings, FAISS indexing and retrieval |
| [model_selection.md](model_selection.md) | Current local embedding model and remote answer-generation provider |
| [deployment.md](deployment.md) | Supported local developer setup and production-readiness gaps |
| [adtc_alignment.md](adtc_alignment.md) | Historical ADTC 2026 design/compliance material; not a statement of current runtime behaviour |

## Recommended reading order

1. [System overview](system_overview.md)
2. [Software architecture](software_architecture.md)
3. [Data flow](data_flow.md)
4. [RAG design](rag_design.md)
5. [Model and provider selection](model_selection.md)
6. [Development and deployment](deployment.md)

## Architecture principles

- Describe the active code accurately; mark planned features as planned.
- Keep Streamlit presentation separate from services and repositories.
- Keep SQL in repositories and preserve parameterised queries.
- Keep the RAG pipeline independent of Streamlit.
- Keep secrets and generated local data out of source control.
- Add migrations before evolving the farm database schema.
- Treat AI as decision support, not veterinary diagnosis or prescription.
- Add cloud services only when validated multi-user or operational requirements justify them.
