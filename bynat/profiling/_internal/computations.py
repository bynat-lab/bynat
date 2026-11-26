from typing import Any

import pandas as pd

from bynat._internal import dedupe_key

from .processing import clean_scalar

__all__ = ["compute_numeric_stats",
    "compute_categorical_stats",
    "compute_boolean_stats",
    "compute_datetime_stats",
    "compute_other_stats",
    "compute_distinct_count",
    "compute_duplicate_rows",
]

def compute_numeric_stats(series: pd.Series) -> dict[str, Any]:
    """Compute descriptive statistics for a numeric column.

    Calculates central tendency, dispersion, quartiles, zero-value prevalence,
    and 1.5*IQR outlier counts over all non-null numeric values in ``series``.

    Notes:
        - ``std`` requires at least 2 non-null numeric observations; otherwise
          it is ``None``.
        - ``outliers_count`` uses the standard Tukey 1.5*IQR rule
          (``< q25 - 1.5 * iqr`` or ``> q75 + 1.5 * iqr``) and requires at least
          5 non-null numeric values; otherwise it is ``None``.
        - When the column has no valid numeric values, summary statistics default
          to ``None`` while ``zeros_count`` is ``0`` and ``zeros_proportion`` is
          ``0.0``.

    Args:
        series (pd.Series): A Series classified with ``kind == 'numeric'``.

    Returns:
        dict[str, Any]: Dictionary with keys:
            - ``min`` (int | float | None): Minimum non-null value.
            - ``max`` (int | float | None): Maximum non-null value.
            - ``mean`` (float | None): Arithmetic mean of non-null values.
            - ``std`` (float | None): Sample standard deviation (``ddof=1``).
            - ``median`` (float | None): 50th percentile (median).
            - ``q25`` (float | None): 25th percentile (first quartile).
            - ``q75`` (float | None): 75th percentile (third quartile).
            - ``iqr`` (float | None): Interquartile range (``q75 - q25``).
            - ``zeros_count`` (int): Number of non-null values equal to zero.
            - ``zeros_proportion`` (float): Fraction of non-null values equal to zero.
            - ``outliers_count`` (int | None): Count of values outside 1.5*IQR bounds.
    """
    non_null = series.dropna()
    empty_stats: dict[str, Any] = {
        "min": None,
        "max": None,
        "mean": None,
        "std": None,
        "median": None,
        "q25": None,
        "q75": None,
        "iqr": None,
        "zeros_count": 0,
        "zeros_proportion": 0.0,
        "outliers_count": None,
    }
    if non_null.empty:
        return empty_stats

    try:
        numeric = pd.to_numeric(non_null, errors="coerce").dropna()
    except Exception:
        return empty_stats

    if numeric.empty:
        return empty_stats

    n = len(numeric)
    min_val = clean_scalar(numeric.min())
    max_val = clean_scalar(numeric.max())
    mean_val = clean_scalar(numeric.mean())
    median_val = clean_scalar(numeric.median())
    std_val = clean_scalar(numeric.std()) if n > 1 else None

    try:
        q25_raw = numeric.quantile(0.25)
        q75_raw = numeric.quantile(0.75)
        q25_val = clean_scalar(q25_raw)
        q75_val = clean_scalar(q75_raw)
    except Exception:
        q25_val = None
        q75_val = None

    if q25_val is not None and q75_val is not None:
        iqr_val: float | None = float(q75_val - q25_val)
    else:
        iqr_val = None

    zeros_count = int((numeric == 0).sum())
    zeros_proportion = float(zeros_count / n)

    outliers_count: int | None = None
    if n >= 5 and iqr_val is not None and q25_val is not None and q75_val is not None:
        lower_bound = q25_val - 1.5 * iqr_val
        upper_bound = q75_val + 1.5 * iqr_val
        outliers_count = int(((numeric < lower_bound) | (numeric > upper_bound)).sum())

    return {
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "std": std_val,
        "median": median_val,
        "q25": q25_val,
        "q75": q75_val,
        "iqr": iqr_val,
        "zeros_count": zeros_count,
        "zeros_proportion": zeros_proportion,
        "outliers_count": outliers_count,
    }


