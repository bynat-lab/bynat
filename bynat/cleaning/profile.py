"""
DataFrame data quality profiling helpers and report data structures.

This module provides non-mutating data quality profiling for pandas DataFrames
and ``BaseData`` objects. It inspects missing values, duplicate rows, column data
types, cardinality, and type-specific descriptive statistics, returning a
structured :class:`ProfileReport` (or ``dict`` / ``pandas.DataFrame`` /
``BaseData``) suitable for programmatic inspection.
"""

import datetime
import math
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ._common import _dedupe_key

__all__ = [
    "ProfileReport",
    "DatasetProfile",
    "ColumnProfile",
    "profile",
]


def _clean_scalar(val: Any) -> Any:
    """
    Normalize a scalar or container value into a native, JSON-safe Python primitive.

    Converts NumPy scalars, pandas timestamps/timedeltas, floating-point ``NaN``
    or infinity values, and nested containers into standard Python types
    (``int``, ``float``, ``bool``, ``str``, ``list``, ``dict``, or ``None``) so
    that all profile metrics and statistics have a stable, serializable contract.

    Notes:
        - Container types (``set``, ``list``, ``tuple``, ``dict``, ``np.ndarray``)
          are cleaned recursively before ``pd.isna`` is checked to avoid
          ambiguous truth-value errors on array-like objects.
        - ``bool`` and ``np.bool_`` are checked before ``int`` because ``bool``
          is a subclass of ``int`` in Python.
        - ``datetime.timedelta``, ``pd.Timedelta``, and ``np.timedelta64`` are
          checked before ``np.integer`` because ``np.timedelta64`` inherits from
          ``np.generic`` / integer hierarchies in NumPy, and are formatted as
          ISO-8601 duration strings.
        - ``pd.Timestamp``, ``np.datetime64``, and ``datetime.date`` values are
          converted to ISO-8601 strings.
        - Floating-point ``NaN``, ``+inf``, and ``-inf`` are normalized to ``None``.

    Args:
        val (Any): The raw value or container extracted from a pandas Series or
            DataFrame aggregation.

    Returns:
        Any: A native Python primitive (``None``, ``bool``, ``int``, ``float``,
        ``str``) or a recursively cleaned ``list`` or ``dict``.
    """
    if val is None:
        return None
    if isinstance(val, set):
        return [_clean_scalar(x) for x in val]
    if isinstance(val, (list, tuple)):
        return [_clean_scalar(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _clean_scalar(v) for k, v in val.items()}
    if isinstance(val, np.ndarray):
        return val.tolist()
    try:
        if pd.isna(val):
            return None
    except (ValueError, TypeError):
        pass
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, np.datetime64, datetime.date)):
        try:
            return pd.Timestamp(val).isoformat()
        except Exception:
            return str(val)
    if isinstance(val, (datetime.timedelta, pd.Timedelta, np.timedelta64)):
        try:
            return pd.Timedelta(val).isoformat()
        except Exception:
            return str(val)
    if isinstance(val, (float, np.floating)):
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return None
        return f_val
    if isinstance(val, (int, np.integer)):
        return int(val)
    return val


def _detect_column_kind(series: pd.Series) -> tuple[str, str]:
    """
    Classify a pandas Series into a broad analytical kind and a fine-grained inferred type.

    Inspects both the declared pandas ``dtype`` and the non-null values (via
    ``pandas.api.types.infer_dtype``) to determine how the column should be
    summarized. When a column contains only missing values (or belongs to an
    empty DataFrame), classification falls back to the declared dtype, or
    ``('other', 'empty')`` if the dtype is generic ``object``.

    Args:
        series (pd.Series): The column Series to classify.

    Returns:
        tuple[str, str]: A 2-tuple ``(kind, inferred_type)`` where:
            - ``kind`` (str): Broad analytical category, always one of
              ``'numeric'``, ``'categorical'``, ``'boolean'``, ``'datetime'``,
              or ``'other'``.
            - ``inferred_type`` (str): Fine-grained type label from pandas
              (e.g., ``'integer'``, ``'floating'``, ``'string'``, ``'boolean'``,
              ``'datetime64'``, ``'mixed'``, or ``'empty'``).
    """
    non_null = series.dropna()
    if non_null.empty:
        if pd.api.types.is_bool_dtype(series.dtype):
            return "boolean", "boolean"
        if pd.api.types.is_numeric_dtype(series.dtype):
            return "numeric", "numeric"
        if pd.api.types.is_datetime64_any_dtype(series.dtype):
            return "datetime", "datetime"
        if isinstance(series.dtype, pd.CategoricalDtype):
            return "categorical", "categorical"
        if isinstance(series.dtype, pd.StringDtype):
            return "categorical", "string"
        return "other", "empty"

    inferred = pd.api.types.infer_dtype(non_null, skipna=True)

    if pd.api.types.is_bool_dtype(series.dtype) or inferred == "boolean":
        return "boolean", inferred

    if pd.api.types.is_datetime64_any_dtype(series.dtype) or inferred in (
        "datetime64",
        "datetime",
        "date",
        "timestamp",
    ):
        return "datetime", inferred

    if pd.api.types.is_numeric_dtype(series.dtype) or inferred in (
        "integer",
        "floating",
        "decimal",
    ):
        return "numeric", inferred

    if isinstance(series.dtype, pd.CategoricalDtype) or inferred in (
        "categorical",
        "string",
        "unicode",
        "bytes",
    ):
        return "categorical", inferred

    if all(isinstance(x, str) for x in non_null):
        return "categorical", inferred

    return "other", inferred


