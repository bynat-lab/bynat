"""The cached-lookup engine shared by every enrichment method."""

import logging
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from typing import Any

from bynat._internal import cache_value_key
from bynat.caching import CacheManager

from ._internal import unique_values

__all__ = [
    "Fetch",
    "FetchMany",
    "SKIP",
    "cached_map",
]

logger = logging.getLogger(__name__)

# Returned by a fetch to leave a value uncached without logging a failure.
SKIP = object()
"""Sentinel a fetch returns to leave a value uncached without a warning."""

Fetch = Callable[[Any], Any]
"""Callable resolving one value; exceptions are caught and left uncached."""

FetchMany = Callable[[list], Sequence[Any]]
"""Callable resolving one chunk of values, returning one outcome per value."""


def cached_map(
    series: Iterable,
    fetch: Fetch | None,
    bucket: str | Sequence[str],
    save_every: int,
    *,
    cache_manager: CacheManager,
    func_name: str,
    key: Callable[[Any], Hashable] = cache_value_key,
    is_cached: Callable[[Any, Any], bool] | None = None,
    fetch_many: FetchMany | None = None,
    on_fetch_start: Callable[[int], Any] | None = None,
    action: str = "fetch",
    label: str = "values",
) -> Any:
    """Resolve the unique values of `series` through a persistent cache.

    Every enrichment method follows the same loop: take the unique non-null
    values, skip the cached ones, fetch the rest, checkpoint the cache every
    `save_every` values, and return the cache for the caller to map back.

    Args:
        series: Values to resolve. Nulls and duplicates are dropped, and the
            remaining values keep first-seen order.
        fetch: Resolves one value. Ignored when `fetch_many` is given.
        bucket: Cache bucket name. With a sequence of names, each fetch
            returns a mapping of bucket name to value, a value counts as
            cached only when every bucket has it, and the result is a dict of
            bucket name to cache.
        save_every: Number of values fetched between cache checkpoints. It
            is also the chunk size passed to `fetch_many`.
        cache_manager: Manager that owns the cache.
        func_name: Cache function name.
        key: Builds the cache key of a value. Defaults to the normalized
            string key used by every bynat cache.
        is_cached: `(cache, value) -> bool`. Defaults to checking `key(value)`
            in every bucket.
        fetch_many: Resolves one chunk of values and returns one outcome per
            value, in order.
        on_fetch_start: Called once with the number of values to fetch,
            before the first fetch and only when something must be fetched.
            Its exceptions propagate, so it is the place for loading optional
            dependencies or models.
        action: Verb used in failure warnings, e.g. "translate".
        label: Plural noun used in progress messages, e.g. "translations".

    Notes:
        A fetch outcome is stored unless it is `SKIP` (left uncached quietly)
        or an exception (logged as a warning and left uncached, so it is
        retried on the next run).

        The cache is checkpointed every `save_every` values and once more at
        the end when anything is unsaved. A `fetch_many` result whose length
        does not match its chunk is treated as a failure for the whole chunk.

    Returns:
        dict: The cache bucket, or a dict of buckets for multiple names. The
        bucket is returned even when nothing had to be fetched.

    Raises:
        TypeError: If neither `fetch` nor `fetch_many` is provided.

        ValueError: If `fetch_many` returns a chunk of the wrong length.
    """
    bucket_names = (bucket,) if isinstance(bucket, str) else tuple(bucket)
    caches = {name: cache_manager.get_column_cache(func_name, name) for name in bucket_names}
    view = caches[bucket_names[0]] if isinstance(bucket, str) else caches

    def in_every_bucket(_view: Any, value: Any) -> bool:
        """Check that a value is cached in every configured bucket.

        Args:
            _view (Any): Unused view kept for the cached-map callback protocol.
            value (Any): Value whose cache key is checked.

        Returns:
            bool: True when the key exists in every bucket.
        """
        value_key = key(value)
        return all(value_key in cache for cache in caches.values())

    cached = is_cached if is_cached is not None else in_every_bucket
    pending: dict[Hashable, Any] = {}

    for value in unique_values(series):
        if not cached(view, value):
            pending.setdefault(key(value), value)

    to_fetch = list(pending.values())
    total = len(to_fetch)

    if not total:
        logger.info("All requested %s are already cached.", label)
        return view

    if on_fetch_start is not None:
        on_fetch_start(total)

    unsaved = False
    processed = 0

    for start in range(0, total, save_every):
        chunk = to_fetch[start:start + save_every]

        if fetch_many is not None:
            try:
                outcomes = list(fetch_many(chunk))

                if len(outcomes) != len(chunk):
                    raise ValueError(
                        f"expected {len(chunk)} results from a batch, got {len(outcomes)}"
                    )

            except Exception as error:
                outcomes = [error] * len(chunk)

        elif fetch is not None:
            outcomes = []

            for value in chunk:
                try:
                    outcomes.append(fetch(value))
                except Exception as error:
                    outcomes.append(error)

        else:
            raise TypeError("cached_map needs fetch or fetch_many")

        for value, outcome in zip(chunk, outcomes):
            if isinstance(outcome, Exception):
                logger.warning(
                    "Failed to %s: '%s'. Skipping cache for this item. Error: %s",
                    action, value, outcome,
                )
                continue

            if outcome is SKIP:
                continue

            value_key = key(value)

            if isinstance(bucket, str):
                caches[bucket][value_key] = outcome

            else:
                for name in bucket_names:
                    caches[name][value_key] = outcome[name] if isinstance(outcome, Mapping) else outcome

            unsaved = True

        processed += len(chunk)

        if unsaved and processed < total:
            cache_manager.save_function_cache(func_name)
            unsaved = False
            logger.info("Checkpoint: Safely saved %s / %s %s to cache...", processed, total, label)

    if unsaved:
        cache_manager.save_function_cache(func_name)

    logger.info("All %s completed and safely cached!", label)

    return view
