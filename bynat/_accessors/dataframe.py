"""The `df.bynat` pandas accessor for plain `pandas.DataFrame` objects.

This module owns pandas registration, the accessor class, and the
accessor-specific adaptation of profiling output. Every transformation is
delegated to the functional packages (`cleaning`, `profiling`, `caching`);
no domain algorithm lives here.
"""

import os
from typing import Any

import pandas as pd

import bynat.analytics as analytics
from bynat.caching import CacheManager, shared_cache_manager
from bynat.cleaning import columns, io, stats, text
from bynat.cleaning._outputs import is_basedata_type
from bynat.cleaning.enrich import currency, geocode, nlp, translate
from bynat.profiling import profile as _profiling_profile

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
    if is_basedata_type(output_type):
        return output_type(data = _profiling_profile(df, *columns, output_type = pd.DataFrame))
    return _profiling_profile(df, *columns, output_type = output_type)


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
    """Return distribution counts for a categorical column."""
    _reject_inplace("get_categorical_distribution", kwargs)
    return analytics.Analyzer(df).get_categorical_distribution(
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
    """Aggregate a numeric column by category."""
    _reject_inplace("get_numerical_aggregation", kwargs)
    return analytics.Analyzer(df).get_numerical_aggregation(
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
    """Build a time-series aggregation from a date/datetime column."""
    _reject_inplace("get_time_series", kwargs)
    return analytics.Analyzer(df).get_time_series(
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
    """Compute a single KPI metric."""
    _reject_inplace("get_kpi_value", kwargs)
    return analytics.Analyzer(df).get_kpi_value(
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
    """Create histogram bins for a numeric column."""
    _reject_inplace("get_bins", kwargs)
    return analytics.Analyzer(df).get_bins(
        col,
        bins=bins,
        filters=filters,
        rules=rules,
        orient=orient,
        **kwargs,
    )


# The canonical docstrings live on `Analyzer`; keep runtime help and the
# generated stub synchronized with that single source of truth.
_get_categorical_distribution.__doc__ = analytics.Analyzer.get_categorical_distribution.__doc__
_get_numerical_aggregation.__doc__ = analytics.Analyzer.get_numerical_aggregation.__doc__
_get_time_series.__doc__ = analytics.Analyzer.get_time_series.__doc__
_get_kpi_value.__doc__ = analytics.Analyzer.get_kpi_value.__doc__
_get_bins.__doc__ = analytics.Analyzer.get_bins.__doc__


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
            self._cache_manager = shared_cache_manager()

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
        manager = cache if isinstance(cache, CacheManager) else shared_cache_manager(cache)
        return BynatAccessor(self._obj, cache_manager = manager)

    def clear_cache_for_column(self, func_name: str, target_col: str) -> None:
        """
        Delete a cached column bucket for one of the cached methods.

        Args:
            func_name (str): Name of the cached method.
            target_col (str): Nested cache key to remove, usually a column name.
        """
        self.cache_manager.delete_column_cache(func_name, target_col)

    drop_by_substring = _frame_method(columns.drop_by_substring, inplace = True)
    drop_CLASS_columns = _frame_method(columns.drop_CLASS_columns, inplace = True)
    rename_by_substring = _frame_method(columns.rename_by_substring, inplace = True)
    rename_all_DOTS = _frame_method(columns.rename_all_DOTS, inplace = True)
    reorder_columns = _frame_method(columns.reorder_columns, inplace = True)
    melt_transform_pivot = _frame_method(columns.melt_transform_pivot, inplace = True)
    move_column = _frame_method(columns.move_column, inplace = True)
    align_lat_lng = _frame_method(columns.align_lat_lng, inplace = True)
    split_list_objects = _frame_method(columns.split_list_objects, inplace = True)

    extract_keywords = _frame_method(text.extract_keywords, inplace = True)
    truncate_after_substring = _frame_method(text.truncate_after_substring, inplace = True)
    categorize_by_reference = _frame_method(text.categorize_by_reference, inplace = True)

    handle_outliers = _frame_method(stats.handle_outliers, inplace = True, stats = True)
    drop_outliers = _frame_method(stats.drop_outliers, inplace = True, stats = True)
    fill_missing = _frame_method(stats.fill_missing, inplace = True, stats = True)
    fill_missing_from = _frame_method(stats.fill_missing_from, inplace = True, stats = True)
    get_hierarchical_stats = _frame_method(stats.get_hierarchical_stats)
    profile = _frame_method(profile)

    get_categorical_distribution = _frame_method(_get_categorical_distribution)
    get_numerical_aggregation = _frame_method(_get_numerical_aggregation)
    get_time_series = _frame_method(_get_time_series)
    get_kpi_value = _frame_method(_get_kpi_value)
    get_bins = _frame_method(_get_bins)

    impute_by_language = _frame_method(translate.impute_by_language, inplace = True)
    translate_conditional_column = _cached_frame_method(
        translate.translate_conditional_column, inplace = True, inplace_before = "random_state"
    )
    translate_categorical_column = _cached_frame_method(translate.translate_categorical_column, inplace = True)
    fill_missing_coordinates = _cached_frame_method(geocode.fill_missing_coordinates, inplace = True)
    convert_to_usd = _cached_frame_method(currency.convert_to_usd, inplace = True)
    extract_entities_nlp = _cached_frame_method(nlp.extract_entities_nlp, inplace = True)

    save_to_json = _frame_method(io.save_to_json)
    save_to_sql = _frame_method(io.save_to_sql)
