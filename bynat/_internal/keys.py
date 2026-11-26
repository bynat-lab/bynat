"""Key normalization and lookup helpers shared across bynat packages."""

import json
from typing import Any

import numpy as np

__all__ = [
    'dedupe_key',
    'cache_value_key',
    'cache_has_value',
    'cache_lookup_value',
]


def dedupe_key(value: Any) -> Any:
    """Return a hashable stand-in for unhashable values such as lists and dicts.

    Sets are sorted by their string form, NumPy arrays become lists, and
    lists/dicts/tuples are serialized with `json.dumps(sort_keys=True,
    default=str)`. Other values are returned unchanged.

    Args:
        value (Any): Value to normalize.

    Returns:
        Any: A hashable value usable in a `set` or `groupby` key.
    """
    if isinstance(value, set):
        value = sorted(value, key = str)
    elif isinstance(value, np.ndarray):
        value = value.tolist()

    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, sort_keys = True, default = str)

    return value


def cache_value_key(value: Any) -> str:
    """Convert a cache lookup value into a stable JSON object key.

    Integers and integral floats collapse to the same string (`1` and `1.0`
    both become `"1"`), so a value cached before a save/load round trip is
    still found. Every other value is converted with `str`.

    Args:
        value (Any): Value to normalize.

    Returns:
        str: The normalized key.
    """
    if isinstance(value, (int, np.integer)):
        return str(int(value))

    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))

    return str(value)


def cache_has_value(cache: dict, value: Any) -> bool:
    """Check whether a cache holds a value under either key form.

    The normalized key is tested first, so a value written by a previous run
    is found; the raw key is a fallback for caches written in memory by an
    older version. Unhashable values simply count as absent.

    Args:
        cache (dict): Cache bucket to inspect.
        value (Any): Value to look up.

    Returns:
        bool: True when either key is present.
    """
    if cache_value_key(value) in cache:
        return True

    try:
        return value in cache
    except TypeError:
        return False


def cache_lookup_value(cache: dict, value: Any) -> Any:
    """Return a cached value, falling back to legacy in-memory keys.

    Args:
        cache (dict): Cache bucket to read.
        value (Any): Value to look up.

    Returns:
        Any: The cached value, or `value` unchanged when the key is absent.
    """
    normalized_key = cache_value_key(value)

    if normalized_key in cache:
        return cache[normalized_key]

    try:
        return cache[value]
    except (KeyError, TypeError):
        return value
