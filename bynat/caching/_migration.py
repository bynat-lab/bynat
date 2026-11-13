"""Legacy JSON cache migration and quarantine logic."""

import json
import logging
import os
import sqlite3
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from ._storage import SQLiteStorage

__all__ = [
    "migrate_legacy_json_cache",
    "quarantine_corrupt_cache_file",
]

logger = logging.getLogger("bynat.caching.Caching")


def quarantine_corrupt_cache_file(file_path: str) -> str | None:
    """Move a corrupt cache file aside without overwriting a quarantine."""
    quarantine_path = None

    for _ in range(10):
        candidate = f"{file_path}.corrupt.{time.time_ns()}.{uuid.uuid4().hex}"
        try:
            descriptor = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            quarantine_path = candidate
            break
        except FileExistsError:
            continue

    if quarantine_path is None:
        return None

    try:
        os.replace(file_path, quarantine_path)
        return quarantine_path
    except FileNotFoundError:
        # Another process may have quarantined the source first.
        try:
            os.remove(quarantine_path)
        except OSError:
            pass
        return None
    except OSError:
        try:
            os.remove(quarantine_path)
        except OSError:
            pass
        return None


def migrate_legacy_json_cache(
    cache_dir_path: str,
    func_name: str,
    file_path: str,
    storage: SQLiteStorage,
    initialize_fn: Callable[[], None] | None = None,
    connect_fn: Callable[[], sqlite3.Connection] | None = None,
) -> None:
    """Import one legacy JSON cache into SQLite, without changing the API."""
    source_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        return

    try:
        with open(file_path, encoding = "utf-8") as cache:
            loaded_cache = json.load(cache)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        try:
            quarantine_path = quarantine_corrupt_cache_file(file_path)
            location = (
                f"moved it to '{quarantine_path}'"
                if quarantine_path is not None
                else "another process may have moved it aside"
            )
        except OSError as quarantine_error:
            location = f"could not move it aside: {quarantine_error}"
        logger.warning(
            "Legacy cache file '%s' is corrupted; %s. Details: %s",
            file_path, location, error,
        )
        return
    except OSError as error:
        logger.warning("Could not read legacy cache file '%s'. Details: %s", file_path, error)
        return

    if not isinstance(loaded_cache, dict):
        try:
            quarantine_path = quarantine_corrupt_cache_file(file_path)
            location = (
                f"moved it to '{quarantine_path}'"
                if quarantine_path is not None
                else "another process may have moved it aside"
            )
        except OSError as quarantine_error:
            location = f"could not move it aside: {quarantine_error}"
        logger.warning(
            "Legacy cache file '%s' has an invalid top-level JSON value; %s.",
            file_path, location,
        )
        return

    for bucket, entries in loaded_cache.items():
        if not isinstance(entries, dict):
            logger.warning(
                "Legacy cache file '%s' is unsupported: bucket '%s' is not a JSON object; "
                "source preserved for recovery.",
                file_path, bucket,
            )
            return

    prepared_entries = []
    created_at = datetime.now(UTC).isoformat()
    try:
        for bucket, entries in loaded_cache.items():
            for key, value in entries.items():
                prepared_entries.append(
                    (func_name, bucket, key, json.dumps(value, ensure_ascii = False), created_at)
                )
    except (TypeError, ValueError) as error:
        logger.warning(
            "Legacy cache file '%s' contains an unsupported value; source preserved for recovery. "
            "Details: %s",
            file_path, error,
        )
        return

    connection = None
    try:
        for attempt in range(6):
            try:
                if callable(initialize_fn):
                    initialize_fn()
                else:
                    storage.initialize(connect_fn = connect_fn)
                break
            except sqlite3.OperationalError as error:
                if "locked" not in str(error).lower() or attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))

        connection = connect_fn() if callable(connect_fn) else storage.connect()
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM migration_metadata WHERE source_name = ?",
            (source_name,),
        ).fetchone() is not None:
            connection.rollback()
            return

        connection.executemany(
            """
            INSERT OR IGNORE INTO cache_entries
            (func_name, bucket, key, value_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            prepared_entries,
        )
        connection.execute(
            "INSERT INTO migration_metadata (source_name, migrated_at) VALUES (?, ?)",
            (source_name, datetime.now(UTC).isoformat()),
        )
        connection.commit()
    except Exception:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        raise
    finally:
        if connection is not None:
            connection.close()


# Internal aliases
_quarantine_corrupt_cache_file = quarantine_corrupt_cache_file
_migrate_legacy_json_cache = migrate_legacy_json_cache
