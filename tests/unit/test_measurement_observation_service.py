"""Tests for validated manual measurement observations."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import app.database.connection as database_connection
import pytest
from app.database import MeasurementObservation
from app.database.migrations import runner
from app.services.measurement_observation_service import (
    MeasurementObservationService,
)


@pytest.fixture()
def observation_context(tmp_path, monkeypatch):
    """Build a migrated, isolated database with two flocks and one daily row."""
    database_path = tmp_path / "measurement-observations-test.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    database_connection.initialise_database()

    with database_connection.get_connection() as connection:
        farm_cursor = connection.execute(
            """
            INSERT INTO farms (farm_name, farmer_name, location)
            VALUES (?, ?, ?)
            """,
            ("Test Farm", "Test Farmer", "Kano"),
        )
        farm_id = farm_cursor.lastrowid

        flock_cursor = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch A", "Chicken", 100),
        )
        flock_id = flock_cursor.lastrowid

        other_flock_cursor = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch B", "Chicken", 100),
        )
        other_flock_id = other_flock_cursor.lastrowid

        daily_cursor = connection.execute(
            """
            INSERT INTO daily_records (
                flock_id, record_date, feed_kg, water_litres, mortality
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (flock_id, "2026-11-19", 0.0, None, 0),
        )
        daily_record_id = daily_cursor.lastrowid

    with database_connection.get_connection() as connection:
        runner.migrate(connection)

    return {
        "service": MeasurementObservationService(),
        "flock_id": flock_id,
        "other_flock_id": other_flock_id,
        "daily_record_id": daily_record_id,
        "database_path": database_path,
    }


@pytest.mark.parametrize(
    ("metric_name", "value", "expected_unit"),
    [
        ("mortality", 0, "birds"),
        ("feed_kg", 0.0, "kg"),
        ("water_litres", 0.0, "litres"),
        ("average_weight_kg", 1.25, "kg_per_bird"),
        ("temperature_c", -8.5, "degrees_celsius"),
        ("humidity_percent", 0.0, "percent_relative_humidity"),
    ],
)
def test_create_observation_uses_canonical_metric_unit_and_manual_provenance(
    observation_context, metric_name, value, expected_unit
):
    service = observation_context["service"]
    observation_id = service.create_observation(
        flock_id=observation_context["flock_id"],
        record_date=date(2026, 11, 19),
        metric_name=metric_name,
        value_numeric=value,
    )

    observation = service.get_observation(observation_id)
    assert observation is not None
    assert observation["metric_name"] == metric_name
    assert observation["unit"] == expected_unit
    assert observation["value_numeric"] == value
    assert observation["source_type"] == "manual_entry"
    assert observation["quality_status"] == "observed"
    assert observation["observed_at"] is None
    assert observation["recorded_at"].endswith("Z")
    assert observation["supersedes_observation_id"] is None
    assert observation["correction_reason"] is None


def test_zero_is_preserved_as_an_observed_value(observation_context):
    service = observation_context["service"]
    observation_id = service.create_observation(
        flock_id=observation_context["flock_id"],
        record_date="2026-11-19",
        metric_name="feed_kg",
        value_numeric=0,
    )

    observation = service.get_observation(observation_id)
    assert observation is not None
    assert observation["value_numeric"] == 0
    assert observation["quality_status"] == "observed"


def test_create_observation_links_matching_daily_record(observation_context):
    service = observation_context["service"]
    observation_id = service.create_observation(
        flock_id=observation_context["flock_id"],
        daily_record_id=observation_context["daily_record_id"],
        record_date="2026-11-19",
        metric_name="feed_kg",
        value_numeric=1.5,
    )

    linked = service.list_daily_record_observations(
        observation_context["daily_record_id"]
    )
    assert [row["observation_id"] for row in linked] == [observation_id]
    assert linked[0]["flock_id"] == observation_context["flock_id"]


def test_observed_at_is_normalised_to_utc(observation_context):
    service = observation_context["service"]
    observation_id = service.create_observation(
        flock_id=observation_context["flock_id"],
        record_date="2026-11-19",
        metric_name="temperature_c",
        value_numeric=29.0,
        observed_at="2026-11-19T15:30:00+01:00",
    )
    observation = service.get_observation(observation_id)
    assert observation is not None
    assert observation["observed_at"] == "2026-11-19T14:30:00Z"


def test_naive_observed_at_is_rejected(observation_context):
    with pytest.raises(ValueError, match="must include a timezone"):
        observation_context["service"].create_observation(
            flock_id=observation_context["flock_id"],
            record_date="2026-11-19",
            metric_name="temperature_c",
            value_numeric=29.0,
            observed_at="2026-11-19T15:30:00",
        )


