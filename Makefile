# Common developer commands for PoultryGuard AI.
# These targets are intentionally lightweight while the repository is in scaffold mode.

.PHONY: help install install-dev lint format format-check test check run clean benchmark profile

help:
	@echo "Available targets:"
	@echo "  install       Install runtime dependencies"
	@echo "  install-dev   Install development dependencies"
	@echo "  lint          Run Ruff lint checks"
	@echo "  format        Format Python files with Black and Ruff"
	@echo "  format-check  Verify formatting without modifying files"
	@echo "  test          Run unit tests"
	@echo "  check         Run lint, format-check, and tests"
	@echo "  run           Placeholder for future Streamlit app"
	@echo "  benchmark     Placeholder for future benchmark suite"
	@echo "  profile       Placeholder for future profiler suite"

install:
	python -m pip install -r requirements.txt

install-dev:
	python -m pip install -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff check . --fix
	black .

format-check:
	black --check .

test:
	pytest

check: lint format-check test

run:
	@echo "Streamlit app is not implemented yet."

benchmark:
	python benchmarks/benchmark_placeholder.py

profile:
	python profiler/profile_placeholder.py

clean:
	@echo "Remove generated caches, benchmark outputs, and vector indexes manually with care."

