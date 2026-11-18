"""Tests for AnalyticsService — uses isolated in-memory databases."""

from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import patch

import pytest
from app.database import (
    DailyRecord,
    DailyRecordRepository,
    Farm,
    FarmRepository,
    Flock,
    FlockRepository,
)
from app.services.analytics_service import AnalyticsService

# ---------------------------------------------------------------------------
# Fixtures: isolated in-memory database per test
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn():
    """Provide an isolated in-memory SQLite connection for each test."""
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


def _make_repos(conn):
    """Return repository instances patched to use the given connection."""
    farm_repo = FarmRepository()
    flock_repo = FlockRepository()
    record_repo = DailyRecordRepository()

    def _get_conn():
        return conn

    patcher = patch("app.database.repositories.get_connection", side_effect=_get_conn)
    patcher.start()
    return farm_repo, flock_repo, record_repo, patcher


@pytest.fixture()
def repos(db_conn):
    farm_repo, flock_repo, record_repo, patcher = _make_repos(db_conn)
    yield farm_repo, flock_repo, record_repo
    patcher.stop()


@pytest.fixture()
def populated_flock(repos):
    """Create a farm, flock and three daily records; return (flock_id, repos)."""
    farm_repo, flock_repo, record_repo = repos

    farm_id = farm_repo.create(
        Farm(
            farm_name="Test Farm",
            farmer_name="Test Farmer",
            location="Kano",
            production_type="Broiler",
        )
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Batch A",
            species="Chicken",
            production_type="Broiler",
            breed="Cobb 500",
            initial_count=500,
            stocking_date="2026-11-01",
            status="active",
        )
    )
    # Insert in non-chronological order to prove sorting works
    for rec_date, mortality, feed, water, weight, temp, humidity in [
        ("2026-11-03", 3, 35.0, 70.0, 0.70, 28.5, 67.0),
        ("2026-11-01", 2, 30.0, 60.0, 0.50, 28.0, 65.0),
        ("2026-11-02", 1, 32.0, 64.0, 0.60, 29.0, 66.0),
    ]:
        record_repo.create(
            DailyRecord(
                flock_id=flock_id,
                record_date=rec_date,
                feed_kg=feed,
                water_litres=water,
                mortality=mortality,
                average_weight_kg=weight,
                temperature_c=temp,
                humidity_percent=humidity,
            )
        )

    return flock_id, repos


# ---------------------------------------------------------------------------
# Tests: flock summary
# ---------------------------------------------------------------------------


def test_flock_summary_totals(populated_flock):
    flock_id, (_, flock_repo, record_repo) = populated_flock
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    summary = service.get_flock_summary(flock_id)

    assert summary["initial_count"] == 500
    assert summary["total_mortality"] == 6.0
    assert summary["current_flock_size"] == 494
    assert summary["mortality_rate_percent"] == 1.2
    assert summary["total_feed_kg"] == 97.0
    assert summary["total_water_litres"] == 194.0
    assert summary["average_weight_kg"] == 0.6
    assert summary["average_temperature_c"] == 28.5
    assert summary["average_humidity_percent"] == 66.0
    assert summary["record_count"] == 3


def test_flock_summary_empty_records(repos):
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Empty",
            species="Chicken",
            initial_count=200,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    summary = service.get_flock_summary(flock_id)

    assert summary["initial_count"] == 200
    assert summary["current_flock_size"] == 200
    assert summary["total_mortality"] == 0.0
    assert summary["record_count"] == 0
    assert summary["average_weight_kg"] is None
    assert summary["average_temperature_c"] is None
    assert summary["average_humidity_percent"] is None


def test_flock_summary_missing_flock_raises(repos):
    _, flock_repo, record_repo = repos
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    with pytest.raises(ValueError, match="was not found"):
        service.get_flock_summary(999999)


# ---------------------------------------------------------------------------
# Tests: daily metrics — chronological order is the critical correctness check
# ---------------------------------------------------------------------------


