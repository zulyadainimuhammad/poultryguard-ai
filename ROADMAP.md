# Roadmap

This roadmap tracks the planned development lifecycle for PoultryGuard AI through the Africa Deep Tech Challenge 2026.

## Phase 1 Repository Setup

- Create scalable repository structure.
- Add open-source governance files.
- Configure Python 3.11 project metadata.
- Add CI placeholders for linting, formatting, and unit tests.
- Establish documentation folders.

## Phase 2 Knowledge Base

- Define Markdown schema for knowledge entries.
- Curate poultry disease, vaccination, climate, biosecurity, feeding, management, and market content.
- Add source attribution and review metadata.
- Establish knowledge-base quality checks.

## Phase 3 Local LLM

- Select and document GGUF model variant.
- Add llama.cpp integration boundary.
- Define inference configuration profiles for 8 GB RAM.
- Validate offline CPU-only inference.

## Phase 4 RAG

- Implement document chunking and indexing.
- Add local embeddings pipeline.
- Build FAISS retrieval layer.
- Add prompt templates grounded in retrieved context.
- Add tests for retrieval correctness.

## Phase 5 Desktop UI

- Build Streamlit MVP.
- Add workflows for symptoms, vaccination, climate, and farm records.
- Add accessible offline user experience.
- Add screenshots and demo documentation.

## Phase 6 Optimization

- Profile startup time, latency, memory, and retrieval performance.
- Optimize model settings for integrated graphics and CPU-only operation.
- Reduce memory pressure on 8 GB RAM devices.
- Add reproducible benchmark reports.

## Phase 7 ADTC Benchmarking

- Validate on Ubuntu 22.04 LTS.
- Run offline compatibility tests.
- Record latency, RAM usage, and answer-quality benchmarks.
- Prepare competition evidence and review material.

## Phase 8 Final Submission

- Finalize report, demo, screenshots, and documentation.
- Freeze model and knowledge-base versions.
- Tag release candidate.
- Package local deployment instructions.

