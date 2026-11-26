"""Hierarchy helpers shared by the outlier, imputation, and statistics functions."""

from collections.abc import Iterator, Sequence
from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "HIERARCHICAL_STATS_COLUMNS",
    "hierarchical_outlier_masks",
    "left_merge_aligned",
    "normalize_hierarchy",
]

HIERARCHICAL_STATS_COLUMNS = (
    'hierarchy_level',
    'hierarchy_columns',
    'group_key',
    'target_column',
    'strategy',
    'statistic',
)


def left_merge_aligned(frame: pd.DataFrame, right: pd.DataFrame, on: list) -> pd.DataFrame:
    """
    Left-merge `right` onto the `on` columns of `frame` and return the result
    indexed like `frame`.

    A left merge preserves the row order of the left frame, so the merged rows
    are re-labelled positionally. This works for named, duplicate, and
    multi-level indexes, unlike round-tripping through `reset_index()`.

    Args:
        frame (pd.DataFrame): Left frame whose index the result inherits.
        right (pd.DataFrame): Right frame to merge on.
        on (list): Column names present in both frames.

    Returns:
        pd.DataFrame: The merged frame, with `frame`'s index.
    """
    merged = frame[on].merge(right, on = on, how = 'left')
    merged.index = frame.index
    return merged


def normalize_hierarchy(hierarchy_cols: Any) -> list:
    """Return the hierarchy as a list, treating one string as one column."""
    if isinstance(hierarchy_cols, str):
        return [hierarchy_cols]

    return list(hierarchy_cols) if hierarchy_cols else []


def hierarchical_outlier_masks(
    frame: pd.DataFrame,
    target_cols: Sequence[Any],
    hierarchy_cols: Sequence[Any],
    min_samples: int,
) -> Iterator[tuple[Any, np.ndarray]]:
    """
    Yield `(target_col, outlier_mask)` for every target and hierarchy level.

    The full hierarchy is evaluated first, then its last column is dropped at
    each level. A row is judged only at the most specific level where its
    group has at least `min_samples` non-null values; values outside the
    group's 1.5 IQR bounds are flagged. Quartiles come from one grouped
    `quantile([0.25, 0.75])` call per level and are mapped back to rows by
    group number, with no merge.

    `frame` is re-read at every level, so a caller that blanks the yielded
    outliers before resuming excludes them from later levels
    (`handle_outliers`); a caller that leaves `frame` untouched keeps them in
    later quartiles (`drop_outliers`).
    """
    row_count = len(frame)

    for target_col in target_cols:
        if target_col not in frame.columns:
            continue

        processed = np.zeros(row_count, dtype = bool)
        current_hierarchy = list(hierarchy_cols)

        while current_hierarchy:
            values = frame[target_col]
            unprocessed = ~processed & values.notna().to_numpy()

            if not unprocessed.any():
                break

            grouped = values.groupby(
                [frame[col] for col in current_hierarchy],
                dropna = False,
                observed = True,
                sort = False,
            )

            group_ids = grouped.ngroup().to_numpy()
            valid = grouped.count().to_numpy()[group_ids] >= min_samples

            if valid.any():
                quartiles = grouped.quantile([0.25, 0.75]).to_numpy(dtype = float).reshape(-1, 2)
                q1 = quartiles[group_ids, 0]
                q3 = quartiles[group_ids, 1]
                iqr = q3 - q1

                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                numeric = values.to_numpy(dtype = float, na_value = np.nan)

                with np.errstate(invalid = 'ignore'):
                    outliers = (
                        valid & unprocessed & ~np.isnan(lower_bound) &
                        ((numeric < lower_bound) | (numeric > upper_bound))
                    )

                yield target_col, outliers

            processed |= valid
            current_hierarchy.pop()
