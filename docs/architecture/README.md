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
| [sqlite_migrations.md](sqlite_migrations.md) | Explicit SQLite migration runner, baseline adoption, backup-protected CLI and schema migration operations |
| [sqlite_unit_of_work.md](sqlite_unit_of_work.md) | Shared SQLite connection/transaction lifecycle and current daily-record integration |
| [measurement_observation_schema_migration_design.md](measurement_observation_schema_migration_design.md) | Proposed additive observation table, constraints, correction-chain safeguards, migration ledger and backfill rehearsal design (not approved for implementation) |
| [measurement_provenance.md](measurement_provenance.md) | Measurement dictionary, provenance model, observation-time semantics, missing-value rules, correction and audit model, proposed data contract and future architecture (Stage 3.2.2 design specification) |
| [measurement_provenance_implementation_plan.md](measurement_provenance_implementation_plan.md) | Proposed Stage 3.2.3 implementation sequence, migration safeguards, repository/service boundaries, testing and release gates |
| [adr_v2_2_correction_report.md](adr_v2_2_correction_report.md) | Source correction report for five architecture issues; legacy ADR numbering remains subject to reconciliation |
| [architecture_decision_register_v2_2_draft.md](architecture_decision_register_v2_2_draft.md) | Consolidated architecture register draft; not approved for implementation |
| [repository_assessment_2026-11-19.md](repository_assessment_2026-11-19.md) | Read-only inspection of the current committed repository baseline |
| [source_document_reconciliation_review_2026-11-19.md](source_document_reconciliation_review_2026-11-19.md) | Cross-document reconciliation, current-code facts, unresolved design issues and safe next steps |

## Product requirements

| Document | Description |
|---|---|
| [product_requirements_ui_ux.md](../product/product_requirements_ui_ux.md) | Product vision, users, account and farm membership requirements, roles, UI/UX, security, localisation and release acceptance criteria |

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
5. [Measurement provenance](measurement_provenance.md) — understand measurement definitions, provenance, timestamps and the proposed data contract.
6. [RAG design](rag_design.md) — understand knowledge indexing and retrieval.
7. [Model and provider selection](model_selection.md) — understand the active AI providers.
8. [Development and deployment](deployment.md) — run the local MVP and understand production gaps.

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