def _compute_numeric_stats(series: pd.Series) -> dict[str, Any]:
    """
    Compute descriptive statistics for a numeric column.

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
    min_val = _clean_scalar(numeric.min())
    max_val = _clean_scalar(numeric.max())
    mean_val = _clean_scalar(numeric.mean())
    median_val = _clean_scalar(numeric.median())
    std_val = _clean_scalar(numeric.std()) if n > 1 else None

    try:
        q25_raw = numeric.quantile(0.25)
        q75_raw = numeric.quantile(0.75)
        q25_val = _clean_scalar(q25_raw)
        q75_val = _clean_scalar(q75_raw)
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


def _compute_categorical_stats(series: pd.Series) -> dict[str, Any]:
    """
    Compute descriptive statistics for a categorical or string column.

    Determines the most frequent value (mode), its frequency and proportion
    among non-null values, and character length statistics when all non-null
    values are strings.

    Notes:
        - If the column contains unhashable objects, values are normalized
          through :func:`._common._dedupe_key` before counting frequencies.
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
        deduped = non_null.map(_dedupe_key)
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
        "top": _clean_scalar(top_val),
        "top_frequency": top_freq,
        "top_proportion": top_prop,
        "min_length": min_len,
        "max_length": max_len,
        "mean_length": mean_len,
    }


def _compute_boolean_stats(series: pd.Series) -> dict[str, Any]:
    """
    Compute descriptive statistics for a boolean column.

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


def _compute_datetime_stats(series: pd.Series) -> dict[str, Any]:
    """
    Compute descriptive statistics for a datetime or date column.

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


def _compute_other_stats(series: pd.Series) -> dict[str, Any]:
    """
    Compute descriptive statistics for mixed-type, object, or untyped empty columns.

    Finds the most frequent non-null value and its frequency/proportion, using
    :func:`._common._dedupe_key` as a fallback when elements are unhashable
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
        deduped = non_null.map(_dedupe_key)
        counts = deduped.value_counts()
        top_repr = counts.index[0]
        top_freq = int(counts.iloc[0])
        first_idx = deduped.tolist().index(top_repr)
        top_val = non_null.iloc[first_idx]

    top_prop = float(top_freq / n)
    return {
        "top": _clean_scalar(top_val),
        "top_frequency": top_freq,
        "top_proportion": top_prop,
    }


def _compute_distinct_count(series: pd.Series) -> int:
    """
    Count the number of unique non-null values in a Series.

    Uses ``series.nunique(dropna=True)`` for hashable elements and falls back
    to :func:`._common._dedupe_key` when the Series contains unhashable objects
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
        return int(non_null.map(_dedupe_key).nunique(dropna=True))


