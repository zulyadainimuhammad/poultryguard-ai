from __future__ import annotations

import re
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

_VALID_SPECIES = {"Chicken", "Turkey", "Duck", "Quail", "Guinea Fowl", "Goose"}
_VALID_PRODUCTION_TYPES = {"Broiler", "Layer", "Breeder", "Dual Purpose", "Other"}
_VALID_STATUSES = {"active", "closed", "sold"}


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
        """Validate inputs and create a farm, returning its database ID."""
        farm_name = farm_name.strip() if farm_name else ""
        farmer_name = farmer_name.strip() if farmer_name else ""
        location = location.strip() if location else ""

        if not farm_name:
            raise ValueError("Farm name is required.")
        if not farmer_name:
            raise ValueError("Farmer name is required.")
        if not location:
            raise ValueError("Location is required.")
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Email address is not valid.")

        farm = Farm(
            farm_name=farm_name,
            farmer_name=farmer_name,
            location=location,
            phone=phone or None,
            email=email or None,
            production_type=production_type or None,
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
        """Validate inputs and create a flock belonging to a farm."""
        flock_name = flock_name.strip() if flock_name else ""

        if not flock_name:
            raise ValueError("Flock name is required.")
        if not species or species.strip() not in _VALID_SPECIES:
            raise ValueError(
                f"Species must be one of: {', '.join(sorted(_VALID_SPECIES))}."
            )
        if not isinstance(initial_count, int) or initial_count <= 0:
            raise ValueError("Initial bird count must be a positive integer.")
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Status must be one of: {', '.join(sorted(_VALID_STATUSES))}."
            )

        farm = self.farm_repository.get_by_id(farm_id)
        if farm is None:
            raise ValueError(f"Farm with ID {farm_id} does not exist.")

        flock = Flock(
            farm_id=farm_id,
            flock_name=flock_name,
            species=species.strip(),
            production_type=production_type or None,
            breed=breed.strip() if breed else None,
            initial_count=initial_count,
            stocking_date=str(stocking_date) if stocking_date else None,
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
        allow_duplicate: bool = False,
    ) -> int:
        """Validate inputs and create a daily production record for a flock.

        By default, raises DuplicateRecordError if a record already exists for
        this flock on this date. Pass allow_duplicate=True to override.
        """
        flock = self.flock_repository.get_by_id(flock_id)
        if flock is None:
            raise ValueError(f"Flock with ID {flock_id} does not exist.")

        date_str = str(record_date)

        if not allow_duplicate:
            existing = self.daily_record_repository.get_by_flock_and_date(
                flock_id, date_str
            )
            if existing:
                raise DuplicateRecordError(
                    f"A daily record for flock {flock_id} on {date_str} already "
                    "exists. Edit the existing record or pass allow_duplicate=True."
                )

        # Validate mortality against remaining flock population
        if mortality < 0:
            raise ValueError("Mortality cannot be negative.")

        existing_records = self.daily_record_repository.get_by_flock(flock_id)
        cumulative_mortality = sum(
            int(r.get("mortality") or 0) for r in existing_records
        )
        remaining = flock["initial_count"] - cumulative_mortality
        if mortality > remaining:
            raise ValueError(
                f"Mortality ({mortality}) exceeds the remaining flock population "
                f"({remaining})."
            )

        record = DailyRecord(
            flock_id=flock_id,
            record_date=date_str,
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
        """Return daily records for a flock in chronological order."""
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


class DuplicateRecordError(ValueError):
    """Raised when a daily record already exists for a flock on a given date."""
