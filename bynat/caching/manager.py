"""High-level cache manager and process-wide cache registry."""

import copy
import logging
import os
import threading
from os import PathLike

from ._internal import normalize_cache_dir, validate_cache_key
from ._persistence import load_cache, persist_cache
from ._storage import SQLiteStorage

__all__ = [
    "CACHE_DIR_ENV_VAR",
    "DEFAULT_CACHE_DIR",
    "CacheManager",
    "resolve_cache_dir",
    "shared_cache_manager",
]

logger = logging.getLogger(__name__)

CACHE_DIR_ENV_VAR = "BYNAT_CACHE_DIR"
"""Environment variable that overrides the default cache directory."""

DEFAULT_CACHE_DIR = "Settings/Cache Data/Automated"
"""Legacy relative default cache directory, resolved from the working directory."""


def resolve_cache_dir(cache_dir: str | PathLike | None) -> str | PathLike:
    """
    Resolve the cache directory without creating anything.

    Resolution order: `cache_dir` when it is not None, otherwise the
    `BYNAT_CACHE_DIR` environment variable when it is set and non-empty,
    otherwise `DEFAULT_CACHE_DIR`. The value is returned as given; expansion
    of `~` and environment variables happens in `CacheManager`.

    Args:
        cache_dir (str | os.PathLike | None): Caller-supplied directory, or
            None to fall back to the environment variable and default.

    Returns:
        str | os.PathLike: The resolved directory.
    """
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

        Construction creates nothing on disk. The SQLite database file and its
        directory are created lazily on the first cache access or the first
        save of in-memory changes.

    Attributes:
        cache_dir_path (str): Absolute, normalized path of the cache directory.
        cache_dir (str): Normalized path as given after expansion.
        caches (dict[str, dict]): Live in-memory cache per function name.
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
        self.cache_dir_path, self.cache_dir = normalize_cache_dir(resolve_cache_dir(cache_dir))

        self._storage = SQLiteStorage(self.cache_dir_path)

        self.caches: dict[str, dict] = {}
        self._baselines: dict[str, dict] = {}

    def load_function_cache(self, func_name: str) -> dict:
        """
        Load a function cache from SQLite into memory on first access.

        The SQLite backend is created on first public access for any function.
        Before reading, any legacy JSON cache for the function is migrated into
        SQLite through the accepted migration helper, then the function's cache
        is rebuilt from its SQLite rows via
        ``SQLiteStorage.rebuild_function_cache``. On first load the reconstructed
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
        func_name = validate_cache_key(func_name, "func_name")

        if func_name not in self.caches:
            self.caches[func_name] = load_cache(self._storage, func_name)
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
            The dictionary is created automatically in the live cache if it
            does not yet exist, so mutating the returned dict is persisted by
            the next `save_function_cache`.

        Raises:
            TypeError: If `func_name` or `col_name` is not a string.
            ValueError: If `func_name` or `col_name` is empty or contains
                path separators.
        """
        col_name = validate_cache_key(col_name, "col_name")
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
                An unknown name starts an empty live cache, so saving without a
                prior load writes nothing.

        Returns:
            None. Failures are logged, not raised.

        Raises:
            TypeError: If `func_name` is not a string.
            ValueError: If `func_name` is empty or contains path separators.
        """
        func_name = validate_cache_key(func_name, "func_name")

        if func_name not in self.caches:
            self.caches[func_name] = {}

        live_cache = self.caches[func_name]

        if persist_cache(self._storage, func_name, live_cache, self._baselines.get(func_name)):
            self._baselines[func_name] = copy.deepcopy(live_cache)

    def delete_column_cache(self, func_name: str, col_name: str) -> None:
        """
        Remove a nested cache bucket from a function cache and save the result.

        Args:
            func_name (str): Parent function cache name.
            col_name (str): Nested cache key to remove.

        Returns:
            None. An `INFO` message is logged whether the bucket existed.

        Raises:
            TypeError: If `func_name` or `col_name` is not a string.
            ValueError: If `func_name` or `col_name` is empty or contains
                path separators.
        """
        col_name = validate_cache_key(col_name, "col_name")
        func_cache = self.load_function_cache(func_name)

        if col_name in func_cache:
            del func_cache[col_name]
            self.save_function_cache(func_name)

            logger.info("Cache for column '%s' deleted from '%s'", col_name, func_name)
        else:
            logger.info("No cache found for column '%s' in '%s'", col_name, func_name)


_shared_managers: dict[str, CacheManager] = {}
_shared_managers_lock = threading.Lock()


def shared_cache_manager(cache_dir: str | PathLike | None = None) -> CacheManager:
    """
    Return one process-wide `CacheManager` per resolved cache directory.

    The `df.bynat` accessor uses this so pandas operations never build a new
    manager; every frame that targets the same directory shares one instance.
    The registry is process-wide and thread-safe, and managers are never
    removed from it.

    Args:
        cache_dir (str | os.PathLike | None): Cache directory, resolved like
            `CacheManager(cache_dir)`. Managers are keyed by the resolved
            absolute path, so different spellings of the same directory share
            one instance.

    Returns:
        CacheManager: The shared manager for that directory. A manager is
        created on first request for a directory and reused afterwards.

    Raises:
        TypeError: If `cache_dir` is not a string or path-like object.
        ValueError: If `cache_dir` is empty after normalization.
    """
    probe = CacheManager(cache_dir)

    with _shared_managers_lock:
        return _shared_managers.setdefault(probe.cache_dir_path, probe)
