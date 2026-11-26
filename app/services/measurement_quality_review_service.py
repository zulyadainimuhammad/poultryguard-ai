"""Application service for operator-recorded measurement quality decisions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.database import (
    EffectiveMeasurementQualityStatus,
    MeasurementQualityReviewEvent,
    UnitOfWork,
)


class MeasurementQualityReviewService:
    """Record one immutable quality decision for a pending observation.

    This local workflow records an operator-entered decision. It does not
    authenticate reviewers or provide secure independent approval.
    """

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork] = UnitOfWork,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory

    def accept_observation(self, observation_id: str, *, review_reason: str) -> str:
        """Accept one pending observation without changing its source row."""
        return self._record_review(
            observation_id, decision="accepted", review_reason=review_reason
        )

    def reject_observation(self, observation_id: str, *, review_reason: str) -> str:
        """Reject one pending observation without changing its source row."""
        return self._record_review(
            observation_id, decision="rejected", review_reason=review_reason
        )

    def get_effective_quality_status(
        self, observation_id: str
    ) -> EffectiveMeasurementQualityStatus:
        """Return raw and derived statuses as separately named values."""
        self._require_text(observation_id, "Observation ID")
        with self.unit_of_work_factory() as unit_of_work:
            observation = unit_of_work.measurement_observations.get_by_id(
                observation_id
            )
            if observation is None:
                raise ValueError(
                    f"Observation with ID {observation_id} does not exist."
                )

            raw_status = observation["quality_status"]
            review_event = (
                unit_of_work.measurement_quality_review_events.get_by_observation_id(
                    observation_id
                )
            )
            effective_status = raw_status
            if raw_status == "pending_validation" and review_event is not None:
                if review_event["decision"] == "accepted":
                    effective_status = "observed"
                elif review_event["decision"] == "rejected":
                    effective_status = "invalid"

            return EffectiveMeasurementQualityStatus(
                observation_id=observation_id,
                raw_quality_status=raw_status,
                effective_quality_status=effective_status,
            )

    def _record_review(
        self, observation_id: str, *, decision: str, review_reason: str
    ) -> str:
        self._require_text(observation_id, "Observation ID")
        reason = self._require_text(review_reason, "Review reason")

        with self.unit_of_work_factory() as unit_of_work:
            observation = unit_of_work.measurement_observations.get_by_id(
                observation_id
            )
            if observation is None:
                raise ValueError(
                    f"Observation with ID {observation_id} does not exist."
                )
            if observation["quality_status"] != "pending_validation":
                raise ValueError(
                    "Only raw pending_validation observations can be reviewed."
                )
            if (
                unit_of_work.measurement_quality_review_events.get_by_observation_id(
                    observation_id
                )
                is not None
            ):
                raise ValueError(
                    f"Observation {observation_id} has already been reviewed."
                )

            event = MeasurementQualityReviewEvent(
                event_id=str(uuid4()),
                observation_id=observation_id,
                decision=decision,
                review_reason=reason,
                reviewed_at=self._utc_now(),
            )
            return unit_of_work.measurement_quality_review_events.create(event)

    @staticmethod
    def _require_text(value: str, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be non-empty text.")
        return value.strip()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
