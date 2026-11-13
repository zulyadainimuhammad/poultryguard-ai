from __future__ import annotations

from datetime import date
from typing import Any

from app.database import (
    DailyRecordRepository,
    FlockRepository,
)


class AnalyticsService:
    """Calculate farm and flock performance metrics."""

    def __init__(
        self,
        flock_repository: FlockRepository | None = None,
        daily_record_repository: DailyRecordRepository | None = None,
    ) -> None:
        self.flock_repository = flock_repository or FlockRepository()
        self.daily_record_repository = (
            daily_record_repository or DailyRecordRepository()
        )

    def get_flock_summary(self, flock_id: int) -> dict[str, Any]:
        """Return a summary of flock performance."""

        flock = self.flock_repository.get_by_id(flock_id)

        if flock is None:
            raise ValueError(f"Flock with ID {flock_id} was not found.")

        records = self.daily_record_repository.get_by_flock(flock_id)

        total_mortality = sum(
            self._number(record.get("mortality"))
            for record in records
        )

        current_flock_size = max(
            flock["initial_count"] - total_mortality,
            0,
        )

        mortality_rate = (
            (total_mortality / flock["initial_count"]) * 100
            if flock["initial_count"] > 0
            else 0.0
        )

        total_feed = sum(
            self._number(record.get("feed_kg"))
            for record in records
        )

        total_water = sum(
            self._number(record.get("water_litres"))
            for record in records
        )

        average_weight = self._average(
            record.get("average_weight_kg")
            for record in records
            if record.get("average_weight_kg") is not None
        )

        average_temperature = self._average(
            record.get("temperature_c")
            for record in records
            if record.get("temperature_c") is not None
        )

        average_humidity = self._average(
            record.get("humidity_percent")
            for record in records
            if record.get("humidity_percent") is not None
        )

        return {
            "flock_id": flock["id"],
            "flock_name": flock["flock_name"],
            "farm_id": flock["farm_id"],
            "species": flock["species"],
            "production_type": flock["production_type"],
            "breed": flock["breed"],
            "initial_count": flock["initial_count"],
            "current_flock_size": current_flock_size,
            "total_mortality": total_mortality,
            "mortality_rate_percent": round(mortality_rate, 2),
            "total_feed_kg": round(total_feed, 2),
            "total_water_litres": round(total_water, 2),
            "average_weight_kg": self._round_or_none(average_weight),
            "average_temperature_c": self._round_or_none(
                average_temperature
            ),
            "average_humidity_percent": self._round_or_none(
                average_humidity
            ),
            "record_count": len(records),
        }

    def get_daily_metrics(self, flock_id: int) -> list[dict[str, Any]]:
        """Return calculated metrics for each daily record."""

        flock = self.flock_repository.get_by_id(flock_id)

        if flock is None:
            raise ValueError(f"Flock with ID {flock_id} was not found.")

        records = self.daily_record_repository.get_by_flock(flock_id)

        metrics: list[dict[str, Any]] = []

        cumulative_mortality = 0

        for record in records:
            mortality = self._number(record.get("mortality"))
            cumulative_mortality += mortality

            current_flock_size = max(
                flock["initial_count"] - cumulative_mortality,
                0,
            )

            mortality_rate = (
                (cumulative_mortality / flock["initial_count"]) * 100
                if flock["initial_count"] > 0
                else 0.0
            )

            metrics.append(
                {
                    "record_id": record["id"],
                    "record_date": record["record_date"],
                    "feed_kg": round(
                        self._number(record.get("feed_kg")),
                        2,
                    ),
                    "water_litres": round(
                        self._number(record.get("water_litres")),
                        2,
                    ),
                    "mortality": mortality,
                    "cumulative_mortality": cumulative_mortality,
                    "current_flock_size": current_flock_size,
                    "mortality_rate_percent": round(
                        mortality_rate,
                        2,
                    ),
                    "average_weight_kg": self._round_or_none(
                        record.get("average_weight_kg")
                    ),
                    "temperature_c": self._round_or_none(
                        record.get("temperature_c")
                    ),
                    "humidity_percent": self._round_or_none(
                        record.get("humidity_percent")
                    ),
                    "notes": record.get("notes"),
                }
            )

        return metrics

    def get_metrics_by_date_range(
        self,
        flock_id: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Return daily metrics for a specified date range."""

        flock = self.flock_repository.get_by_id(flock_id)

        if flock is None:
            raise ValueError(f"Flock with ID {flock_id} was not found.")

        records = self.daily_record_repository.get_by_date_range(
            flock_id=flock_id,
            start_date=start_date,
            end_date=end_date,
        )

        return [
            {
                "record_id": record["id"],
                "record_date": record["record_date"],
                "feed_kg": round(
                    self._number(record.get("feed_kg")),
                    2,
                ),
                "water_litres": round(
                    self._number(record.get("water_litres")),
                    2,
                ),
                "mortality": self._number(
                    record.get("mortality")
                ),
                "average_weight_kg": self._round_or_none(
                    record.get("average_weight_kg")
                ),
                "temperature_c": self._round_or_none(
                    record.get("temperature_c")
                ),
                "humidity_percent": self._round_or_none(
                    record.get("humidity_percent")
                ),
                "notes": record.get("notes"),
            }
            for record in records
        ]

    @staticmethod
    def _number(value: Any) -> float:
        """Convert a numeric value to float."""

        if value is None:
            return 0.0

        return float(value)

    @staticmethod
    def _average(values: Any) -> float | None:
        """Calculate an average safely."""

        values = list(values)

        if not values:
            return None

        return sum(float(value) for value in values) / len(values)

    @staticmethod
    def _round_or_none(
        value: float | None,
        digits: int = 2,
    ) -> float | None:
        """Round a number while preserving None."""

        if value is None:
            return None

        return round(value, digits)