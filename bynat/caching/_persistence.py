"""
Private core logic for loading and saving function caches through SQLite.

This module holds the orchestration that sits between the public
:class:`bynat.caching.manager.CacheManager` and the lower-level
:mod:`bynat.caching._storage` and :mod:`bynat.caching._migration` modules.
Functions here receive the manager's state explicitly and never keep state of
their own.

This module is private and not part of the public API. Use
:class:`CacheManager` instead.
"""

import logging
import sqlite3

from ._internal import compute_cache_diff, legacy_json_path
from ._migration import migrate_legacy_json_cache
from ._storage import SQLiteStorage

__all__ = ["load_cache", "persist_cache"]

logger = logging.getLogger(__name__)


def load_cache(storage: SQLiteStorage, func_name: str) -> dict:
    """
    Load one function's cache state from SQLite, migrating legacy JSON first.

    Creates the SQLite schema when missing, imports the function's legacy
    `<func_name>_cache.json` file when present (at most once), then rebuilds
    the nested cache from its SQLite rows. Explicit `None` and nested
    lists/dicts round-trip faithfully because every value is decoded with
    `json.loads`.

    Args:
        storage (SQLiteStorage): Storage bound to the cache directory.
        func_name (str): Validated function identifier whose cache should be
            loaded.

    Returns:
        dict: Nested `{bucket: {key: value}}` mapping for the function. Empty
        when the function has no rows.

    Raises:
        sqlite3.Error: If schema creation, migration, or the read fails.
    """
    storage.initialize()

    migrate_legacy_json_cache(
        storage.cache_dir_path,
        func_name,
        legacy_json_path(storage.cache_dir_path, func_name),
        storage,
    )

    return storage.rebuild_function_cache(func_name)


def persist_cache(
    storage: SQLiteStorage,
    func_name: str,
    live_cache: dict,
    baseline: dict | None,
) -> bool:
    """
    Persist the difference between a live cache and its baseline to SQLite.

    Serialization happens first via :func:`compute_cache_diff`; additions,
    changes, and removals are then applied together in one transaction by
    :meth:`SQLiteStorage.save_diff`. Serialization, locking, transaction, and
    commit failures are logged and swallowed, so the caller keeps its baseline
    and retries on the next save.

    Args:
        storage (SQLiteStorage): Storage bound to the cache directory.
        func_name (str): Validated function identifier whose cache is saved.
        live_cache (dict): Current in-memory `{bucket: {key: value}}` cache.
        baseline (dict | None): Snapshot taken at load or last successful
            save. A non-dict value is treated as an empty baseline.

    Returns:
        bool: True when changes were committed and the caller should advance
        its baseline. False when there was nothing to write or the save
        failed.
    """
    if not isinstance(baseline, dict):
        baseline = {}

    try:
        prepared_entries, removal_identities = compute_cache_diff(func_name, live_cache, baseline)
    except (TypeError, ValueError) as error:
        logger.error("Could not save cache for '%s'. Details: %s", func_name, error)
        return False

    if not prepared_entries and not removal_identities:
        return False

    try:
        storage.initialize()
        return storage.save_diff(func_name, prepared_entries, removal_identities)
    except (sqlite3.Error, OSError) as error:
        logger.error("Could not save cache for '%s'. Details: %s", func_name, error)
        return False
