"""Private helpers shared by the cleaning modules, `BaseData`, and the accessor."""

import importlib
import json
import logging
from types import ModuleType
from typing import Any, TypeVar, cast

import numpy as np
import pandas as pd

__all__ = [
    "FrameT",
    "HIERARCHICAL_STATS_COLUMNS",
    "dedupe_key",
    "import_optional",
    "left_merge_aligned",
    "like",
    "logger",
    "require_positive_int",
]

# Keep the pre-0.4 logger name so existing logging configuration still applies.
logger = logging.getLogger("bynat.cleaning.Cleaning")

FrameT = TypeVar("FrameT", bound = pd.DataFrame)

HIERARCHICAL_STATS_COLUMNS = (
    'hierarchy_level',
    'hierarchy_columns',
    'group_key',
    'target_column',
    'strategy',
    'statistic',
)


def import_optional(module_name: str, distribution: str, feature: str) -> ModuleType:
    """Import a feature dependency only when the feature is used."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(
            f"{feature} requires the optional '{distribution}' dependency."
        ) from exc


def require_positive_int(value: Any, arg_name: str) -> None:
    """
    Validate integer parameters that control sampling or cache checkpointing.

    Raises:
        ValueError: If `value` is not a positive integer.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"The '{arg_name}' parameter must be a positive integer")


def left_merge_aligned(frame: pd.DataFrame, right: pd.DataFrame, on: list) -> pd.DataFrame:
    """
    Left-merge `right` onto the `on` columns of `frame` and return the result
    indexed like `frame`.

    A left merge preserves the row order of the left frame, so the merged rows
    are re-labelled positionally. This works for named, duplicate, and
    multi-level indexes, unlike round-tripping through `reset_index()`.
    """
    merged = frame[on].merge(right, on = on, how = 'left')
    merged.index = frame.index
    return merged


def dedupe_key(value: Any) -> Any:
    """Return a hashable stand-in for unhashable values such as lists and dicts."""
    if isinstance(value, set):
        value = sorted(value, key = str)
    elif isinstance(value, np.ndarray):
        value = value.tolist()

    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, sort_keys = True, default = str)

    return value


def like(df: FrameT, data: pd.DataFrame) -> FrameT:
    """Return `data` as `df`'s frame type, carrying `df`'s metadata."""
    if type(df) is pd.DataFrame:
        return cast(FrameT, data)

    # pandas-stubs types `_constructor` as an attribute, not a callable.
    constructor: Any = df._constructor
    return cast(FrameT, constructor(data).__finalize__(df))


# Internal aliases for backward compatibility within the package.
_HIERARCHICAL_STATS_COLUMNS = HIERARCHICAL_STATS_COLUMNS
_import_optional = import_optional
_require_positive_int = require_positive_int
_left_merge_aligned = left_merge_aligned
_dedupe_key = dedupe_key
_like = like
