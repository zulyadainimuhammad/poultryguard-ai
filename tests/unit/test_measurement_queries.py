"""Temporary-database tests for accepted measurement and audit queries."""

from __future__ import annotations

import sqlite3

import app.database.connection as database_connection
import pytest
from app.database import (
    MeasurementCorrectionRequest,
    MeasurementCorrectionRequestEvent,
    UnitOfWork,
)
from app.database.migrations import runner
from app.services.measurement_correction_service import MeasurementCorrectionService
from app.services.measurement_observation_service import MeasurementObservationService
from app.services.measurement_quality_review_service import (
    MeasurementQualityReviewService,
)
from app.services.measurement_query_service import (
    AmbiguousMeasurementError,
    MeasurementQueryService,
)


@pytest.fixture()
def query_context(tmp_path, monkeypatch):
    database_path = tmp_path / "measurement-queries-test.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    database_connection.initialise_database()

    with database_connection.get_connection() as connection:
        farm_id = connection.execute(
            "INSERT INTO farms (farm_name, farmer_name) VALUES (?, ?)",
            ("Query Farm", "Test Farmer"),
        ).lastrowid
        flock_id = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch A", "Chicken", 100),
        ).lastrowid
        other_flock_id = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch B", "Chicken", 100),
        ).lastrowid
        daily_record_id = connection.execute(
            """
            INSERT INTO daily_records (flock_id, record_date, mortality)
            VALUES (?, ?, 0)
            """,
            (flock_id, "2026-11-24"),
        ).lastrowid

    with database_connection.get_connection() as connection:
        runner.migrate(connection)

    return {
        "database_path": database_path,
        "flock_id": flock_id,
        "other_flock_id": other_flock_id,
        "daily_record_id": daily_record_id,
        "observations": MeasurementObservationService(),
        "corrections": MeasurementCorrectionService(),
        "reviews": MeasurementQualityReviewService(),
        "queries": MeasurementQueryService(),
    }


def _create_observation(
    context,
    *,
    metric_name="feed_kg",
    value=4.5,
    record_date="2026-11-24",
    flock_id=None,
    observed_at=None,
):
    return context["observations"].create_observation(
        flock_id=flock_id or context["flock_id"],
        record_date=record_date,
        metric_name=metric_name,
        value_numeric=value,
        daily_record_id=(
            context["daily_record_id"]
            if record_date == "2026-11-24" and flock_id is None
            else None
        ),
        observed_at=observed_at,
    )


def _insert_raw_observation(
    context,
    *,
    observation_id,
    quality_status,
    record_date="2026-11-24",
    value=4.5,
    metric_name="feed_kg",
    unit="kg",
    observed_at=None,
):
    absence_statuses = {
        "not_recorded",
        "not_measured",
        "not_applicable",
        "device_unavailable",
    }
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_observations (
                observation_id, flock_id, record_date, metric_name,
                value_numeric, unit, observed_at, recorded_at, source_type,
                quality_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation_id,
                context["flock_id"],
                record_date,
                metric_name,
                None if quality_status in absence_statuses else value,
                unit,
                observed_at,
                "2026-11-24T12:00:00Z",
                "manual_entry",
                quality_status,
            ),
        )
    return observation_id


def _current_ids(context, *, record_date="2026-11-24", metric_name="feed_kg"):
    rows = context["queries"].list_accepted_measurements(
        flock_id=context["flock_id"],
        metric_name=metric_name,
        record_date=record_date,
    )
    return [row["observation_id"] for row in rows]


def _snapshot(database_path):
    with sqlite3.connect(database_path) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in (
                "measurement_observations",
                "measurement_correction_requests",
                "measurement_correction_request_events",
                "measurement_quality_review_events",
            )
        }


def _insert_identified_request_and_rejection(
    request_id,
    event_id,
    target_observation_id,
    *,
    proposed_value,
    requested_at,
    event_at,
):
    with UnitOfWork() as unit_of_work:
        unit_of_work.measurement_correction_requests.create(
            MeasurementCorrectionRequest(
                request_id=request_id,
                target_observation_id=target_observation_id,
                proposed_value_numeric=proposed_value,
                correction_reason=f"Proposal {request_id}",
                requested_at=requested_at,
                requested_by_user_id=f"requester-{request_id}",
            )
        )
        unit_of_work.measurement_correction_request_events.create(
            MeasurementCorrectionRequestEvent(
                event_id=event_id,
                request_id=request_id,
                outcome="rejected",
                outcome_reason=f"Decision {request_id}",
                event_at=event_at,
                reviewed_by_user_id=f"reviewer-{event_id}",
            )
        )


