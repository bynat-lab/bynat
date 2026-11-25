"""Internal implementation modules for the profiling subpackage."""

from .processing import clean_scalar, detect_column_kind
from .computations import (
    compute_numeric_stats,
    compute_categorical_stats,
    compute_boolean_stats,
    compute_datetime_stats,
    compute_other_stats,
    compute_distinct_count,
    compute_duplicate_rows
)

__all__ = ["compute_numeric_stats",
    "compute_categorical_stats",
    "compute_boolean_stats",
    "compute_datetime_stats",
    "compute_other_stats",
    "compute_distinct_count",
    "compute_duplicate_rows",

    "clean_scalar",
    "detect_column_kind",
]
