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

logger = logging.getLogger(__name__)

SQLITE_DATABASE_NAME = "cache.sqlite3"
"""File name of the SQLite cache database inside the cache directory."""

SQLITE_TIMEOUT_SECONDS = 30.0
"""SQLite busy timeout in seconds, also used as the WAL busy timeout."""


def connect_sqlite(database_path: str, timeout: float = SQLITE_TIMEOUT_SECONDS) -> sqlite3.Connection:
    """Open and configure a SQLite connection for cache infrastructure.

    Applies `PRAGMA busy_timeout`, `PRAGMA journal_mode = WAL`, and
    `PRAGMA synchronous = FULL`. If any pragma fails the connection is closed
    and the error propagates.

    Args:
        database_path (str): Path to the SQLite database file.
        timeout (float): Busy timeout in seconds. Defaults to
            `SQLITE_TIMEOUT_SECONDS`.

    Returns:
        sqlite3.Connection: The configured connection.

    Raises:
        sqlite3.Error: If the connection or a pragma fails.
    """
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
    """Encapsulates SQLite database persistence, schema creation, and queries.

    One instance belongs to one cache directory; the database file is
    `cache.sqlite3` inside it. The directory is created by `initialize`,
    not by the constructor.

    Attributes:
        cache_dir_path (str): Directory holding the database file.
        timeout (float): Busy timeout in seconds used for new connections.
    """

    def __init__(self, cache_dir_path: str, timeout: float = SQLITE_TIMEOUT_SECONDS) -> None:
        """Bind the storage to a cache directory.

        Args:
            cache_dir_path (str): Directory holding the database file.
            timeout (float): Busy timeout in seconds. Defaults to
                `SQLITE_TIMEOUT_SECONDS`.
        """
        self.cache_dir_path = cache_dir_path
        self.timeout = timeout

    def get_database_path(self) -> str:
        """Return the SQLite database path for this cache directory.

        Returns:
            str: `cache_dir_path` joined with `SQLITE_DATABASE_NAME`.
        """
        return os.path.join(self.cache_dir_path, SQLITE_DATABASE_NAME)

    def connect(self) -> sqlite3.Connection:
        """Open and configure a SQLite connection for this storage.

        Returns:
            sqlite3.Connection: The configured connection.

        Raises:
            sqlite3.Error: If the connection or a pragma fails.
        """
        return connect_sqlite(self.get_database_path(), timeout = self.timeout)

    def initialize(self, connect_fn: object | None = None) -> None:
        """Create the SQLite cache schema in one explicit transaction.

        Creates the cache directory when missing, then issues
        `BEGIN IMMEDIATE` and creates the `cache_entries` table, its
        `(func_name, bucket)` index, and the `migration_metadata` table. On
        failure the transaction is rolled back and the connection closed.

        Args:
            connect_fn (callable | None): Zero-argument connection factory
                used instead of `self.connect`, so callers can pass a shared
                connection. Defaults to None.

        Raises:
            sqlite3.Error: If the schema creation or commit fails.
        """
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
        """Rebuild the nested cache for one function from its SQLite rows.

        Reads every `cache_entries` row for `func_name`, ordered by bucket and
        key, and decodes each `value_json` blob with `json.loads`. The result
        mirrors the legacy JSON shape: `{bucket: {key: decoded_value}}`.

        Args:
            func_name (str): Function identifier whose rows should be read.
            connect_fn (callable | None): Zero-argument connection factory
                used instead of `self.connect`. Defaults to None.

        Returns:
            dict: Nested `{bucket: {key: value}}` mapping for the function.
            Empty when the function has no rows.
        """
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
        """Persist prepared entries and removals in one BEGIN IMMEDIATE transaction.

        Additions and changes are written with `INSERT OR REPLACE`, so a
        later committed writer wins for the same `(func_name, bucket, key)`;
        removals use an exact `(func_name, bucket, key)` `DELETE`. The
        transaction is rolled back and the failure logged on error, and the
        connection is always closed.

        Args:
            func_name (str): Function identifier the rows belong to.
            prepared_entries (list[tuple[str, str, str, str, str]]): Rows of
                `(func_name, bucket, key, value_json, created_at)`.
            removal_identities (list[tuple[str, str, str]]): Identities of
                `(func_name, bucket, key)` to delete.
            connect_fn (callable | None): Zero-argument connection factory
                used instead of `self.connect`. Defaults to None.

        Returns:
            bool: True when the transaction committed (including when there
            was nothing to write), False when it failed and was rolled back.
        """
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
