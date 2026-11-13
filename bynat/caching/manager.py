"""High-level cache manager and process-wide cache registry."""

import copy
import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from os import PathLike

from ._migration import (
    migrate_legacy_json_cache,
    quarantine_corrupt_cache_file,
)
from ._storage import (
    SQLITE_DATABASE_NAME,
    SQLITE_TIMEOUT_SECONDS,
    SQLiteStorage,
)

__all__ = [
    "CACHE_DIR_ENV_VAR",
    "DEFAULT_CACHE_DIR",
    "CacheManager",
    "resolve_cache_dir",
    "shared_cache_manager",
]

# Keep the pre-0.4 logger name so existing logging configuration still applies.
logger = logging.getLogger("bynat.caching.Caching")

CACHE_DIR_ENV_VAR = "BYNAT_CACHE_DIR"
DEFAULT_CACHE_DIR = "Settings/Cache Data/Automated"
_SQLITE_DATABASE_NAME = SQLITE_DATABASE_NAME
_SQLITE_TIMEOUT_SECONDS = SQLITE_TIMEOUT_SECONDS


def resolve_cache_dir(cache_dir: str | PathLike | None) -> str | PathLike:
    """Return `cache_dir`, else `$BYNAT_CACHE_DIR`, else the legacy relative default."""
    if cache_dir is not None:
        return cache_dir

    return os.environ.get(CACHE_DIR_ENV_VAR) or DEFAULT_CACHE_DIR


