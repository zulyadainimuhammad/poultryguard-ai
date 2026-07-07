"""Validate that core scaffold directories exist.

This helper is intentionally lightweight and does not validate AI functionality.
"""

from pathlib import Path


REQUIRED_DIRECTORIES = [
    "app",
    "knowledge_base",
    "rag",
    "models",
    "vector_store",
    "datasets",
    "benchmarks",
    "evaluation",
    "profiler",
    "docs",
    "tests",
]


def main() -> None:
    """Raise an error if a required scaffold directory is missing."""
    root = Path(__file__).resolve().parents[1]
    missing = [name for name in REQUIRED_DIRECTORIES if not (root / name).is_dir()]
    if missing:
        raise SystemExit(f"Missing scaffold directories: {', '.join(missing)}")
    print("Repository scaffold looks complete.")


if __name__ == "__main__":
    main()