def compute_categorical_stats(series: pd.Series) -> dict[str, Any]:
    """Compute descriptive statistics for a categorical or string column.

    Determines the most frequent value (mode), its frequency and proportion
    among non-null values, and character length statistics when all non-null
    values are strings.

    Notes:
        - If the column contains unhashable objects, values are normalized
          through :func:`_dedupe_key` before counting frequencies.
        - Character length metrics (``min_length``, ``max_length``,
          ``mean_length``) are computed only when every non-null value is a
          ``str``; for non-string categoricals they are ``None``.

    Args:
        series (pd.Series): A Series classified with ``kind == 'categorical'``.

    Returns:
        dict[str, Any]: Dictionary with keys:
            - ``top`` (Any | None): Most frequent non-null value.
            - ``top_frequency`` (int | None): Occurrence count of ``top``.
            - ``top_proportion`` (float | None): ``top_frequency / count``.
            - ``min_length`` (int | None): Minimum string character length.
            - ``max_length`` (int | None): Maximum string character length.
            - ``mean_length`` (float | None): Mean string character length.
    """
    non_null = series.dropna()
    if non_null.empty:
        return {
            "top": None,
            "top_frequency": None,
            "top_proportion": None,
            "min_length": None,
            "max_length": None,
            "mean_length": None,
        }

    n = len(non_null)
    try:
        counts = non_null.value_counts()
        top_val = counts.index[0]
        top_freq = int(counts.iloc[0])
    except TypeError:
        deduped = non_null.map(dedupe_key)
        counts = deduped.value_counts()
        top_repr = counts.index[0]
        top_freq = int(counts.iloc[0])
        first_idx = deduped.tolist().index(top_repr)
        top_val = non_null.iloc[first_idx]

    top_prop = float(top_freq / n)

    str_items = [x for x in non_null if isinstance(x, str)]
    if len(str_items) == n and n > 0:
        lengths = [len(x) for x in str_items]
        min_len: int | None = int(min(lengths))
        max_len: int | None = int(max(lengths))
        mean_len: float | None = float(sum(lengths) / len(lengths))
    else:
        min_len = None
        max_len = None
        mean_len = None

    return {
        "top": clean_scalar(top_val),
        "top_frequency": top_freq,
        "top_proportion": top_prop,
        "min_length": min_len,
        "max_length": max_len,
        "mean_length": mean_len,
    }


def compute_boolean_stats(series: pd.Series) -> dict[str, Any]:
    """Compute descriptive statistics for a boolean column.

    Counts the number of ``True`` and ``False`` values and calculates the
    proportion of non-null values that are ``True``.

    Args:
        series (pd.Series): A Series classified with ``kind == 'boolean'``.

    Returns:
        dict[str, Any]: Dictionary with keys:
            - ``true_count`` (int): Number of non-null ``True`` values.
            - ``false_count`` (int): Number of non-null ``False`` values.
            - ``true_proportion`` (float | None): ``true_count / count``, or
              ``None`` if the column has no non-null values.
    """
    non_null = series.dropna()
    if non_null.empty:
        return {
            "true_count": 0,
            "false_count": 0,
            "true_proportion": None,
        }

    n = len(non_null)
    true_count = int((non_null == True).sum())  # noqa: E712
    false_count = int((non_null == False).sum())  # noqa: E712
    true_prop = float(true_count / n) if n > 0 else None

    return {
        "true_count": true_count,
        "false_count": false_count,
        "true_proportion": true_prop,
    }


