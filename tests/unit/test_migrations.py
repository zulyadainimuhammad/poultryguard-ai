"""Tests for safe, additive SQLite schema migrations."""

from __future__ import annotations

import sqlite3

import app.database.connection as database_connection
import pytest
from app.database.migrations import runner
from app.database.migrations.versions import add_measurement_observations


def _initialised_database(tmp_path, monkeypatch):
    database_path = tmp_path / "migration-test.db"
    monkeypatch.setattr(database_connection, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database_connection, "DATABASE_PATH", database_path)
    database_connection.initialise_database()
    return database_path


def _seed_legacy_rows():
    with database_connection.get_connection() as connection:
        farm_cursor = connection.execute(
            """
            INSERT INTO farms (farm_name, farmer_name, location)
            VALUES (?, ?, ?)
            """,
            ("Legacy Farm", "Test Farmer", "Kano"),
        )
        farm_id = farm_cursor.lastrowid

        flock_cursor = connection.execute(
            """
            INSERT INTO flocks (
                farm_id, flock_name, species, initial_count
            )
            VALUES (?, ?, ?, ?)
            """,
            (farm_id, "Batch 1", "Chicken", 120),
        )
        flock_id = flock_cursor.lastrowid

        record_cursor = connection.execute(
            """
            INSERT INTO daily_records (
                flock_id,
                record_date,
                feed_kg,
                water_litres,
                mortality,
                temperature_c,
                humidity_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (flock_id, "2026-11-19", 0.0, None, 0, 28.5, 65.0),
        )
        record_id = record_cursor.lastrowid

    return farm_id, flock_id, record_id


def _connect():
    return database_connection.get_connection()


def _insert_observation(
    connection,
    *,
    observation_id="obs-001",
    flock_id,
    daily_record_id=None,
    record_date="2026-11-19",
    metric_name="feed_kg",
    value_numeric=0.0,
    unit="kg",
    quality_status="observed",
    supersedes_observation_id=None,
    correction_reason=None,
    replace=False,
):
    insert_verb = "INSERT OR REPLACE" if replace else "INSERT"
    return connection.execute(
        f"""
        {insert_verb} INTO measurement_observations (
            observation_id,
            flock_id,
            daily_record_id,
            record_date,
            metric_name,
            value_numeric,
            unit,
            recorded_at,
            source_type,
            quality_status,
            supersedes_observation_id,
            correction_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            observation_id,
            flock_id,
            daily_record_id,
            record_date,
            metric_name,
            value_numeric,
            unit,
            "2026-11-19T12:00:00Z",
            "manual_entry",
            quality_status,
            supersedes_observation_id,
            correction_reason,
        ),
    )


def test_migration_adopts_baseline_and_applies_schema_once(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        assert runner.migration_status(connection) == {
            "baseline_adoption_required": True,
            "applied_versions": [],
            "pending_versions": ["0001"],
        }

    with _connect() as connection:
        assert runner.migrate(connection) == ["0001"]

    with _connect() as connection:
        assert runner.migrate(connection) == []
        status = runner.migration_status(connection)
        assert status["baseline_adoption_required"] is False
        assert status["applied_versions"] == ["0000", "0001"]
        assert status["pending_versions"] == []

        ledger = connection.execute(
            """
            SELECT version, name, checksum, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
        assert [row[0] for row in ledger] == ["0000", "0001"]
        assert len(ledger[0][2]) == 64
        assert ledger[1][2] == add_measurement_observations.CHECKSUM
        assert ledger[0][3].endswith("Z")
        assert ledger[1][3].endswith("Z")


def test_registered_follow_on_migration_can_extend_adopted_baseline(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        runner.migrate(connection)

    original = runner.MIGRATIONS

    def add_farm_timezone(connection):
        connection.execute("ALTER TABLE farms ADD COLUMN timezone TEXT")

    def validate_farm_timezone(connection):
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info('farms')").fetchall()
        }
        if "timezone" not in columns:
            raise RuntimeError("Follow-on farm timezone migration did not apply.")

    runner.MIGRATIONS = (
        *original,
        runner.Migration(
            version="0002",
            name="add_farm_timezone",
            checksum="2" * 64,
            upgrade=add_farm_timezone,
            validate=validate_farm_timezone,
        ),
    )
    try:
        with _connect() as connection:
            assert runner.migrate(connection) == ["0002"]
            assert "timezone" in {
                row[1]
                for row in connection.execute("PRAGMA table_info('farms')").fetchall()
            }
    finally:
        runner.MIGRATIONS = original


def test_populated_legacy_database_is_preserved_without_backfill(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)
    farm_id, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        before = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT id, flock_id, record_date, feed_kg, water_litres,
                       mortality, temperature_c, humidity_percent
                FROM daily_records
                """
            ).fetchall()
        ]
        assert runner.migrate(connection) == ["0001"]

    with _connect() as connection:
        after = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT id, flock_id, record_date, feed_kg, water_litres,
                       mortality, temperature_c, humidity_percent
                FROM daily_records
                """
            ).fetchall()
        ]
        observation_count = connection.execute(
            "SELECT COUNT(*) FROM measurement_observations"
        ).fetchone()[0]
        farm_count = connection.execute("SELECT COUNT(*) FROM farms").fetchone()[0]
        flock_count = connection.execute("SELECT COUNT(*) FROM flocks").fetchone()[0]

    assert before == after
    assert observation_count == 0
    assert farm_count == 1
    assert flock_count == 1
    assert before[0][0] == record_id
    assert before[0][1] == flock_id
    assert farm_id > 0


def test_unrecognised_baseline_fails_without_creating_ledger(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        connection.execute("DROP TABLE flocks")

    with _connect() as connection:
        with pytest.raises(
            runner.BaselineSchemaError,
            match="missing required PoultryGuard tables",
        ):
            runner.migrate(connection)

    with _connect() as connection:
        assert not runner._table_exists(connection, runner.LEDGER_TABLE)
        assert runner._table_exists(connection, "farms")
        assert not runner._table_exists(connection, "measurement_observations")


def test_baseline_with_foreign_key_violations_fails_closed(
    tmp_path, monkeypatch
):
    database_path = _initialised_database(tmp_path, monkeypatch)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            VALUES (999999, 'Orphan flock', 'Chicken', 10)
            """
        )
        connection.commit()
    finally:
        connection.close()

    with _connect() as connection:
        with pytest.raises(
            runner.MigrationError,
            match="foreign-key violations",
        ):
            runner.migrate(connection)

    with _connect() as connection:
        assert not runner._table_exists(connection, runner.LEDGER_TABLE)
        assert not runner._table_exists(connection, "measurement_observations")


