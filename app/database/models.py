from dataclasses import dataclass


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
