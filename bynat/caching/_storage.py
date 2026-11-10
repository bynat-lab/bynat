"""SQLite storage and persistence implementation for caching."""

import json
import logging
import os
import sqlite3

__all__ = [
    "SQLITE_DATABASE_NAME",
    "SQLITE_TIMEOUT_SECONDS",
    "SQLiteStorage",
    "connect_sqlite",
]

logger = logging.getLogger("bynat.caching.Caching")

SQLITE_DATABASE_NAME = "cache.sqlite3"
SQLITE_TIMEOUT_SECONDS = 30.0


def connect_sqlite(database_path: str, timeout: float = SQLITE_TIMEOUT_SECONDS) -> sqlite3.Connection:
    """Open and configure a SQLite connection for cache infrastructure."""
    connection = sqlite3.connect(database_path, timeout = timeout)
    try:
        connection.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection
    except Exception:
        connection.close()
        raise


class SQLiteStorage:
    """Encapsulates SQLite database persistence, schema creation, and queries."""

    def __init__(self, cache_dir_path: str, timeout: float = SQLITE_TIMEOUT_SECONDS) -> None:
        self.cache_dir_path = cache_dir_path
        self.timeout = timeout

    def get_database_path(self) -> str:
        """Return the SQLite database path for this cache directory."""
        return os.path.join(self.cache_dir_path, SQLITE_DATABASE_NAME)

    def connect(self) -> sqlite3.Connection:
        """Open and configure a SQLite connection for this storage."""
        return connect_sqlite(self.get_database_path(), timeout = self.timeout)

    def initialize(self, connect_fn: object | None = None) -> None:
        """Create the SQLite cache schema in one explicit transaction."""
        os.makedirs(self.cache_dir_path, exist_ok = True)
        connection = None

        try:
            connection = connect_fn() if callable(connect_fn) else self.connect()
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    func_name TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (func_name, bucket, key)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cache_entries_func_bucket
                ON cache_entries (func_name, bucket)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS migration_metadata (
                    source_name TEXT PRIMARY KEY,
                    migrated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                finally:
                    connection.close()
            raise
        else:
            connection.close()

    def rebuild_function_cache(self, func_name: str, connect_fn: object | None = None) -> dict:
        """Rebuild the nested cache for one function from its SQLite rows."""
        reconstructed: dict = {}
        connection = connect_fn() if callable(connect_fn) else self.connect()

        try:
            rows = connection.execute(
                "SELECT bucket, key, value_json FROM cache_entries "
                "WHERE func_name = ? ORDER BY bucket, key",
                (func_name,),
            ).fetchall()
        finally:
            connection.close()

        for bucket, key, value_json in rows:
            reconstructed.setdefault(bucket, {})[key] = json.loads(value_json)

        return reconstructed

    def save_diff(
        self,
        func_name: str,
        prepared_entries: list[tuple[str, str, str, str, str]],
        removal_identities: list[tuple[str, str, str]],
        connect_fn: object | None = None,
    ) -> bool:
        """Persist prepared entries and removals in one BEGIN IMMEDIATE transaction."""
        if not prepared_entries and not removal_identities:
            return True

        connection = None
        try:
            connection = connect_fn() if callable(connect_fn) else self.connect()
            connection.execute("BEGIN IMMEDIATE")
            if prepared_entries:
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (func_name, bucket, key, value_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    prepared_entries,
                )
            if removal_identities:
                connection.executemany(
                    "DELETE FROM cache_entries WHERE func_name = ? AND bucket = ? AND key = ?",
                    removal_identities,
                )
            connection.commit()
            return True
        except (sqlite3.Error, OSError) as error:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            logger.error("Could not save cache for '%s'. Details: %s", func_name, error)
            return False
        finally:
            if connection is not None:
                connection.close()