def test_accepted_queries_filter_exact_scope_and_include_independent_same_day_rows(
    query_context,
):
    first = _create_observation(query_context, value=3.0)
    second = _create_observation(query_context, value=6.0)
    _create_observation(query_context, metric_name="water_litres", value=7.0)
    _create_observation(
        query_context,
        value=8.0,
        record_date="2026-11-25",
    )
    _create_observation(
        query_context,
        value=9.0,
        flock_id=query_context["other_flock_id"],
    )

    same_day = query_context["queries"].list_accepted_measurements(
        flock_id=query_context["flock_id"],
        metric_name="feed_kg",
        record_date="2026-11-24",
    )

    assert {row["observation_id"] for row in same_day} == {first, second}
    assert all(row["effective_quality_status"] == "observed" for row in same_day)


def test_accepted_queries_include_accepted_pending_only(query_context):
    observed = _create_observation(query_context)
    accepted_pending = _insert_raw_observation(
        query_context,
        observation_id="accepted-candidate",
        quality_status="pending_validation",
    )
    pending = _insert_raw_observation(
        query_context,
        observation_id="unreviewed-candidate",
        quality_status="pending_validation",
    )
    rejected = _insert_raw_observation(
        query_context,
        observation_id="rejected-candidate",
        quality_status="pending_validation",
    )
    invalid = _insert_raw_observation(
        query_context,
        observation_id="invalid-observation",
        quality_status="invalid",
    )
    absences = [
        _insert_raw_observation(
            query_context,
            observation_id=f"absence-{status}",
            quality_status=status,
        )
        for status in (
            "not_recorded",
            "not_measured",
            "not_applicable",
            "device_unavailable",
        )
    ]
    query_context["reviews"].accept_observation(
        accepted_pending, review_reason="Verified"
    )
    query_context["reviews"].reject_observation(rejected, review_reason="Not supported")

    results = _current_ids(query_context)

    assert set(results) == {observed, accepted_pending}
    assert pending not in results
    assert invalid not in results
    assert set(absences).isdisjoint(results)
    accepted_candidate = query_context["queries"].get_accepted_measurement_by_id(
        accepted_pending
    )
    assert accepted_candidate["quality_status"] == "pending_validation"
    assert accepted_candidate["effective_quality_status"] == "observed"
    assert query_context["queries"].get_accepted_measurement_by_id(pending) is None


def test_superseded_target_is_excluded_and_accepted_correction_is_included(
    query_context,
):
    target_id = _create_observation(query_context)
    request_id = query_context["corrections"].submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="Corrected transcription",
    )
    before_approval = _current_ids(query_context)
    result = query_context["corrections"].approve_correction_request(request_id)

    after_approval = _current_ids(query_context)

    assert before_approval == [target_id]
    assert result.created_observation_id in after_approval
    assert target_id not in after_approval
    assert query_context["queries"].get_accepted_measurement_by_id(target_id) is None


def test_pending_and_rejected_requests_do_not_change_accepted_results(query_context):
    target_id = _create_observation(query_context)
    before = _current_ids(query_context)
    pending_request = query_context["corrections"].submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=5.0,
        correction_reason="Pending proposal",
    )
    rejected_request = query_context["corrections"].submit_correction_request(
        target_observation_id=target_id,
        proposed_value_numeric=6.0,
        correction_reason="Rejected proposal",
    )
    query_context["corrections"].reject_correction_request(
        rejected_request, rejection_reason="Rejected for test"
    )

    assert (
        query_context["queries"].get_correction_request_status(pending_request)
        == "pending"
    )
    assert (
        query_context["queries"].get_correction_request_status(rejected_request)
        == "rejected"
    )
    assert _current_ids(query_context) == before
    assert (
        query_context["queries"].get_accepted_measurement_by_id(target_id) is not None
    )


def test_date_range_is_inclusive_and_single_result_has_explicit_ambiguity(
    query_context,
):
    _create_observation(query_context, record_date="2026-11-23")
    start = _create_observation(query_context, record_date="2026-11-24")
    end = _create_observation(query_context, record_date="2026-11-25")
    _create_observation(query_context, record_date="2026-11-26")
    rows = query_context["queries"].list_accepted_measurements_in_range(
        flock_id=query_context["flock_id"],
        metric_name="feed_kg",
        start_date="2026-11-24",
        end_date="2026-11-25",
    )
    assert {row["observation_id"] for row in rows} == {start, end}

    assert (
        query_context["queries"].get_single_accepted_measurement(
            flock_id=query_context["flock_id"],
            metric_name="feed_kg",
            record_date="2026-11-22",
        )
        is None
    )
    assert (
        query_context["queries"].get_single_accepted_measurement(
            flock_id=query_context["flock_id"],
            metric_name="feed_kg",
            record_date="2026-11-24",
        )["observation_id"]
        == start
    )

    duplicate = _create_observation(query_context, value=99.0, record_date="2026-11-24")
    with pytest.raises(AmbiguousMeasurementError) as error:
        query_context["queries"].get_single_accepted_measurement(
            flock_id=query_context["flock_id"],
            metric_name="feed_kg",
            record_date="2026-11-24",
        )
    assert set(error.value.observation_ids) == {start, duplicate}


