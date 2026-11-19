# SQLite Unit-of-Work

**Status:** Implemented on the feature branch; review required before merge.

## Purpose

A Unit-of-Work creates one write transaction and binds the farm, flock and daily-record repositories to the same SQLite connection. Repository methods do not commit or close an injected connection. The Unit-of-Work owns commit, rollback and connection closure.

## Lifecycle

1. Entering the Unit-of-Work opens a connection with the existing connection factory.
2. It executes `BEGIN IMMEDIATE` so a write workflow obtains SQLite's writer reservation before performing validation reads.
3. The repositories share that connection.
4. Successful exit commits; exceptional exit rolls back.
5. The existing connection context-manager contract closes the connection in either case.

Standalone repository usage remains supported: when a repository is constructed without an injected connection, each method obtains and closes its own connection as before.

## Current integration

`FarmService.create_daily_record()` performs flock lookup, duplicate-date validation, cumulative-mortality validation and insertion inside one Unit-of-Work. The existing `allow_duplicate=True` override remains available; no new unique constraint is introduced.

## Safety and scope

- No schema changes or migrations are included.
- No existing database file is opened by this change; tests use temporary SQLite databases or in-memory fixtures.
- Measurement-observation dual-write is not implemented yet. It can later join the same Unit-of-Work once its schema and correction semantics are approved.
- The Unit-of-Work is write-oriented. Read-only reporting repositories continue to use their existing standalone connection scope.
