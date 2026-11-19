"""Shared SQLite transaction boundary for multi-repository use cases."""

from collections.abc import Callable
import sqlite3

from .connection import get_connection
from .repositories import DailyRecordRepository, FarmRepository, FlockRepository


class UnitOfWork:
    """Coordinate repositories on one connection and one write transaction.

    The Unit-of-Work owns the connection it creates. Repositories receive that
    connection but never commit or close it. Exiting the Unit-of-Work commits
    when the body succeeds and rolls back when the body raises, then closes the
    connection through the project's connection context-manager contract.

    A write-oriented transaction starts with BEGIN IMMEDIATE so concurrent
    writers do not both validate against the same pre-write state.
    """

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection] | None = None,
    ) -> None:
        self._connection_factory = connection_factory or get_connection
        self._connection: sqlite3.Connection | None = None

        self.farms: FarmRepository
        self.flocks: FlockRepository
        self.daily_records: DailyRecordRepository

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active transaction connection."""
        if self._connection is None:
            raise RuntimeError("UnitOfWork must be entered before use.")
        return self._connection

    def __enter__(self) -> "UnitOfWork":
        if self._connection is not None:
            raise RuntimeError("UnitOfWork is already active.")

        connection = self._connection_factory()
        try:
            connection.execute("BEGIN IMMEDIATE")
        except BaseException:
            connection.close()
            raise

        self._connection = connection
        self.farms = FarmRepository(connection=connection)
        self.flocks = FlockRepository(connection=connection)
        self.daily_records = DailyRecordRepository(connection=connection)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool | None:
        connection = self._connection
        self._connection = None

        if connection is None:
            return False

        try:
            if exc_type is None:
                connection.commit()
            else:
                connection.rollback()
        finally:
            connection.close()

        return False