def test_request_status_derivation_includes_all_terminal_outcomes(query_context):
    target = _create_observation(query_context, record_date="2026-11-23")
    pending = query_context["corrections"].submit_correction_request(
        target_observation_id=target,
        proposed_value_numeric=5.0,
        correction_reason="Pending",
    )
    rejected = query_context["corrections"].submit_correction_request(
        target_observation_id=target,
        proposed_value_numeric=6.0,
        correction_reason="Rejected",
    )
    approved = query_context["corrections"].submit_correction_request(
        target_observation_id=target,
        proposed_value_numeric=7.0,
        correction_reason="Approved",
    )
    invalidated = query_context["corrections"].submit_correction_request(
        target_observation_id=target,
        proposed_value_numeric=8.0,
        correction_reason="Sibling",
    )
    assert query_context["queries"].get_correction_request_status(pending) == "pending"
    query_context["corrections"].reject_correction_request(
        rejected, rejection_reason="No"
    )
    query_context["corrections"].approve_correction_request(approved)

    assert (
        query_context["queries"].get_correction_request_status(pending) == "invalidated"
    )
    assert (
        query_context["queries"].get_correction_request_status(rejected) == "rejected"
    )
    assert (
        query_context["queries"].get_correction_request_status(approved) == "approved"
    )
    assert (
        query_context["queries"].get_correction_request_status(invalidated)
        == "invalidated"
    )
    assert query_context["queries"].get_correction_request_status("missing") is None


def test_audit_history_traverses_complete_chain_from_any_node_and_is_read_only(
    query_context,
):
    original_id = _insert_raw_observation(
        query_context,
        observation_id="audit-original",
        quality_status="pending_validation",
        observed_at="2099-01-01T00:00:00Z",
    )
    query_context["reviews"].accept_observation(
        original_id, review_reason="Original source reviewed"
    )
    _insert_identified_request_and_rejection(
        "request-z",
        "event-z",
        original_id,
        proposed_value=8.0,
        requested_at="2026-11-24T14:00:00Z",
        event_at="2026-11-24T15:00:00Z",
    )
    _insert_identified_request_and_rejection(
        "request-a",
        "event-a",
        original_id,
        proposed_value=9.0,
        requested_at="2026-11-24T14:00:00Z",
        event_at="2026-11-24T15:00:00Z",
    )

    rejected_request = query_context["corrections"].submit_correction_request(
        target_observation_id=original_id,
        proposed_value_numeric=5.0,
        correction_reason="Old proposal",
    )
    query_context["corrections"].reject_correction_request(
        rejected_request, rejection_reason="Prior review rejected"
    )
    accepted_request = query_context["corrections"].submit_correction_request(
        target_observation_id=original_id,
        proposed_value_numeric=6.0,
        correction_reason="Correct first reading",
    )
    sibling_request = query_context["corrections"].submit_correction_request(
        target_observation_id=original_id,
        proposed_value_numeric=6.5,
        correction_reason="Sibling proposal",
    )
    first_correction = (
        query_context["corrections"]
        .approve_correction_request(accepted_request)
        .created_observation_id
    )
    second_request = query_context["corrections"].submit_correction_request(
        target_observation_id=first_correction,
        proposed_value_numeric=7.0,
        correction_reason="Corrected follow-up",
    )
    latest_correction = (
        query_context["corrections"]
        .approve_correction_request(second_request)
        .created_observation_id
    )
    pending_latest_request = query_context["corrections"].submit_correction_request(
        target_observation_id=latest_correction,
        proposed_value_numeric=7.5,
        correction_reason="Pending latest proposal",
    )

    before = _snapshot(query_context["database_path"])
    queries = query_context["queries"]
    from_original = queries.get_measurement_audit_history(original_id)
    from_intermediate = queries.get_measurement_audit_history(first_correction)
    from_latest = queries.get_measurement_audit_history(latest_correction)
    after = _snapshot(query_context["database_path"])

    expected_chain = (original_id, first_correction, latest_correction)
    assert (
        tuple(row["observation_id"] for row in from_original.observations)
        == expected_chain
    )
    assert (
        tuple(row["observation_id"] for row in from_intermediate.observations)
        == expected_chain
    )
    assert (
        tuple(row["observation_id"] for row in from_latest.observations)
        == expected_chain
    )
    assert from_original.observations[0]["quality_status"] == "pending_validation"
    assert from_original.observations[0]["effective_quality_status"] == "observed"
    assert [row["value_numeric"] for row in from_original.observations] == [
        4.5,
        6.0,
        7.0,
    ]
    assert all(row["unit"] == "kg" for row in from_original.observations)
    assert all(
        row["source_type"] == "manual_entry" for row in from_original.observations
    )
    assert from_original.observations[0]["observed_at"] == "2099-01-01T00:00:00Z"
    assert from_original.observations[0]["recorded_at"].endswith("Z")
    assert all(
        row["observed_at"] == "2099-01-01T00:00:00Z"
        for row in from_original.observations
    )
    assert from_original.observations[0]["supersedes_observation_id"] is None
    assert (
        from_original.observations[-1]["supersedes_observation_id"] == first_correction
    )
    assert from_original.observations[-1]["correction_reason"] == "Corrected follow-up"
    assert from_original.quality_review_events[0]["decision"] == "accepted"
    assert [event["event_id"] for event in from_original.correction_events[:2]] == [
        "event-a",
        "event-z",
    ]
    assert [row["request_id"] for row in from_original.correction_requests[:2]] == [
        "request-a",
        "request-z",
    ]
    assert (
        from_original.correction_events[0]["reviewed_by_user_id"] == "reviewer-event-a"
    )
    assert from_original.correction_events[0]["outcome_reason"] == "Decision request-a"
    assert any(
        row["request_id"] == "request-a" for row in from_original.correction_requests
    )
    assert any(
        row["requested_by_user_id"] == "requester-request-a"
        for row in from_original.correction_requests
    )
    assert any(
        row["request_id"] == rejected_request and row["request_status"] == "rejected"
        for row in from_original.correction_requests
    )
    assert any(
        row["request_id"] == accepted_request and row["request_status"] == "approved"
        for row in from_original.correction_requests
    )
    assert any(
        row["request_id"] == sibling_request and row["request_status"] == "invalidated"
        for row in from_original.correction_requests
    )
    assert any(
        row["request_id"] == pending_latest_request
        and row["request_status"] == "pending"
        for row in from_original.correction_requests
    )
    assert all(
        row["requested_at"].endswith("Z") for row in from_original.correction_requests
    )
    assert all(
        event["event_at"].endswith("Z") for event in from_original.correction_events
    )
    assert all(
        event["created_observation_id"] is None
        or event["created_observation_id"] in expected_chain
        for event in from_original.correction_events
    )
    assert any(
        event["outcome"] == "approved"
        and event["created_observation_id"] == first_correction
        for event in from_original.correction_events
    )
    assert before == after


