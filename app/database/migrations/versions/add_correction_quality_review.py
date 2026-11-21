"""Add append-only correction-request and quality-review event tables."""

from __future__ import annotations

import hashlib
import sqlite3

VERSION = "0002"
NAME = "add_correction_quality_review"

_UTC_TIMESTAMP_CHECK = """
    length({column}) = 20
    AND {column} GLOB
        '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T'
        || '[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
    AND strftime('%Y-%m-%dT%H:%M:%SZ', {column}) = {column}
"""

CREATE_CORRECTION_REQUESTS_SQL = f"""
CREATE TABLE measurement_correction_requests (
    request_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(request_id)) > 0),
    target_observation_id TEXT NOT NULL
        CHECK (length(trim(target_observation_id)) > 0),
    proposed_value_numeric REAL NOT NULL
        CHECK (
            typeof(proposed_value_numeric) IN ('integer', 'real')
            AND proposed_value_numeric = proposed_value_numeric
            AND abs(proposed_value_numeric) <= 1.7976931348623157e308
        ),
    correction_reason TEXT NOT NULL
        CHECK (length(trim(correction_reason)) > 0),
    requested_by_user_id TEXT
        CHECK (
            requested_by_user_id IS NULL
            OR length(trim(requested_by_user_id)) > 0
        ),
    requested_at TEXT NOT NULL
        CHECK ({_UTC_TIMESTAMP_CHECK.format(column="requested_at")}),

    FOREIGN KEY (target_observation_id)
        REFERENCES measurement_observations(observation_id)
        ON DELETE RESTRICT
)
"""

CREATE_CORRECTION_EVENTS_SQL = f"""
CREATE TABLE measurement_correction_request_events (
    event_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(event_id)) > 0),
    request_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(request_id)) > 0),
    outcome TEXT NOT NULL
        CHECK (outcome IN ('approved', 'rejected', 'invalidated')),
    outcome_reason TEXT NOT NULL
        CHECK (length(trim(outcome_reason)) > 0),
    reviewed_by_user_id TEXT
        CHECK (
            reviewed_by_user_id IS NULL
            OR length(trim(reviewed_by_user_id)) > 0
        ),
    event_at TEXT NOT NULL
        CHECK ({_UTC_TIMESTAMP_CHECK.format(column="event_at")}),
    created_observation_id TEXT UNIQUE
        CHECK (
            created_observation_id IS NULL
            OR length(trim(created_observation_id)) > 0
        ),
    CHECK (
        (outcome = 'approved' AND created_observation_id IS NOT NULL)
        OR (
            outcome IN ('rejected', 'invalidated')
            AND created_observation_id IS NULL
        )
    ),

    FOREIGN KEY (request_id)
        REFERENCES measurement_correction_requests(request_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (created_observation_id)
        REFERENCES measurement_observations(observation_id)
        ON DELETE RESTRICT
)
"""

CREATE_QUALITY_REVIEW_EVENTS_SQL = f"""
CREATE TABLE measurement_quality_review_events (
    event_id TEXT PRIMARY KEY NOT NULL
        CHECK (length(trim(event_id)) > 0),
    observation_id TEXT NOT NULL UNIQUE
        CHECK (length(trim(observation_id)) > 0),
    decision TEXT NOT NULL
        CHECK (decision IN ('accepted', 'rejected')),
    review_reason TEXT NOT NULL
        CHECK (length(trim(review_reason)) > 0),
    reviewed_by_user_id TEXT
        CHECK (
            reviewed_by_user_id IS NULL
            OR length(trim(reviewed_by_user_id)) > 0
        ),
    reviewed_at TEXT NOT NULL
        CHECK ({_UTC_TIMESTAMP_CHECK.format(column="reviewed_at")}),

    FOREIGN KEY (observation_id)
        REFERENCES measurement_observations(observation_id)
        ON DELETE RESTRICT
)
"""

