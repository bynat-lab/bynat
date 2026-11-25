"""
Public entry point for DataFrame data quality profiling.

This module exposes :func:`profile`, which validates its inputs, delegates the
computation to the private core in :mod:`bynat.profiling._census`, and returns
the report models defined in :mod:`bynat.profiling.report` in the requested
output type.
"""

from typing import Any

import pandas as pd

from .report import ProfileReport
from ._builders import build_report

__all__ = ["profile"]


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
        - Column metrics are always computed over the selected columns, so
          proportions are relative to the profiled subset rather than the
          whole frame.

    Args:
        df (pd.DataFrame): The DataFrame to profile.
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

    Returns:
        ProfileReport | dict[str, Any] | pd.DataFrame: The generated data quality
        report in the requested ``output_type``.

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

    if output_type not in (None, ProfileReport, dict, pd.DataFrame):
        raise TypeError(
            f"Unsupported output_type: {output_type}. Expected None, ProfileReport, "
            "dict, or pandas.DataFrame."
        )

    report = build_report(df, columns)

    if output_type is dict:
        return report.to_dict()
    if output_type is pd.DataFrame:
        return report.to_dataframe()
    return report