def test_daily_metrics_are_chronological(populated_flock):
    """Records inserted out of order must be returned and calculated chronologically."""
    flock_id, (_, flock_repo, record_repo) = populated_flock
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_daily_metrics(flock_id)

    assert len(metrics) == 3

    # Chronological order: Nov 1, Nov 2, Nov 3
    assert metrics[0]["record_date"] == "2026-11-01"
    assert metrics[1]["record_date"] == "2026-11-02"
    assert metrics[2]["record_date"] == "2026-11-03"


def test_daily_metrics_cumulative_mortality_is_correct(populated_flock):
    """Cumulative mortality must accumulate in date order, not insertion order."""
    flock_id, (_, flock_repo, record_repo) = populated_flock
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_daily_metrics(flock_id)

    # Nov 1: mortality=2, cumulative=2, remaining=498
    assert metrics[0]["mortality"] == 2.0
    assert metrics[0]["cumulative_mortality"] == 2.0
    assert metrics[0]["current_flock_size"] == 498

    # Nov 2: mortality=1, cumulative=3, remaining=497
    assert metrics[1]["mortality"] == 1.0
    assert metrics[1]["cumulative_mortality"] == 3.0
    assert metrics[1]["current_flock_size"] == 497

    # Nov 3: mortality=3, cumulative=6, remaining=494
    assert metrics[2]["mortality"] == 3.0
    assert metrics[2]["cumulative_mortality"] == 6.0
    assert metrics[2]["current_flock_size"] == 494


def test_daily_metrics_empty_flock(repos):
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Empty",
            species="Chicken",
            initial_count=100,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    assert service.get_daily_metrics(flock_id) == []


# ---------------------------------------------------------------------------
# Tests: date range metrics
# ---------------------------------------------------------------------------


def test_metrics_by_date_range(populated_flock):
    flock_id, (_, flock_repo, record_repo) = populated_flock
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_metrics_by_date_range(
        flock_id=flock_id,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
    )

    assert len(metrics) == 2
    assert metrics[0]["record_date"] == "2026-11-02"
    assert metrics[0]["mortality"] == 1.0
    assert metrics[1]["record_date"] == "2026-11-03"
    assert metrics[1]["mortality"] == 3.0


# ---------------------------------------------------------------------------
# Tests: None vs 0.0 preservation for chart filtering
# ---------------------------------------------------------------------------


def test_daily_metrics_preserves_none_for_unrecorded_feed(repos):
    """feed_kg=None must stay None in metrics, not become 0.0."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Sparse",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            feed_kg=None,
            water_litres=None,
            average_weight_kg=None,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_daily_metrics(flock_id)

    assert len(metrics) == 1
    assert metrics[0]["feed_kg"] is None
    assert metrics[0]["water_litres"] is None
    assert metrics[0]["average_weight_kg"] is None


def test_daily_metrics_preserves_recorded_feed_value(repos):
    """A recorded feed_kg value must be returned unchanged."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Fed",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            feed_kg=35.5,
            water_litres=70.0,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_daily_metrics(flock_id)

    assert metrics[0]["feed_kg"] == 35.5
    assert metrics[0]["water_litres"] == 70.0


def test_daily_metrics_weight_stored_and_returned_accurately(repos):
    """Small weight values like 0.04 kg must be stored and returned as-is."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Chicks",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            average_weight_kg=0.04,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_daily_metrics(flock_id)

    # Value must be returned exactly as stored; no biological filtering applied.
    assert metrics[0]["average_weight_kg"] == 0.04


def test_flock_summary_feed_total_excludes_none(repos):
    """Summary total_feed_kg must sum only recorded values, treating None as 0."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Mixed",
            species="Chicken",
            initial_count=100,
        )
    )
    # One record with feed, one without
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            feed_kg=30.0,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-02",
            mortality=0,
            feed_kg=None,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    summary = service.get_flock_summary(flock_id)

    # Only the 30.0 record should contribute
    assert summary["total_feed_kg"] == 30.0
    assert summary["record_count"] == 2


# ---------------------------------------------------------------------------
# Tests: get_metrics_by_date_range — None / 0.0 / value preservation
# ---------------------------------------------------------------------------