CREATE_INDEX_SQL = (
    """
    CREATE INDEX ix_measurement_correction_requests_target_requested_at
    ON measurement_correction_requests (target_observation_id, requested_at)
    """,
    """
    CREATE INDEX ix_measurement_correction_requests_requested_at
    ON measurement_correction_requests (requested_at)
    """,
    """
    CREATE INDEX ix_measurement_correction_events_event_at
    ON measurement_correction_request_events (event_at)
    """,
    """
    CREATE INDEX ix_measurement_quality_review_events_reviewed_at
    ON measurement_quality_review_events (reviewed_at)
    """,
)

CREATE_INTEGRITY_TRIGGERS_SQL = (
    """
    CREATE TRIGGER trg_measurement_correction_requests_validate_insert
    BEFORE INSERT ON measurement_correction_requests
    WHEN NOT EXISTS (
        SELECT 1
        FROM measurement_observations AS target
        WHERE target.observation_id = NEW.target_observation_id
          AND target.source_type = 'manual_entry'
          AND (
              target.quality_status = 'observed'
              OR (
                  target.quality_status = 'pending_validation'
                  AND EXISTS (
                      SELECT 1
                      FROM measurement_quality_review_events AS review_event
                      WHERE review_event.observation_id = target.observation_id
                        AND review_event.decision = 'accepted'
                  )
              )
          )
          AND NOT EXISTS (
              SELECT 1
              FROM measurement_observations AS successor
              WHERE successor.supersedes_observation_id = target.observation_id
          )
          AND target.value_numeric <> NEW.proposed_value_numeric
          AND CASE target.metric_name
              WHEN 'mortality' THEN
                  NEW.proposed_value_numeric >= 0
                  AND NEW.proposed_value_numeric <= 9223372036854775807
                  AND NEW.proposed_value_numeric = CAST(
                      NEW.proposed_value_numeric AS INTEGER
                  )
              WHEN 'feed_kg' THEN NEW.proposed_value_numeric >= 0
              WHEN 'water_litres' THEN NEW.proposed_value_numeric >= 0
              WHEN 'average_weight_kg' THEN NEW.proposed_value_numeric > 0
              WHEN 'humidity_percent' THEN
                  NEW.proposed_value_numeric BETWEEN 0 AND 100
              WHEN 'temperature_c' THEN 1
              ELSE 0
          END
    )
    BEGIN
        SELECT RAISE(
            ABORT,
            'correction request target or proposed value is not eligible'
        );
    END
    """,
    """
    CREATE TRIGGER trg_measurement_correction_events_validate_approval
    BEFORE INSERT ON measurement_correction_request_events
    WHEN NEW.outcome = 'approved'
      AND NOT EXISTS (
          SELECT 1
          FROM measurement_correction_requests AS request
          JOIN measurement_observations AS correction
            ON correction.observation_id = NEW.created_observation_id
          JOIN measurement_observations AS target
            ON target.observation_id = request.target_observation_id
          WHERE request.request_id = NEW.request_id
            AND correction.supersedes_observation_id = target.observation_id
            AND correction.flock_id = target.flock_id
            AND correction.metric_name = target.metric_name
            AND correction.record_date = target.record_date
            AND correction.unit = target.unit
            AND correction.observed_at IS target.observed_at
            AND correction.source_type = 'manual_entry'
            AND correction.quality_status = 'observed'
            AND correction.value_numeric = request.proposed_value_numeric
            AND correction.correction_reason = request.correction_reason
      )
    BEGIN
        SELECT RAISE(
            ABORT,
            'approved correction must reference a matching successor of its target'
        );
    END
    """,
    """
    CREATE TRIGGER trg_measurement_correction_events_validate_invalidation
    BEFORE INSERT ON measurement_correction_request_events
    WHEN NEW.outcome = 'invalidated'
      AND NOT EXISTS (
          SELECT 1
          FROM measurement_correction_requests AS request
          JOIN measurement_observations AS target
            ON target.observation_id = request.target_observation_id
          JOIN measurement_observations AS successor
            ON successor.supersedes_observation_id = target.observation_id
          WHERE request.request_id = NEW.request_id
      )
    BEGIN
        SELECT RAISE(
            ABORT,
            'invalidated correction request must have a stale target'
        );
    END
    """,
    """
    CREATE TRIGGER trg_measurement_quality_reviews_validate_insert
    BEFORE INSERT ON measurement_quality_review_events
    WHEN NOT EXISTS (
        SELECT 1
        FROM measurement_observations AS candidate
        WHERE candidate.observation_id = NEW.observation_id
          AND candidate.quality_status = 'pending_validation'
    )
    BEGIN
        SELECT RAISE(
            ABORT,
            'quality review requires a pending_validation observation'
        );
    END
    """,
)


