from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from typing import Any

from app.database import (
    DailyRecord,
    DailyRecordRepository,
    Farm,
    FarmRepository,
    Flock,
    FlockRepository,
    UnitOfWork,
)

_VALID_SPECIES = {"Chicken", "Turkey", "Duck", "Quail", "Guinea Fowl", "Goose"}
_VALID_PRODUCTION_TYPES = {"Broiler", "Layer", "Breeder", "Dual Purpose", "Other"}
_VALID_STATUSES = {"active", "closed", "sold"}


class FarmService:
    """Application service for farm, flock and daily-record operations.

    Standalone repository dependencies support ordinary reads and CRUD.
    Daily-record creation uses the Unit-of-Work factory so its validation
    reads and insert share one transaction. Custom database adapters should
    provide a Unit-of-Work factory targeting the same database.
    """

    def __init__(
        self,
        farm_repository: FarmRepository | None = None,
        flock_repository: FlockRepository | None = None,
        daily_record_repository: DailyRecordRepository | None = None,
        unit_of_work_factory: Callable[[], UnitOfWork] | None = None,
    ) -> None:
        self.farm_repository = farm_repository or FarmRepository()
        self.flock_repository = flock_repository or FlockRepository()
        self.daily_record_repository = (
            daily_record_repository or DailyRecordRepository()
        )
        self.unit_of_work_factory = unit_of_work_factory or UnitOfWork

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

    def update_farm(
        self,
        farm_id: int,
        farm_name: str,
        farmer_name: str,
        location: str,
        production_type: str | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> None:
        """Validate and update an existing farm without changing its identity."""
        if self.farm_repository.get_by_id(farm_id) is None:
            raise ValueError(f"Farm with ID {farm_id} does not exist.")

        farm_name = farm_name.strip() if isinstance(farm_name, str) else ""
        farmer_name = farmer_name.strip() if isinstance(farmer_name, str) else ""
        location = location.strip() if isinstance(location, str) else ""

        if not farm_name:
            raise ValueError("Farm name is required.")
        if not farmer_name:
            raise ValueError("Farmer name is required.")
        if not location:
            raise ValueError("Location is required.")

        if production_type is not None and not isinstance(production_type, str):
            raise ValueError("Production type must be text or None.")
        if production_type is not None:
            production_type = production_type.strip() or None

        if phone is not None and not isinstance(phone, str):
            raise ValueError("Phone number must be text or None.")
        if phone is not None:
            phone = phone.strip() or None

        if email is not None and not isinstance(email, str):
            raise ValueError("Email address must be text or None.")
        if email is not None:
            email = email.strip() or None
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Email address is not valid.")

        self.farm_repository.update(
            farm_id,
            farm_name=farm_name,
            farmer_name=farmer_name,
            location=location,
            production_type=production_type,
            phone=phone,
            email=email,
        )

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
        """Validate and create a daily record in one write transaction.

        Flock lookup, duplicate-date checking, cumulative-mortality checking
        and insertion share the Unit-of-Work connection. By default, a record
        already exists for this flock/date and raises DuplicateRecordError.
        Pass allow_duplicate=True to preserve the existing override behaviour.
        """
        date_str = str(record_date)

        with self.unit_of_work_factory() as unit_of_work:
            flock = unit_of_work.flocks.get_by_id(flock_id)
            if flock is None:
                raise ValueError(f"Flock with ID {flock_id} does not exist.")

            if not allow_duplicate:
                existing = unit_of_work.daily_records.get_by_flock_and_date(
                    flock_id, date_str
                )
                if existing:
                    raise DuplicateRecordError(
                        f"A daily record for flock {flock_id} on {date_str} already "
                        "exists. Edit the existing record or pass allow_duplicate=True."
                    )

            if mortality < 0:
                raise ValueError("Mortality cannot be negative.")

            existing_records = unit_of_work.daily_records.get_by_flock(flock_id)
            cumulative_mortality = sum(
                int(record.get("mortality") or 0) for record in existing_records
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

            return unit_of_work.daily_records.create(record)

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