def _compute_duplicate_rows(df: pd.DataFrame) -> int:
    """
    Count duplicate rows in a DataFrame using ``keep='first'`` semantics.

    The first occurrence of each unique row is treated as canonical and not
    counted; every subsequent identical row is counted as a duplicate. If the
    DataFrame contains unhashable cell values (e.g., ``list`` or ``dict``),
    cells are normalized via :func:`._common._dedupe_key` before checking for
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
        deduped_df = df.map(_dedupe_key)
        return int(deduped_df.duplicated(keep="first").sum())


@dataclass
class DatasetProfile(Mapping[str, Any]):
    """
    Dataset-level data quality summary metrics for a profiled DataFrame.

    Implements the :class:`collections.abc.Mapping` protocol so fields can be
    accessed both as attributes (``dataset.row_count``) and by key
    (``dataset['row_count']``).

    Attributes:
        row_count (int): Total number of rows in the profiled DataFrame.
        column_count (int): Total number of profiled columns.
        total_cells (int): Total number of cells (``row_count * column_count``).
        missing_count (int): Total count of missing (``NaN`` / ``None`` / ``NA``)
            cells across all profiled columns.
        missing_proportion (float): Fraction of total cells that are missing
            (``missing_count / total_cells``, or ``0.0`` when ``total_cells == 0``).
        duplicate_rows (int): Number of duplicate rows using ``keep='first'``
            semantics (first occurrence kept, subsequent identical rows counted).
        duplicate_proportion (float): Fraction of rows that are duplicates
            (``duplicate_rows / row_count``, or ``0.0`` when ``row_count == 0``).
        empty_column_count (int): Number of profiled columns where all values
            are missing (``count == 0``).
        memory_bytes (int): Estimated memory footprint of the profiled columns
            in bytes (via ``df.memory_usage(deep=True).sum()``).
        dtype_counts (dict[str, int]): Mapping from pandas dtype string
            (e.g., ``'int64'``, ``'object'``) to the number of columns with that dtype.
    """

    row_count: int
    column_count: int
    total_cells: int
    missing_count: int
    missing_proportion: float
    duplicate_rows: int
    duplicate_proportion: float
    empty_column_count: int
    memory_bytes: int
    dtype_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the dataset profile into a plain Python dictionary.

        Returns:
            dict[str, Any]: Dictionary containing all :class:`DatasetProfile`
            attributes mapped to native Python types.
        """
        return asdict(self)

    def __getitem__(self, item: str) -> Any:
        """
        Retrieve a dataset metric by its field name.

        Args:
            item (str): Name of the :class:`DatasetProfile` attribute.

        Returns:
            Any: The value of the requested attribute.

        Raises:
            KeyError: If ``item`` is not a valid attribute name.
        """
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item) from None

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over the field names of the dataset profile.

        Returns:
            Iterator[str]: An iterator yielding each attribute name in declaration order.
        """
        return iter(asdict(self))

    def __len__(self) -> int:
        """
        Return the number of fields in the dataset profile.

        Returns:
            int: Total number of :class:`DatasetProfile` attributes (10).
        """
        return len(asdict(self))


@dataclass
class ColumnProfile(Mapping[str, Any]):
    """
    Data quality metrics and descriptive statistics for a single DataFrame column.

    Implements the :class:`collections.abc.Mapping` protocol so fields can be
    accessed both as attributes (``col_profile.missing_count``) and by key
    (``col_profile['missing_count']``).

    Attributes:
        name (Any): The column name/label in the DataFrame.
        dtype (str): String representation of the pandas dtype (e.g., ``'int64'``,
            ``'Float64'``, ``'object'``, ``'datetime64[ns]'``).
        inferred_type (str): Fine-grained type inferred from non-null values by
            ``pandas.api.types.infer_dtype`` (e.g., ``'integer'``, ``'floating'``,
            ``'string'``, ``'boolean'``, ``'datetime64'``, ``'mixed'``, ``'empty'``).
        kind (str): Broad analytical category used to select descriptive
            statistics. Always one of ``'numeric'``, ``'categorical'``,
            ``'boolean'``, ``'datetime'``, or ``'other'``.
        count (int): Number of non-null values in the column.
        missing_count (int): Number of missing (``NaN`` / ``None`` / ``NA``)
            values in the column.
        missing_proportion (float): Fraction of column rows that are missing
            (``missing_count / row_count``, or ``0.0`` when ``row_count == 0``).
        distinct_count (int): Number of unique non-null values in the column.
        distinct_proportion (float): Fraction of non-null values that are unique
            (``distinct_count / count``, or ``0.0`` when ``count == 0``).
        is_unique (bool): ``True`` if and only if ``count > 0`` and every
            non-null value in the column is distinct (``distinct_count == count``).
        stats (dict[str, Any]): Kind-specific descriptive statistics dictionary.
            Unavailable or inapplicable metrics are represented as ``None``:
            - When ``kind == 'numeric'``: ``min``, ``max``, ``mean``, ``std``,
              ``median``, ``q25``, ``q75``, ``iqr``, ``zeros_count``,
              ``zeros_proportion``, ``outliers_count``.
            - When ``kind == 'categorical'``: ``top``, ``top_frequency``,
              ``top_proportion``, ``min_length``, ``max_length``, ``mean_length``.
            - When ``kind == 'boolean'``: ``true_count``, ``false_count``,
              ``true_proportion``.
            - When ``kind == 'datetime'``: ``min``, ``max``, ``range_days``.
            - When ``kind == 'other'``: ``top``, ``top_frequency``,
              ``top_proportion``.
    """

    name: Any
    dtype: str
    inferred_type: str
    kind: str
    count: int
    missing_count: int
    missing_proportion: float
    distinct_count: int
    distinct_proportion: float
    is_unique: bool
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the column profile into a plain Python dictionary.

        Returns:
            dict[str, Any]: Dictionary containing all :class:`ColumnProfile`
            attributes and nested ``stats`` mapped to native Python types.
        """
        return asdict(self)

    def __getitem__(self, item: str) -> Any:
        """
        Retrieve a column profile field by its attribute name.

        Args:
            item (str): Name of the :class:`ColumnProfile` attribute.

        Returns:
            Any: The value of the requested attribute.

        Raises:
            KeyError: If ``item`` is not a valid attribute name.
        """
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item) from None

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over the field names of the column profile.

        Returns:
            Iterator[str]: An iterator yielding each attribute name in declaration order.
        """
        return iter(asdict(self))

    def __len__(self) -> int:
        """
        Return the number of fields in the column profile.

        Returns:
            int: Total number of :class:`ColumnProfile` attributes (11).
        """
        return len(asdict(self))


@dataclass
class ProfileReport(Mapping[str, Any]):
    """
    Complete data quality report for a DataFrame.

    Combines dataset-wide summary metrics (:attr:`dataset`) and per-column
    profiles (:attr:`columns` and :attr:`column_list`). Implements the
    :class:`collections.abc.Mapping` protocol with keys ``'dataset'`` and
    ``'columns'``, and provides :meth:`to_dict` and :meth:`to_dataframe` for
    programmatic consumption.

    Attributes:
        dataset (DatasetProfile): Aggregate quality metrics for the entire
            profiled DataFrame.
        columns (dict[Any, ColumnProfile]): Mapping from each column name to its
            corresponding :class:`ColumnProfile`. If duplicate column names exist,
            this dictionary holds the last occurrence while :attr:`column_list`
            preserves every column by position.
        column_list (list[ColumnProfile]): Positional list of
            :class:`ColumnProfile` objects in the exact order the columns appear
            in the profiled DataFrame.
    """

    dataset: DatasetProfile
    columns: dict[Any, ColumnProfile]
    column_list: list[ColumnProfile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the full profile report to a nested dictionary of Python primitives.

        Returns:
            dict[str, Any]: A dictionary with two top-level keys:
                - ``'dataset'`` (dict[str, Any]): Output of ``self.dataset.to_dict()``.
                - ``'columns'`` (dict[Any, dict[str, Any]]): Mapping of column
                  names to ``col_profile.to_dict()``.
        """
        return {
            "dataset": self.dataset.to_dict(),
            "columns": {k: v.to_dict() for k, v in self.columns.items()},
        }

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert per-column quality profiles into a tabular ``pandas.DataFrame``.

        Each row in the returned DataFrame represents one profiled column from
        :attr:`column_list` (preserving duplicate column names if present).
        Standard column metrics appear as top-level columns (``column``,
        ``dtype``, ``inferred_type``, ``kind``, ``count``, ``missing_count``,
        ``missing_proportion``, ``distinct_count``, ``distinct_proportion``,
        ``is_unique``), and entries from ``col.stats`` are flattened with a
        ``stat_`` prefix (e.g., ``stat_mean``, ``stat_iqr``, ``stat_top``).

        Returns:
            pd.DataFrame: A summary DataFrame with one row per profiled column.
        """
        rows: list[dict[str, Any]] = []
        for col in self.column_list:
            row: dict[str, Any] = {
                "column": col.name,
                "dtype": col.dtype,
                "inferred_type": col.inferred_type,
                "kind": col.kind,
                "count": col.count,
                "missing_count": col.missing_count,
                "missing_proportion": col.missing_proportion,
                "distinct_count": col.distinct_count,
                "distinct_proportion": col.distinct_proportion,
                "is_unique": col.is_unique,
            }
            for stat_k, stat_v in col.stats.items():
                row[f"stat_{stat_k}"] = stat_v
            rows.append(row)
        return pd.DataFrame(rows)

    def __getitem__(self, key: str) -> Any:
        """
        Retrieve a top-level section of the report by key (``'dataset'`` or ``'columns'``).

        Args:
            key (str): Section name, either ``'dataset'`` or ``'columns'``.

        Returns:
            DatasetProfile | dict[Any, ColumnProfile]: The requested report section.

        Raises:
            KeyError: If ``key`` is neither ``'dataset'`` nor ``'columns'``.
        """
        if key == "dataset":
            return self.dataset
        if key == "columns":
            return self.columns
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over the top-level mapping keys of the report.

        Returns:
            Iterator[str]: Yields ``'dataset'`` and ``'columns'``.
        """
        yield "dataset"
        yield "columns"

    def __len__(self) -> int:
        """
        Return the number of top-level sections in the report mapping.

        Returns:
            int: Always ``2`` (``'dataset'`` and ``'columns'``).
        """
        return 2

    def __repr__(self) -> str:
        """
        Return a concise human-readable summary string of the profile report.

        Returns:
            str: Summary displaying row count, column count, missing cell count
            and percentage, and duplicate row count.
        """
        return (
            f"ProfileReport(rows={self.dataset.row_count}, "
            f"columns={self.dataset.column_count}, "
            f"missing={self.dataset.missing_count} ({self.dataset.missing_proportion:.1%}), "
            f"duplicate_rows={self.dataset.duplicate_rows})"
        )


