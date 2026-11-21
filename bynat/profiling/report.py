"""
Data quality profile report data structures.

This module owns the structured report models returned by
:func:`bynat.profiling.profile`: :class:`DatasetProfile`,
:class:`ColumnProfile`, and :class:`ProfileReport`. The models are plain
``dataclasses`` implementing the :class:`collections.abc.Mapping` protocol and
serialize to native Python primitives.
"""

from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

__all__ = ["ProfileReport", "DatasetProfile", "ColumnProfile"]


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
            in bytes (via ``df.memory_usage(deep=True).sum()``). ``0`` for an
            empty frame or when the measurement fails.
        dtype_counts (dict[str, int]): Mapping from pandas dtype string
            (e.g., ``'int64'``, ``'object'``) to the number of columns with that dtype.

    Notes:
        Every metric is a native Python value (``int``, ``float``, ``str``,
        ``bool``, ``list``, ``dict``, or ``None``), so the profile is JSON
        serializable. The instance has 10 fields.
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

    Notes:
        Every metric is a native Python value, so the profile is JSON
        serializable. The instance has 11 fields.
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

    Notes:
        The instance has two mapping keys (``'dataset'`` and ``'columns'``).
        With duplicate column names, ``columns`` holds the last occurrence
        while ``column_list`` keeps every column by position.
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