class CacheManager:
    """
    Manage SQLite-backed caches for function-level and column-level
    operations.

    Notes:
        Each function's entries are stored in a shared SQLite database inside
        the configured cache directory (with automatic one-time migration from
        legacy per-function JSON cache files). Individual methods can then store
        nested objects keyed by column name or another logical cache bucket.
    """

    def __init__(self, cache_dir: str | PathLike | None = None) -> None:
        """
        Initialize the cache manager and resolve its storage directory.

        Relative paths are resolved from the current working directory. Absolute
        paths are used as provided. User home markers (`~`) and environment
        variables are expanded before the path is normalized.

        Args:
            cache_dir (str | os.PathLike | None): Directory where the SQLite
                cache database is stored. When None, the `BYNAT_CACHE_DIR`
                environment variable is used if set, otherwise
                `"Settings/Cache Data/Automated"` relative to the working
                directory.

        Raises:
            TypeError: If `cache_dir` is not a string or path-like object.
            ValueError: If `cache_dir` is empty after normalization.
        """
        cache_dir = resolve_cache_dir(cache_dir)

        if not isinstance(cache_dir, (str, PathLike)):
            raise TypeError("cache_dir must be a string or path-like object")

        cache_dir = os.fspath(cache_dir)

        if not isinstance(cache_dir, str):
            raise TypeError("cache_dir must resolve to a string path")

        cache_dir = cache_dir.strip()

        if not cache_dir:
            raise ValueError("cache_dir cannot be empty")

        expanded_cache_dir = os.path.expandvars(os.path.expanduser(cache_dir))

        self.cache_dir_path = os.path.abspath(expanded_cache_dir)
        self.cache_dir = os.path.normpath(expanded_cache_dir)

        self._storage = SQLiteStorage(self.cache_dir_path)

        self.caches: dict[str, dict] = {}
        self._baselines: dict[str, dict] = {}

    def _get_database_path(self) -> str:
        """Return the SQLite database path for this cache directory."""
        return self._storage.get_database_path()

    def _connect_sqlite(self) -> sqlite3.Connection:
        """Open and configure a SQLite connection for cache infrastructure."""
        return self._storage.connect()

    def _initialize_sqlite(self) -> None:
        """Create the SQLite cache schema in one explicit transaction."""
        self._storage.initialize(connect_fn = self._connect_sqlite)

    def _quarantine_corrupt_cache_file(self, file_path: str) -> str | None:
        """Move a corrupt cache file aside without overwriting a quarantine."""
        return quarantine_corrupt_cache_file(file_path)

    def _migrate_legacy_json_cache(self, func_name: str) -> None:
        """Import one legacy JSON cache into SQLite, without changing the API."""
        func_name = self._validate_cache_key(func_name, "func_name")
        file_path = self._get_file_path(func_name)
        migrate_legacy_json_cache(
            self.cache_dir_path,
            func_name,
            file_path,
            self._storage,
            initialize_fn = self._initialize_sqlite,
            connect_fn = self._connect_sqlite,
        )

    def _migrate_legacy_cache(self, func_name: str) -> None:
        """Compatibility name for the reusable legacy migration helper."""
        self._migrate_legacy_json_cache(func_name)

    def _rebuild_function_cache_from_sqlite(self, func_name: str) -> dict:
        """
        Rebuild the nested cache for one function from its SQLite rows.

        Reads every ``cache_entries`` row for ``func_name`` and decodes each
        ``value_json`` blob back into a Python value with ``json.loads``, so
        explicit ``None`` and nested lists/dicts round-trip faithfully. The
        result mirrors the legacy JSON shape: ``{bucket: {key: decoded_value}}``.

        Args:
            func_name (str): Function identifier whose rows should be rebuilt.

        Returns:
            dict: Nested ``{bucket: {key: value}}`` mapping for the function.
            An empty dictionary is returned when the function has no rows.
        """
        func_name = self._validate_cache_key(func_name, "func_name")
        return self._storage.rebuild_function_cache(func_name, connect_fn = self._connect_sqlite)

    def _validate_cache_key(self, key: str, key_name: str) -> str:
        """
        Validate a cache key before using it in file paths or dictionaries.

        Args:
            key (str): Cache key value to validate.
            key_name (str): Human-readable argument name for error messages.

        Returns:
            str: Normalized cache key.

        Raises:
            TypeError: If `key` is not a string.
            ValueError: If `key` is empty or contains path separators.
        """
        if not isinstance(key, str):
            raise TypeError(f"{key_name} must be a string")

        key = key.strip()

        if not key:
            raise ValueError(f"{key_name} cannot be empty")

        if os.path.basename(key) != key or os.path.sep in key or (os.path.altsep and os.path.altsep in key):
            raise ValueError(f"{key_name} cannot contain path separators")

        return key

    def _get_file_path(self, func_name: str) -> str:
        """
        Build the cache-file path for a specific function name.

        Args:
            func_name (str): The logical function identifier used as the cache
                filename prefix.

        Returns:
            str: Absolute path to the JSON cache file for the requested
            function.

        Raises:
            TypeError: If `func_name` is not a string.
            ValueError: If `func_name` is empty or contains path separators.
        """
        func_name = self._validate_cache_key(func_name, "func_name")

        return os.path.join(self.cache_dir_path, f"{func_name}_cache.json")

    def load_function_cache(self, func_name: str) -> dict:
        """
        Load a function cache from SQLite into memory on first access.

        The SQLite backend is created on first public access for any function.
        Before reading, any legacy JSON cache for the function is migrated into
        SQLite through the accepted migration helper, then the function's cache
        is rebuilt from its SQLite rows via
        ``_rebuild_function_cache_from_sqlite``. On first load the reconstructed
        state is deep-copied into a private per-function baseline
        (``_baselines[func_name]``) so the snapshot never shares nested mutable
        references with the live cache. The returned dict is memoized, so
        repeated lookups and in-place mutations stay consistent for the lifetime
        of the manager.

        Args:
            func_name (str): Function identifier whose cache should be loaded.

        Returns:
            dict: The in-memory cache object for the requested function, backed
            by SQLite. A function with no cached entries returns an empty
            dictionary.

        Raises:
            TypeError: If `func_name` is not a string.
            ValueError: If `func_name` is empty or contains path separators.
        """
        func_name = self._validate_cache_key(func_name, "func_name")

        if func_name not in self.caches:
            self._initialize_sqlite()
            self._migrate_legacy_json_cache(func_name)
            self.caches[func_name] = self._rebuild_function_cache_from_sqlite(func_name)
            self._baselines[func_name] = copy.deepcopy(self.caches[func_name])

        return self.caches[func_name]

    def get_column_cache(self, func_name: str, col_name: str) -> dict:
        """
        Return a nested cache bucket for a specific function and column.

        Args:
            func_name (str): Parent function cache name.
            col_name (str): Nested cache key, commonly a column name.

        Returns:
            dict: The cache dictionary stored under the requested nested key.
            The dictionary is created automatically if it does not yet exist.
        """
        col_name = self._validate_cache_key(col_name, "col_name")
        func_cache = self.load_function_cache(func_name)

        if col_name not in func_cache or not isinstance(func_cache[col_name], dict):
            func_cache[col_name] = {}

        return func_cache[col_name]

    def save_function_cache(self, func_name: str) -> None:
        """
        Persist newly added, changed, or removed entries of a function cache to SQLite.

        The live in-memory cache is diffed against the deep baseline snapshot
        captured at load time (``_baselines[func_name]``). Entries that were
        newly added or whose value changed are written, and every baseline
        ``(bucket, key)`` identity no longer present in the live cache — including
        the keys of an entirely removed bucket — is deleted. This detects nested
        JSON-compatible mutations and explicit ``None`` because each changed
        value is compared as a whole and then re-serialized. Serialization
        happens first; additions, changes, and removals are then applied
        together, in one explicit ``BEGIN IMMEDIATE`` transaction: added and
        changed rows use ``INSERT OR REPLACE`` conflict semantics so that writes
        to the same key resolve to the last committed writer while disjoint keys
        merge, and each removed identity is deleted with an exact
        ``(func_name, bucket, key)`` ``DELETE`` so no broad bucket delete is ever
        issued.

        The deep baseline is advanced to a copy of the live cache only after the
        transaction commits. Serialization, locking, transaction, or commit
        failures are logged and swallowed: the transaction is rolled back, the
        baseline is left unchanged, and the pending in-memory changes are
        preserved so the next save re-diffs against the same baseline and retries.

        Args:
            func_name (str): Function identifier whose cache should be written.

        Returns:
            None
        """
        func_name = self._validate_cache_key(func_name, "func_name")

        if func_name not in self.caches:
            self.caches[func_name] = {}

        live_cache = self.caches[func_name]
        baseline = self._baselines.get(func_name)

        if not isinstance(baseline, dict):
            baseline = {}

        prepared_entries = []
        removal_identities = []
        created_at = datetime.now(UTC).isoformat()

        try:
            for bucket, entries in live_cache.items():
                if not isinstance(entries, dict):
                    continue

                baseline_bucket = baseline.get(bucket)

                if not isinstance(baseline_bucket, dict):
                    baseline_bucket = {}

                for key, value in entries.items():
                    if key in baseline_bucket and baseline_bucket[key] == value:
                        continue

                    prepared_entries.append(
                        (
                            func_name,
                            bucket,
                            key,
                            json.dumps(value, ensure_ascii = False),
                            created_at,
                        )
                    )

            for bucket, baseline_entries in baseline.items():
                if not isinstance(baseline_entries, dict):
                    continue

                live_bucket = live_cache.get(bucket)

                if isinstance(live_bucket, dict):
                    removed_keys = [key for key in baseline_entries if key not in live_bucket]
                else:
                    removed_keys = list(baseline_entries)

                for key in removed_keys:
                    removal_identities.append((func_name, bucket, key))
        except (TypeError, ValueError) as error:
            logger.error("Could not save cache for '%s'. Details: %s", func_name, error)
            return

        if not prepared_entries and not removal_identities:
            return

        try:
            self._initialize_sqlite()
            success = self._storage.save_diff(
                func_name,
                prepared_entries,
                removal_identities,
                connect_fn = self._connect_sqlite,
            )
            if success:
                self._baselines[func_name] = copy.deepcopy(live_cache)
        except (sqlite3.Error, OSError) as error:
            logger.error("Could not save cache for '%s'. Details: %s", func_name, error)

    def delete_column_cache(self, func_name: str, col_name: str) -> None:
        """
        Remove a nested cache bucket from a function cache and save the result.

        Args:
            func_name (str): Parent function cache name.
            col_name (str): Nested cache key to remove.

        Returns:
            None
        """
        col_name = self._validate_cache_key(col_name, "col_name")
        func_cache = self.load_function_cache(func_name)

        if col_name in func_cache:
            del func_cache[col_name]
            self.save_function_cache(func_name)

            logger.info("Cache for column '%s' deleted from '%s_cache.json'", col_name, func_name)
        else:
            logger.info("No cache found for column '%s' in '%s_cache.json'", col_name, func_name)


_shared_managers: dict[str, CacheManager] = {}
_shared_managers_lock = threading.Lock()


def shared_cache_manager(cache_dir: str | PathLike | None = None) -> CacheManager:
    """
    Return one process-wide `CacheManager` per resolved cache directory.

    The `df.bynat` accessor uses this so pandas operations never build a new
    manager; every frame that targets the same directory shares one instance.

    Args:
        cache_dir (str | os.PathLike | None): Cache directory, resolved like
            `CacheManager(cache_dir)`.

    Returns:
        CacheManager: The shared manager for that directory.
    """
    probe = CacheManager(cache_dir)

    with _shared_managers_lock:
        return _shared_managers.setdefault(probe.cache_dir_path, probe)
