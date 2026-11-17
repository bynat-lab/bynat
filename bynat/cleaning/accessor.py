"""The `df.bynat` pandas accessor."""

import functools
import inspect
import os
from collections.abc import Callable
from typing import Any

import pandas as pd

from bynat.caching import CacheManager, shared_cache_manager

from . import columns, io, profile, stats, text
from .enrich import currency, geocode, nlp, translate

__all__ = ['BynatAccessor']


def _method_signature(func: Callable) -> inspect.Signature:
    """The accessor-facing signature: `self` replaces the frame, no `cache_manager`."""
    signature = inspect.signature(func)
    parameters = [
        parameter
        for parameter in list(signature.parameters.values())[1:]
        if parameter.name != 'cache_manager'
    ]
    self_parameter = inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return signature.replace(parameters = [self_parameter, *parameters])


def _with_inplace(
    signature: inspect.Signature, before: str | None = None
) -> tuple[inspect.Signature, bool, int]:
    """Insert `inplace` where the class API declares it.

    Returns the new signature, whether `inplace` is keyword-only, and its
    index among the positional parameters. Without ``before``, `inplace`
    follows the last positional-or-keyword parameter; when the wrapped
    function takes variadic positional arguments there is no free
    positional slot, so it leads the keyword-only parameters instead.
    """
    parameters = list(signature.parameters.values())
    kind: inspect._ParameterKind
    if before is not None:
        index = next(
            position
            for position, parameter in enumerate(parameters)
            if parameter.name == before
        )
        kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
    else:
        index = next(
            (
                position
                for position, parameter in enumerate(parameters)
                if parameter.kind
                in (
                    inspect.Parameter.KEYWORD_ONLY,
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ),
            len(parameters),
        )
        if index < len(parameters) and parameters[index].kind is inspect.Parameter.VAR_POSITIONAL:
            # No free positional slot: `inplace` becomes the first
            # keyword-only parameter, i.e. it goes AFTER the *args.
            kind = inspect.Parameter.KEYWORD_ONLY
            index += 1
        else:
            kind = inspect.Parameter.POSITIONAL_OR_KEYWORD

    position = sum(
        1
        for parameter in parameters[1:index]
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )
    parameters.insert(index, inspect.Parameter('inplace', kind, default = False))
    return signature.replace(parameters = parameters), kind is inspect.Parameter.KEYWORD_ONLY, position


def _frame_method(
    func: Callable, *, inplace: bool = False, stats: bool = False, inplace_before: str | None = None
) -> Callable:
    """Expose a shared implementation as an accessor method on the wrapped frame."""
    signature = _method_signature(func)
    keyword_only = True
    position = -1
    if inplace:
        signature, keyword_only, position = _with_inplace(signature, before = inplace_before)

    if inplace:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            if keyword_only:
                flag = kwargs.pop('inplace', False)
            elif position >= 0 and len(args) > position:
                # `inplace` sits at `position`, so any further positional
                # arguments belong to the parameters that follow it and must
                # be handed on rather than dropped.
                flag = args[position]
                args = args[:position] + args[position + 1 :]
            else:
                flag = kwargs.pop('inplace', False)

            with_stats = stats and bool(kwargs.get('get_hierarchical_stats', False))
            outcome = func(self._obj, *args, **kwargs)

            if not flag:
                return outcome

            result, statistics = outcome if with_stats else (outcome, None)
            self._obj._update_inplace(result)  # type: ignore[operator]
            return statistics
    else:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            return func(self._obj, *args, **kwargs)

    method.__signature__ = signature  # type: ignore[attr-defined]
    return method


def _cached_frame_method(
    func: Callable, *, inplace: bool = False, inplace_before: str | None = None
) -> Callable:
    """Like `_frame_method`, also passing the accessor's `CacheManager`."""
    signature = _method_signature(func)
    keyword_only = True
    position = -1
    if inplace:
        signature, keyword_only, position = _with_inplace(signature, before = inplace_before)

    if inplace:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            if keyword_only:
                flag = kwargs.pop('inplace', False)
            elif position >= 0 and len(args) > position:
                # See `_frame_method`: keep the arguments that follow `inplace`.
                flag = args[position]
                args = args[:position] + args[position + 1 :]
            else:
                flag = kwargs.pop('inplace', False)

            result = func(self._obj, *args, cache_manager = self.cache_manager, **kwargs)

            if not flag:
                return result

            self._obj._update_inplace(result)  # type: ignore[operator]
            return None
    else:
        @functools.wraps(func)
        def method(self: "BynatAccessor", *args: Any, **kwargs: Any) -> Any:
            return func(self._obj, *args, cache_manager = self.cache_manager, **kwargs)

    method.__signature__ = signature  # type: ignore[attr-defined]
    return method


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
        self._obj = pandas_obj
        self._cache_manager = cache_manager

    @property
    def cache_manager(self) -> CacheManager:
        """The `CacheManager` used by cached methods."""
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
    profile = _frame_method(profile.profile)

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