def test_date_range_metrics_preserves_none_for_unrecorded_feed(repos):
    """feed_kg=None and water_litres=None must remain None in date-range results."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Sparse",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            feed_kg=None,
            water_litres=None,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_metrics_by_date_range(
        flock_id=flock_id,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 1),
    )

    assert len(metrics) == 1
    assert metrics[0]["feed_kg"] is None
    assert metrics[0]["water_litres"] is None


def test_date_range_metrics_preserves_genuine_zero_feed(repos):
    """feed_kg=0.0 and water_litres=0.0 must be returned as 0.0, not None."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Zero",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            feed_kg=0.0,
            water_litres=0.0,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_metrics_by_date_range(
        flock_id=flock_id,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 1),
    )

    assert len(metrics) == 1
    assert metrics[0]["feed_kg"] == 0.0
    assert metrics[0]["water_litres"] == 0.0


def test_date_range_metrics_returns_recorded_values_accurately(repos):
    """Recorded feed and water values must be returned with two-decimal precision."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Measured",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=1,
            feed_kg=42.75,
            water_litres=85.5,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    metrics = service.get_metrics_by_date_range(
        flock_id=flock_id,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 1),
    )

    assert len(metrics) == 1
    assert metrics[0]["feed_kg"] == 42.75
    assert metrics[0]["water_litres"] == 85.5
    assert metrics[0]["mortality"] == 1.0


# ---------------------------------------------------------------------------
# Tests: get_environmental_summary
# ---------------------------------------------------------------------------


def test_env_summary_averages_min_max(populated_flock):
    """Temperature and humidity averages, minimums and maximums are correct."""
    flock_id, (_, flock_repo, record_repo) = populated_flock
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)
    t = result["temperature"]
    h = result["humidity"]

    # populated_flock has temps 28.0, 29.0, 28.5 and humidities 65.0, 66.0, 67.0
    assert t["average_c"] == round((28.0 + 29.0 + 28.5) / 3, 2)
    assert t["minimum_c"] == 28.0
    assert t["maximum_c"] == 29.0
    assert h["average_percent"] == round((65.0 + 66.0 + 67.0) / 3, 2)
    assert h["minimum_percent"] == 65.0
    assert h["maximum_percent"] == 67.0


def test_env_summary_counts_and_coverage(populated_flock):
    """Recorded counts, missing counts and coverage percentages are correct."""
    flock_id, (_, flock_repo, record_repo) = populated_flock
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)

    assert result["total_records"] == 3
    assert result["temperature"]["recorded_count"] == 3
    assert result["temperature"]["missing_count"] == 0
    assert result["temperature"]["coverage_percent"] == 100.0
    assert result["humidity"]["recorded_count"] == 3
    assert result["humidity"]["missing_count"] == 0
    assert result["humidity"]["coverage_percent"] == 100.0


def test_env_summary_missing_measurements_are_none(repos):
    """When no temperature or humidity is ever recorded, all stats are None."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="NoEnv",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            temperature_c=None,
            humidity_percent=None,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)
    t = result["temperature"]
    h = result["humidity"]

    assert t["recorded_count"] == 0
    assert t["missing_count"] == 1
    assert t["coverage_percent"] == 0.0
    assert t["average_c"] is None
    assert t["minimum_c"] is None
    assert t["maximum_c"] is None
    assert t["latest_record_date"] is None
    assert t["latest_value_c"] is None
    assert h["average_percent"] is None
    assert h["latest_value_percent"] is None


