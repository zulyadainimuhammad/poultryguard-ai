from dataclasses import dataclass
from typing import Any


@dataclass
class Farm:
    farm_name: str
    farmer_name: str
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    production_type: str | None = None


@dataclass
class Flock:
    farm_id: int
    flock_name: str
    species: str
    production_type: str | None = None
    breed: str | None = None
    initial_count: int = 0
    stocking_date: str | None = None
    status: str = "active"


@dataclass
class DailyRecord:
    flock_id: int
    record_date: str
    feed_kg: float | None = None
    water_litres: float | None = None
    mortality: int = 0
    average_weight_kg: float | None = None
    temperature_c: float | None = None
    humidity_percent: float | None = None
    notes: str | None = None


@dataclass(frozen=True)
class MeasurementObservation:
    """An immutable, provenance-aware observation of one flock metric."""

    observation_id: str
    flock_id: int
    record_date: str
    metric_name: str
    value_numeric: int | float | None
    unit: str
    recorded_at: str
    daily_record_id: int | None = None
    observed_at: str | None = None
    source_type: str = "manual_entry"
    entered_by_user_id: str | None = None
    device_id: str | None = None
    import_batch_id: str | None = None
    source_reference: str | None = None
    calibration_reference: str | None = None
    calculation_method: str | None = None
    calculation_version: str | None = None
    quality_status: str = "observed"
    supersedes_observation_id: str | None = None
    correction_reason: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class MeasurementCorrectionRequest:
    """An immutable proposal to correct one exact observation."""

    request_id: str
    target_observation_id: str
    proposed_value_numeric: int | float
    correction_reason: str
    requested_at: str
    requested_by_user_id: str | None = None


@dataclass(frozen=True)
class MeasurementCorrectionRequestEvent:
    """One immutable terminal decision on a correction request."""

    event_id: str
    request_id: str
    outcome: str
    outcome_reason: str
    event_at: str
    created_observation_id: str | None = None
    reviewed_by_user_id: str | None = None


@dataclass(frozen=True)
class CorrectionDecisionResult:
    """The terminal result of approving, rejecting or invalidating a request."""

    outcome: str
    event_id: str
    created_observation_id: str | None = None


@dataclass(frozen=True)
class MeasurementQualityReviewEvent:
    """An immutable accept/reject decision for one pending observation."""

    event_id: str
    observation_id: str
    decision: str
    review_reason: str
    reviewed_at: str
    reviewed_by_user_id: str | None = None


@dataclass(frozen=True)
class EffectiveMeasurementQualityStatus:
    """Expose the immutable raw status separately from its derived status."""

    observation_id: str
    raw_quality_status: str
    effective_quality_status: str


@dataclass(frozen=True)
class MeasurementAuditHistory:
    """Structured read-only audit data for one correction chain."""

    queried_observation_id: str
    observations: tuple[dict[str, Any], ...]
    correction_requests: tuple[dict[str, Any], ...]
    correction_events: tuple[dict[str, Any], ...]
    quality_review_events: tuple[dict[str, Any], ...]
