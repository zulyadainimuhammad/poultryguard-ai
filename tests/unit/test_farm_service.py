"""Tests for FarmService — uses isolated in-memory databases."""

from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import patch

import pytest
from app.database import (
    DailyRecordRepository,
    FarmRepository,
    FlockRepository,
)
from app.services.farm_service import DuplicateRecordError, FarmService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE farms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_name TEXT NOT NULL,
            farmer_name TEXT NOT NULL,
            location TEXT,
            phone TEXT,
            email TEXT,
            production_type TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE flocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_id INTEGER NOT NULL,
            flock_name TEXT NOT NULL,
            species TEXT NOT NULL,
            production_type TEXT,
            breed TEXT,
            initial_count INTEGER NOT NULL CHECK (initial_count > 0),
            stocking_date TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
        );
        CREATE TABLE daily_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flock_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            feed_kg REAL,
            water_litres REAL,
            mortality INTEGER NOT NULL DEFAULT 0,
            average_weight_kg REAL,
            temperature_c REAL,
            humidity_percent REAL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (flock_id) REFERENCES flocks(id) ON DELETE CASCADE,
            CHECK (mortality >= 0),
            CHECK (
                humidity_percent IS NULL
                OR (humidity_percent >= 0 AND humidity_percent <= 100)
            )
        );
        """
    )
    yield conn
    conn.close()


@pytest.fixture()
def service(db_conn):
    farm_repo = FarmRepository()
    flock_repo = FlockRepository()
    record_repo = DailyRecordRepository()

    patcher = patch(
        "app.database.repositories.get_connection", side_effect=lambda: db_conn
    )
    uow_patcher = patch(
        "app.database.unit_of_work.get_connection", side_effect=lambda: db_conn
    )
    patcher.start()
    uow_patcher.start()
    svc = FarmService(
        farm_repository=farm_repo,
        flock_repository=flock_repo,
        daily_record_repository=record_repo,
    )
    yield svc
    uow_patcher.stop()
    patcher.stop()


@pytest.fixture()
def farm_id(service):
    return service.create_farm(
        farm_name="Kano Broiler Farm",
        farmer_name="Aminu Musa",
        location="Kano, Nigeria",
        production_type="Broiler",
    )


@pytest.fixture()
def flock_id(service, farm_id):
    return service.create_flock(
        farm_id=farm_id,
        flock_name="Batch 1",
        species="Chicken",
        production_type="Broiler",
        breed="Cobb 500",
        initial_count=500,
        stocking_date=date(2026, 11, 1),
    )


# ---------------------------------------------------------------------------
# Farm creation
# ---------------------------------------------------------------------------


def test_create_farm_returns_id(service):
    farm_id = service.create_farm(
        farm_name="Test Farm",
        farmer_name="Test Farmer",
        location="Kano",
        production_type="Broiler",
    )
    assert isinstance(farm_id, int)
    assert farm_id > 0


def test_create_farm_persists(service):
    farm_id = service.create_farm(
        farm_name="Persist Farm",
        farmer_name="Farmer A",
        location="Kaduna",
        production_type="Layer",
        phone="08012345678",
        email="farmer@example.com",
    )
    farm = service.get_farm(farm_id)
    assert farm is not None
    assert farm["farm_name"] == "Persist Farm"
    assert farm["farmer_name"] == "Farmer A"
    assert farm["location"] == "Kaduna"
    assert farm["phone"] == "08012345678"
    assert farm["email"] == "farmer@example.com"


def test_create_farm_missing_name_raises(service):
    with pytest.raises(ValueError, match="Farm name is required"):
        service.create_farm(
            farm_name="  ",
            farmer_name="Farmer",
            location="Kano",
            production_type="Broiler",
        )


def test_create_farm_missing_farmer_name_raises(service):
    with pytest.raises(ValueError, match="Farmer name is required"):
        service.create_farm(
            farm_name="Farm",
            farmer_name="",
            location="Kano",
            production_type="Broiler",
        )


def test_create_farm_missing_location_raises(service):
    with pytest.raises(ValueError, match="Location is required"):
        service.create_farm(
            farm_name="Farm",
            farmer_name="Farmer",
            location="",
            production_type="Broiler",
        )


def test_create_farm_invalid_email_raises(service):
    with pytest.raises(ValueError, match="Email address is not valid"):
        service.create_farm(
            farm_name="Farm",
            farmer_name="Farmer",
            location="Kano",
            production_type="Broiler",
            email="not-an-email",
        )


def test_list_farms_returns_all(service):
    service.create_farm("Farm A", "Farmer A", "Kano", "Broiler")
    service.create_farm("Farm B", "Farmer B", "Kaduna", "Layer")
    farms = service.list_farms()
    assert len(farms) == 2


# ---------------------------------------------------------------------------
# Flock creation
# ---------------------------------------------------------------------------


def test_create_flock_returns_id(service, farm_id):
    flock_id = service.create_flock(
        farm_id=farm_id,
        flock_name="Batch 1",
        species="Chicken",
        production_type="Broiler",
        breed=None,
        initial_count=100,
        stocking_date=date(2026, 11, 1),
    )
    assert isinstance(flock_id, int)
    assert flock_id > 0


def test_create_flock_persists(service, farm_id):
    flock_id = service.create_flock(
        farm_id=farm_id,
        flock_name="Batch 2",
        species="Chicken",
        production_type="Layer",
        breed="ISA Brown",
        initial_count=300,
        stocking_date=date(2026, 10, 1),
    )
    flock = service.get_flock(flock_id)
    assert flock is not None
    assert flock["flock_name"] == "Batch 2"
    assert flock["initial_count"] == 300
    assert flock["breed"] == "ISA Brown"


def test_create_flock_invalid_species_raises(service, farm_id):
    with pytest.raises(ValueError, match="Species must be one of"):
        service.create_flock(
            farm_id=farm_id,
            flock_name="Batch",
            species="Elephant",
            production_type="Broiler",
            breed=None,
            initial_count=100,
            stocking_date=date(2026, 11, 1),
        )


def test_create_flock_zero_count_raises(service, farm_id):
    with pytest.raises(ValueError, match="positive integer"):
        service.create_flock(
            farm_id=farm_id,
            flock_name="Batch",
            species="Chicken",
            production_type="Broiler",
            breed=None,
            initial_count=0,
            stocking_date=date(2026, 11, 1),
        )


def test_create_flock_nonexistent_farm_raises(service):
    with pytest.raises(ValueError, match="does not exist"):
        service.create_flock(
            farm_id=99999,
            flock_name="Batch",
            species="Chicken",
            production_type="Broiler",
            breed=None,
            initial_count=100,
            stocking_date=date(2026, 11, 1),
        )


def test_create_flock_missing_name_raises(service, farm_id):
    with pytest.raises(ValueError, match="Flock name is required"):
        service.create_flock(
            farm_id=farm_id,
            flock_name="  ",
            species="Chicken",
            production_type="Broiler",
            breed=None,
            initial_count=100,
            stocking_date=date(2026, 11, 1),
        )


def test_list_flocks_for_farm(service, farm_id):
    service.create_flock(farm_id, "A", "Chicken", "Broiler", None, 100, date.today())
    service.create_flock(farm_id, "B", "Turkey", "Other", None, 50, date.today())
    flocks = service.list_flocks(farm_id)
    assert len(flocks) == 2


# ---------------------------------------------------------------------------
# Daily record creation
# ---------------------------------------------------------------------------


def test_create_daily_record_returns_id(service, flock_id):
    record_id = service.create_daily_record(
        flock_id=flock_id,
        record_date=date(2026, 11, 1),
        mortality=2,
        feed_kg=30.0,
        water_litres=60.0,
    )
    assert isinstance(record_id, int)
    assert record_id > 0


def test_create_daily_record_persists(service, flock_id):
    service.create_daily_record(
        flock_id=flock_id,
        record_date=date(2026, 11, 1),
        mortality=2,
        feed_kg=30.0,
        water_litres=60.0,
        temperature_c=28.0,
        humidity_percent=65.0,
        notes="Test note",
    )
    records = service.get_daily_records(flock_id)
    assert len(records) == 1
    assert records[0]["mortality"] == 2
    assert records[0]["feed_kg"] == 30.0
    assert records[0]["notes"] == "Test note"


def test_duplicate_record_raises_by_default(service, flock_id):
    service.create_daily_record(
        flock_id=flock_id, record_date=date(2026, 11, 1), mortality=0
    )
    with pytest.raises(DuplicateRecordError):
        service.create_daily_record(
            flock_id=flock_id, record_date=date(2026, 11, 1), mortality=0
        )


def test_duplicate_record_allowed_with_flag(service, flock_id):
    service.create_daily_record(
        flock_id=flock_id, record_date=date(2026, 11, 1), mortality=0
    )
    record_id = service.create_daily_record(
        flock_id=flock_id,
        record_date=date(2026, 11, 1),
        mortality=0,
        allow_duplicate=True,
    )
    assert record_id > 0


def test_mortality_exceeding_population_raises(service, flock_id):
    # flock has 500 birds; try to record 501 deaths
    with pytest.raises(ValueError, match="exceeds the remaining flock population"):
        service.create_daily_record(
            flock_id=flock_id, record_date=date(2026, 11, 1), mortality=501
        )


def test_mortality_accumulates_correctly(service, flock_id):
    service.create_daily_record(
        flock_id=flock_id, record_date=date(2026, 11, 1), mortality=300
    )
    # 200 birds remain; 201 should fail
    with pytest.raises(ValueError, match="exceeds the remaining flock population"):
        service.create_daily_record(
            flock_id=flock_id, record_date=date(2026, 11, 2), mortality=201
        )


def test_negative_mortality_raises(service, flock_id):
    with pytest.raises(ValueError, match="cannot be negative"):
        service.create_daily_record(
            flock_id=flock_id, record_date=date(2026, 11, 1), mortality=-1
        )


def test_negative_feed_raises(service, flock_id):
    with pytest.raises(ValueError, match="Feed consumed cannot be negative"):
        service.create_daily_record(
            flock_id=flock_id,
            record_date=date(2026, 11, 1),
            mortality=0,
            feed_kg=-5.0,
        )


def test_negative_water_raises(service, flock_id):
    with pytest.raises(ValueError, match="Water consumed cannot be negative"):
        service.create_daily_record(
            flock_id=flock_id,
            record_date=date(2026, 11, 1),
            mortality=0,
            water_litres=-1.0,
        )


def test_invalid_weight_raises(service, flock_id):
    with pytest.raises(ValueError, match="Average weight must be greater than zero"):
        service.create_daily_record(
            flock_id=flock_id,
            record_date=date(2026, 11, 1),
            mortality=0,
            average_weight_kg=0.0,
        )


def test_humidity_out_of_range_raises(service, flock_id):
    with pytest.raises(ValueError, match="Humidity must be between"):
        service.create_daily_record(
            flock_id=flock_id,
            record_date=date(2026, 11, 1),
            mortality=0,
            humidity_percent=101.0,
        )


def test_nonexistent_flock_raises(service):
    with pytest.raises(ValueError, match="does not exist"):
        service.create_daily_record(
            flock_id=99999, record_date=date(2026, 11, 1), mortality=0
        )


def test_records_returned_in_chronological_order(service, flock_id):
    """Daily records must be returned oldest-first for correct analytics."""
    service.create_daily_record(
        flock_id=flock_id, record_date=date(2026, 11, 3), mortality=3
    )
    service.create_daily_record(
        flock_id=flock_id, record_date=date(2026, 11, 1), mortality=1
    )
    service.create_daily_record(
        flock_id=flock_id, record_date=date(2026, 11, 2), mortality=2
    )
    records = service.get_daily_records(flock_id)
    dates = [r["record_date"] for r in records]
    assert dates == ["2026-11-01", "2026-11-02", "2026-11-03"]


def test_genuine_zero_feed_water_distinguished_from_none(service, flock_id):
    """A recorded 0.0 feed/water must be stored as 0.0, not None.

    A separate record with no feed/water must be stored as None.
    The two must be distinguishable when retrieved.
    """
    service.create_daily_record(
        flock_id=flock_id,
        record_date=date(2026, 11, 1),
        mortality=0,
        feed_kg=0.0,
        water_litres=0.0,
    )
    service.create_daily_record(
        flock_id=flock_id,
        record_date=date(2026, 11, 2),
        mortality=0,
        feed_kg=None,
        water_litres=None,
    )
    records = service.get_daily_records(flock_id)
    assert len(records) == 2

    zero_record = records[0]  # 2026-11-01, chronological order
    none_record = records[1]  # 2026-11-02

    assert zero_record["feed_kg"] == 0.0
    assert zero_record["water_litres"] == 0.0
    assert none_record["feed_kg"] is None
    assert none_record["water_litres"] is None
