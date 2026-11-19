"""Tests for shared SQLite Unit-of-Work transaction behaviour."""

import sqlite3

import pytest

import app.database.connection as database_connection
from app.database import DailyRecord, Farm, Flock, UnitOfWork


def _configure_test_database(tmp_path, monkeypatch):
    database_path = tmp_path / "unit-of-work.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    database_connection.initialise_database()
    return database_path


def test_repositories_share_connection_and_success_commits(tmp_path, monkeypatch):
    database_path = _configure_test_database(tmp_path, monkeypatch)

    with UnitOfWork() as unit_of_work:
        connection = unit_of_work.connection

        assert connection.in_transaction
        assert unit_of_work.farms._connection is connection
        assert unit_of_work.flocks._connection is connection
        assert unit_of_work.daily_records._connection is connection

        farm_id = unit_of_work.farms.create(
            Farm(
                farm_name="Transaction Farm",
                farmer_name="Test Farmer",
                location="Kano",
            )
        )
        flock_id = unit_of_work.flocks.create(
            Flock(
                farm_id=farm_id,
                flock_name="Batch 1",
                species="Chicken",
                initial_count=100,
            )
        )
        unit_of_work.daily_records.create(
            DailyRecord(
                flock_id=flock_id,
                record_date="2026-11-19",
                mortality=1,
            )
        )

    with sqlite3.connect(database_path) as verification:
        counts = (
            verification.execute("SELECT COUNT(*) FROM farms").fetchone()[0],
            verification.execute("SELECT COUNT(*) FROM flocks").fetchone()[0],
            verification.execute("SELECT COUNT(*) FROM daily_records").fetchone()[0],
        )

    assert counts == (1, 1, 1)
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_exception_rolls_back_all_repository_writes(tmp_path, monkeypatch):
    database_path = _configure_test_database(tmp_path, monkeypatch)

    with pytest.raises(RuntimeError, match="force full rollback"):
        with UnitOfWork() as unit_of_work:
            farm_id = unit_of_work.farms.create(
                Farm(
                    farm_name="Should Roll Back",
                    farmer_name="Test Farmer",
                    location="Kano",
                )
            )
            unit_of_work.flocks.create(
                Flock(
                    farm_id=farm_id,
                    flock_name="Should Also Roll Back",
                    species="Chicken",
                    initial_count=50,
                )
            )
            raise RuntimeError("force full rollback")

    with sqlite3.connect(database_path) as verification:
        farm_count = verification.execute("SELECT COUNT(*) FROM farms").fetchone()[0]
        flock_count = verification.execute("SELECT COUNT(*) FROM flocks").fetchone()[0]

    assert farm_count == 0
    assert flock_count == 0


def test_unit_of_work_cannot_be_used_before_entering():
    unit_of_work = UnitOfWork()

    with pytest.raises(RuntimeError, match="must be entered"):
        _ = unit_of_work.connection


def test_unit_of_work_rejects_nested_entry(tmp_path, monkeypatch):
    _configure_test_database(tmp_path, monkeypatch)

    with UnitOfWork() as unit_of_work:
        with pytest.raises(RuntimeError, match="already active"):
            unit_of_work.__enter__()


def test_unit_of_work_closes_factory_connection():
    connection = sqlite3.connect(":memory:")
    unit_of_work = UnitOfWork(connection_factory=lambda: connection)

    with unit_of_work:
        assert unit_of_work.connection is connection
        assert connection.in_transaction

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")
