import datetime
import math
from typing import Any

import numpy as np
import pandas as pd

__all__ = ["dedupe_key", "clean_scalar", "detect_column_kind"]

def clean_scalar(val: Any) -> Any:
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
        return [clean_scalar(x) for x in val]
    if isinstance(val, (list, tuple)):
        return [clean_scalar(x) for x in val]
    if isinstance(val, dict):
        return {str(k): clean_scalar(v) for k, v in val.items()}
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


def detect_column_kind(series: pd.Series) -> tuple[str, str]:
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