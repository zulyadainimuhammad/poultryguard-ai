"""Tests for the explicit, backup-protected migration CLI."""

from __future__ import annotations

import sqlite3

from app.database.migrations import runner
from scripts import migrate_database

from tests.unit.test_migrations import _initialised_database, _seed_legacy_rows


def test_status_command_is_read_only(tmp_path, monkeypatch, capsys):
    database_path = _initialised_database(tmp_path, monkeypatch)

    result = migrate_database.main(["--database", str(database_path), "--status"])

    output = capsys.readouterr().out
    assert result == 0
    assert "Baseline adoption required: True" in output
    with sqlite3.connect(database_path) as connection:
        assert not runner._table_exists(connection, runner.LEDGER_TABLE)


def test_apply_command_requires_and_creates_verified_backup(
    tmp_path, monkeypatch, capsys
):
    database_path = _initialised_database(tmp_path, monkeypatch)
    _seed_legacy_rows()
    backup_path = tmp_path / "poultryguard-before-migration.db"

    result = migrate_database.main(
        [
            "--database",
            str(database_path),
            "--apply",
            "--backup-to",
            str(backup_path),
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert backup_path.is_file()
    assert "Verified SQLite backup created" in output
    assert "Migration runner completed successfully" in output

    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute("SELECT COUNT(*) FROM daily_records").fetchone()[0] == 1
        assert not runner._table_exists(backup, "measurement_observations")

    with sqlite3.connect(database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM daily_records").fetchone()[0] == 1
        assert runner._table_exists(database, "measurement_observations")


def test_apply_does_not_overwrite_existing_backup_or_migrate(
    tmp_path, monkeypatch, capsys
):
    database_path = _initialised_database(tmp_path, monkeypatch)
    backup_path = tmp_path / "existing-backup.db"
    backup_path.write_bytes(b"do not overwrite")

    result = migrate_database.main(
        [
            "--database",
            str(database_path),
            "--apply",
            "--backup-to",
            str(backup_path),
        ]
    )

    output = capsys.readouterr().err
    assert result == 1
    assert "already exists" in output
    assert backup_path.read_bytes() == b"do not overwrite"

    with sqlite3.connect(database_path) as connection:
        assert not runner._table_exists(connection, runner.LEDGER_TABLE)
        assert not runner._table_exists(connection, "measurement_observations")


def test_status_command_does_not_initialise_a_blank_database(
    tmp_path, capsys
):
    database_path = tmp_path / "blank.db"
    with sqlite3.connect(database_path):
        pass

    result = migrate_database.main(["--database", str(database_path), "--status"])

    assert result == 2
    assert not runner._table_exists(sqlite3.connect(database_path), runner.LEDGER_TABLE)
