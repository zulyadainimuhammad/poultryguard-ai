"""Explicit, transactional SQLite schema migration runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import sqlite3
from typing import Callable

from .versions import add_measurement_observations

LEDGER_TABLE = "schema_migrations"
BASELINE_VERSION = "0000"
BASELINE_NAME = "existing_farms_flocks_daily_records"
BASELINE_CHECKSUM = (
    "sha256:"
    "a4c0f25d1ef4f9cde0d0f2e1a09b97c3"
    "0d4e5dcaa32c85cb7f1b4f0c1a0d5f12"
)


class MigrationError(RuntimeError):
    """Base exception for migration failures."""


class BaselineSchemaError(MigrationError):
    """Raised when an existing database does not match the supported baseline."""


class MigrationChecksumError(MigrationError):
    """Raised when an applied migration no longer matches its recorded checksum."""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    checksum: str
    upgrade: Callable[[sqlite3.Connection], None]
    validate: Callable[[sqlite3.Connection], None]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=add_measurement_observations.VERSION,
        name=add_measurement_observations.NAME,
        checksum=add_measurement_observations.CHECKSUM,
        upgrade=add_measurement_observations.upgrade,
        validate=add_measurement_observations.validate,
    ),
)

_BASELINE_COLUMNS = {
    "farms": {
        "id",
        "farm_name",
        "farmer_name",
        "location",
        "phone",
        "email",
        "production_type",
        "created_at",
        "updated_at",
    },
    "flocks": {
        "id",
        "farm_id",
        "flock_name",
        "species",
        "production_type",
        "breed",
        "initial_count",
        "stocking_date",
        "status",
        "created_at",
        "updated_at",
    },
    "daily_records": {
        "id",
        "flock_id",
        "record_date",
        "feed_kg",
        "water_litres",
        "mortality",
        "average_weight_kg",
        "temperature_c",
        "humidity_percent",
        "notes",
        "created_at",
    },
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    }


def _foreign_keys(
    connection: sqlite3.Connection, table_name: str
) -> set[tuple[str, str, str, str]]:
    return {
        (row[2], row[3], row[4], row[6].upper())
        for row in connection.execute(
            f'PRAGMA foreign_key_list("{table_name}")'
        ).fetchall()
    }


def _verify_baseline(connection: sqlite3.Connection) -> None:
    missing_tables = {
        table for table in _BASELINE_COLUMNS if not _table_exists(connection, table)
    }
    if missing_tables:
        raise BaselineSchemaError(
            "Database is not initialised with the PoultryGuard baseline schema; "
            f"missing tables: {sorted(missing_tables)}. Run the existing "
            "initialise_database() bootstrap on a new database before migrations."
        )

    missing_columns: dict[str, list[str]] = {}
    for table, expected in _BASELINE_COLUMNS.items():
        missing = expected - _columns(connection, table)
        if missing:
            missing_columns[table] = sorted(missing)
    if missing_columns:
        raise BaselineSchemaError(
            f"Baseline schema is incomplete; missing columns: {missing_columns}."
        )

    required_foreign_keys = {
        "flocks": {("farms", "farm_id", "id", "CASCADE")},
        "daily_records": {("flocks", "flock_id", "id", "CASCADE")},
    }
    for table, expected in required_foreign_keys.items():
        actual = _foreign_keys(connection, table)
        if not expected.issubset(actual):
            raise BaselineSchemaError(
                f"Baseline foreign keys for {table} do not match the supported "
                f"schema. Expected at least {sorted(expected)}, got {sorted(actual)}."
            )

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise BaselineSchemaError(
            f"Baseline database contains foreign-key violations: {len(violations)}."
        )


def _create_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"""
        CREATE TABLE {LEDGER_TABLE} (
            version TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _ledger_rows(connection: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    rows = connection.execute(
        f"SELECT version, name, checksum FROM {LEDGER_TABLE}"
    ).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def _record_migration(
    connection: sqlite3.Connection,
    version: str,
    name: str,
    checksum: str,
) -> None:
    connection.execute(
        f"""
        INSERT INTO {LEDGER_TABLE} (version, name, checksum, applied_at)
        VALUES (?, ?, ?, ?)
        """,
        (version, name, checksum, _utc_now()),
    )


def _verify_ledger(connection: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    columns = _columns(connection, LEDGER_TABLE)
    required = {"version", "name", "checksum", "applied_at"}
    if not required.issubset(columns):
        raise MigrationError(
            f"Migration ledger is malformed; expected columns {sorted(required)}."
        )

    rows = _ledger_rows(connection)
    baseline = rows.get(BASELINE_VERSION)
    if baseline != (BASELINE_NAME, BASELINE_CHECKSUM):
        raise MigrationError(
            "Migration ledger does not contain the recognised PoultryGuard "
            "baseline marker. Stop and inspect this database; do not auto-adopt it."
        )

    known = {migration.version: migration for migration in MIGRATIONS}
    unknown = set(rows) - {BASELINE_VERSION} - set(known)
    if unknown:
        raise MigrationError(
            f"Migration ledger contains unknown versions: {sorted(unknown)}."
        )

    for version, migration in known.items():
        recorded = rows.get(version)
        if recorded is None:
            continue
        if recorded != (migration.name, migration.checksum):
            raise MigrationChecksumError(
                f"Applied migration {version} does not match its recorded name/checksum."
            )
        migration.validate(connection)

    return rows


def migrate(connection: sqlite3.Connection) -> list[str]:
    """Adopt the known baseline and apply pending migrations on one connection.

    The caller owns the connection. The function requires an idle connection
    with foreign-key enforcement enabled. All ledger and DDL changes are made
    in one explicit transaction. It does not initialise a blank database:
    callers must first use the existing baseline bootstrap, initialise_database().
    """
    if connection.in_transaction:
        raise MigrationError("Migrations require an idle connection.")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise MigrationError("SQLite foreign-key enforcement must be enabled.")

    ledger_exists = _table_exists(connection, LEDGER_TABLE)
    observation_exists = _table_exists(connection, "measurement_observations")

    if not ledger_exists:
        if observation_exists:
            raise MigrationError(
                "measurement_observations exists without a migration ledger. "
                "Refusing to infer or adopt this partial state."
            )
        _verify_baseline(connection)
    else:
        _verify_baseline(connection)

    applied_now: list[str] = []
    try:
        connection.execute("BEGIN IMMEDIATE")

        if not ledger_exists:
            _create_ledger(connection)
            _record_migration(
                connection,
                BASELINE_VERSION,
                BASELINE_NAME,
                BASELINE_CHECKSUM,
            )
            rows: dict[str, tuple[str, str]] = {
                BASELINE_VERSION: (BASELINE_NAME, BASELINE_CHECKSUM)
            }
        else:
            rows = _verify_ledger(connection)

        for migration in MIGRATIONS:
            recorded = rows.get(migration.version)
            expected = (migration.name, migration.checksum)

            if recorded is not None:
                if recorded != expected:
                    raise MigrationChecksumError(
                        f"Applied migration {migration.version} checksum mismatch."
                    )
                migration.validate(connection)
                continue

            migration.upgrade(connection)
            migration.validate(connection)
            _record_migration(
                connection,
                migration.version,
                migration.name,
                migration.checksum,
            )
            applied_now.append(migration.version)

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise MigrationError(
                f"Migration produced {len(violations)} foreign-key violation(s)."
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return applied_now


def migration_status(connection: sqlite3.Connection) -> dict[str, object]:
    """Return read-only migration status after validating the baseline/ledger."""
    _verify_baseline(connection)
    if not _table_exists(connection, LEDGER_TABLE):
        return {
            "baseline_adoption_required": True,
            "applied_versions": [],
            "pending_versions": [migration.version for migration in MIGRATIONS],
        }

    rows = _verify_ledger(connection)
    applied = sorted(rows)
    pending = [
        migration.version for migration in MIGRATIONS if migration.version not in rows
    ]
    return {
        "baseline_adoption_required": False,
        "applied_versions": applied,
        "pending_versions": pending,
    }
