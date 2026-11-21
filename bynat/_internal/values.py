"""Domain-independent value normalization helpers."""

import json
from typing import Any

import numpy as np

__all__ = ['dedupe_key']


def dedupe_key(value: Any) -> Any:
    """
    Return a hashable stand-in for unhashable values such as lists and dicts.

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