def test_audit_history_includes_quality_rejection_and_unknown_id_errors(query_context):
    rejected_candidate = _insert_raw_observation(
        query_context,
        observation_id="audit-rejected-candidate",
        quality_status="pending_validation",
    )
    query_context["reviews"].reject_observation(
        rejected_candidate,
        review_reason="Source value could not be verified",
    )

    audit = query_context["queries"].get_measurement_audit_history(rejected_candidate)

    assert len(audit.observations) == 1
    assert audit.observations[0]["quality_status"] == "pending_validation"
    assert audit.observations[0]["effective_quality_status"] == "invalid"
    assert audit.quality_review_events[0]["decision"] == "rejected"
    assert (
        audit.quality_review_events[0]["review_reason"]
        == "Source value could not be verified"
    )
    with pytest.raises(ValueError, match="does not exist"):
        query_context["queries"].get_measurement_audit_history("unknown-observation")


def test_audit_history_returns_stored_quality_reviewer_identity(query_context):
    observation_id = _insert_raw_observation(
        query_context,
        observation_id="identified-review-candidate",
        quality_status="pending_validation",
    )
    with database_connection.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurement_quality_review_events (
                event_id, observation_id, decision, review_reason,
                reviewed_by_user_id, reviewed_at
            ) VALUES (?, ?, 'accepted', ?, ?, ?)
            """,
            (
                "identified-quality-event",
                observation_id,
                "Reviewer identity fixture",
                "reviewer-42",
                "2026-11-24T14:00:00Z",
            ),
        )

    audit = query_context["queries"].get_measurement_audit_history(observation_id)

    assert audit.quality_review_events[0]["event_id"] == "identified-quality-event"
    assert audit.quality_review_events[0]["reviewed_by_user_id"] == "reviewer-42"
    assert audit.quality_review_events[0]["reviewed_at"] == "2026-11-24T14:00:00Z"


def test_query_uow_repositories_share_connection_and_do_not_mutate_rows(query_context):
    observation_id = _create_observation(query_context)
    before = _snapshot(query_context["database_path"])
    with UnitOfWork() as unit_of_work:
        assert unit_of_work.measurement_queries._connection is unit_of_work.connection
        assert (
            unit_of_work.measurement_observations._connection is unit_of_work.connection
        )
        unit_of_work.measurement_queries.get_current_accepted_by_id(observation_id)
    assert _snapshot(query_context["database_path"]) == before
