from __future__ import annotations

from datetime import date
from typing import Any

from app.database import (
    DailyRecord,
    DailyRecordRepository,
    Farm,
    FarmRepository,
    Flock,
    FlockRepository,
)


class FarmService:
    """Application service for farm, flock and daily-record operations."""

    def __init__(
        self,
        farm_repository: FarmRepository | None = None,
        flock_repository: FlockRepository | None = None,
        daily_record_repository: DailyRecordRepository | None = None,
    ) -> None:
        self.farm_repository = farm_repository or FarmRepository()
        self.flock_repository = flock_repository or FlockRepository()
        self.daily_record_repository = (
            daily_record_repository or DailyRecordRepository()
        )

    # ------------------------------------------------------------------
    # FARM OPERATIONS
    # ------------------------------------------------------------------

    def create_farm(
        self,
        farm_name: str,
        farmer_name: str,
        location: str,
        production_type: str,
        phone: str | None = None,
        email: str | None = None,
    ) -> int:
        """Create a farm and return its database ID."""

        farm = Farm(
            farm_name=farm_name,
            farmer_name=farmer_name,
            location=location,
            phone=phone,
            email=email,
            production_type=production_type,
        )

        return self.farm_repository.create(farm)

    def get_farm(self, farm_id: int) -> dict[str, Any] | None:
        """Return a farm by ID."""

        return self.farm_repository.get_by_id(farm_id)

    def list_farms(self) -> list[dict[str, Any]]:
        """Return all farms."""

        return self.farm_repository.get_all()

    # ------------------------------------------------------------------
    # FLOCK OPERATIONS
    # ------------------------------------------------------------------

    def create_flock(
        self,
        farm_id: int,
        flock_name: str,
        species: str,
        production_type: str,
        breed: str | None,
        initial_count: int,
        stocking_date: date,
        status: str = "active",
    ) -> int:
        """Create a flock belonging to a farm."""

        flock = Flock(
            farm_id=farm_id,
            flock_name=flock_name,
            species=species,
            production_type=production_type,
            breed=breed,
            initial_count=initial_count,
            stocking_date=stocking_date,
            status=status,
        )

        return self.flock_repository.create(flock)

    def get_flock(self, flock_id: int) -> dict[str, Any] | None:
        """Return a flock by ID."""

        return self.flock_repository.get_by_id(flock_id)

    def list_flocks(self, farm_id: int) -> list[dict[str, Any]]:
        """Return all flocks belonging to a farm."""

        return self.flock_repository.get_by_farm(farm_id)

    # ------------------------------------------------------------------
    # DAILY RECORD OPERATIONS
    # ------------------------------------------------------------------

    def create_daily_record(
        self,
        flock_id: int,
        record_date: date,
        feed_kg: float | None = None,
        water_litres: float | None = None,
        mortality: int = 0,
        average_weight_kg: float | None = None,
        temperature_c: float | None = None,
        humidity_percent: float | None = None,
        notes: str | None = None,
    ) -> int:
        """Create a daily production record for a flock."""

        record = DailyRecord(
            flock_id=flock_id,
            record_date=record_date,
            feed_kg=feed_kg,
            water_litres=water_litres,
            mortality=mortality,
            average_weight_kg=average_weight_kg,
            temperature_c=temperature_c,
            humidity_percent=humidity_percent,
            notes=notes,
        )

        return self.daily_record_repository.create(record)

    def get_daily_records(self, flock_id: int) -> list[dict[str, Any]]:
        """Return daily records for a flock."""

        return self.daily_record_repository.get_by_flock(flock_id)

    def get_daily_records_by_date_range(
        self,
        flock_id: int,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Return daily records within a date range."""

        return self.daily_record_repository.get_by_date_range(
            flock_id=flock_id,
            start_date=start_date,
            end_date=end_date,
        )