def compute_datetime_stats(series: pd.Series) -> dict[str, Any]:
    """Compute descriptive statistics for a datetime or date column.

    Identifies the earliest and latest timestamps (formatted as ISO-8601 strings)
    and computes the time span between them in fractional days.

    Args:
        series (pd.Series): A Series classified with ``kind == 'datetime'``.

    Returns:
        dict[str, Any]: Dictionary with keys:
            - ``min`` (str | None): Earliest timestamp as an ISO-8601 string.
            - ``max`` (str | None): Latest timestamp as an ISO-8601 string.
            - ``range_days`` (float | None): Total span ``(max - min)`` in days,
              or ``None`` if the column contains no valid timestamps.
    """
    non_null = series.dropna()
    if non_null.empty:
        return {
            "min": None,
            "max": None,
            "range_days": None,
        }

    try:
        dt_series = pd.to_datetime(non_null)
        min_dt = dt_series.min()
        max_dt = dt_series.max()
        if pd.isna(min_dt) or pd.isna(max_dt):
            return {
                "min": None,
                "max": None,
                "range_days": None,
            }
        min_iso = min_dt.isoformat()
        max_iso = max_dt.isoformat()
        range_days = float((max_dt - min_dt).total_seconds() / 86400.0)
        return {
            "min": min_iso,
            "max": max_iso,
            "range_days": range_days,
        }
    except Exception:
        return {
            "min": None,
            "max": None,
            "range_days": None,
        }


def compute_other_stats(series: pd.Series) -> dict[str, Any]:
    """Compute descriptive statistics for mixed or untyped columns.

    Finds the most frequent non-null value and its frequency/proportion, using
    :func:`_dedupe_key` as a fallback when elements are unhashable
    (such as ``list``, ``dict``, or ``set`` cells).

    Args:
        series (pd.Series): A Series classified with ``kind == 'other'``.

    Returns:
        dict[str, Any]: Dictionary with keys:
            - ``top`` (Any | None): Most frequent non-null value (cleaned via
              :func:`_clean_scalar`).
            - ``top_frequency`` (int | None): Occurrence count of ``top``.
            - ``top_proportion`` (float | None): ``top_frequency / count``, or
              ``None`` when empty.
    """
    non_null = series.dropna()
    if non_null.empty:
        return {
            "top": None,
            "top_frequency": None,
            "top_proportion": None,
        }

    n = len(non_null)
    try:
        counts = non_null.value_counts()
        top_val = counts.index[0]
        top_freq = int(counts.iloc[0])
    except TypeError:
        deduped = non_null.map(dedupe_key)
        counts = deduped.value_counts()
        top_repr = counts.index[0]
        top_freq = int(counts.iloc[0])
        first_idx = deduped.tolist().index(top_repr)
        top_val = non_null.iloc[first_idx]

    top_prop = float(top_freq / n)
    return {
        "top": clean_scalar(top_val),
        "top_frequency": top_freq,
        "top_proportion": top_prop,
    }


def compute_distinct_count(series: pd.Series) -> int:
    """Count the number of unique non-null values in a Series.

    Uses ``series.nunique(dropna=True)`` for hashable elements and falls back
    to :func:`_dedupe_key` when the Series contains unhashable objects
    such as lists, dictionaries, sets, or NumPy arrays.

    Args:
        series (pd.Series): The column Series whose distinct values should be counted.

    Returns:
        int: Number of unique non-null values (``0`` if all values are missing).
    """
    non_null = series.dropna()
    if non_null.empty:
        return 0
    try:
        return int(non_null.nunique(dropna=True))
    except TypeError:
        return int(non_null.map(dedupe_key).nunique(dropna=True))


def compute_duplicate_rows(df: pd.DataFrame) -> int:
    """Count duplicate rows in a DataFrame using ``keep='first'`` semantics.

    The first occurrence of each unique row is treated as canonical and not
    counted; every subsequent identical row is counted as a duplicate. If the
    DataFrame contains unhashable cell values (e.g., ``list`` or ``dict``),
    cells are normalized via :func:`_dedupe_key` before checking for
    duplicates.

    Args:
        df (pd.DataFrame): The DataFrame to inspect for duplicate rows.

    Returns:
        int: Total number of duplicate rows (``0`` for empty or zero-column DataFrames).
    """
    if df.empty or len(df.columns) == 0:
        return 0
    try:
        return int(df.duplicated(keep="first").sum())
    except TypeError:
        deduped_df = df.map(dedupe_key)
        return int(deduped_df.duplicated(keep="first").sum())
