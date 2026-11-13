# Contributing to PoultryGuard AI

Thank you for your interest in contributing. PoultryGuard AI is currently maintained by its repository owner and is being developed as a poultry farm intelligence prototype.

## Project principles

- Match documentation to implemented behaviour; label future capabilities as planned.
- Keep Streamlit presentation code separate from services, repositories and persistence.
- Preserve traceability for poultry knowledge and cite credible sources.
- Treat AI as decision support, not veterinary diagnosis or prescription.
- Validate data carefully and document assumptions.
- Keep API credentials, personal data, local databases, model files and generated indexes out of Git.
- Introduce cloud infrastructure only when validated product requirements justify it.

## Development setup

Use Python 3.11.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

Run checks:

```powershell
python -m pytest -v
ruff check .
ruff format --check .
python scripts/validate_knowledge_base.py
python scripts/validate_metadata.py
python scripts/validate_references.py
python scripts/validate_links.py
```

## Branching and commits

- Use focused branches such as `feat/farm-dashboard`, `feat/vaccination-records` or `docs/roadmap-refresh`.
- Keep pull requests limited to one coherent change.
- Use descriptive commit messages.
- Do not rewrite shared history or force-push without explicit coordination.
- The repository owner is responsible for merging changes to the default branch.

## Pull request checklist

- [ ] The change solves a stated product or engineering need.
- [ ] Tests cover changed behaviour.
- [ ] Ruff lint and format checks pass.
- [ ] Knowledge-base changes include credible sources and review metadata.
- [ ] Documentation reflects the actual implementation.
- [ ] No secrets, local databases, indexes, model files or private farmer data are committed.
- [ ] User-facing safety limitations are preserved.

## Knowledge-base contributions

Knowledge content must be sourced, dated/reviewed where appropriate, locally relevant and clear about uncertainty. Disease, vaccination and treatment guidance should receive review by qualified poultry professionals before being presented as authoritative advice. Do not invent drug dosages, diagnosis criteria or treatment protocols.

## Attribution

Contributions must accurately identify the people who made substantive contributions. Do not add co-author trailers, contributor entries or endorsements for tools or automated assistants unless required by the actual contribution and authorised by the named party. Do not alter existing commit history solely to change attribution without an agreed, backed-up history-rewrite plan.

## Reporting issues

Include expected behaviour, actual behaviour, reproduction steps, Python version, operating system and relevant non-sensitive logs. Report security concerns using [SECURITY.md](SECURITY.md).
