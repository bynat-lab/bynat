"""
Private core logic for non-mutating DataFrame data quality profiling.

This module implements the profiling algorithm behind
:func:`bynat.profiling.profile`: dataset-level quality metrics and per-column
profiles covering missing values, duplicate rows, column types, cardinality,
and kind-specific descriptive statistics. It depends only on the Python
standard library, NumPy, pandas, and :mod:`bynat.profiling.report` for the
report models.

This module is private and not part of the public API. Use
:func:`bynat.profiling.profile` instead.
"""

from collections.abc import Sequence
from typing import Any

import pandas as pd

from .report import ColumnProfile, DatasetProfile, ProfileReport
from ._internal import (
    detect_column_kind,
    compute_numeric_stats,
    compute_categorical_stats,
    compute_boolean_stats,
    compute_datetime_stats,
    compute_other_stats,
    compute_distinct_count,
    compute_duplicate_rows,
)

_STATS_BY_KIND = {
    "numeric": compute_numeric_stats,
    "categorical": compute_categorical_stats,
    "boolean": compute_boolean_stats,
    "datetime": compute_datetime_stats,
}


def resolve_columns(df: pd.DataFrame, columns: Sequence[Any]) -> list[Any]:
    """
    Determine which column labels to profile and validate that they exist.

    Accepts the same forms as the public ``*columns`` argument: either
    individual labels (``('col1', 'col2')``) or a single collection
    (``(['col1', 'col2'],)``). When no columns are given, every column in
    ``df`` is selected.

    Args:
        df (pd.DataFrame): The DataFrame whose columns are being selected.
        columns (Sequence[Any]): The raw positional column arguments passed to
            :func:`bynat.profiling.profile`. May be empty.

    Returns:
        list[Any]: The column labels to profile, in the order requested (or in
        DataFrame order when ``columns`` is empty).

    Raises:
        KeyError: If any requested column does not exist in ``df``.
    """
    if not columns:
        return list(df.columns)

    if len(columns) == 1 and isinstance(columns[0], (list, tuple, set)):
        target_cols = list(columns[0])
    else:
        target_cols = list(columns)

    for col in target_cols:
        if col not in df.columns:
            raise KeyError(f"Column '{col}' not found in DataFrame.")
    return target_cols


def build_column_profile(series: pd.Series, name: Any, row_count: int) -> ColumnProfile:
    """
    Build the data quality profile for a single column.

    Detects the column kind, counts non-null and missing values, computes
    cardinality, and selects the kind-specific statistics function. Columns
    whose kind has no dedicated statistics (``'other'``) fall back to
    :func:`compute_other_stats`.

    Args:
        series (pd.Series): The column values to profile.
        name (Any): The column name/label to record in the profile.
        row_count (int): Number of rows in the profiled frame, used as the
            denominator for ``missing_proportion``.

    Returns:
        ColumnProfile: The populated profile for the column. Proportions are
        ``0.0`` when their denominator is zero.
    """
    kind, inferred_type = detect_column_kind(series)
    non_null_count = int(series.count())
    missing_count = int(series.isna().sum())
    distinct_count = compute_distinct_count(series)

    stats_fn = _STATS_BY_KIND.get(kind, compute_other_stats)

    return ColumnProfile(
        name=name,
        dtype=str(series.dtype),
        inferred_type=inferred_type,
        kind=kind,
        count=non_null_count,
        missing_count=missing_count,
        missing_proportion=float(missing_count / row_count) if row_count > 0 else 0.0,
        distinct_count=distinct_count,
        distinct_proportion=(
            float(distinct_count / non_null_count) if non_null_count > 0 else 0.0
        ),
        is_unique=bool(non_null_count > 0 and distinct_count == non_null_count),
        stats=stats_fn(series),
    )


def build_dataset_profile(
    frame: pd.DataFrame,
    column_profiles: Sequence[ColumnProfile],
) -> DatasetProfile:
    """
    Build the dataset-level data quality summary.

    Aggregates missing counts, empty columns, and dtype distribution from the
    already-built column profiles, and computes duplicate rows and memory usage
    directly from the frame.

    Args:
        frame (pd.DataFrame): The profiled frame (already restricted to the
            selected columns).
        column_profiles (Sequence[ColumnProfile]): Profiles of every column in
            ``frame``, in positional order.

    Returns:
        DatasetProfile: The populated dataset summary. Proportions are ``0.0``
        when their denominator is zero, and ``memory_bytes`` is ``0`` for an
        empty frame or when the measurement fails.
    """
    row_count = len(frame)
    column_count = len(column_profiles)
    total_cells = row_count * column_count

    missing_count = sum(c.missing_count for c in column_profiles)
    duplicate_rows = compute_duplicate_rows(frame)

    dtype_counts: dict[str, int] = {}
    for c in column_profiles:
        dtype_counts[c.dtype] = dtype_counts.get(c.dtype, 0) + 1

    try:
        memory_bytes = int(frame.memory_usage(deep=True).sum()) if not frame.empty else 0
    except Exception:
        memory_bytes = 0

    return DatasetProfile(
        row_count=row_count,
        column_count=column_count,
        total_cells=total_cells,
        missing_count=missing_count,
        missing_proportion=float(missing_count / total_cells) if total_cells > 0 else 0.0,
        duplicate_rows=duplicate_rows,
        duplicate_proportion=float(duplicate_rows / row_count) if row_count > 0 else 0.0,
        empty_column_count=sum(1 for c in column_profiles if c.count == 0),
        memory_bytes=memory_bytes,
        dtype_counts=dtype_counts,
    )


def build_report(df: pd.DataFrame, columns: Sequence[Any]) -> ProfileReport:
    """
    Build the complete data quality report for a DataFrame.

    Resolves the columns to profile, builds a :class:`ColumnProfile` for each
    one by position (so duplicate column names are preserved in
    ``column_list``), and combines them with the dataset-level summary. The
    input DataFrame is never mutated.

    Args:
        df (pd.DataFrame): The DataFrame to profile.
        columns (Sequence[Any]): The raw positional column arguments passed to
            :func:`bynat.profiling.profile`. When empty, all columns are
            profiled.

    Returns:
        ProfileReport: The report with dataset metrics, a name-keyed column
        mapping (last occurrence wins for duplicate names), and the positional
        column list.

    Raises:
        KeyError: If any requested column does not exist in ``df``.
    """
    target_cols = resolve_columns(df, columns)
    frame = df[target_cols] if columns else df
    row_count = len(frame)

    column_list = [
        build_column_profile(frame.iloc[:, i], col, row_count)
        for i, col in enumerate(target_cols)
    ]

    return ProfileReport(
        dataset=build_dataset_profile(frame, column_list),
        columns={c.name: c for c in column_list},
        column_list=column_list,
    )