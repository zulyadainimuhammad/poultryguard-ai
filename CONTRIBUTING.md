# Contributing to PoultryGuard AI

Thank you for helping build PoultryGuard AI. This project aims to be a reliable, offline-first assistant for poultry farming contexts, with a special focus on practical use in African environments.

## Contribution Principles

- Keep the system offline-first and compatible with modest laptop hardware.
- Prefer clear, maintainable Python over clever abstractions.
- Separate UI, orchestration, retrieval, model inference, and knowledge-base concerns.
- Document assumptions, limitations, and data sources.
- Avoid adding cloud services, telemetry, or internet-dependent runtime behavior.

## Development Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make lint
make format-check
make test
```

## Branching

- Use short, descriptive branch names such as `docs/architecture-notes` or `feat/rag-indexer`.
- Keep pull requests focused on one logical change.
- Avoid mixing generated artifacts, model files, indexes, and source code in the same change.

## Pull Request Checklist

- The change is scoped and documented.
- Tests pass locally with `make test`.
- Linting passes with `make lint`.
- Formatting passes with `make format-check`.
- New documentation is added for new user-facing or developer-facing behavior.
- Large files, GGUF models, FAISS indexes, and raw datasets are not committed.

## Knowledge Base Contributions

Knowledge base material must be:

- Written in clear Markdown.
- Attributed to credible sources where applicable.
- Reviewed for local relevance and practical usefulness.
- Marked with uncertainty where evidence is incomplete.
- Free from claims that replace professional veterinary diagnosis.

## Code Style

This repository uses:

- Python 3.11
- Ruff for linting
- Black for formatting
- pytest for tests

Run the standard checks before opening a pull request:

```bash
make check
```

## Reporting Issues

When opening an issue, include:

- Expected behavior
- Actual behavior
- Steps to reproduce
- Operating system and Python version
- Any relevant logs or screenshots

Security issues should be reported using the process in [SECURITY.md](SECURITY.md).

