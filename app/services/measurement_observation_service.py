"""Application service for validated manual measurement observations."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from app.database import (
    MeasurementObservation,
    MeasurementObservationRepository,
    UnitOfWork,
)

# Canonical units are owned here; callers cannot provide or override a unit.
_METRIC_UNITS = {
    "mortality": "birds",
    "feed_kg": "kg",
    "water_litres": "litres",
    "average_weight_kg": "kg_per_bird",
    "temperature_c": "degrees_celsius",
    "humidity_percent": "percent_relative_humidity",
}


class MeasurementObservationService:
    """Create and retrieve append-only, provenance-aware observations.

    This first service increment deliberately supports only manually entered,
    observed values. It does not implement imports, sensors, system-generated
    observations, quality-review transitions, corrections, or backfill.
    """

    def __init__(
        self,
        repository: MeasurementObservationRepository | None = None,
        unit_of_work_factory: Callable[[], UnitOfWork] = UnitOfWork,
    ) -> None:
        self.repository = repository or MeasurementObservationRepository()
        self.unit_of_work_factory = unit_of_work_factory

    def create_observation(
        self,
        *,
        flock_id: int,
        record_date: date | str,
        metric_name: str,
        value_numeric: int | float,
        daily_record_id: int | None = None,
        observed_at: datetime | str | None = None,
        notes: str | None = None,
    ) -> str:
        """Validate and insert one manual observation in a write transaction.

        The metric's canonical unit, UUID and UTC recording timestamp are
        assigned by the service. Observation time remains NULL unless the
        caller supplies a timezone-aware timestamp.
        """
        self._validate_positive_id(flock_id, "Flock ID")
        if daily_record_id is not None:
            self._validate_positive_id(daily_record_id, "Daily record ID")

        record_date_text = self._normalise_record_date(record_date)
        unit = self._metric_unit(metric_name)
        value = self._validate_value(metric_name, value_numeric)
        observed_at_text = self._normalise_observed_at(observed_at)

        if notes is not None and not isinstance(notes, str):
            raise ValueError("Notes must be text or None.")
        notes_text = notes.strip() if notes is not None else None
        notes_text = notes_text or None

        observation = MeasurementObservation(
            observation_id=str(uuid4()),
            flock_id=flock_id,
            daily_record_id=daily_record_id,
            record_date=record_date_text,
            metric_name=metric_name,
            value_numeric=value,
            unit=unit,
            observed_at=observed_at_text,
            recorded_at=self._utc_now(),
            source_type="manual_entry",
            quality_status="observed",
            notes=notes_text,
        )

        # A single BEGIN IMMEDIATE transaction protects the parent checks and
        # insert. No migration or database initialisation is run implicitly.
        with self.unit_of_work_factory() as unit_of_work:
            flock = unit_of_work.flocks.get_by_id(flock_id)
            if flock is None:
                raise ValueError(f"Flock with ID {flock_id} does not exist.")

            if daily_record_id is not None:
                daily_record = unit_of_work.daily_records.get_by_id(daily_record_id)
                if daily_record is None:
                    raise ValueError(
                        f"Daily record with ID {daily_record_id} does not exist."
                    )
                if daily_record["flock_id"] != flock_id:
                    raise ValueError(
                        "Daily record does not belong to the specified flock."
                    )
                if daily_record["record_date"] != record_date_text:
                    raise ValueError(
                        "Observation date must match its linked daily record."
                    )

            return unit_of_work.measurement_observations.create(observation)

    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        """Return an observation by ID."""
        return self.repository.get_by_id(observation_id)

    def list_flock_observations(self, flock_id: int) -> list[dict[str, Any]]:
        """Return a flock's observation history."""
        self._validate_positive_id(flock_id, "Flock ID")
        return self.repository.get_by_flock(flock_id)

    def list_daily_record_observations(
        self, daily_record_id: int
    ) -> list[dict[str, Any]]:
        """Return observations associated with a legacy daily-record row."""
        self._validate_positive_id(daily_record_id, "Daily record ID")
        return self.repository.get_by_daily_record(daily_record_id)

    def list_metric_observations(
        self,
        *,
        flock_id: int,
        metric_name: str,
        start_date: date | str,
        end_date: date | str,
    ) -> list[dict[str, Any]]:
        """Return a metric's observations over an inclusive reporting period."""
        self._validate_positive_id(flock_id, "Flock ID")
        self._metric_unit(metric_name)
        start = self._normalise_record_date(start_date)
        end = self._normalise_record_date(end_date)
        if start > end:
            raise ValueError("Start date must not be after end date.")
        return self.repository.get_by_flock_metric_date_range(
            flock_id, metric_name, start, end
        )

    @staticmethod
    def _validate_positive_id(value: int, label: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{label} must be a positive integer.")

    @staticmethod
    def _metric_unit(metric_name: str) -> str:
        try:
            return _METRIC_UNITS[metric_name]
        except (KeyError, TypeError):
            raise ValueError(
                f"Metric must be one of: {', '.join(_METRIC_UNITS)}."
            ) from None

    @staticmethod
    def _normalise_record_date(value: date | str) -> str:
        if isinstance(value, datetime):
            raise ValueError("Record date must be a date, not a datetime.")
        if isinstance(value, date):
            return value.isoformat()
        if not isinstance(value, str):
            raise ValueError("Record date must be an ISO calendar date.")
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise ValueError("Record date must use YYYY-MM-DD format.") from None
        if parsed.isoformat() != value:
            raise ValueError("Record date must use YYYY-MM-DD format.")
        return value

    @staticmethod
    def _validate_value(metric_name: str, value: int | float) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Observation value must be a finite number.")
        try:
            numeric_value = float(value)
        except OverflowError:
            raise ValueError("Observation value must be a finite number.") from None
        if not math.isfinite(numeric_value):
            raise ValueError("Observation value must be a finite number.")

        if metric_name == "mortality":
            if not isinstance(value, int):
                raise ValueError("Mortality must be a whole-number count of birds.")
            if value < 0:
                raise ValueError("Mortality cannot be negative.")
            if value > 2**63 - 1:
                raise ValueError("Mortality exceeds SQLite's supported integer range.")
        elif metric_name in {"feed_kg", "water_litres"} and value < 0:
            raise ValueError(f"{metric_name} cannot be negative.")
        elif metric_name == "average_weight_kg" and value <= 0:
            raise ValueError("Average weight must be greater than zero.")
        elif metric_name == "humidity_percent" and not 0 <= value <= 100:
            raise ValueError("Humidity must be between 0 and 100 percent.")
        # Temperature intentionally has no new biological range restriction.

        return value if metric_name == "mortality" else numeric_value

    @staticmethod
    def _normalise_observed_at(value: datetime | str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(
                    "Observed-at timestamp must be valid ISO 8601."
                ) from None
        elif isinstance(value, datetime):
            parsed = value
        else:
            raise ValueError(
                "Observed-at timestamp must be a datetime, ISO 8601 string or None."
            )

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Observed-at timestamp must include a timezone.")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
