"""Read-only accepted-measurement and audit query services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from app.database import MeasurementAuditHistory, UnitOfWork
from app.services.measurement_observation_service import MeasurementObservationService


class AmbiguousMeasurementError(ValueError):
    """Raised when a single accepted value is requested but several exist."""

    def __init__(self, observation_ids: tuple[str, ...]) -> None:
        self.observation_ids = observation_ids
        super().__init__(
            "Multiple accepted measurements match this flock, metric and date: "
            + ", ".join(observation_ids)
        )


class MeasurementQueryService:
    """Retrieve accepted observation leaves and structured audit history."""

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork] = UnitOfWork,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory

    def list_accepted_measurements(
        self,
        *,
        flock_id: int,
        metric_name: str,
        record_date: date | str,
    ) -> list[dict[str, Any]]:
        """Return all current accepted leaves for one exact flock/metric/date."""
        self._validate_scope(flock_id, metric_name)
        day = MeasurementObservationService._normalise_record_date(record_date)
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_queries.list_current_accepted(
                flock_id=flock_id,
                metric_name=metric_name,
                record_date=day,
            )

    def list_accepted_measurements_in_range(
        self,
        *,
        flock_id: int,
        metric_name: str,
        start_date: date | str,
        end_date: date | str,
    ) -> list[dict[str, Any]]:
        """Return all current accepted leaves in an inclusive date range."""
        self._validate_scope(flock_id, metric_name)
        start = MeasurementObservationService._normalise_record_date(start_date)
        end = MeasurementObservationService._normalise_record_date(end_date)
        if start > end:
            raise ValueError("Start date must not be after end date.")
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_queries.list_current_accepted(
                flock_id=flock_id,
                metric_name=metric_name,
                start_date=start,
                end_date=end,
            )

    def get_accepted_measurement_by_id(
        self, observation_id: str
    ) -> dict[str, Any] | None:
        """Return the exact observation only if it is an accepted current leaf."""
        self._require_text(observation_id, "Observation ID")
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_queries.get_current_accepted_by_id(
                observation_id
            )

    def get_single_accepted_measurement(
        self,
        *,
        flock_id: int,
        metric_name: str,
        record_date: date | str,
    ) -> dict[str, Any] | None:
        """Return None, one measurement, or raise an explicit ambiguity error."""
        matches = self.list_accepted_measurements(
            flock_id=flock_id,
            metric_name=metric_name,
            record_date=record_date,
        )
        if len(matches) > 1:
            raise AmbiguousMeasurementError(
                tuple(row["observation_id"] for row in matches)
            )
        return matches[0] if matches else None

    def get_correction_request_status(self, request_id: str) -> str | None:
        """Derive pending/terminal state without a mutable status column."""
        self._require_text(request_id, "Correction request ID")
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_queries.get_correction_request_status(
                request_id
            )

    def get_measurement_audit_history(
        self, observation_id: str
    ) -> MeasurementAuditHistory:
        """Return the complete correction chain and its review/request history."""
        self._require_text(observation_id, "Observation ID")
        with self.unit_of_work_factory() as unit_of_work:
            observations = (
                unit_of_work.measurement_queries.get_connected_observation_chain(
                    observation_id
                )
            )
            if not observations:
                raise ValueError(
                    f"Observation with ID {observation_id} does not exist."
                )

            ordered_observations = self._order_correction_chain(observations)
            observation_ids = tuple(
                row["observation_id"] for row in ordered_observations
            )
            query_repository = unit_of_work.measurement_queries
            request_rows = query_repository.get_correction_history_for_observations(
                observation_ids
            )
            review_events = query_repository.get_quality_review_events_for_observations(
                observation_ids
            )

            requests: list[dict[str, Any]] = []
            correction_events: list[dict[str, Any]] = []
            for row in request_rows:
                request = {
                    key: value
                    for key, value in row.items()
                    if not key.startswith("terminal_")
                    and key != "created_observation_id"
                }
                requests.append(request)
                if row["terminal_event_id"] is not None:
                    correction_events.append(
                        {
                            "event_id": row["terminal_event_id"],
                            "request_id": row["request_id"],
                            "outcome": row["terminal_outcome"],
                            "outcome_reason": row["terminal_outcome_reason"],
                            "reviewed_by_user_id": row["terminal_reviewer_id"],
                            "event_at": row["terminal_event_at"],
                            "created_observation_id": row["created_observation_id"],
                        }
                    )

            correction_events.sort(
                key=lambda event: (event["event_at"], event["event_id"])
            )
            return MeasurementAuditHistory(
                queried_observation_id=observation_id,
                observations=tuple(ordered_observations),
                correction_requests=tuple(requests),
                correction_events=tuple(correction_events),
                quality_review_events=tuple(review_events),
            )

    @staticmethod
    def _validate_scope(flock_id: int, metric_name: str) -> None:
        MeasurementObservationService._validate_positive_id(flock_id, "Flock ID")
        MeasurementObservationService._metric_unit(metric_name)

    @staticmethod
    def _require_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be non-empty text.")
        return value.strip()

    @staticmethod
    def _order_correction_chain(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_id = {row["observation_id"]: row for row in observations}
        children: dict[str, list[str]] = {}
        roots = []
        for row in observations:
            parent_id = row["supersedes_observation_id"]
            if parent_id in by_id:
                children.setdefault(parent_id, []).append(row["observation_id"])
            else:
                roots.append(row["observation_id"])

        if len(roots) != 1:
            raise RuntimeError("Correction history does not form one connected chain.")

        ordered = []
        current_id = roots[0]
        while current_id is not None:
            ordered.append(by_id[current_id])
            successors = children.get(current_id, [])
            if len(successors) > 1:
                raise RuntimeError("Correction history contains multiple successors.")
            current_id = successors[0] if successors else None

        if len(ordered) != len(observations):
            raise RuntimeError(
                "Correction history contains a cycle or disconnected row."
            )
        return ordered
