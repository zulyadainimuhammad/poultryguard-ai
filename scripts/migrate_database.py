"""Explicit, backup-protected CLI for applying SQLite schema migrations."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from app.database.migrations import runner

BASELINE_TABLES = ("farms", "flocks", "daily_records")


def _open_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in BASELINE_TABLES
    }


def _create_verified_backup(database_path: Path, backup_path: Path) -> None:
    """Create a SQLite online backup and verify integrity and baseline row counts."""
    if database_path.resolve() == backup_path.resolve():
        raise ValueError("Backup path must be different from the database path.")
    if backup_path.exists():
        raise FileExistsError(
            f"Backup destination already exists; refusing to overwrite: {backup_path}"
        )
    if not backup_path.parent.is_dir():
        raise FileNotFoundError(
            f"Backup destination directory does not exist: {backup_path.parent}"
        )

    source = _open_database(database_path)
    destination = sqlite3.connect(backup_path)
    try:
        expected_counts = _row_counts(source)
        source.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite backup integrity check failed: {integrity}")
        backup_counts = _row_counts(destination)
        if backup_counts != expected_counts:
            raise RuntimeError(
                "SQLite backup row-count verification failed: "
                f"source={expected_counts}, backup={backup_counts}."
            )
    except Exception:
        destination.close()
        source.close()
        if backup_path.exists():
            backup_path.unlink()
        raise
    else:
        destination.close()
        source.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect or apply PoultryGuard SQLite schema migrations. "
            "This command never initialises an empty database automatically."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Explicit path to an already-initialised PoultryGuard SQLite database.",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--status",
        action="store_true",
        help="Read and display the baseline and migration status without writes.",
    )
    action.add_argument(
        "--apply",
        action="store_true",
        help="Create a verified backup, then apply pending migrations.",
    )
    parser.add_argument(
        "--backup-to",
        type=Path,
        help="New backup file path; required with --apply and must not already exist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    database_path = args.database.expanduser()

    if not database_path.is_file():
        parser.error(
            f"Database file does not exist: {database_path}. "
            "Initialise a test/new database separately; migrations never bootstrap it."
        )

    if args.status and args.backup_to is not None:
        parser.error("--backup-to can only be used with --apply.")

    if args.apply and args.backup_to is None:
        parser.error("--apply requires --backup-to with a new backup file path.")

    connection = _open_database(database_path)
    try:
        status = runner.migration_status(connection)
    except Exception as exc:
        print(f"Migration status failed: {exc}", file=sys.stderr)
        connection.close()
        return 2

    if args.status:
        print(f"Database: {database_path}")
        print(f"Baseline adoption required: {status['baseline_adoption_required']}")
        print(f"Applied versions: {status['applied_versions']}")
        print(f"Pending versions: {status['pending_versions']}")
        connection.close()
        return 0

    backup_path = args.backup_to.expanduser()
    backup_created = False
    try:
        if status["pending_versions"] or status["baseline_adoption_required"]:
            _create_verified_backup(database_path, backup_path)
            backup_created = True
            print(f"Verified SQLite backup created: {backup_path}")

        applied = runner.migrate(connection)
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        if backup_created:
            print(f"Preserve the verified backup for recovery: {backup_path}")
        connection.close()
        return 1
    else:
        connection.close()
        print(f"Applied migration versions: {applied}")
        print("Migration runner completed successfully.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
