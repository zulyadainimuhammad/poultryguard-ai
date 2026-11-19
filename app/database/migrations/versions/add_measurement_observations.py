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
        value_numeric IS NULL
        OR typeof(value_numeric) IN ('integer', 'real')
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
    """
    CREATE TRIGGER trg_measurement_observations_no_replace
    BEFORE INSERT ON measurement_observations
    WHEN EXISTS (
        SELECT 1
        FROM measurement_observations
        WHERE observation_id = NEW.observation_id
    )
    OR (
        NEW.supersedes_observation_id IS NOT NULL
        AND EXISTS (
            SELECT 1
            FROM measurement_observations
            WHERE supersedes_observation_id = NEW.supersedes_observation_id
        )
    )
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
    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' "
        "AND name = 'measurement_observations'"
    ).fetchone()
    if table is None or table[0] is None:
        raise RuntimeError("measurement_observations table is missing.")

    expected_columns = {
        "observation_id",
        "flock_id",
        "daily_record_id",
        "record_date",
        "metric_name",
        "value_numeric",
        "unit",
        "observed_at",
        "recorded_at",
        "source_type",
        "entered_by_user_id",
        "device_id",
        "import_batch_id",
        "source_reference",
        "calibration_reference",
        "calculation_method",
        "calculation_version",
        "quality_status",
        "supersedes_observation_id",
        "correction_reason",
        "notes",
    }
    actual_columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info('measurement_observations')"
        ).fetchall()
    }
    if expected_columns != actual_columns:
        raise RuntimeError(
            "Observation schema columns differ from the expected contract: "
            f"missing={sorted(expected_columns - actual_columns)}, "
            f"extra={sorted(actual_columns - expected_columns)}."
        )

    required_foreign_keys = {
        ("flocks", "flock_id", "id", "RESTRICT"),
        ("daily_records", "daily_record_id", "id", "RESTRICT"),
        ("daily_records", "flock_id", "flock_id", "RESTRICT"),
        (
            "measurement_observations",
            "supersedes_observation_id",
            "observation_id",
            "RESTRICT",
        ),
        ("measurement_observations", "flock_id", "flock_id", "RESTRICT"),
        ("measurement_observations", "metric_name", "metric_name", "RESTRICT"),
        ("measurement_observations", "record_date", "record_date", "RESTRICT"),
    }
    actual_foreign_keys = {
        (row[2], row[3], row[4], row[6].upper())
        for row in connection.execute(
            "PRAGMA foreign_key_list('measurement_observations')"
        ).fetchall()
    }
    if required_foreign_keys != actual_foreign_keys:
        raise RuntimeError(
            "Observation schema foreign-key validation failed: "
            f"missing={sorted(required_foreign_keys - actual_foreign_keys)}, "
            f"extra={sorted(actual_foreign_keys - required_foreign_keys)}."
        )

    normalised_table_sql = "".join((table[0] or "").lower().split())
    required_constraints = (
        "metric_name='mortality'andunit='birds'",
        "quality_statusin('observed','invalid','pending_validation')",
        "typeof(value_numeric)in('integer','real')",
        "supersedes_observation_idisnotnull",
    )
    if any(fragment not in normalised_table_sql for fragment in required_constraints):
        raise RuntimeError("Observation schema is missing required CHECK constraints.")

    def normalise(sql: str | None) -> str:
        return "".join((sql or "").lower().split()).rstrip(";")

    expected_index_sql = {
        "uq_daily_records_id_flock": (
            "CREATE UNIQUE INDEX uq_daily_records_id_flock "
            "ON daily_records (id, flock_id)"
        ),
        "ix_measurement_observations_flock_metric_date": (
            "CREATE INDEX ix_measurement_observations_flock_metric_date "
            "ON measurement_observations (flock_id, metric_name, record_date)"
        ),
        "ix_measurement_observations_flock_metric_observed_at": (
            "CREATE INDEX ix_measurement_observations_flock_metric_observed_at "
            "ON measurement_observations (flock_id, metric_name, observed_at)"
        ),
        "ix_measurement_observations_daily_record": (
            "CREATE INDEX ix_measurement_observations_daily_record "
            "ON measurement_observations (daily_record_id)"
        ),
        "uq_measurement_observations_accepted_successor": (
            "CREATE UNIQUE INDEX uq_measurement_observations_accepted_successor "
            "ON measurement_observations (supersedes_observation_id) "
            "WHERE supersedes_observation_id IS NOT NULL"
        ),
    }
    actual_index_sql = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
        if row[1] is not None
    }
    mismatched_indexes = [
        name
        for name, expected_sql in expected_index_sql.items()
        if normalise(actual_index_sql.get(name)) != normalise(expected_sql)
    ]

    expected_trigger_sql = {
        "trg_measurement_observations_no_update": (
            "CREATE TRIGGER trg_measurement_observations_no_update "
            "BEFORE UPDATE ON measurement_observations BEGIN "
            "SELECT RAISE(ABORT, 'measurement observations are append-only'); END"
        ),
        "trg_measurement_observations_no_delete": (
            "CREATE TRIGGER trg_measurement_observations_no_delete "
            "BEFORE DELETE ON measurement_observations BEGIN "
            "SELECT RAISE(ABORT, 'measurement observations are append-only'); END"
        ),
        "trg_measurement_observations_no_replace": (
            "CREATE TRIGGER trg_measurement_observations_no_replace "
            "BEFORE INSERT ON measurement_observations "
            "WHEN EXISTS (SELECT 1 FROM measurement_observations "
            "WHERE observation_id = NEW.observation_id) OR "
            "(NEW.supersedes_observation_id IS NOT NULL AND EXISTS "
            "(SELECT 1 FROM measurement_observations "
            "WHERE supersedes_observation_id = NEW.supersedes_observation_id)) "
            "BEGIN SELECT RAISE(ABORT, 'measurement observations are append-only'); END"
        ),
    }
    actual_trigger_sql = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
    }
    mismatched_triggers = [
        name
        for name, expected_sql in expected_trigger_sql.items()
        if normalise(actual_trigger_sql.get(name)) != normalise(expected_sql)
    ]

    if mismatched_indexes or mismatched_triggers:
        raise RuntimeError(
            "Observation schema validation failed: "
            f"mismatched indexes={mismatched_indexes}, "
            f"mismatched triggers={mismatched_triggers}."
        )
