"""Tests for immutable quality-review decisions and effective status."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from threading import Barrier
from uuid import UUID

import app.database.connection as database_connection
import pytest
from app.database import (
    MeasurementQualityReviewEvent,
    MeasurementQualityReviewEventRepository,
)
from app.database.migrations import runner
from app.services.measurement_quality_review_service import (
    MeasurementQualityReviewService,
)


@pytest.fixture()
def review_context(tmp_path, monkeypatch):
    database_path = tmp_path / "measurement-quality-review-test.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    database_connection.initialise_database()

    with database_connection.get_connection() as connection:
        farm_id = connection.execute(
            "INSERT INTO farms (farm_name, farmer_name) VALUES (?, ?)",
            ("Review Farm", "Test Farmer"),
        ).lastrowid
        flock_id = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch A", "Chicken", 100),
        ).lastrowid

    with database_connection.get_connection() as connection:
        runner.migrate(connection)

    return {
        "service": MeasurementQualityReviewService(),
        "flock_id": flock_id,
        "database_path": database_path,
    }


def _insert_observation(
    context, observation_id="candidate-001", quality_status="pending_validation"
):
    value = (
        None
        if quality_status
        in {
            "not_recorded",
            "not_measured",
            "not_applicable",
            "device_unavailable",
        }
        else 4.5
    )
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_observations (
                observation_id, flock_id, record_date, metric_name,
                value_numeric, unit, recorded_at, source_type, quality_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation_id,
                context["flock_id"],
                "2026-11-24",
                "feed_kg",
                value,
                "kg",
                "2026-11-24T12:00:00Z",
                "manual_entry",
                quality_status,
            ),
        )
    return observation_id


def _insert_review_event(observation_id, decision):
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_quality_review_events (
                event_id, observation_id, decision, review_reason, reviewed_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"review-{observation_id}",
                observation_id,
                decision,
                "Fixture decision",
                "2026-11-24T13:00:00Z",
            ),
        )


def _get_observation(context, observation_id):
    with database_connection.get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM measurement_observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        return tuple(row)


def _event_rows(context, observation_id):
    with database_connection.get_connection() as connection:
        return connection.execute(
            """
            SELECT event_id, observation_id, decision, review_reason,
                   reviewed_by_user_id, reviewed_at
            FROM measurement_quality_review_events
            WHERE observation_id = ?
            """,
            (observation_id,),
        ).fetchall()


def test_accept_pending_observation_records_event_only_and_preserves_raw_row(
    review_context,
):
    observation_id = _insert_observation(review_context)
    before = _get_observation(review_context, observation_id)

    event_id = review_context["service"].accept_observation(
        observation_id, review_reason="Source document verified"
    )

    after = _get_observation(review_context, observation_id)
    event = _event_rows(review_context, observation_id)[0]
    effective = review_context["service"].get_effective_quality_status(observation_id)
    assert before == after
    assert event[0] == event_id
    assert str(UUID(event_id)) == event_id
    assert event[2] == "accepted"
    assert event[3] == "Source document verified"
    assert event[4] is None
    assert event[5].endswith("Z")
    assert effective.raw_quality_status == "pending_validation"
    assert effective.effective_quality_status == "observed"


def test_reject_pending_observation_records_event_only_and_derives_invalid(
    review_context,
):
    observation_id = _insert_observation(review_context)
    before = _get_observation(review_context, observation_id)

    event_id = review_context["service"].reject_observation(
        observation_id, review_reason="Measurement could not be verified"
    )

    event = _event_rows(review_context, observation_id)[0]
    effective = review_context["service"].get_effective_quality_status(observation_id)
    assert _get_observation(review_context, observation_id) == before
    assert event[0] == event_id
    assert event[2] == "rejected"
    assert event[4] is None
    assert effective.raw_quality_status == "pending_validation"
    assert effective.effective_quality_status == "invalid"


def test_missing_observations_are_rejected_for_review_and_status_lookup(review_context):
    with pytest.raises(ValueError, match="does not exist"):
        review_context["service"].accept_observation("missing", review_reason="Review")
    with pytest.raises(ValueError, match="does not exist"):
        review_context["service"].get_effective_quality_status("missing")


@pytest.mark.parametrize(
    "quality_status",
    [
        "observed",
        "invalid",
        "not_recorded",
        "not_measured",
        "not_applicable",
        "device_unavailable",
    ],
)
def test_only_pending_validation_observations_can_be_reviewed(
    review_context, quality_status
):
    observation_id = _insert_observation(review_context, quality_status=quality_status)
    with pytest.raises(ValueError, match="pending_validation"):
        review_context["service"].accept_observation(
            observation_id, review_reason="Review"
        )
    assert _event_rows(review_context, observation_id) == []


@pytest.mark.parametrize("reason", ["", "   ", "\t\n"])
def test_empty_or_whitespace_review_reason_is_rejected(review_context, reason):
    observation_id = _insert_observation(review_context)
    with pytest.raises(ValueError, match="non-empty"):
        review_context["service"].accept_observation(
            observation_id, review_reason=reason
        )
    assert _event_rows(review_context, observation_id) == []


def test_duplicate_terminal_decision_is_rejected_without_another_event(review_context):
    observation_id = _insert_observation(review_context)
    service = review_context["service"]
    service.accept_observation(observation_id, review_reason="Accepted")
    original_event = _event_rows(review_context, observation_id)

    with pytest.raises(ValueError, match="already been reviewed"):
        service.reject_observation(observation_id, review_reason="Reject instead")

    assert _event_rows(review_context, observation_id) == original_event


def test_event_ids_are_unique_and_reviewer_identity_remains_nullable(review_context):
    first_id = _insert_observation(review_context, observation_id="candidate-a")
    second_id = _insert_observation(review_context, observation_id="candidate-b")
    service = review_context["service"]
    first_event = service.accept_observation(first_id, review_reason="Verified")
    second_event = service.reject_observation(second_id, review_reason="Rejected")

    assert first_event != second_event
    assert _event_rows(review_context, first_id)[0][4] is None
    assert _event_rows(review_context, second_id)[0][4] is None


def test_quality_review_event_model_is_immutable():
    event = MeasurementQualityReviewEvent(
        event_id="event-1",
        observation_id="observation-1",
        decision="accepted",
        review_reason="Verified",
        reviewed_at="2026-11-24T13:00:00Z",
    )
    with pytest.raises(FrozenInstanceError):
        event.decision = "rejected"


@pytest.mark.parametrize(
    ("quality_status", "decision", "expected"),
    [
        ("observed", None, "observed"),
        ("pending_validation", None, "pending_validation"),
        ("pending_validation", "accepted", "observed"),
        ("pending_validation", "rejected", "invalid"),
        ("invalid", None, "invalid"),
        ("not_recorded", None, "not_recorded"),
        ("not_measured", None, "not_measured"),
        ("not_applicable", None, "not_applicable"),
        ("device_unavailable", None, "device_unavailable"),
    ],
)
def test_effective_status_derivation_matrix(
    review_context, quality_status, decision, expected
):
    observation_id = _insert_observation(
        review_context,
        observation_id=f"status-{quality_status}-{decision}",
        quality_status=quality_status,
    )
    if decision is not None:
        _insert_review_event(observation_id, decision)

    status = review_context["service"].get_effective_quality_status(observation_id)

    assert status.observation_id == observation_id
    assert status.raw_quality_status == quality_status
    assert status.effective_quality_status == expected


def test_review_event_insert_failure_rolls_back(review_context, monkeypatch):
    observation_id = _insert_observation(review_context)
    before = _get_observation(review_context, observation_id)

    def fail_create(self, event):
        raise sqlite3.IntegrityError("forced review insert failure")

    monkeypatch.setattr(MeasurementQualityReviewEventRepository, "create", fail_create)
    with pytest.raises(sqlite3.IntegrityError, match="forced review insert failure"):
        review_context["service"].accept_observation(
            observation_id, review_reason="Verified"
        )

    assert _get_observation(review_context, observation_id) == before
    assert _event_rows(review_context, observation_id) == []


def test_concurrent_reviews_create_exactly_one_terminal_event(review_context):
    observation_id = _insert_observation(review_context)
    service = review_context["service"]
    barrier = Barrier(2)

    def accept():
        barrier.wait()
        try:
            return True, service.accept_observation(
                observation_id,
                review_reason="Concurrent review",
            )
        except ValueError as error:
            return False, str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: accept(), range(2)))

    assert (
        sum(
            not success and "already been reviewed" in result
            for success, result in results
        )
        == 1
    )
    assert sum(success for success, _ in results) == 1
    assert len(_event_rows(review_context, observation_id)) == 1
