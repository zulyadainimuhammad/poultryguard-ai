from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3
from typing import Any

from .connection import get_connection
from .models import DailyRecord, Farm, Flock


class _BaseRepository:
    """Provide either a shared Unit-of-Work connection or a standalone one."""

    def __init__(self, connection: sqlite3.Connection | None = None) -> None:
        self._connection = connection

    @contextmanager
    def _connection_scope(self) -> Iterator[sqlite3.Connection]:
        """Yield the injected connection without taking ownership of it."""
        if self._connection is not None:
            yield self._connection
            return

        with get_connection() as connection:
            yield connection


class FarmRepository(_BaseRepository):
    """Database operations for farms."""

    def create(self, farm: Farm) -> int:
        with self._connection_scope() as connection:
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

    def get_by_id(self, farm_id: int) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
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
        with self._connection_scope() as connection:
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

        updates = {key: value for key, value in fields.items() if key in allowed_fields}

        if not updates:
            return

        set_clause = ", ".join(f"{field} = ?" for field in updates)

        values = list(updates.values())
        values.append(farm_id)

        with self._connection_scope() as connection:
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
        with self._connection_scope() as connection:
            connection.execute(
                """
                DELETE FROM farms
                WHERE id = ?
                """,
                (farm_id,),
            )


class FlockRepository(_BaseRepository):
    """Database operations for poultry flocks."""

    def create(self, flock: Flock) -> int:
        if flock.initial_count <= 0:
            raise ValueError("Initial flock count must be greater than zero.")

        with self._connection_scope() as connection:
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

    def get_by_id(self, flock_id: int) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
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
        with self._connection_scope() as connection:
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

        updates = {key: value for key, value in fields.items() if key in allowed_fields}

        if not updates:
            return

        if "initial_count" in updates and updates["initial_count"] <= 0:
            raise ValueError("Initial flock count must be greater than zero.")

        set_clause = ", ".join(f"{field} = ?" for field in updates)

        values = list(updates.values())
        values.append(flock_id)

        with self._connection_scope() as connection:
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
        with self._connection_scope() as connection:
            connection.execute(
                """
                DELETE FROM flocks
                WHERE id = ?
                """,
                (flock_id,),
            )


class DailyRecordRepository(_BaseRepository):
    """Database operations for daily flock records."""

    def get_by_flock_and_date(
        self, flock_id: int, record_date: str
    ) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM daily_records
                WHERE flock_id = ? AND record_date = ?
                """,
                (flock_id, record_date),
            ).fetchone()

            return dict(row) if row else None

    def create(self, record: DailyRecord) -> int:
        if record.mortality < 0:
            raise ValueError("Mortality cannot be negative.")

        if record.feed_kg is not None and record.feed_kg < 0:
            raise ValueError("Feed consumed cannot be negative.")

        if record.water_litres is not None and record.water_litres < 0:
            raise ValueError("Water consumed cannot be negative.")

        if record.average_weight_kg is not None and record.average_weight_kg <= 0:
            raise ValueError("Average weight must be greater than zero.")

        if record.humidity_percent is not None:
            if not 0 <= record.humidity_percent <= 100:
                raise ValueError("Humidity must be between 0 and 100 percent.")

        with self._connection_scope() as connection:
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

    def get_by_id(self, record_id: int) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
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
        with self._connection_scope() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM daily_records
                WHERE flock_id = ?
                ORDER BY record_date ASC, id ASC
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
        with self._connection_scope() as connection:
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
        with self._connection_scope() as connection:
            connection.execute(
                """
                DELETE FROM daily_records
                WHERE id = ?
                """,
                (record_id,),
            )