def test_baseline_with_missing_check_constraint_fails_closed(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        connection.execute("DROP TABLE daily_records")
        connection.execute(
            """
            CREATE TABLE daily_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flock_id INTEGER NOT NULL,
                record_date TEXT NOT NULL,
                feed_kg REAL,
                water_litres REAL,
                mortality INTEGER NOT NULL DEFAULT 0,
                average_weight_kg REAL,
                temperature_c REAL,
                humidity_percent REAL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (flock_id)
                    REFERENCES flocks(id)
                    ON DELETE CASCADE
            )
            """
        )

    with _connect() as connection:
        with pytest.raises(
            runner.BaselineSchemaError,
            match="missing required constraints",
        ):
            runner.migrate(connection)

    with _connect() as connection:
        assert not runner._table_exists(connection, runner.LEDGER_TABLE)


def test_partial_observation_table_without_ledger_is_not_auto_adopted(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        connection.execute(
            "CREATE TABLE measurement_observations (observation_id TEXT PRIMARY KEY)"
        )

    with _connect() as connection:
        with pytest.raises(runner.MigrationError, match="without a migration ledger"):
            runner.migrate(connection)


def test_migration_requires_foreign_keys_enabled(tmp_path, monkeypatch):
    database_path = _initialised_database(tmp_path, monkeypatch)

    connection = sqlite3.connect(database_path)
    try:
        with pytest.raises(runner.MigrationError, match="foreign-key enforcement"):
            runner.migrate(connection)
    finally:
        connection.close()


def test_migration_rejects_a_connection_with_an_open_transaction(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        connection.execute("CREATE TABLE unrelated_test (id INTEGER)")

    connection = _connect()
    try:
        connection.execute("BEGIN")
        with pytest.raises(runner.MigrationError, match="idle connection"):
            runner.migrate(connection)
        connection.rollback()
    finally:
        connection.close()


def test_applied_migration_checksum_mismatch_is_rejected(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        runner.migrate(connection)

    original = runner.MIGRATIONS
    runner.MIGRATIONS = (
        runner.Migration(
            version=add_measurement_observations.VERSION,
            name=add_measurement_observations.NAME,
            checksum="0" * 64,
            upgrade=add_measurement_observations.upgrade,
            validate=add_measurement_observations.validate,
        ),
    )
    try:
        with _connect() as connection:
            with pytest.raises(
                runner.MigrationChecksumError,
                match="name/checksum",
            ):
                runner.migrate(connection)
    finally:
        runner.MIGRATIONS = original


def test_failure_rolls_back_schema_and_ledger(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    original = runner.MIGRATIONS

    def fail_upgrade(connection):
        raise RuntimeError("injected migration failure")

    runner.MIGRATIONS = (
        *original,
        runner.Migration(
            version="0002",
            name="injected_failure",
            checksum="1" * 64,
            upgrade=fail_upgrade,
            validate=lambda connection: None,
        ),
    )
    try:
        with _connect() as connection:
            with pytest.raises(RuntimeError, match="injected migration failure"):
                runner.migrate(connection)
    finally:
        runner.MIGRATIONS = original

    with _connect() as connection:
        assert not runner._table_exists(connection, runner.LEDGER_TABLE)
        assert not runner._table_exists(connection, "measurement_observations")
        assert "uq_daily_records_id_flock" not in {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }


def test_migration_ledger_is_append_only(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        runner.migrate(connection)

    with _connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE schema_migrations SET name = 'tampered' WHERE version = '0001'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM schema_migrations WHERE version = '0001'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                """
                INSERT OR REPLACE INTO schema_migrations (
                    version, name, checksum, applied_at
                )
                VALUES ('0001', 'tampered', ?, '2026-11-19T12:00:00Z')
                """,
                ("0" * 64,),
            )


def test_observation_schema_accepts_zero_and_explicit_missing_status(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            flock_id=flock_id,
            daily_record_id=record_id,
            value_numeric=0.0,
        )
        _insert_observation(
            connection,
            observation_id="obs-002",
            flock_id=flock_id,
            daily_record_id=record_id,
            metric_name="temperature_c",
            value_numeric=None,
            unit="degrees_celsius",
            quality_status="not_recorded",
        )

    with _connect() as connection:
        rows = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT observation_id, value_numeric, quality_status
                FROM measurement_observations
                ORDER BY observation_id
                """
            ).fetchall()
        ]

    assert rows == [
        ("obs-001", 0.0, "observed"),
        ("obs-002", None, "not_recorded"),
    ]


def test_observation_rejects_metric_unit_and_status_value_mismatch(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                flock_id=flock_id,
                metric_name="temperature_c",
                value_numeric=28.0,
                unit="litres",
            )

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                observation_id="obs-null",
                flock_id=flock_id,
                value_numeric=None,
                quality_status="observed",
            )

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                observation_id="obs-humidity",
                flock_id=flock_id,
                metric_name="humidity_percent",
                value_numeric=101.0,
                unit="percent_relative_humidity",
            )

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                observation_id="obs-mortality",
                flock_id=flock_id,
                metric_name="mortality",
                value_numeric=1.5,
                unit="birds",
            )

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                observation_id="obs-nonnumeric",
                flock_id=flock_id,
                metric_name="temperature_c",
                value_numeric="not-a-number",
                unit="degrees_celsius",
            )


def test_daily_record_reference_must_belong_to_same_flock(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        other_flock = connection.execute(
            """
            INSERT INTO flocks (farm_id, flock_name, species, initial_count)
            SELECT farm_id, 'Batch 2', 'Chicken', 40
            FROM flocks WHERE id = ?
            """,
            (flock_id,),
        ).lastrowid

    with _connect() as connection:
        runner.migrate(connection)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                flock_id=other_flock,
                daily_record_id=record_id,
                observation_id="obs-cross-flock",
            )


def test_observation_foreign_keys_prevent_invalid_parent_and_parent_deletion(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                flock_id=999999,
                observation_id="obs-invalid-flock",
            )

        _insert_observation(
            connection,
            flock_id=flock_id,
            daily_record_id=record_id,
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM daily_records WHERE id = ?", (record_id,))

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM flocks WHERE id = ?", (flock_id,))


def test_correction_chain_is_linear_and_append_only(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            flock_id=flock_id,
            daily_record_id=record_id,
            observation_id="original",
            value_numeric=30.0,
        )
        _insert_observation(
            connection,
            flock_id=flock_id,
            daily_record_id=record_id,
            observation_id="correction-1",
            value_numeric=29.0,
            supersedes_observation_id="original",
            correction_reason="Transcription error",
        )

        with pytest.raises(sqlite3.IntegrityError):
            _insert_observation(
                connection,
                flock_id=flock_id,
                daily_record_id=record_id,
                observation_id="branch",
                value_numeric=28.0,
                supersedes_observation_id="original",
                correction_reason="Another attempt against an old value",
            )

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_observation(
                connection,
                flock_id=flock_id,
                daily_record_id=record_id,
                observation_id="replace-branch",
                value_numeric=27.0,
                supersedes_observation_id="original",
                correction_reason="REPLACE must not branch history",
                replace=True,
            )

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_observation(
                connection,
                flock_id=flock_id,
                daily_record_id=record_id,
                observation_id="original",
                value_numeric=15.0,
                replace=True,
            )

        _insert_observation(
            connection,
            flock_id=flock_id,
            daily_record_id=record_id,
            observation_id="correction-2",
            value_numeric=28.5,
            supersedes_observation_id="correction-1",
            correction_reason="Follow-up correction",
        )

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE measurement_observations SET value_numeric = 25 "
                "WHERE observation_id = 'original'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM measurement_observations WHERE observation_id = 'original'"
            )

    with _connect() as connection:
        ids = [
            row[0]
            for row in connection.execute(
                """
                SELECT observation_id
                FROM measurement_observations
                ORDER BY recorded_at, observation_id
                """
            ).fetchall()
        ]

    assert ids == ["correction-1", "correction-2", "original"]
