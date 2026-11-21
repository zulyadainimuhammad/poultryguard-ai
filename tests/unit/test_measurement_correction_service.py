"""Tests for exact-observation correction requests and decisions."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import app.database.connection as database_connection
import pytest
from app.database import MeasurementCorrectionRequestEventRepository
from app.database.migrations import runner
from app.services.measurement_correction_service import MeasurementCorrectionService
from app.services.measurement_observation_service import MeasurementObservationService


@pytest.fixture()
def correction_context(tmp_path, monkeypatch):
    database_path = tmp_path / "measurement-corrections-test.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    database_connection.initialise_database()

    with database_connection.get_connection() as connection:
        farm_id = connection.execute(
            "INSERT INTO farms (farm_name, farmer_name) VALUES (?, ?)",
            ("Correction Farm", "Test Farmer"),
        ).lastrowid
        flock_id = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch A", "Chicken", 100),
        ).lastrowid
        daily_record_id = connection.execute(
            """
            INSERT INTO daily_records (flock_id, record_date, mortality)
            VALUES (?, ?, ?)
            """,
            (flock_id, "2026-11-20", 0),
        ).lastrowid

    with database_connection.get_connection() as connection:
        runner.migrate(connection)

    return {
        "service": MeasurementCorrectionService(),
        "observations": MeasurementObservationService(),
        "flock_id": flock_id,
        "daily_record_id": daily_record_id,
        "database_path": database_path,
    }


def _create_target(context, *, value=4.5, observed_at="2026-11-20T10:30:00Z"):
    return context["observations"].create_observation(
        flock_id=context["flock_id"],
        daily_record_id=context["daily_record_id"],
        record_date="2026-11-20",
        metric_name="feed_kg",
        value_numeric=value,
        observed_at=observed_at,
    )


def _insert_candidate(
    context, *, observation_id="candidate-001", source="manual_entry"
):
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_observations (
                observation_id, flock_id, record_date, metric_name,
                value_numeric, unit, recorded_at, source_type, quality_status,
                import_batch_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation_id,
                context["flock_id"],
                "2026-11-20",
                "feed_kg",
                4.5,
                "kg",
                "2026-11-20T12:00:00Z",
                source,
                "pending_validation",
                "test-import" if source == "file_import" else None,
            ),
        )


def _accept_candidate(observation_id="candidate-001"):
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_quality_review_events (
                event_id, observation_id, decision, review_reason, reviewed_at
            ) VALUES (?, ?, 'accepted', ?, ?)
            """,
            (
                f"review-{observation_id}",
                observation_id,
                "Accepted test candidate",
                "2026-11-20T13:00:00Z",
            ),
        )


def _observation_rows(database_path):
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            """
            SELECT observation_id, value_numeric, supersedes_observation_id
            FROM measurement_observations ORDER BY observation_id
            """
        ).fetchall()


def test_request_targets_exact_observation_and_does_not_insert_measurement(
    correction_context,
):
    target_a = _create_target(correction_context, value=4.5)
    target_b = _create_target(correction_context, value=4.5)
    service = correction_context["service"]
    before = _observation_rows(correction_context["database_path"])

    request_id = service.submit_correction_request(
        target_observation_id=target_b,
        proposed_value_numeric=5.25,
        correction_reason="Corrected scale transcription",
    )

    request = service.get_correction_request(request_id)
    assert request["target_observation_id"] == target_b
    assert request["target_observation_id"] != target_a
    assert request["requested_by_user_id"] is None
    assert request["requested_at"].endswith("Z")
    assert service.list_pending_correction_requests(target_b) == [request]
    assert service.get_terminal_event(request_id) is None
    assert _observation_rows(correction_context["database_path"]) == before


def test_missing_and_ineligible_targets_are_rejected(correction_context):
    with pytest.raises(ValueError, match="does not exist"):
        correction_context["service"].submit_correction_request(
            target_observation_id="missing",
            proposed_value_numeric=1.0,
            correction_reason="Correct value",
        )

    _insert_candidate(correction_context)
    with pytest.raises(ValueError, match="not eligible"):
        correction_context["service"].submit_correction_request(
            target_observation_id="candidate-001",
            proposed_value_numeric=5.0,
            correction_reason="Correct value",
        )

    _insert_candidate(
        correction_context, observation_id="import-candidate", source="file_import"
    )
    _accept_candidate("import-candidate")
    with pytest.raises(ValueError, match="not eligible"):
        correction_context["service"].submit_correction_request(
            target_observation_id="import-candidate",
            proposed_value_numeric=5.0,
            correction_reason="Correct value",
        )


