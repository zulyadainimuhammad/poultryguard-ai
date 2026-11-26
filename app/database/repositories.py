import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .connection import get_connection
from .models import (
    DailyRecord,
    Farm,
    Flock,
    MeasurementCorrectionRequest,
    MeasurementCorrectionRequestEvent,
    MeasurementObservation,
    MeasurementQualityReviewEvent,
)


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


class MeasurementObservationRepository(_BaseRepository):
    """Insert and query append-only measurement observations.

    The repository intentionally exposes no update or delete operation.
    """

    def create(self, observation: MeasurementObservation) -> str:
        """Insert one observation and return its immutable identifier."""
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO measurement_observations (
                    observation_id,
                    flock_id,
                    daily_record_id,
                    record_date,
                    metric_name,
                    value_numeric,
                    unit,
                    observed_at,
                    recorded_at,
                    source_type,
                    entered_by_user_id,
                    device_id,
                    import_batch_id,
                    source_reference,
                    calibration_reference,
                    calculation_method,
                    calculation_version,
                    quality_status,
                    supersedes_observation_id,
                    correction_reason,
                    notes
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    observation.observation_id,
                    observation.flock_id,
                    observation.daily_record_id,
                    observation.record_date,
                    observation.metric_name,
                    observation.value_numeric,
                    observation.unit,
                    observation.observed_at,
                    observation.recorded_at,
                    observation.source_type,
                    observation.entered_by_user_id,
                    observation.device_id,
                    observation.import_batch_id,
                    observation.source_reference,
                    observation.calibration_reference,
                    observation.calculation_method,
                    observation.calculation_version,
                    observation.quality_status,
                    observation.supersedes_observation_id,
                    observation.correction_reason,
                    observation.notes,
                ),
            )
        return observation.observation_id

    def get_by_id(self, observation_id: str) -> dict[str, Any] | None:
        """Return a single observation by its immutable identifier."""
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM measurement_observations
                WHERE observation_id = ?
                """,
                (observation_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_by_flock(self, flock_id: int) -> list[dict[str, Any]]:
        """Return a flock's complete observation history in stable order."""
        with self._connection_scope() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM measurement_observations
                WHERE flock_id = ?
                ORDER BY record_date ASC, recorded_at ASC, observation_id ASC
                """,
                (flock_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_by_daily_record(self, daily_record_id: int) -> list[dict[str, Any]]:
        """Return observations linked to one legacy daily-record row."""
        with self._connection_scope() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM measurement_observations
                WHERE daily_record_id = ?
                ORDER BY metric_name ASC, recorded_at ASC, observation_id ASC
                """,
                (daily_record_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_by_flock_metric_date_range(
        self,
        flock_id: int,
        metric_name: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Return one metric's observations in an inclusive date range."""
        with self._connection_scope() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM measurement_observations
                WHERE flock_id = ?
                  AND metric_name = ?
                  AND record_date BETWEEN ? AND ?
                ORDER BY record_date ASC, recorded_at ASC, observation_id ASC
                """,
                (flock_id, metric_name, start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]


class MeasurementCorrectionRequestRepository(_BaseRepository):
    """Insert and query immutable correction requests."""

    def create(self, request: MeasurementCorrectionRequest) -> str:
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO measurement_correction_requests (
                    request_id,
                    target_observation_id,
                    proposed_value_numeric,
                    correction_reason,
                    requested_by_user_id,
                    requested_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.request_id,
                    request.target_observation_id,
                    request.proposed_value_numeric,
                    request.correction_reason,
                    request.requested_by_user_id,
                    request.requested_at,
                ),
            )
        return request.request_id

    def get_by_id(self, request_id: str) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT * FROM measurement_correction_requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_pending_by_target(self, target_observation_id: str) -> list[dict[str, Any]]:
        with self._connection_scope() as connection:
            rows = connection.execute(
                """
                SELECT request.*
                FROM measurement_correction_requests AS request
                LEFT JOIN measurement_correction_request_events AS event
                  ON event.request_id = request.request_id
                WHERE request.target_observation_id = ?
                  AND event.request_id IS NULL
                ORDER BY request.requested_at, request.request_id
                """,
                (target_observation_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_eligible_target(self, observation_id: str) -> dict[str, Any] | None:
        """Return the exact target if it is accepted and has no successor."""
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT target.*
                FROM measurement_observations AS target
                WHERE target.observation_id = ?
                  AND target.source_type = 'manual_entry'
                  AND (
                      target.quality_status = 'observed'
                      OR (
                          target.quality_status = 'pending_validation'
                          AND EXISTS (
                              SELECT 1
                              FROM measurement_quality_review_events AS review
                              WHERE review.observation_id = target.observation_id
                                AND review.decision = 'accepted'
                          )
                      )
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM measurement_observations AS successor
                      WHERE successor.supersedes_observation_id = target.observation_id
                  )
                """,
                (observation_id,),
            ).fetchone()
            return dict(row) if row else None


class MeasurementCorrectionRequestEventRepository(_BaseRepository):
    """Insert and query immutable correction decision events."""

    def create(self, event: MeasurementCorrectionRequestEvent) -> str:
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO measurement_correction_request_events (
                    event_id,
                    request_id,
                    outcome,
                    outcome_reason,
                    reviewed_by_user_id,
                    event_at,
                    created_observation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.request_id,
                    event.outcome,
                    event.outcome_reason,
                    event.reviewed_by_user_id,
                    event.event_at,
                    event.created_observation_id,
                ),
            )
        return event.event_id

    def get_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT * FROM measurement_correction_request_events
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            return dict(row) if row else None


