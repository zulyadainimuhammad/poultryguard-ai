# Developer commands for the current PoultryGuard prototype.

.PHONY: help install install-dev lint format format-check test check run index clean

help:
	@echo "Available targets:"
	@echo "  install       Install runtime dependencies"
	@echo "  install-dev   Install runtime and development dependencies"
	@echo "  lint          Run Ruff lint checks"
	@echo "  format        Format Python files with Ruff"
	@echo "  format-check  Verify formatting without modifying files"
	@echo "  test          Run pytest"
	@echo "  check         Run lint, format-check, and tests"
	@echo "  run           Start the current Streamlit knowledge assistant"
	@echo "  index         Build the local FAISS knowledge index"
	@echo "  clean         Display safe cleanup guidance"

install:
	python -m pip install -r requirements.txt

install-dev:
	python -m pip install -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

test:
	python -m pytest

check: lint format-check test

run:
	streamlit run app/frontend/main.py

index:
	python scripts/build_index.py

clean:
	@echo "Remove generated caches and local artefacts only when you understand their contents."
	@echo "Do not delete data/poultryguard.db unless you intend to discard local farm records."