def test_env_summary_zero_is_recorded_observation(repos):
    """A temperature or humidity of 0.0 counts as a recorded observation."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="ZeroEnv",
            species="Chicken",
            initial_count=50,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            temperature_c=0.0,
            humidity_percent=0.0,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)

    assert result["temperature"]["recorded_count"] == 1
    assert result["temperature"]["average_c"] == 0.0
    assert result["humidity"]["recorded_count"] == 1
    assert result["humidity"]["average_percent"] == 0.0


def test_env_summary_different_latest_dates_for_temp_and_humidity(repos):
    """Missing observations are excluded from stats; coverage uses all records.

    Three daily records:
      Nov 1 — temperature 28.0, humidity 65.0 (both recorded)
      Nov 2 — temperature 29.0, humidity None (temperature only)
      Nov 3 — temperature None, humidity None (neither recorded)

    Temperature: 2 recorded, 1 missing, coverage 66.67 %.
    Humidity:    1 recorded, 2 missing, coverage 33.33 %.
    Latest observations are not displaced by later None records.
    """
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="SplitEnv",
            species="Chicken",
            initial_count=100,
        )
    )
    # Nov 1: both recorded
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            temperature_c=28.0,
            humidity_percent=65.0,
        )
    )
    # Nov 2: temperature only
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-02",
            mortality=0,
            temperature_c=29.0,
            humidity_percent=None,
        )
    )
    # Nov 3: neither recorded — must not affect latest observations
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-03",
            mortality=0,
            temperature_c=None,
            humidity_percent=None,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)
    t = result["temperature"]
    h = result["humidity"]

    # Temperature: 2 of 3 records have a value
    assert t["recorded_count"] == 2
    assert t["missing_count"] == 1
    assert t["coverage_percent"] == 66.67
    assert t["average_c"] == round((28.0 + 29.0) / 2, 2)
    assert t["minimum_c"] == 28.0
    assert t["maximum_c"] == 29.0
    # Latest temperature observation is Nov 2; Nov 3 (None) must not replace it
    assert t["latest_record_date"] == "2026-11-02"
    assert t["latest_value_c"] == 29.0

    # Humidity: 1 of 3 records has a value
    assert h["recorded_count"] == 1
    assert h["missing_count"] == 2
    assert h["coverage_percent"] == 33.33
    assert h["average_percent"] == 65.0
    assert h["minimum_percent"] == 65.0
    assert h["maximum_percent"] == 65.0
    # Latest humidity observation is Nov 1; later None records must not replace it
    assert h["latest_record_date"] == "2026-11-01"
    assert h["latest_value_percent"] == 65.0


def test_env_summary_later_missing_does_not_replace_latest(repos):
    """A later record with None does not become the latest observation."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="LatestCheck",
            species="Chicken",
            initial_count=100,
        )
    )
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-01",
            mortality=0,
            temperature_c=27.5,
        )
    )
    # Nov 2 has no temperature — must not overwrite Nov 1 as latest
    record_repo.create(
        DailyRecord(
            flock_id=flock_id,
            record_date="2026-11-02",
            mortality=0,
            temperature_c=None,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)
    t = result["temperature"]

    assert t["latest_record_date"] == "2026-11-01"
    assert t["latest_value_c"] == 27.5
    assert t["recorded_count"] == 1
    assert t["missing_count"] == 1
    assert t["coverage_percent"] == 50.0


def test_env_summary_no_records_returns_zero_counts(repos):
    """A flock with no daily records returns zero counts and None stats."""
    farm_repo, flock_repo, record_repo = repos
    farm_id = farm_repo.create(
        Farm(farm_name="F", farmer_name="N", location="L", production_type="Broiler")
    )
    flock_id = flock_repo.create(
        Flock(
            farm_id=farm_id,
            flock_name="Empty",
            species="Chicken",
            initial_count=100,
        )
    )
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    result = service.get_environmental_summary(flock_id)

    assert result["total_records"] == 0
    assert result["temperature"]["recorded_count"] == 0
    assert result["temperature"]["missing_count"] == 0
    assert result["temperature"]["coverage_percent"] == 0.0
    assert result["temperature"]["average_c"] is None
    assert result["temperature"]["latest_record_date"] is None
    assert result["humidity"]["recorded_count"] == 0
    assert result["humidity"]["average_percent"] is None


def test_env_summary_unknown_flock_raises(repos):
    """Requesting a summary for an unknown flock raises ValueError."""
    _, flock_repo, record_repo = repos
    service = AnalyticsService(
        flock_repository=flock_repo, daily_record_repository=record_repo
    )
    with pytest.raises(ValueError, match="was not found"):
        service.get_environmental_summary(999999)