class MeasurementQualityReviewEventRepository(_BaseRepository):
    """Insert and retrieve immutable observation review events."""

    def create(self, event: MeasurementQualityReviewEvent) -> str:
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO measurement_quality_review_events (
                    event_id,
                    observation_id,
                    decision,
                    review_reason,
                    reviewed_by_user_id,
                    reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.observation_id,
                    event.decision,
                    event.review_reason,
                    event.reviewed_by_user_id,
                    event.reviewed_at,
                ),
            )
        return event.event_id

    def get_by_observation_id(self, observation_id: str) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT * FROM measurement_quality_review_events
                WHERE observation_id = ?
                """,
                (observation_id,),
            ).fetchone()
            return dict(row) if row else None


class MeasurementQueryRepository(_BaseRepository):
    """Read-only queries for accepted measurements and correction audit data."""

    def list_current_accepted(
        self,
        *,
        flock_id: int,
        metric_name: str,
        record_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        if record_date is None:
            if start_date is None or end_date is None:
                raise ValueError("Specify either record_date or both range endpoints.")
        elif start_date is not None or end_date is not None:
            raise ValueError("Specify either record_date or both range endpoints.")

        conditions = [
            "observation.flock_id = ?",
            "observation.metric_name = ?",
            "(observation.quality_status = 'observed' OR ("
            "observation.quality_status = 'pending_validation' AND "
            "review.decision = 'accepted'))",
            "NOT EXISTS ("
            "SELECT 1 FROM measurement_observations AS successor "
            "WHERE successor.supersedes_observation_id = observation.observation_id "
            "AND (successor.quality_status = 'observed' OR ("
            "successor.quality_status = 'pending_validation' AND EXISTS ("
            "SELECT 1 FROM measurement_quality_review_events AS successor_review "
            "WHERE successor_review.observation_id = successor.observation_id "
            "AND successor_review.decision = 'accepted'))))",
        ]
        parameters: list[Any] = [flock_id, metric_name]
        if record_date is not None:
            conditions.append("observation.record_date = ?")
            parameters.append(record_date)
        else:
            conditions.append("observation.record_date BETWEEN ? AND ?")
            parameters.extend((start_date, end_date))

        with self._connection_scope() as connection:
            rows = connection.execute(
                f"""
                SELECT observation.*,
                       CASE
                           WHEN observation.quality_status = 'pending_validation'
                                AND review.decision = 'accepted'
                               THEN 'observed'
                           WHEN observation.quality_status = 'pending_validation'
                                AND review.decision = 'rejected'
                               THEN 'invalid'
                           ELSE observation.quality_status
                       END AS effective_quality_status
                FROM measurement_observations AS observation
                LEFT JOIN measurement_quality_review_events AS review
                  ON review.observation_id = observation.observation_id
                WHERE {" AND ".join(conditions)}
                ORDER BY observation.record_date,
                         observation.recorded_at,
                         observation.observation_id
                """,
                parameters,
            ).fetchall()
            return [dict(row) for row in rows]

    def get_current_accepted_by_id(self, observation_id: str) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT observation.*,
                       CASE
                           WHEN observation.quality_status = 'pending_validation'
                                AND review.decision = 'accepted'
                               THEN 'observed'
                           WHEN observation.quality_status = 'pending_validation'
                                AND review.decision = 'rejected'
                               THEN 'invalid'
                           ELSE observation.quality_status
                       END AS effective_quality_status
                FROM measurement_observations AS observation
                LEFT JOIN measurement_quality_review_events AS review
                  ON review.observation_id = observation.observation_id
                WHERE observation.observation_id = ?
                  AND (
                      observation.quality_status = 'observed'
                      OR (
                          observation.quality_status = 'pending_validation'
                          AND review.decision = 'accepted'
                      )
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM measurement_observations AS successor
                      WHERE successor.supersedes_observation_id =
                            observation.observation_id
                        AND (
                            successor.quality_status = 'observed'
                            OR (
                                successor.quality_status = 'pending_validation'
                                AND EXISTS (
                                    SELECT 1
                                    FROM measurement_quality_review_events AS sq_review
                                    WHERE sq_review.observation_id =
                                          successor.observation_id
                                      AND sq_review.decision = 'accepted'
                                )
                            )
                        )
                  )
                """,
                (observation_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_correction_request_status(self, request_id: str) -> str | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                """
                SELECT CASE
                           WHEN event.request_id IS NULL THEN 'pending'
                           ELSE event.outcome
                       END AS request_status
                FROM measurement_correction_requests AS request
                LEFT JOIN measurement_correction_request_events AS event
                  ON event.request_id = request.request_id
                WHERE request.request_id = ?
                """,
                (request_id,),
            ).fetchone()
            return row["request_status"] if row else None

    def get_connected_observation_chain(
        self, observation_id: str
    ) -> list[dict[str, Any]]:
        """Return all observations connected by supersession from any chain node."""
        with self._connection_scope() as connection:
            rows = connection.execute(
                """
                WITH RECURSIVE chain(observation_id) AS (
                    SELECT observation_id
                    FROM measurement_observations
                    WHERE observation_id = ?
                    UNION
                    SELECT related.observation_id
                    FROM chain
                    JOIN measurement_observations AS current
                      ON current.observation_id = chain.observation_id
                    JOIN measurement_observations AS related
                      ON related.observation_id = current.supersedes_observation_id
                      OR related.supersedes_observation_id = current.observation_id
                )
                SELECT observation.*,
                       CASE
                           WHEN observation.quality_status = 'pending_validation'
                                AND review.decision = 'accepted'
                               THEN 'observed'
                           WHEN observation.quality_status = 'pending_validation'
                                AND review.decision = 'rejected'
                               THEN 'invalid'
                           ELSE observation.quality_status
                       END AS effective_quality_status
                FROM chain
                JOIN measurement_observations AS observation
                  ON observation.observation_id = chain.observation_id
                LEFT JOIN measurement_quality_review_events AS review
                  ON review.observation_id = observation.observation_id
                ORDER BY observation.recorded_at, observation.observation_id
                """,
                (observation_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_correction_history_for_observations(
        self, observation_ids: tuple[str, ...]
    ) -> list[dict[str, Any]]:
        if not observation_ids:
            return []
        placeholders = ", ".join("?" for _ in observation_ids)
        with self._connection_scope() as connection:
            rows = connection.execute(
                f"""
                SELECT request.*,
                       CASE
                           WHEN event.request_id IS NULL THEN 'pending'
                           ELSE event.outcome
                       END AS request_status,
                       event.event_id AS terminal_event_id,
                       event.outcome AS terminal_outcome,
                       event.outcome_reason AS terminal_outcome_reason,
                       event.reviewed_by_user_id AS terminal_reviewer_id,
                       event.event_at AS terminal_event_at,
                       event.created_observation_id
                FROM measurement_correction_requests AS request
                LEFT JOIN measurement_correction_request_events AS event
                  ON event.request_id = request.request_id
                WHERE request.target_observation_id IN ({placeholders})
                ORDER BY request.requested_at, request.request_id,
                         event.event_at, event.event_id
                """,
                observation_ids,
            ).fetchall()
            return [dict(row) for row in rows]

    def get_quality_review_events_for_observations(
        self, observation_ids: tuple[str, ...]
    ) -> list[dict[str, Any]]:
        if not observation_ids:
            return []
        placeholders = ", ".join("?" for _ in observation_ids)
        with self._connection_scope() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM measurement_quality_review_events
                WHERE observation_id IN ({placeholders})
                ORDER BY reviewed_at, event_id
                """,
                observation_ids,
            ).fetchall()
            return [dict(row) for row in rows]
