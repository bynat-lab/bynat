"""The `df.bynat` pandas accessor for plain `pandas.DataFrame` objects.

This module owns pandas registration, the accessor class, and the
accessor-specific adaptation of profiling output. Every transformation is
delegated to the functional packages (`cleaning`, `profiling`, `caching`);
no domain algorithm lives here.
"""

import os
from typing import Any

import pandas as pd

from bynat._internal import is_named_type_from_module
from bynat.analytics._insights import (
    build_bins,
    build_categorical_distribution,
    build_kpi_value,
    build_numerical_aggregation,
    build_time_series,
)
from bynat.caching._registry import CacheManager, resolve_cache_manager
from bynat.cleaning import _columns, _stats, _text
from bynat.cleaning._writers import write_json, write_sql
from bynat.cleaning.enrich import _currency, _geocode, _nlp, _translate
from bynat.profiling._builders import ProfileReport, build_report

from ._binding import _cached_frame_method, _frame_method

__all__ = ['BynatAccessor']


def profile(df: pd.DataFrame, *columns: Any, output_type: Any = None) -> Any:
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

    is_basedata = is_named_type_from_module(output_type, "BaseData", "bynat.cleaning.base")

    if output_type not in (None, ProfileReport, dict, pd.DataFrame) and not is_basedata:
        raise TypeError(
            f"Unsupported output_type: {output_type}. Expected None, ProfileReport, "
            "dict, or pandas.DataFrame."
        )

    report = build_report(df, columns)

    if is_basedata:
        return output_type(data = report.to_dataframe())
    if output_type is dict:
        return report.to_dict()
    if output_type is pd.DataFrame:
        return report.to_dataframe()
    return report


def _reject_inplace(method_name: str, kwargs: dict[str, Any]) -> None:
    """
    Reject the reserved `inplace` keyword on non-mutating analytics methods.

    Args:
        method_name (str): Accessor method name used in the error message.
        kwargs (dict[str, Any]): Caller keyword arguments to inspect.

    Raises:
        TypeError: If `kwargs` contains `inplace`, so it can never leak into
            an analyzer response as metadata.
    """
    if "inplace" in kwargs:
        raise TypeError(f"{method_name}() got an unexpected keyword argument 'inplace'")


