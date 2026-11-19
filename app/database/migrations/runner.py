"""Explicit, transactional SQLite schema migration runner."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from .versions import add_measurement_observations

LEDGER_TABLE = "schema_migrations"
BASELINE_VERSION = "0000"
BASELINE_NAME = "existing_farms_flocks_daily_records"
_CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def _column_info(
    connection: sqlite3.Connection, table_name: str
) -> dict[str, tuple[str, int, str | None, int]]:
    return {
        row[1]: (row[2].upper(), row[3], row[4], row[5])
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


def _baseline_checksum(connection: sqlite3.Connection) -> str:
    """Fingerprint the baseline table DDL at the time it is first adopted."""
    rows = connection.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name IN ('farms', 'flocks', 'daily_records')
        ORDER BY name
        """
    ).fetchall()
    payload = "\n".join(
        f"{row[0]}:{' '.join((row[1] or '').split()).lower()}" for row in rows
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalise_sql(sql: str | None) -> str:
    return re.sub(r"\s+", "", sql or "").lower()


def _verify_required_tables(connection: sqlite3.Connection) -> None:
    missing_tables = {
        table for table in _BASELINE_COLUMNS if not _table_exists(connection, table)
    }
    if missing_tables:
        raise BaselineSchemaError(
            "Database is missing required PoultryGuard tables: "
            f"{sorted(missing_tables)}."
        )


def _verify_foreign_key_integrity(connection: sqlite3.Connection) -> None:
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise MigrationError(
            f"Database contains foreign-key violations: {len(violations)}."
        )


def _verify_baseline(connection: sqlite3.Connection) -> None:
    _verify_required_tables(connection)

    expected_column_info = {
        "farms": {
            "id": ("INTEGER", 0, None, 1),
            "farm_name": ("TEXT", 1, None, 0),
            "farmer_name": ("TEXT", 1, None, 0),
            "location": ("TEXT", 0, None, 0),
            "phone": ("TEXT", 0, None, 0),
            "email": ("TEXT", 0, None, 0),
            "production_type": ("TEXT", 0, None, 0),
            "created_at": ("TEXT", 1, "CURRENT_TIMESTAMP", 0),
            "updated_at": ("TEXT", 1, "CURRENT_TIMESTAMP", 0),
        },
        "flocks": {
            "id": ("INTEGER", 0, None, 1),
            "farm_id": ("INTEGER", 1, None, 0),
            "flock_name": ("TEXT", 1, None, 0),
            "species": ("TEXT", 1, None, 0),
            "production_type": ("TEXT", 0, None, 0),
            "breed": ("TEXT", 0, None, 0),
            "initial_count": ("INTEGER", 1, None, 0),
            "stocking_date": ("TEXT", 0, None, 0),
            "status": ("TEXT", 1, "'active'", 0),
            "created_at": ("TEXT", 1, "CURRENT_TIMESTAMP", 0),
            "updated_at": ("TEXT", 1, "CURRENT_TIMESTAMP", 0),
        },
        "daily_records": {
            "id": ("INTEGER", 0, None, 1),
            "flock_id": ("INTEGER", 1, None, 0),
            "record_date": ("TEXT", 1, None, 0),
            "feed_kg": ("REAL", 0, None, 0),
            "water_litres": ("REAL", 0, None, 0),
            "mortality": ("INTEGER", 1, "0", 0),
            "average_weight_kg": ("REAL", 0, None, 0),
            "temperature_c": ("REAL", 0, None, 0),
            "humidity_percent": ("REAL", 0, None, 0),
            "notes": ("TEXT", 0, None, 0),
            "created_at": ("TEXT", 1, "CURRENT_TIMESTAMP", 0),
        },
    }
    schema_differences: dict[str, dict[str, object]] = {}
    for table, expected in expected_column_info.items():
        actual = _column_info(connection, table)
        if actual != expected:
            schema_differences[table] = {
                "missing": sorted(set(expected) - set(actual)),
                "extra": sorted(set(actual) - set(expected)),
                "mismatched": sorted(
                    column
                    for column in set(actual) & set(expected)
                    if actual[column] != expected[column]
                ),
            }
    if schema_differences:
        raise BaselineSchemaError(
            f"Baseline columns/types/nullability/defaults differ: {schema_differences}."
        )

    required_foreign_keys = {
        "flocks": {("farms", "farm_id", "id", "CASCADE")},
        "daily_records": {("flocks", "flock_id", "id", "CASCADE")},
    }
    required_checks = {
        "flocks": ("check(initial_count>0)",),
        "daily_records": (
            "check(mortality>=0)",
            "check(humidity_percentisnullor(humidity_percent>=0andhumidity_percent<=100))",
        ),
    }
    for table, fragments in required_checks.items():
        definition = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()[0]
        normalised = _normalise_sql(definition)
        missing = [fragment for fragment in fragments if fragment not in normalised]
        if missing:
            raise BaselineSchemaError(
                f"Baseline table {table} is missing required constraints: {missing}."
            )

    for table, expected in required_foreign_keys.items():
        actual = _foreign_keys(connection, table)
        if expected != actual:
            raise BaselineSchemaError(
                f"Baseline foreign keys for {table} do not match the supported "
                f"schema. Expected {sorted(expected)}, got {sorted(actual)}."
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
    connection.execute(
        """
        CREATE TRIGGER trg_schema_migrations_no_update
        BEFORE UPDATE ON schema_migrations
        BEGIN
            SELECT RAISE(ABORT, 'schema migration history is append-only');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER trg_schema_migrations_no_delete
        BEFORE DELETE ON schema_migrations
        BEGIN
            SELECT RAISE(ABORT, 'schema migration history is append-only');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER trg_schema_migrations_no_replace
        BEFORE INSERT ON schema_migrations
        WHEN EXISTS (
            SELECT 1 FROM schema_migrations WHERE version = NEW.version
        )
        BEGIN
            SELECT RAISE(ABORT, 'schema migration history is append-only');
        END
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

    ledger_triggers = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
    }
    required_triggers = {
        "trg_schema_migrations_no_update",
        "trg_schema_migrations_no_delete",
        "trg_schema_migrations_no_replace",
    }
    if not required_triggers.issubset(ledger_triggers):
        raise MigrationError("Migration ledger append-only triggers are missing.")

    rows = _ledger_rows(connection)
    baseline = rows.get(BASELINE_VERSION)
    if (
        baseline is None
        or baseline[0] != BASELINE_NAME
        or not _CHECKSUM_PATTERN.fullmatch(baseline[1])
    ):
        raise MigrationError(
            "Migration ledger does not contain a valid PoultryGuard baseline "
            "fingerprint. Stop and inspect this database; do not auto-adopt it."
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
                f"Applied migration {version} does not match its recorded "
                "name/checksum."
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
        _verify_required_tables(connection)
        _verify_foreign_key_integrity(connection)
        _verify_ledger(connection)

    applied_now: list[str] = []
    try:
        connection.execute("BEGIN IMMEDIATE")

        if not ledger_exists:
            _create_ledger(connection)
            baseline_checksum = _baseline_checksum(connection)
            _record_migration(
                connection,
                BASELINE_VERSION,
                BASELINE_NAME,
                baseline_checksum,
            )
            rows: dict[str, tuple[str, str]] = {
                BASELINE_VERSION: (BASELINE_NAME, baseline_checksum)
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
    """Return read-only migration status after validating baseline or ledger."""
    if not _table_exists(connection, LEDGER_TABLE):
        _verify_baseline(connection)
        return {
            "baseline_adoption_required": True,
            "applied_versions": [],
            "pending_versions": [migration.version for migration in MIGRATIONS],
        }

    _verify_required_tables(connection)
    _verify_foreign_key_integrity(connection)
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