def test_accepted_pending_manual_candidate_is_eligible(correction_context):
    _insert_candidate(correction_context)
    _accept_candidate()

    request_id = correction_context["service"].submit_correction_request(
        target_observation_id="candidate-001",
        proposed_value_numeric=5.0,
        correction_reason="Correct candidate value",
    )

    assert correction_context["service"].get_correction_request(request_id) is not None


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -1.0],
)
def test_metric_validation_rejects_non_finite_and_invalid_values(
    correction_context, value
):
    target_id = _create_target(correction_context)
    with pytest.raises(ValueError):
        correction_context["service"].submit_correction_request(
            target_observation_id=target_id,
            proposed_value_numeric=value,
            correction_reason="Invalid proposal",
        )


@pytest.mark.parametrize(
    ("metric_name", "existing", "proposed"),
    [
        ("mortality", 4, 4.5),
        ("humidity_percent", 50.0, 100.1),
        ("average_weight_kg", 1.5, 0),
    ],
)
def test_correction_reuses_metric_specific_value_validation(
    correction_context, metric_name, existing, proposed
):
    target_id = correction_context["observations"].create_observation(
        flock_id=correction_context["flock_id"],
        record_date="2026-11-20",
        metric_name=metric_name,
        value_numeric=existing,
    )
    with pytest.raises(ValueError):
        correction_context["service"].submit_correction_request(
            target_observation_id=target_id,
            proposed_value_numeric=proposed,
            correction_reason="Invalid metric-specific proposal",
        )


def test_noop_and_empty_reasons_are_rejected(correction_context):
    target_id = _create_target(correction_context, value=4.5)
    with pytest.raises(ValueError, match="no-op"):
        correction_context["service"].submit_correction_request(
            target_observation_id=target_id,
            proposed_value_numeric=4.5,
            correction_reason="Same value",
        )
    with pytest.raises(ValueError, match="non-empty"):
        correction_context["service"].submit_correction_request(
            target_observation_id=target_id,
            proposed_value_numeric=5.0,
            correction_reason="  ",
        )


def test_multiple_requests_are_allowed_for_same_exact_target(correction_context):
    target_id = _create_target(correction_context)
    service = correction_context["service"]
    first = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="First proposal",
    )
    second = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=6.0,
        correction_reason="Second proposal",
    )
    assert {
        row["request_id"] for row in service.list_pending_correction_requests(target_id)
    } == {
        first,
        second,
    }


def test_approval_inherits_metadata_and_invalidates_siblings_atomically(
    correction_context,
):
    target_id = _create_target(correction_context, observed_at="2026-11-20T10:30:00Z")
    service = correction_context["service"]
    approved_request = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.25,
        correction_reason="Scale was misread",
    )
    sibling_request = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.5,
        correction_reason="Alternate proposal",
    )

    result = service.approve_correction_request(approved_request)

    assert result.outcome == "approved"
    assert result.created_observation_id
    observation = correction_context["observations"].get_observation(
        result.created_observation_id
    )
    assert observation["flock_id"] == correction_context["flock_id"]
    assert observation["daily_record_id"] == correction_context["daily_record_id"]
    assert observation["record_date"] == "2026-11-20"
    assert observation["metric_name"] == "feed_kg"
    assert observation["unit"] == "kg"
    assert observation["observed_at"] == "2026-11-20T10:30:00Z"
    assert observation["recorded_at"].endswith("Z")
    assert observation["source_type"] == "manual_entry"
    assert observation["quality_status"] == "observed"
    assert observation["supersedes_observation_id"] == target_id
    assert observation["correction_reason"] == "Scale was misread"

    event = service.get_terminal_event(approved_request)
    sibling_event = service.get_terminal_event(sibling_request)
    assert event["outcome"] == "approved"
    assert event["created_observation_id"] == result.created_observation_id
    assert sibling_event["outcome"] == "invalidated"
    assert sibling_event["created_observation_id"] is None
    assert service.list_pending_correction_requests(target_id) == []


