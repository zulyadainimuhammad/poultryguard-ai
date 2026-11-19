import sqlite3
from pathlib import Path


class _ClosingSQLiteConnection(sqlite3.Connection):
    """SQLite connection that closes after its context manager exits."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "poultryguard.db"


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled.

    Use the returned connection as a context manager. On exit, SQLite commits
    or rolls back the transaction and the connection is then closed.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        factory=_ClosingSQLiteConnection,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialise_database() -> None:
    """Create the initial PoultryGuard database tables."""

    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_name TEXT NOT NULL,
                farmer_name TEXT NOT NULL,
                location TEXT,
                phone TEXT,
                email TEXT,
                production_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS flocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                flock_name TEXT NOT NULL,
                species TEXT NOT NULL,
                production_type TEXT,
                breed TEXT,
                initial_count INTEGER NOT NULL CHECK (initial_count > 0),
                stocking_date TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (farm_id)
                    REFERENCES farms(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS daily_records (
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
                    ON DELETE CASCADE,

                CHECK (mortality >= 0),

                CHECK (
                    humidity_percent IS NULL
                    OR (
                        humidity_percent >= 0
                        AND humidity_percent <= 100
                    )
                )
            );
            """
        )
