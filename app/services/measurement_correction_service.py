"""Application service for correction requests and terminal decisions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.database import (
    CorrectionDecisionResult,
    MeasurementCorrectionRequest,
    MeasurementCorrectionRequestEvent,
    MeasurementObservation,
    UnitOfWork,
)
from app.services.measurement_observation_service import MeasurementObservationService


class MeasurementCorrectionService:
    """Record and decide value-only requests against exact observations.

    This local workflow records operator-entered decisions. It does not
    authenticate actors or provide secure independent approval.
    """

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork] = UnitOfWork,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory

    def submit_correction_request(
        self,
        *,
        target_observation_id: str,
        proposed_value_numeric: int | float,
        correction_reason: str,
    ) -> str:
        """Create a pending request without changing measurement history."""
        self._required_text(target_observation_id, "Target observation ID")
        reason = self._required_text(correction_reason, "Correction reason")

        with self.unit_of_work_factory() as unit_of_work:
            target = unit_of_work.measurement_observations.get_by_id(
                target_observation_id
            )
            if target is None:
                raise ValueError(
                    f"Observation with ID {target_observation_id} does not exist."
                )

            eligible = unit_of_work.measurement_correction_requests.get_eligible_target(
                target_observation_id
            )
            if eligible is None:
                raise ValueError("Target observation is not eligible for correction.")

            value = MeasurementObservationService._validate_value(
                target["metric_name"], proposed_value_numeric
            )
            if float(value) == float(target["value_numeric"]):
                raise ValueError(
                    "Proposed value is unchanged; a correction is a no-op."
                )

            request = MeasurementCorrectionRequest(
                request_id=str(uuid4()),
                target_observation_id=target_observation_id,
                proposed_value_numeric=value,
                correction_reason=reason,
                requested_at=self._utc_now(),
            )
            return unit_of_work.measurement_correction_requests.create(request)

    def approve_correction_request(self, request_id: str) -> CorrectionDecisionResult:
        """Approve a pending request or invalidate it if its target is stale."""
        self._required_text(request_id, "Correction request ID")
        with self.unit_of_work_factory() as unit_of_work:
            request = self._get_pending_request(unit_of_work, request_id)
            target = unit_of_work.measurement_observations.get_by_id(
                request["target_observation_id"]
            )
            eligible = unit_of_work.measurement_correction_requests.get_eligible_target(
                request["target_observation_id"]
            )
            if target is None or eligible is None:
                return self._invalidate(
                    unit_of_work,
                    request_id,
                    "Target observation is no longer an eligible current observation.",
                )

            proposed_value = request["proposed_value_numeric"]
            # SQLite REAL affinity returns whole-number mortality proposals as
            # floats; restore the domain's integer type before shared validation.
            if (
                target["metric_name"] == "mortality"
                and isinstance(proposed_value, float)
                and proposed_value.is_integer()
            ):
                proposed_value = int(proposed_value)
            value = MeasurementObservationService._validate_value(
                target["metric_name"], proposed_value
            )
            if float(value) == float(target["value_numeric"]):
                raise ValueError(
                    "Proposed value is unchanged; a correction is a no-op."
                )

            observation_id = str(uuid4())
            event_id = str(uuid4())
            observation = MeasurementObservation(
                observation_id=observation_id,
                flock_id=target["flock_id"],
                daily_record_id=target["daily_record_id"],
                record_date=target["record_date"],
                metric_name=target["metric_name"],
                value_numeric=value,
                unit=target["unit"],
                observed_at=target["observed_at"],
                recorded_at=self._utc_now(),
                source_type="manual_entry",
                entered_by_user_id=request["requested_by_user_id"],
                quality_status="observed",
                supersedes_observation_id=target["observation_id"],
                correction_reason=request["correction_reason"],
            )
            unit_of_work.measurement_observations.create(observation)
            unit_of_work.measurement_correction_request_events.create(
                MeasurementCorrectionRequestEvent(
                    event_id=event_id,
                    request_id=request_id,
                    outcome="approved",
                    outcome_reason="Correction approved.",
                    event_at=self._utc_now(),
                    created_observation_id=observation_id,
                )
            )

            siblings = (
                unit_of_work.measurement_correction_requests.get_pending_by_target(
                    target["observation_id"]
                )
            )
            for sibling in siblings:
                if sibling["request_id"] == request_id:
                    continue
                self._insert_event(
                    unit_of_work,
                    request_id=sibling["request_id"],
                    outcome="invalidated",
                    reason=("Another correction request for this target was approved."),
                )

            return CorrectionDecisionResult(
                outcome="approved",
                event_id=event_id,
                created_observation_id=observation_id,
            )

    def reject_correction_request(
        self, request_id: str, *, rejection_reason: str
    ) -> CorrectionDecisionResult:
        """Reject a pending request without inserting an observation."""
        self._required_text(request_id, "Correction request ID")
        reason = self._required_text(rejection_reason, "Rejection reason")
        with self.unit_of_work_factory() as unit_of_work:
            request = self._get_pending_request(unit_of_work, request_id)
            eligible = unit_of_work.measurement_correction_requests.get_eligible_target(
                request["target_observation_id"]
            )
            if eligible is None:
                return self._invalidate(
                    unit_of_work,
                    request_id,
                    "Target observation is no longer an eligible current observation.",
                )
            return self._insert_event(
                unit_of_work,
                request_id=request_id,
                outcome="rejected",
                reason=reason,
            )

    def get_correction_request(self, request_id: str) -> dict | None:
        """Retrieve one request by its exact ID."""
        self._required_text(request_id, "Correction request ID")
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_correction_requests.get_by_id(request_id)

    def list_pending_correction_requests(
        self, target_observation_id: str
    ) -> list[dict]:
        """List pending requests for one exact observation ID."""
        self._required_text(target_observation_id, "Target observation ID")
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_correction_requests.get_pending_by_target(
                target_observation_id
            )

    def get_terminal_event(self, request_id: str) -> dict | None:
        """Return the terminal event for a request, if one exists."""
        self._required_text(request_id, "Correction request ID")
        with self.unit_of_work_factory() as unit_of_work:
            return unit_of_work.measurement_correction_request_events.get_by_request_id(
                request_id
            )

    @staticmethod
    def _get_pending_request(unit_of_work: UnitOfWork, request_id: str) -> dict:
        request = unit_of_work.measurement_correction_requests.get_by_id(request_id)
        if request is None:
            raise ValueError(f"Correction request with ID {request_id} does not exist.")
        if (
            unit_of_work.measurement_correction_request_events.get_by_request_id(
                request_id
            )
            is not None
        ):
            raise ValueError(
                f"Correction request {request_id} has already been decided."
            )
        return request

    def _invalidate(
        self, unit_of_work: UnitOfWork, request_id: str, reason: str
    ) -> CorrectionDecisionResult:
        return self._insert_event(
            unit_of_work,
            request_id=request_id,
            outcome="invalidated",
            reason=reason,
        )

    @staticmethod
    def _insert_event(
        unit_of_work: UnitOfWork,
        *,
        request_id: str,
        outcome: str,
        reason: str,
    ) -> CorrectionDecisionResult:
        event_id = str(uuid4())
        unit_of_work.measurement_correction_request_events.create(
            MeasurementCorrectionRequestEvent(
                event_id=event_id,
                request_id=request_id,
                outcome=outcome,
                outcome_reason=reason,
                event_at=MeasurementCorrectionService._utc_now(),
            )
        )
        return CorrectionDecisionResult(outcome=outcome, event_id=event_id)

    @staticmethod
    def _required_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be non-empty text.")
        return value.strip()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
