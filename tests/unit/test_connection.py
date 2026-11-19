"""Tests for SQLite connection lifecycle and per-connection settings."""

import sqlite3

import app.database.connection as database_connection
import pytest


def _use_temporary_database(tmp_path, monkeypatch):
    database_path = tmp_path / "poultryguard-test.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    return database_path


def test_get_connection_enables_foreign_keys_and_closes(tmp_path, monkeypatch):
    database_path = _use_temporary_database(tmp_path, monkeypatch)

    connection = database_connection.get_connection()

    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with connection as active_connection:
        active_connection.execute(
            """
            CREATE TABLE connection_test (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        active_connection.execute(
            "INSERT INTO connection_test (value) VALUES (?)",
            ("committed",),
        )

    with sqlite3.connect(database_path) as verification:
        row = verification.execute(
            "SELECT value FROM connection_test WHERE id = 1"
        ).fetchone()

    assert row == ("committed",)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_connection_rolls_back_and_closes_when_context_raises(tmp_path, monkeypatch):
    database_path = _use_temporary_database(tmp_path, monkeypatch)

    with sqlite3.connect(database_path) as setup_connection:
        setup_connection.execute(
            """
            CREATE TABLE connection_test (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

    connection = database_connection.get_connection()

    with pytest.raises(RuntimeError, match="force rollback"):
        with connection as active_connection:
            active_connection.execute(
                "INSERT INTO connection_test (value) VALUES (?)",
                ("must roll back",),
            )
            raise RuntimeError("force rollback")

    with sqlite3.connect(database_path) as verification:
        count = verification.execute("SELECT COUNT(*) FROM connection_test").fetchone()[
            0
        ]

    assert count == 0
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")



def test_foreign_key_constraint_rejects_invalid_reference(tmp_path, monkeypatch):
    _use_temporary_database(tmp_path, monkeypatch)

    with database_connection.get_connection() as connection:
        connection.execute(
            "CREATE TABLE parent_record (id INTEGER PRIMARY KEY)"
        )
        connection.execute(
            """
            CREATE TABLE child_record (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES parent_record(id)
            )
            """
        )

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                "INSERT INTO child_record (parent_id) VALUES (?)",
                (99999,),
            )