def _get_categorical_distribution(
    df: pd.DataFrame,
    x_col: str,
    top_n: int | None = None,
    show_others: bool = False,
    filters: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    orient: str = "records",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Return distribution counts for a categorical column.

    Rows are counted with `value_counts()` and returned in descending
    count order. With `show_others=True` the rows beyond `top_n` are
    collapsed into a single `"Others"` row carrying `is_others=True` and
    an `others_breakdown` list of the collapsed `{"x", "y"}` rows; the
    retained rows get `is_others=False` and `others_breakdown=None`.
    `show_others` has no effect when `top_n` is None or the number of
    categories does not exceed it.

    Notes:
        - An empty filtered frame returns `{"data": []}`. A missing
          `x_col` also returns `{"data": []}` and is logged as a warning.
        - The response `data` value is `DataFrame.to_dict(orient=orient)`,
          so `orient` changes the shape of every row mapping.

    Args:
        x_col (str): Categorical column to aggregate.
        top_n (int | None): Optional limit for top categories. Defaults to
            None (no limit).
        show_others (bool): If True, collapse categories outside `top_n`
            into an `"Others"` row with a breakdown payload. Defaults to
            False.
        filters (dict[str, Any] | None): Optional pre-aggregation filters.
            Defaults to None.
        rules (list[dict[str, Any]] | None): Optional computed rules applied to the result.
            Defaults to None.
        orient (str): Output orientation for `DataFrame.to_dict`.
            Defaults to `"records"`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response object with a `"data"` key containing the
        serialized distribution rows, plus any `kwargs` entries.

    Example:
    ```
        analyzer.get_categorical_distribution(
            x_col="country",
            top_n=10,
            filters={"contract_type": "Permanent"}
        )
    ```
    """
    _reject_inplace("get_categorical_distribution", kwargs)
    if not isinstance(df, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")
    return build_categorical_distribution(
        df.copy(),

        x_col,
        top_n=top_n,
        show_others=show_others,
        filters=filters,
        rules=rules,
        orient=orient,
        **kwargs,
    )


def _get_numerical_aggregation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    agg_func: str = "mean",
    round_value: int = 2,
    top_n: int | None = None,
    show_others: bool = False,
    filters: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    orient: str = "records",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Aggregate a numeric column by category.

    Rows with a null `y_col` are dropped before grouping, and the groups
    are returned sorted by aggregated value in descending order. Numeric
    results are rounded to `round_value` decimals. With
    `show_others=True` the groups beyond `top_n` are collapsed into one
    `"Others"` row whose value is recomputed from the underlying rows (not
    summed from the rounded group values) and whose `others_breakdown`
    lists the collapsed `{"x", "y"}` rows; the retained rows get
    `is_others=False` and `others_breakdown=None`.

    Notes:
        - An empty filtered frame returns `{"data": []}`. A missing
          `x_col` or `y_col`, or a failing `agg_func`, also returns
          `{"data": []}` and is logged as a warning.
        - `round_value` is applied to the group values and, separately, to
          the recomputed `"Others"` value.

    Args:
        x_col (str): Grouping column.
        y_col (str): Numeric column to aggregate.
        agg_func (str): Aggregation function name (for example: `mean`,
            `sum`, `median`, `max`). Defaults to `"mean"`.
        round_value (int): Decimal places used when the aggregated value is
            numeric. Defaults to 2.
        top_n (int | None): Optional cap for highest `y` rows. Defaults to
            None (no cap).
        show_others (bool): If True, collapse categories outside `top_n`
            into an `"Others"` row while preserving a breakdown payload.
            Defaults to False.
        filters (dict[str, Any] | None): Optional filters applied before aggregation.
            Defaults to None.
        rules (list[dict[str, Any]] | None): Optional computed rules on output rows.
            Defaults to None.
        orient (str): Output orientation for `DataFrame.to_dict`.
            Defaults to `"records"`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response object with a `"data"` key containing the
        serialized aggregation rows, plus any `kwargs` entries.
    """
    _reject_inplace("get_numerical_aggregation", kwargs)
    if not isinstance(df, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")
    return build_numerical_aggregation(
        df.copy(),

        x_col,
        y_col,
        agg_func=agg_func,
        round_value=round_value,
        top_n=top_n,
        show_others=show_others,
        filters=filters,
        rules=rules,
        orient=orient,
        **kwargs,
    )


def _get_time_series(
    df: pd.DataFrame,
    date_col: str,
    time_period: str = "M",
    num_col: str | None = None,
    agg_func: str = "count",
    filters: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    orient: str = "records",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Build a time-series aggregation from a date/datetime column.

    The date column is parsed with `pd.to_datetime(errors="coerce")` and
    rows whose date is missing or unparseable are dropped. timezone-aware
    values are converted to naive local time before bucketing. The result
    is reindexed onto a complete date range between the first and last
    bucket, so gaps appear as rows with `y=0`, and the `x` labels are
    sorted ascending.

    Notes:
        Accepted `time_period` values (matched case-insensitively):
        - `M`: Monthly buckets (`YYYY-MM`)
        - `Y`: Yearly buckets (`YYYY`)
        - `H`: Hourly Buckets (`YYYY-MM-DD HH:00`)
        - Any other value: Daily buckets (`YYYY-MM-DD`)

        With `num_col` set and `agg_func != "count"`, the numeric column is
        aggregated per bucket and rounded to whole numbers. Otherwise the
        bucket row count is used. An empty frame returns `{"data": []}`.
        A missing `date_col` or `num_col`, or a failing `agg_func`, also
        returns `{"data": []}` and is logged as a warning.

    Args:
        date_col (str): Source datetime/date column used for time bucketing.
        time_period (str): Time bucket granularity. Defaults to `"M"`.
        num_col (str | None): Optional numeric column for non-count
            aggregation. Defaults to None (count rows).
        agg_func (str): Aggregation function for `num_col`. Defaults to
            `"count"`.
        filters (dict[str, Any] | None): Optional filters applied before aggregation.
            Defaults to None.
        rules (list[dict[str, Any]] | None): Optional computed rules on output rows.
            Defaults to None.
        orient (str): Output orientation for `DataFrame.to_dict`.
            Defaults to `"records"`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response object with a `"data"` key containing the
        serialized time-series rows, plus any `kwargs` entries.
    """
    _reject_inplace("get_time_series", kwargs)
    if not isinstance(df, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")
    return build_time_series(
        df.copy(),

        date_col,
        time_period=time_period,
        num_col=num_col,
        agg_func=agg_func,
        filters=filters,
        rules=rules,
        orient=orient,
        **kwargs,
    )


def _get_kpi_value(
    df: pd.DataFrame,
    column: str,
    agg_func: str = "count",
    round_value: int = 2,
    filters: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Compute a single KPI metric.

    With `agg_func="count"` the value is the number of filtered rows and
    `column` is only used as the default title. Otherwise the value is
    `data[column].agg(agg_func)`; a missing column, a failing aggregation,
    or a non-scalar result yields `None` (each logged as a warning).
    NumPy scalars are converted to Python scalars, a null
    value becomes `None`, a float is rounded to `round_value` when that is
    non-zero, and other numeric values are converted to `int`.

    Args:
        column (str): Source column used when `agg_func` is not `count`.
            Also the default card title.
        agg_func (str): Aggregation function name; `count` uses row count.
            Defaults to `"count"`.
        round_value (int): Decimal places used when the KPI result is a
            floating-point value. A value of 0 skips rounding. Defaults
            to 2.
        filters (dict[str, Any] | None): Optional filters applied before KPI
            computation. Defaults to None.
        **kwargs: Optional metadata fields for the response card. `title`
            customizes the KPI title and is removed from the extra
            metadata; every other entry is copied into the card.

    Returns:
        dict[str, Any]: KPI payload containing `"data"`, `"title"`, and
        any additional metadata.
    """
    _reject_inplace("get_kpi_value", kwargs)
    if not isinstance(df, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")
    return build_kpi_value(
        df.copy(),

        column,
        agg_func=agg_func,
        round_value=round_value,
        filters=filters,
        **kwargs,
    )


def _get_bins(
    df: pd.DataFrame,
    col: str,
    bins: int = 10,
    filters: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    orient: str = "records",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Create histogram bins for a numeric column.

    The column is coerced with `pd.to_numeric(errors="coerce")` and nulls
    are dropped, so non-numeric text is ignored rather than raising. Bins
    come from `numpy.histogram`, and each row's `x` label is the
    `"<lower>-<upper>"` bin range formatted to two decimals.

    Notes:
        - An empty filtered frame, a non-positive or non-integer `bins`
          (booleans included), or no numeric values returns
          `{"data": []}`. A missing `col` also returns `{"data": []}` and
          is logged as a warning.

    Args:
        col (str): Numeric source column.
        bins (int): Number of histogram bins. Defaults to 10.
        filters (dict[str, Any] | None): Optional filters applied before binning.
            Defaults to None.
        rules (list[dict[str, Any]] | None): Optional computed rules on output rows.
            Defaults to None.
        orient (str): Output orientation for `DataFrame.to_dict`.
            Defaults to `"records"`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response object with a `"data"` key containing the
        serialized histogram rows, plus any `kwargs` entries.
    """
    _reject_inplace("get_bins", kwargs)
    if not isinstance(df, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")
    return build_bins(
        df.copy(),

        col,
        bins=bins,
        filters=filters,
        rules=rules,
        orient=orient,
        **kwargs,
    )



def _save_to_json(
    df: pd.DataFrame,
    file_path: str | os.PathLike,
    orient: str = 'records',
    append: bool = False,
    force_ascii: bool = False,
    indent: int = 4,
) -> None:
    """
    Save the dataframe to a JSON file only when content has changed.

    Notes:
        Before writing, the method compares the current dataframe payload to
        the existing file contents when possible. This avoids unnecessary
        rewrites and keeps the output directory stable across unchanged runs.
        Datetime columns are serialized as `%Y-%m-%d %H:%M:%S` strings to
        keep the JSON output human-readable and stable across environments.
        Paths without a directory component, such as `output.json`, are
        written to the current working directory.

        The input `df` is never modified; datetime values are reformatted on
        an internal copy. An existing file that cannot be read for comparison
        is overwritten, except with `append=True`, where an unreadable file
        raises instead of being destroyed. Missing parent directories are
        created.

    Args:
        file_path (str | os.PathLike): Destination JSON file path.
        orient (str): JSON orientation passed to `pandas.DataFrame.to_json`.
            Defaults to `"records"`.
        append (bool): If True and the target file exists, appends current
            rows to the existing JSON data and removes duplicate rows before
            writing. Duplicate detection compares list and dictionary cell
            values by their JSON content. Defaults to False.
        force_ascii (bool): Whether to escape non-ASCII characters in the
            output. Defaults to False.
        indent (int): Indentation width used when writing to disk. Defaults
            to 4.

    Returns:
        None. Nothing is written when an existing non-append file already
        holds identical content.

    Raises:
        ValueError: If `file_path` is empty, or if `append=True` and the
            existing file cannot be read with the given `orient`.
    """
    file_path = os.fspath(file_path).strip() if file_path is not None else ""

    if not file_path:
        raise ValueError("file_path cannot be empty.")

    write_json(
        df,
        file_path,
        orient = orient,
        append = append,
        force_ascii = force_ascii,
        indent = indent,
    )


def _save_to_sql(
    df: pd.DataFrame,
    table_name: str,
    database_type: str,
    database_user: str,
    database_password: str,
    database_host: str,
    database_port: str,
    database_name: str,
    database_driver: str | None = None,
    columns_types: dict | None = None,
    chunk_size: int | None = None,
    fast_executemany: bool = False,
    if_exists: str = 'append',
    index: bool = False,
) -> None:
    """
    Save the dataframe to a SQL database table using SQLAlchemy.

    Notes:
        The method supports standard SQLAlchemy URL styles and includes
        dedicated handling for SQL Server drivers and SQLite paths. For
        SQL Server, `database_driver` is required and is URL-encoded.
        For SQLite, only `database_name` is required.

        Credentials are URL-encoded before being placed in the connection
        URL. Timezone-aware datetime columns are converted to naive datetimes
        on an internal copy, so the input `df` is never modified. The engine
        is disposed of after the write, whether it succeeds or fails.

    Args:
        table_name (str): The name of the SQL table to write to.
        database_type (str): SQLAlchemy dialect/driver, for example
            `"postgresql+psycopg2"`, `"mysql+pymysql"`, `"mssql+pyodbc"`,
            or `"sqlite"`.
        database_user (str): Database username.
        database_password (str): Database password.
        database_host (str): Database host address.
        database_port (str): Database port.
        database_name (str): Database/schema name, or SQLite file path. The
            special value `":memory:"` targets an in-memory SQLite database.
        database_driver (str | None): ODBC driver name for SQL Server
            dialects. Defaults to None.
        columns_types (dict | None): Optional SQLAlchemy dtype mapping to
            control target SQL column types. Defaults to None.
        chunk_size (int | None): Optional number of rows per write chunk.
            Defaults to None (single batch).
        fast_executemany (bool): Enables `fast_executemany` for SQL Server
            pyodbc connections when supported. Defaults to False.
        if_exists (str): How to behave if the table already exists.
            Options: 'fail', 'replace', 'append'. Defaults to 'append'.
        index (bool): Whether to write the DataFrame index as a SQL column.
            Defaults to False.

    Returns:
        None

    Raises:
        ValueError: If `table_name` or `database_type` is empty, if
            `if_exists` is not one of 'fail', 'replace', or 'append', or if
            the credentials required by the selected dialect are missing
            (`database_name` for SQLite, `database_driver` and all
            connection fields for SQL Server).
        ImportError: If the optional `SQLAlchemy` dependency is not
            installed.

    Example:
    ```
        df.save_to_sql(
            table_name="cleaned_search_data",
            database_type="postgresql+psycopg2",
            database_user="postgres",
            database_password="secret",
            database_host="localhost",
            database_port="5432",
            database_name="analytics_db",
            if_exists="replace",
            index=False
        )
    ```
    """
    db_type = str(database_type or '').strip().lower()
    db_user = str(database_user or '').strip()
    db_pass = str(database_password or '').strip()
    db_host = str(database_host or '').strip()
    db_port = str(database_port or '').strip()
    db_name = str(database_name or '').strip()
    db_driver = str(database_driver or '').strip() or None
    table_name = str(table_name or '').strip()

    if not table_name:
        raise ValueError("table_name cannot be empty.")

    if if_exists not in ['fail', 'replace', 'append']:
        raise ValueError(f"Invalid if_exists value '{if_exists}'. Use 'fail', 'replace', or 'append'.")

    if not db_type:
        raise ValueError("database_type cannot be empty.")

    write_sql(
        df,
        table_name,
        db_type,
        db_user,
        db_pass,
        db_host,
        db_port,
        db_name,
        db_driver,
        columns_types,
        chunk_size,
        fast_executemany,
        if_exists,
        index,
    )


@pd.api.extensions.register_dataframe_accessor("bynat")
class BynatAccessor:
    """
    bynat cleaning, enrichment, and export methods for any `pandas.DataFrame`.

    Every transformation returns a new DataFrame and leaves the original
    untouched by default. The in-place capable transformations accept
    `inplace` with the same calling convention as the corresponding
    `BaseData` method (same parameter kind and positional slot);
    `inplace=True` mutates the wrapped DataFrame in place and returns `None`
    (or the hierarchical statistics DataFrame for `handle_outliers`,
    `drop_outliers`, `fill_missing`, and `fill_missing_from` when
    `get_hierarchical_stats=True`), while `inplace=False` leaves the original
    untouched. Cached methods (translation,
    geocoding, currency conversion, and NLP) use one shared `CacheManager` per
    cache directory: the `BYNAT_CACHE_DIR` environment variable or the default
    directory, unless `with_cache(...)` selects another one.

    Example:
    ```
        import bynat
        import pandas as pd

        df = pd.DataFrame({"user.name": ["Ada"], "status": ["مكتمل"]})

        df = df.bynat.rename_all_DOTS()
        df = df.bynat.with_cache("cache").translate_categorical_column("status")
    ```
    """

    def __init__(self, pandas_obj: pd.DataFrame, cache_manager: CacheManager | None = None) -> None:
        """
        Bind the accessor to a frame and an optional cache manager.

        pandas constructs the accessor with only the frame; the cache manager
        is supplied by `with_cache(...)`. A None manager is resolved lazily to
        the shared manager for the default directory on first cached call.

        Args:
            pandas_obj (pd.DataFrame): Frame the accessor wraps. It is stored
                by reference, so `inplace=True` mutates this object.
            cache_manager (CacheManager | None): Manager for cached methods.
                Defaults to None.
        """
        self._obj = pandas_obj
        self._cache_manager = cache_manager

    @property
    def cache_manager(self) -> CacheManager:
        """The `CacheManager` used by cached methods, created on first use."""
        if self._cache_manager is None:
            self._cache_manager = resolve_cache_manager(None)

        return self._cache_manager

    def with_cache(self, cache: str | os.PathLike | CacheManager | None) -> "BynatAccessor":
        """
        Return an accessor for the same frame that caches in another place.

        Args:
            cache (str | os.PathLike | CacheManager | None): A cache directory
                (resolved to its shared manager), an explicit manager, or None
                for the default directory.

        Returns:
            BynatAccessor: An accessor bound to that cache.
        """
        manager = resolve_cache_manager(cache)
        return BynatAccessor(self._obj, cache_manager = manager)

    def clear_cache_for_column(self, func_name: str, target_col: str) -> None:
        """
        Delete a cached column bucket for one of the cached methods.

        Args:
            func_name (str): Name of the cached method.
            target_col (str): Nested cache key to remove, usually a column name.
        """
        self.cache_manager.delete_column_cache(func_name, target_col)

    drop_by_substring = _frame_method(_columns.drop_by_substring, inplace = True)
    drop_CLASS_columns = _frame_method(_columns.drop_CLASS_columns, inplace = True)
    rename_by_substring = _frame_method(_columns.rename_by_substring, inplace = True)
    rename_all_DOTS = _frame_method(_columns.rename_all_DOTS, inplace = True)
    reorder_columns = _frame_method(_columns.reorder_columns, inplace = True)
    melt_transform_pivot = _frame_method(_columns.melt_transform_pivot, inplace = True)
    move_column = _frame_method(_columns.move_column, inplace = True)
    align_lat_lng = _frame_method(_columns.align_lat_lng, inplace = True)
    split_list_objects = _frame_method(_columns.split_list_objects, inplace = True)

    extract_keywords = _frame_method(_text.extract_keywords, inplace = True)
    truncate_after_substring = _frame_method(_text.truncate_after_substring, inplace = True)
    categorize_by_reference = _frame_method(_text.categorize_by_reference, inplace = True)

    handle_outliers = _frame_method(_stats.handle_outliers, inplace = True, stats = True)
    drop_outliers = _frame_method(_stats.drop_outliers, inplace = True, stats = True)
    fill_missing = _frame_method(_stats.fill_missing, inplace = True, stats = True)
    fill_missing_from = _frame_method(_stats.fill_missing_from, inplace = True, stats = True)
    get_hierarchical_stats = _frame_method(_stats.get_hierarchical_stats)
    profile = _frame_method(profile)

    get_categorical_distribution = _frame_method(_get_categorical_distribution)
    get_numerical_aggregation = _frame_method(_get_numerical_aggregation)
    get_time_series = _frame_method(_get_time_series)
    get_kpi_value = _frame_method(_get_kpi_value)
    get_bins = _frame_method(_get_bins)

    impute_by_language = _frame_method(_translate.impute_by_language, inplace = True)
    translate_conditional_column = _cached_frame_method(
        _translate.translate_conditional_column, inplace = True, inplace_before = "random_state"
    )
    translate_categorical_column = _cached_frame_method(_translate.translate_categorical_column, inplace = True)
    fill_missing_coordinates = _cached_frame_method(_geocode.fill_missing_coordinates, inplace = True)
    convert_to_usd = _cached_frame_method(_currency.convert_to_usd, inplace = True)
    extract_entities_nlp = _cached_frame_method(_nlp.extract_entities_nlp, inplace = True)

    save_to_json = _frame_method(_save_to_json)
    save_to_sql = _frame_method(_save_to_sql)
