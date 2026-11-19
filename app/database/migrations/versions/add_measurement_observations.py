"""Add the append-only measurement observation table."""

import hashlib
import sqlite3

VERSION = "0001"
NAME = "add_measurement_observations"

CREATE_SUPPORTING_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_records_id_flock
    ON daily_records (id, flock_id);
"""

CREATE_TABLE_SQL = """
CREATE TABLE measurement_observations (
    observation_id TEXT PRIMARY KEY NOT NULL,
    flock_id INTEGER NOT NULL,
    daily_record_id INTEGER,
    record_date TEXT NOT NULL
        CHECK (
            length(record_date) = 10
            AND record_date GLOB
                '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        ),
    metric_name TEXT NOT NULL
        CHECK (
            metric_name IN (
                'mortality',
                'feed_kg',
                'water_litres',
                'average_weight_kg',
                'temperature_c',
                'humidity_percent'
            )
        ),
    value_numeric REAL,
    unit TEXT NOT NULL,
    observed_at TEXT,
    recorded_at TEXT NOT NULL CHECK (length(trim(recorded_at)) > 0),
    source_type TEXT NOT NULL
        CHECK (
            source_type IN (
                'manual_entry',
                'file_import',
                'sensor_device',
                'system_generated'
            )
        ),
    entered_by_user_id TEXT,
    device_id TEXT,
    import_batch_id TEXT,
    source_reference TEXT,
    calibration_reference TEXT,
    calculation_method TEXT,
    calculation_version TEXT,
    quality_status TEXT NOT NULL
        CHECK (
            quality_status IN (
                'observed',
                'not_recorded',
                'not_measured',
                'not_applicable',
                'device_unavailable',
                'invalid',
                'pending_validation'
            )
        ),
    supersedes_observation_id TEXT,
    correction_reason TEXT,
    notes TEXT,

    CHECK (
        (metric_name = 'mortality' AND unit = 'birds')
        OR (metric_name = 'feed_kg' AND unit = 'kg')
        OR (metric_name = 'water_litres' AND unit = 'litres')
        OR (metric_name = 'average_weight_kg' AND unit = 'kg_per_bird')
        OR (metric_name = 'temperature_c' AND unit = 'degrees_celsius')
        OR (
            metric_name = 'humidity_percent'
            AND unit = 'percent_relative_humidity'
        )
    ),

    CHECK (
        (
            quality_status IN (
                'not_recorded',
                'not_measured',
                'not_applicable',
                'device_unavailable'
            )
            AND value_numeric IS NULL
        )
        OR (
            quality_status IN ('observed', 'invalid', 'pending_validation')
            AND value_numeric IS NOT NULL
        )
    ),

    CHECK (
        quality_status <> 'observed'
        OR (
            metric_name <> 'mortality'
            OR (
                value_numeric >= 0
                AND value_numeric = CAST(value_numeric AS INTEGER)
            )
        )
    ),
    CHECK (
        quality_status <> 'observed'
        OR metric_name <> 'feed_kg'
        OR value_numeric >= 0
    ),
    CHECK (
        quality_status <> 'observed'
        OR metric_name <> 'water_litres'
        OR value_numeric >= 0
    ),
    CHECK (
        quality_status <> 'observed'
        OR metric_name <> 'average_weight_kg'
        OR value_numeric > 0
    ),
    CHECK (
        quality_status <> 'observed'
        OR metric_name <> 'humidity_percent'
        OR value_numeric BETWEEN 0 AND 100
    ),

    CHECK (
        (
            supersedes_observation_id IS NULL
            AND correction_reason IS NULL
        )
        OR (
            supersedes_observation_id IS NOT NULL
            AND length(trim(correction_reason)) > 0
            AND quality_status = 'observed'
        )
    ),

    CHECK (
        (source_type <> 'file_import' OR import_batch_id IS NOT NULL)
        AND (
            source_type <> 'sensor_device'
            OR (device_id IS NOT NULL AND observed_at IS NOT NULL)
        )
        AND (
            source_type <> 'system_generated'
            OR (
                calculation_method IS NOT NULL
                AND calculation_version IS NOT NULL
            )
        )
    ),

    UNIQUE (observation_id, flock_id, metric_name, record_date),

    FOREIGN KEY (flock_id)
        REFERENCES flocks(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (daily_record_id, flock_id)
        REFERENCES daily_records(id, flock_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (
        supersedes_observation_id,
        flock_id,
        metric_name,
        record_date
    )
        REFERENCES measurement_observations (
            observation_id,
            flock_id,
            metric_name,
            record_date
        )
        ON DELETE RESTRICT
);
"""

CREATE_INDEX_SQL = (
    """
    CREATE INDEX ix_measurement_observations_flock_metric_date
    ON measurement_observations (flock_id, metric_name, record_date)
    """,
    """
    CREATE INDEX ix_measurement_observations_flock_metric_observed_at
    ON measurement_observations (flock_id, metric_name, observed_at)
    """,
    """
    CREATE INDEX ix_measurement_observations_daily_record
    ON measurement_observations (daily_record_id)
    """,
    """
    CREATE UNIQUE INDEX uq_measurement_observations_accepted_successor
    ON measurement_observations (supersedes_observation_id)
    WHERE supersedes_observation_id IS NOT NULL
    """,
)

CREATE_APPEND_ONLY_TRIGGERS_SQL = (
    """
    CREATE TRIGGER trg_measurement_observations_no_update
    BEFORE UPDATE ON measurement_observations
    BEGIN
        SELECT RAISE(ABORT, 'measurement observations are append-only');
    END
    """,
    """
    CREATE TRIGGER trg_measurement_observations_no_delete
    BEFORE DELETE ON measurement_observations
    BEGIN
        SELECT RAISE(ABORT, 'measurement observations are append-only');
    END
    """,
)

MIGRATION_SQL = "\n".join(
    (
        CREATE_SUPPORTING_INDEX_SQL,
        CREATE_TABLE_SQL,
        *CREATE_INDEX_SQL,
        *CREATE_APPEND_ONLY_TRIGGERS_SQL,
    )
)
CHECKSUM = hashlib.sha256(MIGRATION_SQL.encode("utf-8")).hexdigest()


def upgrade(connection: sqlite3.Connection) -> None:
    """Apply the additive observation schema using the caller's transaction."""
    connection.execute(CREATE_SUPPORTING_INDEX_SQL)
    connection.execute(CREATE_TABLE_SQL)

    for statement in CREATE_INDEX_SQL:
        connection.execute(statement)

    for statement in CREATE_APPEND_ONLY_TRIGGERS_SQL:
        connection.execute(statement)


def validate(connection: sqlite3.Connection) -> None:
    """Fail when the expected table, indexes, triggers or constraints are absent."""
    expected_indexes = {
        "uq_daily_records_id_flock",
        "ix_measurement_observations_flock_metric_date",
        "ix_measurement_observations_flock_metric_observed_at",
        "ix_measurement_observations_daily_record",
        "uq_measurement_observations_accepted_successor",
    }
    expected_triggers = {
        "trg_measurement_observations_no_update",
        "trg_measurement_observations_no_delete",
    }

    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' "
        "AND name = 'measurement_observations'"
    ).fetchone()
    if table is None or table[0] is None:
        raise RuntimeError("measurement_observations table is missing.")

    indexes = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    }
    triggers = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
    }

    missing_indexes = expected_indexes - indexes
    missing_triggers = expected_triggers - triggers
    if missing_indexes or missing_triggers:
        raise RuntimeError(
            "Observation schema validation failed: "
            f"missing indexes={sorted(missing_indexes)}, "
            f"missing triggers={sorted(missing_triggers)}."
        )
