"""Repository scaffold tests.

These tests protect the initial project structure while implementation modules
are still being designed.
"""

from pathlib import Path


def test_core_directories_exist() -> None:
    """Ensure the main repository folders remain present."""
    root = Path(__file__).resolve().parents[1]
    expected = [
        "app",
        "knowledge_base",
        "rag",
        "models",
        "vector_store",
        "datasets",
        "benchmarks",
        "evaluation",
        "profiler",
        "scripts",
        "notebooks",
        "tests",
        "docs",
        "report",
        "demo",
        "assets",
    ]

    missing = [folder for folder in expected if not (root / folder).is_dir()]

    assert not missing, f"Missing scaffold directories: {missing}"


def test_runtime_entry_point_is_placeholder(capsys) -> None:
    """Confirm the current backend entry point does not start real AI behavior."""
    from app.backend.main import main

    main()

    captured = capsys.readouterr()
    assert "not implemented yet" in captured.out

