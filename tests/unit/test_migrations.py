"""Tests for safe, additive SQLite schema migrations."""

from __future__ import annotations

import sqlite3

import app.database.connection as database_connection
import pytest
from app.database.migrations import runner
from app.database.migrations.versions import (
    add_correction_quality_review,
    add_measurement_observations,
)


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


def _insert_correction_request(
    connection,
    *,
    request_id="request-001",
    target_observation_id="obs-001",
    proposed_value_numeric=2.0,
    correction_reason="Corrected transcription",
    requested_at="2026-11-20T12:00:00Z",
    requested_by_user_id=None,
    replace=False,
):
    verb = "INSERT OR REPLACE" if replace else "INSERT"
    return connection.execute(
        f"""
        {verb} INTO measurement_correction_requests (
            request_id,
            target_observation_id,
            proposed_value_numeric,
            correction_reason,
            requested_by_user_id,
            requested_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            request_id,
            target_observation_id,
            proposed_value_numeric,
            correction_reason,
            requested_by_user_id,
            requested_at,
        ),
    )


def _insert_correction_event(
    connection,
    *,
    event_id="correction-event-001",
    request_id="request-001",
    outcome="rejected",
    outcome_reason="Reviewed",
    event_at="2026-11-20T13:00:00Z",
    created_observation_id=None,
    reviewed_by_user_id=None,
    replace=False,
):
    verb = "INSERT OR REPLACE" if replace else "INSERT"
    return connection.execute(
        f"""
        {verb} INTO measurement_correction_request_events (
            event_id,
            request_id,
            outcome,
            outcome_reason,
            reviewed_by_user_id,
            event_at,
            created_observation_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            request_id,
            outcome,
            outcome_reason,
            reviewed_by_user_id,
            event_at,
            created_observation_id,
        ),
    )


def _insert_quality_review_event(
    connection,
    *,
    event_id="quality-event-001",
    observation_id="candidate-001",
    decision="accepted",
    review_reason="Evidence checked",
    reviewed_at="2026-11-20T13:00:00Z",
    reviewed_by_user_id=None,
    replace=False,
):
    verb = "INSERT OR REPLACE" if replace else "INSERT"
    return connection.execute(
        f"""
        {verb} INTO measurement_quality_review_events (
            event_id,
            observation_id,
            decision,
            review_reason,
            reviewed_by_user_id,
            reviewed_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            observation_id,
            decision,
            review_reason,
            reviewed_by_user_id,
            reviewed_at,
        ),
    )


def test_migration_adopts_baseline_and_applies_schema_once(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)

    with _connect() as connection:
        assert runner.migration_status(connection) == {
            "baseline_adoption_required": True,
            "applied_versions": [],
            "pending_versions": ["0001", "0002"],
        }

    with _connect() as connection:
        assert runner.migrate(connection) == ["0001", "0002"]

    with _connect() as connection:
        assert runner.migrate(connection) == []
        status = runner.migration_status(connection)
        assert status["baseline_adoption_required"] is False
        assert status["applied_versions"] == ["0000", "0001", "0002"]
        assert status["pending_versions"] == []

        ledger = connection.execute(
            """
            SELECT version, name, checksum, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
        assert [row[0] for row in ledger] == ["0000", "0001", "0002"]
        assert len(ledger[0][2]) == 64
        assert ledger[1][2] == add_measurement_observations.CHECKSUM
        assert ledger[2][2] == add_correction_quality_review.CHECKSUM
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
            version="0003",
            name="add_farm_timezone",
            checksum="2" * 64,
            upgrade=add_farm_timezone,
            validate=validate_farm_timezone,
        ),
    )
    try:
        with _connect() as connection:
            assert runner.migrate(connection) == ["0003"]
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
        assert runner.migrate(connection) == ["0001", "0002"]

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


def test_baseline_with_foreign_key_violations_fails_closed(tmp_path, monkeypatch):
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
        *original[1:],
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
            version="0003",
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


