from typing import Any, Optional

from .connection import get_connection
from .models import DailyRecord, Farm, Flock


class FarmRepository:
    """Database operations for farms."""

    def create(self, farm: Farm) -> int:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO farms (
                    farm_name,
                    farmer_name,
                    location,
                    phone,
                    email,
                    production_type
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    farm.farm_name,
                    farm.farmer_name,
                    farm.location,
                    farm.phone,
                    farm.email,
                    farm.production_type,
                ),
            )

            return cursor.lastrowid

    def get_by_id(self, farm_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM farms
                WHERE id = ?
                """,
                (farm_id,),
            ).fetchone()

            return dict(row) if row else None

    def get_all(self) -> list[dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM farms
                ORDER BY created_at DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]

    def update(self, farm_id: int, **fields: Any) -> None:
        allowed_fields = {
            "farm_name",
            "farmer_name",
            "location",
            "phone",
            "email",
            "production_type",
        }

        updates = {
            key: value
            for key, value in fields.items()
            if key in allowed_fields
        }

        if not updates:
            return

        set_clause = ", ".join(
            f"{field} = ?" for field in updates
        )

        values = list(updates.values())
        values.append(farm_id)

        with get_connection() as connection:
            connection.execute(
                f"""
                UPDATE farms
                SET {set_clause},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )

    def delete(self, farm_id: int) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM farms
                WHERE id = ?
                """,
                (farm_id,),
            )


class FlockRepository:
    """Database operations for poultry flocks."""

    def create(self, flock: Flock) -> int:
        if flock.initial_count <= 0:
            raise ValueError(
                "Initial flock count must be greater than zero."
            )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO flocks (
                    farm_id,
                    flock_name,
                    species,
                    production_type,
                    breed,
                    initial_count,
                    stocking_date,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    flock.farm_id,
                    flock.flock_name,
                    flock.species,
                    flock.production_type,
                    flock.breed,
                    flock.initial_count,
                    flock.stocking_date,
                    flock.status,
                ),
            )

            return cursor.lastrowid

    def get_by_id(self, flock_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM flocks
                WHERE id = ?
                """,
                (flock_id,),
            ).fetchone()

            return dict(row) if row else None

    def get_by_farm(self, farm_id: int) -> list[dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM flocks
                WHERE farm_id = ?
                ORDER BY created_at DESC
                """,
                (farm_id,),
            ).fetchall()

            return [dict(row) for row in rows]

    def update(self, flock_id: int, **fields: Any) -> None:
        allowed_fields = {
            "flock_name",
            "species",
            "production_type",
            "breed",
            "initial_count",
            "stocking_date",
            "status",
        }

        updates = {
            key: value
            for key, value in fields.items()
            if key in allowed_fields
        }

        if not updates:
            return

        if (
            "initial_count" in updates
            and updates["initial_count"] <= 0
        ):
            raise ValueError(
                "Initial flock count must be greater than zero."
            )

        set_clause = ", ".join(
            f"{field} = ?" for field in updates
        )

        values = list(updates.values())
        values.append(flock_id)

        with get_connection() as connection:
            connection.execute(
                f"""
                UPDATE flocks
                SET {set_clause},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )

    def delete(self, flock_id: int) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM flocks
                WHERE id = ?
                """,
                (flock_id,),
            )


class DailyRecordRepository:
    """Database operations for daily flock records."""

    def create(self, record: DailyRecord) -> int:
        if record.mortality < 0:
            raise ValueError("Mortality cannot be negative.")

        if record.humidity_percent is not None:
            if not 0 <= record.humidity_percent <= 100:
                raise ValueError(
                    "Humidity must be between 0 and 100 percent."
                )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO daily_records (
                    flock_id,
                    record_date,
                    feed_kg,
                    water_litres,
                    mortality,
                    average_weight_kg,
                    temperature_c,
                    humidity_percent,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.flock_id,
                    record.record_date,
                    record.feed_kg,
                    record.water_litres,
                    record.mortality,
                    record.average_weight_kg,
                    record.temperature_c,
                    record.humidity_percent,
                    record.notes,
                ),
            )

            return cursor.lastrowid

    def get_by_id(self, record_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM daily_records
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()

            return dict(row) if row else None

    def get_by_flock(self, flock_id: int) -> list[dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM daily_records
                WHERE flock_id = ?
                ORDER BY record_date DESC, id DESC
                """,
                (flock_id,),
            ).fetchall()

            return [dict(row) for row in rows]

    def get_by_date_range(
        self,
        flock_id: int,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM daily_records
                WHERE flock_id = ?
                  AND record_date BETWEEN ? AND ?
                ORDER BY record_date ASC, id ASC
                """,
                (flock_id, start_date, end_date),
            ).fetchall()

            return [dict(row) for row in rows]

    def delete(self, record_id: int) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM daily_records
                WHERE id = ?
                """,
                (record_id,),
            )