def _append_only_triggers(table_name: str, unique_columns: tuple[str, ...]):
    # Explicit trigger names avoid depending on the table's pluralisation.
    names = {
        "measurement_correction_requests": "measurement_correction_requests",
        "measurement_correction_request_events": "measurement_correction_events",
        "measurement_quality_review_events": "measurement_quality_review_events",
    }
    prefix = names[table_name]
    no_replace_predicate = " OR ".join(
        f"(NEW.{column} IS NOT NULL AND EXISTS ("
        f"SELECT 1 FROM {table_name} WHERE {column} = NEW.{column}))"
        for column in unique_columns
    )
    return (
        f"""
        CREATE TRIGGER trg_{prefix}_no_update
        BEFORE UPDATE ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, '{table_name} are append-only');
        END
        """,
        f"""
        CREATE TRIGGER trg_{prefix}_no_delete
        BEFORE DELETE ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, '{table_name} are append-only');
        END
        """,
        f"""
        CREATE TRIGGER trg_{prefix}_no_replace
        BEFORE INSERT ON {table_name}
        WHEN {no_replace_predicate}
        BEGIN
            SELECT RAISE(ABORT, '{table_name} are append-only');
        END
        """,
    )


CREATE_APPEND_ONLY_TRIGGERS_SQL = tuple(
    trigger
    for table_name, unique_columns in (
        ("measurement_correction_requests", ("request_id",)),
        (
            "measurement_correction_request_events",
            ("event_id", "request_id", "created_observation_id"),
        ),
        (
            "measurement_quality_review_events",
            ("event_id", "observation_id"),
        ),
    )
    for trigger in _append_only_triggers(table_name, unique_columns)
)

MIGRATION_SQL = "\n".join(
    (
        CREATE_CORRECTION_REQUESTS_SQL,
        CREATE_CORRECTION_EVENTS_SQL,
        CREATE_QUALITY_REVIEW_EVENTS_SQL,
        *CREATE_INDEX_SQL,
        *CREATE_INTEGRITY_TRIGGERS_SQL,
        *CREATE_APPEND_ONLY_TRIGGERS_SQL,
    )
)
CHECKSUM = hashlib.sha256(MIGRATION_SQL.encode("utf-8")).hexdigest()


def upgrade(connection: sqlite3.Connection) -> None:
    """Create the correction and quality-review schema additively."""
    for statement in (
        CREATE_CORRECTION_REQUESTS_SQL,
        CREATE_CORRECTION_EVENTS_SQL,
        CREATE_QUALITY_REVIEW_EVENTS_SQL,
        *CREATE_INDEX_SQL,
        *CREATE_INTEGRITY_TRIGGERS_SQL,
        *CREATE_APPEND_ONLY_TRIGGERS_SQL,
    ):
        connection.execute(statement)


def _normalise_sql(sql: str | None) -> str:
    return "".join((sql or "").lower().split()).rstrip(";")


def _expected_columns(connection: sqlite3.Connection, table_name: str):
    return {
        row[1]
        for row in connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    }


def _foreign_keys(connection: sqlite3.Connection, table_name: str):
    return {
        (row[2], row[3], row[4], row[6].upper())
        for row in connection.execute(
            f"PRAGMA foreign_key_list('{table_name}')"
        ).fetchall()
    }