def test_correction_review_migration_preserves_populated_legacy_and_observation_rows(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()
    registered_migrations = runner.MIGRATIONS

    try:
        runner.MIGRATIONS = registered_migrations[:1]
        with _connect() as connection:
            runner.migrate(connection)
            _insert_observation(
                connection,
                observation_id="preserved-observation",
                flock_id=flock_id,
                daily_record_id=record_id,
                value_numeric=4.5,
            )

        runner.MIGRATIONS = registered_migrations
        with _connect() as connection:
            assert runner.migrate(connection) == ["0002"]
            assert connection.execute("SELECT COUNT(*) FROM farms").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM flocks").fetchone()[0] == 1
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM daily_records WHERE id = ? AND flock_id = ?",
                    (record_id, flock_id),
                ).fetchone()[0]
                == 1
            )
            assert tuple(
                connection.execute(
                    """
                SELECT value_numeric, daily_record_id
                FROM measurement_observations
                WHERE observation_id = 'preserved-observation'
                """
                ).fetchone()
            ) == (4.5, record_id)
            assert add_correction_quality_review.validate(connection) is None
    finally:
        runner.MIGRATIONS = registered_migrations


def test_correction_review_migration_registers_tables_indexes_and_restrict_fks(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _seed_legacy_rows()

    with _connect() as connection:
        assert runner.migrate(connection) == ["0001", "0002"]
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
        for table_name, columns in expected_columns.items():
            assert {
                row[1]
                for row in connection.execute(
                    f"PRAGMA table_info('{table_name}')"
                ).fetchall()
            } == columns

        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        assert {
            "ix_measurement_correction_requests_target_requested_at",
            "ix_measurement_correction_requests_requested_at",
            "ix_measurement_correction_events_event_at",
            "ix_measurement_quality_review_events_reviewed_at",
        }.issubset(indexes)

        expected_foreign_keys = {
            "measurement_correction_requests": {
                ("measurement_observations", "target_observation_id", "RESTRICT"),
            },
            "measurement_correction_request_events": {
                ("measurement_correction_requests", "request_id", "RESTRICT"),
                ("measurement_observations", "created_observation_id", "RESTRICT"),
            },
            "measurement_quality_review_events": {
                ("measurement_observations", "observation_id", "RESTRICT"),
            },
        }
        for table_name, expected in expected_foreign_keys.items():
            actual = {
                (row[2], row[3], row[6].upper())
                for row in connection.execute(
                    f"PRAGMA foreign_key_list('{table_name}')"
                ).fetchall()
            }
            assert actual == expected


def test_multiple_requests_per_target_and_same_date_observations_are_allowed(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="observation-a",
            flock_id=flock_id,
            daily_record_id=record_id,
            value_numeric=1.0,
        )
        _insert_observation(
            connection,
            observation_id="observation-b",
            flock_id=flock_id,
            daily_record_id=record_id,
            value_numeric=5.0,
        )
        _insert_correction_request(
            connection,
            request_id="request-a1",
            target_observation_id="observation-a",
            proposed_value_numeric=2.0,
        )
        _insert_correction_request(
            connection,
            request_id="request-a2",
            target_observation_id="observation-a",
            proposed_value_numeric=3.0,
        )
        _insert_correction_request(
            connection,
            request_id="request-b1",
            target_observation_id="observation-b",
            proposed_value_numeric=6.0,
        )

        assert (
            connection.execute(
                "SELECT COUNT(*) FROM measurement_correction_requests"
            ).fetchone()[0]
            == 3
        )
        assert (
            connection.execute(
                """
            SELECT COUNT(*) FROM measurement_observations
            WHERE flock_id = ? AND metric_name = 'feed_kg' AND record_date = ?
            """,
                (flock_id, "2026-11-19"),
            ).fetchone()[0]
            == 2
        )


def test_quality_reviewed_pending_manual_observation_can_be_requested(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="candidate-accepted",
            flock_id=flock_id,
            daily_record_id=record_id,
            value_numeric=1.0,
            quality_status="pending_validation",
        )
        _insert_quality_review_event(connection)
        _insert_correction_request(
            connection,
            target_observation_id="candidate-accepted",
            proposed_value_numeric=2.0,
        )

        assert (
            connection.execute(
                "SELECT COUNT(*) FROM measurement_correction_requests"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize(
    "value",
    [float("inf"), float("-inf"), float("nan"), -0.1],
)
def test_correction_request_rejects_nonfinite_and_negative_values(
    tmp_path, monkeypatch, value
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, record_id = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection, flock_id=flock_id, daily_record_id=record_id, value_numeric=1.0
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_request(connection, proposed_value_numeric=value)


@pytest.mark.parametrize(
    ("metric_name", "value", "unit", "proposal"),
    [
        ("mortality", 2.0, "birds", 2.5),
        ("average_weight_kg", 1.0, "kg_per_bird", 0.0),
        ("humidity_percent", 50.0, "percent_relative_humidity", 100.1),
    ],
)
def test_correction_request_enforces_target_metric_value_rules(
    tmp_path, monkeypatch, metric_name, value, unit, proposal
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            flock_id=flock_id,
            observation_id="metric-target",
            metric_name=metric_name,
            value_numeric=value,
            unit=unit,
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_request(
                connection,
                target_observation_id="metric-target",
                proposed_value_numeric=proposal,
            )


def test_correction_request_rejects_noop_and_ineligible_targets(tmp_path, monkeypatch):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="target",
            flock_id=flock_id,
            value_numeric=1.0,
        )
        with pytest.raises(sqlite3.IntegrityError, match="not eligible"):
            _insert_correction_request(
                connection,
                target_observation_id="target",
                proposed_value_numeric=1.0,
            )

        _insert_observation(
            connection,
            observation_id="accepted-successor",
            flock_id=flock_id,
            value_numeric=2.0,
            supersedes_observation_id="target",
            correction_reason="Accepted correction",
        )
        with pytest.raises(sqlite3.IntegrityError, match="not eligible"):
            _insert_correction_request(
                connection,
                request_id="stale-request",
                target_observation_id="target",
                proposed_value_numeric=3.0,
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("request_id", " "),
        ("target_observation_id", " "),
        ("correction_reason", "  "),
        ("requested_at", "2026-11-20 12:00:00"),
        ("requested_by_user_id", " "),
    ],
)
def test_correction_request_rejects_empty_required_values_and_invalid_timestamp(
    tmp_path, monkeypatch, field, value
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(connection, flock_id=flock_id, value_numeric=1.0)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_request(connection, **{field: value})


def test_correction_events_enforce_outcomes_linkage_and_single_terminal_event(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="target",
            flock_id=flock_id,
            value_numeric=1.0,
        )
        _insert_correction_request(
            connection,
            target_observation_id="target",
            proposed_value_numeric=2.0,
        )

        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_event(
                connection,
                outcome="approved",
                created_observation_id=None,
            )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_event(
                connection,
                outcome="rejected",
                created_observation_id="target",
            )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_event(connection, outcome="unknown")

        _insert_correction_event(
            connection,
            outcome="rejected",
            outcome_reason="Value was not supported",
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_event(
                connection,
                event_id="second-event",
                outcome="invalidated",
                outcome_reason="Already rejected",
            )

        _insert_correction_request(
            connection,
            request_id="request-after-rejection",
            target_observation_id="target",
            proposed_value_numeric=3.0,
        )
        with pytest.raises(sqlite3.IntegrityError, match="stale target"):
            _insert_correction_event(
                connection,
                event_id="premature-invalidation",
                request_id="request-after-rejection",
                outcome="invalidated",
                outcome_reason="Target became stale",
            )
        _insert_observation(
            connection,
            observation_id="target-successor",
            flock_id=flock_id,
            value_numeric=3.0,
            supersedes_observation_id="target",
            correction_reason="Corrected transcription",
        )
        _insert_correction_event(
            connection,
            event_id="invalidated-event",
            request_id="request-after-rejection",
            outcome="invalidated",
            outcome_reason="Target became stale",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_id", " "),
        ("request_id", " "),
        ("outcome_reason", "  "),
        ("event_at", "2026-11-20T12:00:00+00:00"),
        ("reviewed_by_user_id", " "),
    ],
)
def test_correction_events_reject_empty_required_values_and_invalid_timestamp(
    tmp_path, monkeypatch, field, value
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(connection, flock_id=flock_id, value_numeric=1.0)
        _insert_correction_request(connection, proposed_value_numeric=2.0)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_correction_event(
                connection,
                **{field: value},
            )


def test_approved_event_must_point_to_observation_superseding_exact_request_target(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        for observation_id, value in (("target-a", 1.0), ("target-b", 5.0)):
            _insert_observation(
                connection,
                observation_id=observation_id,
                flock_id=flock_id,
                value_numeric=value,
            )
        _insert_correction_request(
            connection,
            target_observation_id="target-a",
            proposed_value_numeric=2.0,
            correction_reason="Target A correction",
        )
        _insert_observation(
            connection,
            observation_id="wrong-successor",
            flock_id=flock_id,
            value_numeric=2.0,
            supersedes_observation_id="target-b",
            correction_reason="Target A correction",
        )

        with pytest.raises(sqlite3.IntegrityError, match="exact target"):
            _insert_correction_event(
                connection,
                outcome="approved",
                outcome_reason="Approved",
                created_observation_id="wrong-successor",
            )

        _insert_observation(
            connection,
            observation_id="correct-successor",
            flock_id=flock_id,
            value_numeric=2.0,
            supersedes_observation_id="target-a",
            correction_reason="Target A correction",
        )
        _insert_correction_event(
            connection,
            outcome="approved",
            outcome_reason="Approved",
            created_observation_id="correct-successor",
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM measurement_observations "
                "WHERE observation_id = 'correct-successor'"
            )


def test_quality_review_event_constraints_and_pending_status_guard(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="candidate",
            flock_id=flock_id,
            value_numeric=1.0,
            quality_status="pending_validation",
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_quality_review_event(connection, decision="other")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_quality_review_event(connection, review_reason=" ")

        _insert_quality_review_event(connection, decision="rejected")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_quality_review_event(
                connection,
                event_id="second-review",
                decision="accepted",
            )

        _insert_observation(
            connection,
            observation_id="observed-row",
            flock_id=flock_id,
            value_numeric=1.0,
        )
        with pytest.raises(sqlite3.IntegrityError, match="pending_validation"):
            _insert_quality_review_event(
                connection,
                event_id="review-observed-row",
                observation_id="observed-row",
            )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_id", " "),
        ("observation_id", " "),
        ("review_reason", "  "),
        ("reviewed_at", "2026-11-20 13:00:00"),
        ("reviewed_by_user_id", " "),
    ],
)
def test_quality_review_events_reject_empty_required_values_and_invalid_timestamp(
    tmp_path, monkeypatch, field, value
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="candidate",
            flock_id=flock_id,
            value_numeric=1.0,
            quality_status="pending_validation",
        )
        with pytest.raises(sqlite3.IntegrityError):
            _insert_quality_review_event(connection, **{field: value})


def test_append_only_tables_reject_update_delete_and_replace_conflicts(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="target-a",
            flock_id=flock_id,
            value_numeric=1.0,
        )
        _insert_observation(
            connection,
            observation_id="target-b",
            flock_id=flock_id,
            value_numeric=5.0,
        )
        _insert_observation(
            connection,
            observation_id="candidate",
            flock_id=flock_id,
            value_numeric=1.0,
            quality_status="pending_validation",
        )
        _insert_correction_request(
            connection,
            request_id="request-a",
            target_observation_id="target-a",
            proposed_value_numeric=2.0,
        )
        _insert_correction_request(
            connection,
            request_id="request-b",
            target_observation_id="target-b",
            proposed_value_numeric=6.0,
        )
        _insert_correction_event(
            connection,
            request_id="request-a",
            outcome="rejected",
            outcome_reason="Rejected",
        )
        _insert_quality_review_event(connection)

        for sql in (
            "UPDATE measurement_correction_requests "
            "SET correction_reason = 'edited' WHERE request_id = 'request-a'",
            "DELETE FROM measurement_correction_requests "
            "WHERE request_id = 'request-a'",
            "UPDATE measurement_correction_request_events "
            "SET outcome_reason = 'edited' WHERE request_id = 'request-a'",
            "DELETE FROM measurement_correction_request_events "
            "WHERE request_id = 'request-a'",
            "UPDATE measurement_quality_review_events "
            "SET decision = 'rejected' WHERE observation_id = 'candidate'",
            "DELETE FROM measurement_quality_review_events "
            "WHERE observation_id = 'candidate'",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(sql)

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_correction_request(
                connection,
                request_id="request-a",
                target_observation_id="target-b",
                proposed_value_numeric=7.0,
                replace=True,
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_correction_event(
                connection,
                event_id="replacement-event-id",
                request_id="request-a",
                outcome="rejected",
                outcome_reason="Replace unique request conflict",
                replace=True,
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_correction_event(
                connection,
                event_id="correction-event-001",
                request_id="request-b",
                outcome="rejected",
                outcome_reason="Replace primary key conflict",
                replace=True,
            )
        _insert_observation(
            connection,
            observation_id="approved-correction",
            flock_id=flock_id,
            value_numeric=6.0,
            supersedes_observation_id="target-b",
            correction_reason="Corrected transcription",
        )
        _insert_correction_event(
            connection,
            event_id="approved-event",
            request_id="request-b",
            outcome="approved",
            created_observation_id="approved-correction",
        )
        _insert_observation(
            connection,
            observation_id="target-c",
            flock_id=flock_id,
            value_numeric=10.0,
        )
        _insert_correction_request(
            connection,
            request_id="request-c",
            target_observation_id="target-c",
            proposed_value_numeric=11.0,
        )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_correction_event(
                connection,
                event_id="replacement-created-observation",
                request_id="request-c",
                outcome="approved",
                created_observation_id="approved-correction",
                replace=True,
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_quality_review_event(
                connection,
                event_id="replacement-review-id",
                observation_id="candidate",
                replace=True,
            )
        _insert_observation(
            connection,
            observation_id="candidate-two",
            flock_id=flock_id,
            value_numeric=2.0,
            quality_status="pending_validation",
        )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            _insert_quality_review_event(
                connection,
                event_id="quality-event-001",
                observation_id="candidate-two",
                replace=True,
            )


def test_restrict_foreign_keys_protect_requests_and_decision_history(
    tmp_path, monkeypatch
):
    _initialised_database(tmp_path, monkeypatch)
    _, flock_id, _ = _seed_legacy_rows()

    with _connect() as connection:
        runner.migrate(connection)
        _insert_observation(
            connection,
            observation_id="target",
            flock_id=flock_id,
            value_numeric=1.0,
        )
        _insert_observation(
            connection,
            observation_id="candidate",
            flock_id=flock_id,
            value_numeric=2.0,
            quality_status="pending_validation",
        )
        _insert_correction_request(
            connection,
            target_observation_id="target",
            proposed_value_numeric=2.0,
        )
        _insert_correction_event(connection, outcome="rejected")
        _insert_quality_review_event(connection, observation_id="candidate")

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM measurement_correction_requests "
                "WHERE request_id = 'request-001'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM measurement_observations WHERE observation_id = 'target'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM measurement_observations "
                "WHERE observation_id = 'candidate'"
            )