def profile(
    df: pd.DataFrame,
    *columns: Any,
    output_type: Any = None,
) -> Any:
    """
    Generate a structured, non-mutating data quality profile report for a DataFrame.

    Computes dataset-wide metrics (row count, column count, total cells, missing
    cell count and proportion, duplicate row count and proportion using
    ``keep='first'`` semantics, empty column count, memory usage, and dtype
    distribution) alongside per-column profiles (declared dtype, inferred type,
    analytical kind, non-null count, missing count/proportion, distinct
    count/proportion, uniqueness flag, and kind-specific descriptive statistics).

    Notes:
        - This function never mutates the input DataFrame ``df``.
        - Duplicate rows are counted using ``keep='first'`` semantics: the first
          occurrence of a unique row is not counted, and each subsequent identical
          row is counted as a duplicate.
        - Columns containing unhashable values (e.g., ``list``, ``dict``, ``set``)
          are handled safely via deterministic key normalization.
        - Unavailable or inapplicable statistics (such as ``std`` for a single
          observation or ``outliers_count`` when ``count < 5``) are represented
          as ``None``.

    Args:
        df (pd.DataFrame): The DataFrame (or ``BaseData`` instance) to profile.
        *columns: Optional column name(s) to restrict profiling to a subset of
            columns. Can be passed as positional arguments
            (``profile(df, 'col1', 'col2')``) or as a single collection
            (``profile(df, ['col1', 'col2'])``). When omitted, all columns in
            ``df`` are profiled.
        output_type (type | None, optional): Desired return type for the report:
            - ``None`` (default) or :class:`ProfileReport`: returns a
              :class:`ProfileReport` instance.
            - ``dict``: returns ``report.to_dict()`` (nested Python ``dict``).
            - ``pandas.DataFrame``: returns ``report.to_dataframe()`` (one row
              per profiled column).
            - :class:`~bynat.cleaning.base.BaseData` (or subclass): returns the
              summary DataFrame wrapped in that ``BaseData`` class.

    Returns:
        ProfileReport | dict[str, Any] | pd.DataFrame | BaseData: The generated
        data quality report in the requested ``output_type``.

    Raises:
        TypeError: If ``df`` is not a ``pandas.DataFrame`` or if ``output_type``
            is not one of the supported types.
        KeyError: If any column specified in ``*columns`` does not exist in ``df``.

    Example:
    ```
        import bynat
        import pandas as pd

        df = pd.DataFrame({
            "age": [25, 30, None, 40, 30],
            "city": ["Cairo", "Alex", "Cairo", "Giza", "Alex"],
        })

        # Via pandas accessor
        report = df.bynat.profile()
        print(report.dataset.missing_count)
        print(report.columns["age"].stats["median"])

        # Export as a summary DataFrame or dictionary
        summary_df = df.bynat.profile(output_type=pd.DataFrame)
        summary_dict = df.bynat.profile("age", output_type=dict)
    ```
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected a pandas DataFrame, got {type(df).__name__}")

    # Determine columns to profile
    if columns:
        if len(columns) == 1 and isinstance(columns[0], (list, tuple, set)):
            target_cols = list(columns[0])
        else:
            target_cols = list(columns)
        for col in target_cols:
            if col not in df.columns:
                raise KeyError(f"Column '{col}' not found in DataFrame.")
        frame = df[target_cols]
    else:
        target_cols = list(df.columns)
        frame = df

    row_count = len(frame)
    column_count = len(target_cols)
    total_cells = row_count * column_count

    total_missing = int(frame.isna().sum().sum()) if column_count > 0 else 0
    missing_proportion = float(total_missing / total_cells) if total_cells > 0 else 0.0

    duplicate_rows = _compute_duplicate_rows(frame)
    duplicate_proportion = float(duplicate_rows / row_count) if row_count > 0 else 0.0

    empty_column_count = 0
    dtype_counts: dict[str, int] = {}
    col_profiles_dict: dict[Any, ColumnProfile] = {}
    col_profiles_list: list[ColumnProfile] = []

    for i, col in enumerate(target_cols):
        series = frame.iloc[:, i]
        dtype_str = str(series.dtype)
        dtype_counts[dtype_str] = dtype_counts.get(dtype_str, 0) + 1

        kind, inferred_type = _detect_column_kind(series)
        non_null_count = int(series.count())
        missing_count = int(series.isna().sum())
        col_missing_prop = float(missing_count / row_count) if row_count > 0 else 0.0

        if non_null_count == 0:
            empty_column_count += 1

        distinct_count = _compute_distinct_count(series)
        distinct_prop = float(distinct_count / non_null_count) if non_null_count > 0 else 0.0
        is_unique = bool(distinct_count == non_null_count and non_null_count > 0)

        # Compute kind-specific stats
        if kind == "numeric":
            stats = _compute_numeric_stats(series)
        elif kind == "categorical":
            stats = _compute_categorical_stats(series)
        elif kind == "boolean":
            stats = _compute_boolean_stats(series)
        elif kind == "datetime":
            stats = _compute_datetime_stats(series)
        else:
            stats = _compute_other_stats(series)

        col_prof = ColumnProfile(
            name=col,
            dtype=dtype_str,
            inferred_type=inferred_type,
            kind=kind,
            count=non_null_count,
            missing_count=missing_count,
            missing_proportion=col_missing_prop,
            distinct_count=distinct_count,
            distinct_proportion=distinct_prop,
            is_unique=is_unique,
            stats=stats,
        )
        col_profiles_dict[col] = col_prof
        col_profiles_list.append(col_prof)

    try:
        memory_bytes = int(frame.memory_usage(deep=True).sum()) if not frame.empty else 0
    except Exception:
        memory_bytes = 0

    dataset_prof = DatasetProfile(
        row_count=row_count,
        column_count=column_count,
        total_cells=total_cells,
        missing_count=total_missing,
        missing_proportion=missing_proportion,
        duplicate_rows=duplicate_rows,
        duplicate_proportion=duplicate_proportion,
        empty_column_count=empty_column_count,
        memory_bytes=memory_bytes,
        dtype_counts=dtype_counts,
    )

    report = ProfileReport(
        dataset=dataset_prof,
        columns=col_profiles_dict,
        column_list=col_profiles_list,
    )

    # Format according to requested output_type
    if output_type is None or output_type is ProfileReport:
        return report

    if output_type is dict:
        return report.to_dict()

    if output_type is pd.DataFrame:
        return report.to_dataframe()

    from bynat.cleaning.base import BaseData

    if isinstance(output_type, type) and issubclass(output_type, BaseData):
        return output_type(data=report.to_dataframe())

    raise TypeError(
        f"Unsupported output_type: {output_type}. Expected None, ProfileReport, "
        "dict, pandas.DataFrame, or a BaseData subclass."
    )