def validate(connection: sqlite3.Connection) -> None:
    """Verify the complete additive schema and its append-only protections."""
    expected_columns = {
        "measurement_correction_requests": {
            "request_id",
            "target_observation_id",
            "proposed_value_numeric",
            "correction_reason",
            "requested_by_user_id",
            "requested_at",
        },
        "measurement_correction_request_events": {
            "event_id",
            "request_id",
            "outcome",
            "outcome_reason",
            "reviewed_by_user_id",
            "event_at",
            "created_observation_id",
        },
        "measurement_quality_review_events": {
            "event_id",
            "observation_id",
            "decision",
            "review_reason",
            "reviewed_by_user_id",
            "reviewed_at",
        },
    }
    for table_name, expected in expected_columns.items():
        actual = _expected_columns(connection, table_name)
        if actual != expected:
            raise RuntimeError(
                f"{table_name} columns differ from the expected contract: "
                f"missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}."
            )

    expected_foreign_keys = {
        "measurement_correction_requests": {
            (
                "measurement_observations",
                "target_observation_id",
                "observation_id",
                "RESTRICT",
            ),
        },
        "measurement_correction_request_events": {
            (
                "measurement_correction_requests",
                "request_id",
                "request_id",
                "RESTRICT",
            ),
            (
                "measurement_observations",
                "created_observation_id",
                "observation_id",
                "RESTRICT",
            ),
        },
        "measurement_quality_review_events": {
            (
                "measurement_observations",
                "observation_id",
                "observation_id",
                "RESTRICT",
            ),
        },
    }
    for table_name, expected in expected_foreign_keys.items():
        actual = _foreign_keys(connection, table_name)
        if actual != expected:
            raise RuntimeError(
                f"{table_name} foreign keys differ from the expected contract: "
                f"missing={sorted(expected - actual)}, "
                f"extra={sorted(actual - expected)}."
            )

    expected_index_sql = {
        statement.split()[2]: _normalise_sql(statement)
        for statement in CREATE_INDEX_SQL
    }
    actual_index_sql = {
        row[0]: _normalise_sql(row[1])
        for row in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
        if row[0] in expected_index_sql
    }
    if actual_index_sql != expected_index_sql:
        raise RuntimeError(
            "Correction/quality-review indexes differ from the expected contract: "
            f"missing={sorted(expected_index_sql.keys() - actual_index_sql.keys())}."
        )

    expected_trigger_sql = {
        statement.split()[2]: _normalise_sql(statement)
        for statement in (
            *CREATE_INTEGRITY_TRIGGERS_SQL,
            *CREATE_APPEND_ONLY_TRIGGERS_SQL,
        )
    }
    actual_trigger_sql = {
        row[0]: _normalise_sql(row[1])
        for row in connection.execute(
            """
            SELECT name, sql FROM sqlite_master
            WHERE type = 'trigger'
            """
        ).fetchall()
        if row[0] in expected_trigger_sql
    }
    if actual_trigger_sql != expected_trigger_sql:
        missing_triggers = expected_trigger_sql.keys() - actual_trigger_sql.keys()
        raise RuntimeError(
            "Correction/quality-review triggers differ from the expected contract: "
            f"missing={sorted(missing_triggers)}."
        )

    for table_name, expected in {
        "measurement_correction_requests": CREATE_CORRECTION_REQUESTS_SQL,
        "measurement_correction_request_events": CREATE_CORRECTION_EVENTS_SQL,
        "measurement_quality_review_events": CREATE_QUALITY_REVIEW_EVENTS_SQL,
    }.items():
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if row is None or _normalise_sql(row[0]) != _normalise_sql(expected):
            raise RuntimeError(f"{table_name} DDL differs from the expected schema.")

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(
            f"Correction/quality-review schema has {len(violations)} FK violation(s)."
        )