def test_mortality_request_round_trips_as_integer_through_real_affinity(
    correction_context,
):
    target_id = correction_context["observations"].create_observation(
        flock_id=correction_context["flock_id"],
        record_date="2026-11-20",
        metric_name="mortality",
        value_numeric=4,
    )
    service = correction_context["service"]
    request_id = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5,
        correction_reason="Corrected daily count",
    )

    result = service.approve_correction_request(request_id)

    assert result.outcome == "approved"
    corrected = correction_context["observations"].get_observation(
        result.created_observation_id
    )
    assert corrected["value_numeric"] == 5


def test_rejection_is_terminal_without_observation_and_new_request_is_allowed(
    correction_context,
):
    target_id = _create_target(correction_context)
    service = correction_context["service"]
    request_id = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="Correct scale reading",
    )
    before = _observation_rows(correction_context["database_path"])

    rejected = service.reject_correction_request(
        request_id, rejection_reason="Supporting note was missing"
    )
    next_request_id = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.5,
        correction_reason="Revised proposal",
    )

    assert rejected.outcome == "rejected"
    assert service.get_terminal_event(request_id)["created_observation_id"] is None
    assert _observation_rows(correction_context["database_path"]) == before
    assert service.get_correction_request(next_request_id) is not None


def test_stale_request_is_invalidated_without_observation(correction_context):
    target_id = _create_target(correction_context)
    service = correction_context["service"]
    request_id = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="First proposal",
    )
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_observations (
                observation_id, flock_id, record_date, metric_name, value_numeric,
                unit, recorded_at, source_type, quality_status,
                supersedes_observation_id, correction_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "external-successor",
                correction_context["flock_id"],
                "2026-11-20",
                "feed_kg",
                4.75,
                "kg",
                "2026-11-21T12:00:00Z",
                "manual_entry",
                "observed",
                target_id,
                "External test successor",
            ),
        )
    before = _observation_rows(correction_context["database_path"])

    result = service.approve_correction_request(request_id)

    assert result.outcome == "invalidated"
    assert result.created_observation_id is None
    assert service.get_terminal_event(request_id)["outcome"] == "invalidated"
    assert _observation_rows(correction_context["database_path"]) == before


def test_already_decided_request_cannot_receive_another_event(correction_context):
    target_id = _create_target(correction_context)
    service = correction_context["service"]
    request_id = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="Correction",
    )
    service.reject_correction_request(request_id, rejection_reason="Rejected")
    event_before = service.get_terminal_event(request_id)

    with pytest.raises(ValueError, match="already been decided"):
        service.approve_correction_request(request_id)

    assert service.get_terminal_event(request_id) == event_before


def test_approval_failure_rolls_back_observation_and_events(
    correction_context, monkeypatch
):
    target_id = _create_target(correction_context)
    service = correction_context["service"]
    request_id = service.submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="Correction",
    )
    before = _observation_rows(correction_context["database_path"])

    def fail_create(self, event):
        raise sqlite3.IntegrityError("forced decision failure")

    monkeypatch.setattr(
        MeasurementCorrectionRequestEventRepository, "create", fail_create
    )
    with pytest.raises(sqlite3.IntegrityError, match="forced decision failure"):
        service.approve_correction_request(request_id)

    assert _observation_rows(correction_context["database_path"]) == before
    assert service.get_terminal_event(request_id) is None


def test_concurrent_approvals_serialize_and_first_winner_invalidates_sibling(
    correction_context,
):
    target_id = _create_target(correction_context)
    service = correction_context["service"]
    request_ids = [
        service.submit_correction_request(
            target_observation_id=target_id,
            proposed_value_numeric=value,
            correction_reason=f"Proposal {value}",
        )
        for value in (5.0, 6.0)
    ]
    barrier = Barrier(2)

    def approve(request_id):
        barrier.wait()
        try:
            return service.approve_correction_request(request_id).outcome
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(approve, request_ids))

    assert results.count("approved") == 1
    assert sum("already been decided" in result for result in results) == 1
    outcomes = [
        service.get_terminal_event(request_id)["outcome"] for request_id in request_ids
    ]
    assert sorted(outcomes) == ["approved", "invalidated"]
