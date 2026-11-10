"""Cache-key normalization and lookup helpers."""

from typing import Any

import numpy as np

__all__ = [
    "cache_has_value",
    "cache_lookup_value",
    "cache_value_key",
]


def cache_value_key(value: Any) -> str:
    """Convert a cache lookup value into a stable JSON object key."""
    if isinstance(value, (int, np.integer)):
        return str(int(value))

    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))

    return str(value)


def cache_has_value(cache: dict, value: Any) -> bool:
    """
    Check whether a cache contains a value under either the normalized JSON
    key or the raw in-memory key.
    """
    if cache_value_key(value) in cache:
        return True

    try:
        return value in cache
    except TypeError:
        return False


def cache_lookup_value(cache: dict, value: Any) -> Any:
    """
    Return a cached value using normalized JSON keys with a fallback for
    older raw in-memory cache keys, or the original value when absent.
    """
    normalized_key = cache_value_key(value)

    if normalized_key in cache:
        return cache[normalized_key]

    try:
        return cache[value]
    except (KeyError, TypeError):
        return value


# Package-internal aliases for backward compatibility with private imports.
_cache_value_key = cache_value_key
_cache_has_value = cache_has_value
_cache_lookup_value = cache_lookup_value