def test_daily_record_must_belong_to_the_specified_flock(observation_context):
    with pytest.raises(ValueError, match="does not belong to the specified flock"):
        observation_context["service"].create_observation(
            flock_id=observation_context["other_flock_id"],
            daily_record_id=observation_context["daily_record_id"],
            record_date="2026-11-19",
            metric_name="feed_kg",
            value_numeric=1.0,
        )


def test_observation_date_must_match_linked_daily_record(observation_context):
    with pytest.raises(ValueError, match="must match its linked daily record"):
        observation_context["service"].create_observation(
            flock_id=observation_context["flock_id"],
            daily_record_id=observation_context["daily_record_id"],
            record_date="2026-11-20",
            metric_name="feed_kg",
            value_numeric=1.0,
        )


def test_nonexistent_flock_is_rejected(observation_context):
    with pytest.raises(ValueError, match="does not exist"):
        observation_context["service"].create_observation(
            flock_id=999999,
            record_date="2026-11-19",
            metric_name="feed_kg",
            value_numeric=1.0,
        )


def test_nonexistent_daily_record_is_rejected(observation_context):
    with pytest.raises(ValueError, match="Daily record with ID 999999 does not exist"):
        observation_context["service"].create_observation(
            flock_id=observation_context["flock_id"],
            daily_record_id=999999,
            record_date="2026-11-19",
            metric_name="feed_kg",
            value_numeric=1.0,
        )


@pytest.mark.parametrize(
    ("metric_name", "value", "message"),
    [
        ("mortality", -1, "Mortality cannot be negative"),
        ("mortality", 1.5, "whole-number count"),
        ("feed_kg", -0.1, "cannot be negative"),
        ("water_litres", -0.1, "cannot be negative"),
        ("average_weight_kg", 0, "greater than zero"),
        ("humidity_percent", -0.1, "between 0 and 100"),
        ("humidity_percent", 100.1, "between 0 and 100"),
        ("temperature_c", float("nan"), "finite number"),
        ("temperature_c", float("inf"), "finite number"),
        ("feed_kg", True, "finite number"),
    ],
)
def test_invalid_metric_values_are_rejected(
    observation_context, metric_name, value, message
):
    with pytest.raises(ValueError, match=message):
        observation_context["service"].create_observation(
            flock_id=observation_context["flock_id"],
            record_date="2026-11-19",
            metric_name=metric_name,
            value_numeric=value,
        )


def test_unknown_metric_is_rejected(observation_context):
    with pytest.raises(ValueError, match="Metric must be one of"):
        observation_context["service"].create_observation(
            flock_id=observation_context["flock_id"],
            record_date="2026-11-19",
            metric_name="feed",
            value_numeric=1.0,
        )


@pytest.mark.parametrize("record_date", ["19-11-2026", "2026-11-1", "not-a-date"])
def test_non_iso_record_date_is_rejected(observation_context, record_date):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        observation_context["service"].create_observation(
            flock_id=observation_context["flock_id"],
            record_date=record_date,
            metric_name="feed_kg",
            value_numeric=1.0,
        )


def test_metric_date_range_query_returns_only_requested_metric(
    observation_context,
):
    service = observation_context["service"]
    flock_id = observation_context["flock_id"]
    service.create_observation(
        flock_id=flock_id,
        record_date="2026-11-18",
        metric_name="feed_kg",
        value_numeric=1.0,
    )
    service.create_observation(
        flock_id=flock_id,
        record_date="2026-11-19",
        metric_name="feed_kg",
        value_numeric=2.0,
    )
    service.create_observation(
        flock_id=flock_id,
        record_date="2026-11-19",
        metric_name="water_litres",
        value_numeric=3.0,
    )

    results = service.list_metric_observations(
        flock_id=flock_id,
        metric_name="feed_kg",
        start_date="2026-11-19",
        end_date="2026-11-19",
    )
    assert len(results) == 1
    assert results[0]["metric_name"] == "feed_kg"
    assert results[0]["value_numeric"] == 2.0


def test_start_date_cannot_follow_end_date(observation_context):
    with pytest.raises(ValueError, match="Start date must not be after end date"):
        observation_context["service"].list_metric_observations(
            flock_id=observation_context["flock_id"],
            metric_name="feed_kg",
            start_date="2026-11-20",
            end_date="2026-11-19",
        )


def test_repository_exposes_no_update_or_delete_methods(observation_context):
    repository = observation_context["service"].repository
    assert not hasattr(repository, "update")
    assert not hasattr(repository, "delete")


def test_measurement_observation_dataclass_is_frozen():
    observation = MeasurementObservation(
        observation_id="obs-test",
        flock_id=1,
        record_date="2026-11-19",
        metric_name="feed_kg",
        value_numeric=1.0,
        unit="kg",
        recorded_at="2026-11-19T12:00:00Z",
    )
    with pytest.raises(FrozenInstanceError):
        observation.value_numeric = 2.0
