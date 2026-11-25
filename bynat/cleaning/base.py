"""
`pandas.DataFrame` subclasses: `BaseData`, `JsonFile`, and `CsvFile`.

They are thin wrappers over the private `_columns`, `_text`, and `_stats`
modules and the `enrich` and `io` packages, whose functions the `df.bynat`
accessor shares. Both APIs accept `inplace=True` for the transformations that
support it, and `JsonFile` / `CsvFile` load data directly from disk.
"""

import os
from collections.abc import Callable, Iterable
from typing import Any, Self

import numpy as np
import pandas as pd

from bynat.caching import CacheManager
from bynat.profiling import profile

from . import _columns
from . import _stats
from . import _text
from . import io
from ._internal import is_basedata_type
from ._internal import shares_doc as _shares_doc
from .enrich import _currency, _geocode, _nlp, _translate
from .enrich.providers import Geocoder, RateSource, Translator

__all__ = ['BaseData', 'JsonFile', 'CsvFile']


class BaseData(pd.DataFrame):
    """
    Extend `pandas.DataFrame` with project-specific cleaning, translation,
    enrichment, and export helpers.

    Every transformation returns a new object by default and leaves the
    receiver untouched. The transformations that support in-place behavior
    accept `inplace=True`, which mutates the receiver and returns `None`
    (or the hierarchical statistics DataFrame for `handle_outliers`,
    `drop_outliers`, `fill_missing`, and `fill_missing_from` when
    `get_hierarchical_stats=True`). `inplace` is positional-or-keyword on
    most methods and keyword-only where the wrapped function takes variadic
    positional arguments.

    `df.bynat` is the equivalent accessor API for plain `pandas.DataFrame`
    objects; `BaseData` is a `DataFrame` subclass and keeps its subclass
    through pandas operations.

    Notes:
        Instances keep a `CacheManager` in metadata so cached helper methods can
        reuse translation, geocoding, and currency results across runs. It is
        created on first use and shared with the frames pandas derives from
        this one, so pandas operations do not build new managers.
    """

    _metadata = ['cache_manager']

    @property
    def _constructor(self) -> Callable[..., Self]:
        """
        Preserve the custom dataframe subclass during pandas operations.

        pandas calls this property whenever it builds a derived frame, so
        chained operations and slices keep producing the current subclass
        instead of a plain `pandas.DataFrame`.

        Returns:
            Callable: The current subclass (`type(self)`), so chained
            operations keep producing `BaseData`-derived objects.
        """
        return type(self)


    def __init__(self, data = None, cache_dir: str | os.PathLike | None = None, *args, **kwargs) -> None:
        """
        Initialize the custom dataframe from in-memory tabular data.

        Args:
            data: Optional tabular data passed directly to `pandas.DataFrame`.
            cache_dir: Directory for caching data. When None, uses the
                `BYNAT_CACHE_DIR` environment variable if set, otherwise
                "Settings/Cache Data/Automated".
            *args: Additional positional arguments forwarded to
                `pandas.DataFrame`.
            **kwargs: Additional keyword arguments forwarded to
                `pandas.DataFrame`.

        Returns:
            None

        Notes:
            File-specific loading is implemented by `JsonFile` and `CsvFile`.
        """
        object.__setattr__(self, '_bynat_cache_dir', cache_dir)
        object.__setattr__(self, '_bynat_cache_manager', None)

        super().__init__(data = data, *args, **kwargs)


    @property
    def cache_manager(self) -> CacheManager:
        """
        The `CacheManager` used by cached helper methods, created on first use.

        The manager is stored on the instance, so it is shared with every
        frame pandas derives from this one and is not rebuilt by pandas
        operations. Assigning `None` through the setter clears it, and the
        next access creates a fresh manager.

        Returns:
            CacheManager: The manager for this object's cache directory.
        """
        manager = self.__dict__.get('_bynat_cache_manager')

        if manager is None:
            manager = CacheManager(cache_dir = self.__dict__.get('_bynat_cache_dir'))
            object.__setattr__(self, '_bynat_cache_manager', manager)

        return manager


    @cache_manager.setter
    def cache_manager(self, manager: CacheManager | None) -> None:
        """Replace the cached `CacheManager`, or clear it with None."""
        object.__setattr__(self, '_bynat_cache_manager', manager)


    def _finish(self, result: pd.DataFrame, inplace: bool) -> Self | None:
        """
        Return `result`, or copy it into this object when `inplace=True`.

        With `inplace=False` the shared function's result is returned as-is.
        With `inplace=True` the result is written into this object through
        `_update_inplace`, preserving object identity, and `None` is returned.

        Args:
            result (pd.DataFrame): Frame produced by the shared function.
            inplace (bool): Whether to mutate this object.

        Returns:
            Self | None: `result` when `inplace=False`, otherwise None.
        """
        if not inplace:
            return result

        self._update_inplace(result)
        return None


    def _finish_with_stats(self, outcome: Any, inplace: bool, with_stats: bool) -> Any:
        """
        `_finish` for methods that can also return hierarchical statistics.

        With `inplace=False` the outcome is returned unchanged: the frame, or
        the `(frame, statistics)` tuple when `with_stats=True`. With
        `inplace=True` the frame is written into this object and the
        statistics are returned on their own, or `None` when `with_stats` is
        False.

        Args:
            outcome (Any): Frame, or `(frame, statistics)` when `with_stats`.
            inplace (bool): Whether to mutate this object.
            with_stats (bool): Whether the operation produced statistics.

        Returns:
            Any: See above.
        """
        result, hierarchical_stats = outcome if with_stats else (outcome, None)

        if not inplace:
            return (result, hierarchical_stats) if with_stats else result

        self._update_inplace(result)
        return hierarchical_stats


    def clear_cache_for_column(self, func_name: str, target_col: str) -> None:
        """
        Delete a cached column bucket for one of the helper methods.

        Args:
            func_name (str): Name of the cached helper function.
            target_col (str): Nested cache key to remove, usually a column name.

        Returns:
            None
        """
        self.cache_manager.delete_column_cache(func_name, target_col)


    def view(self) -> pd.DataFrame:
        """
        Return the object as a standard pandas DataFrame for inspection and
        rich display.

        The result is a new plain `pandas.DataFrame`: it is not a `BaseData`
        instance, does not carry the `cache_manager` metadata, and mutating it
        does not affect the original.

        Returns:
            pandas.DataFrame: A DataFrame representation of the current object.

        Example:
        ```
            Usage:
                # Viewing a slice of the custom object as a dynamic table
                search_dataframe.iloc[0:100].view()

                # Using pandas-specific plotting on the view
                search_dataframe.view().plot(kind='bar')
        ```
        """

        return pd.DataFrame(self)


    @_shares_doc(_columns.drop_by_substring)
    def drop_by_substring(self, substring: str, inplace: bool = False) -> Self | None:
        """
        Drop all columns that contain a specific substring within their names.

        Columns are matched with a plain ``substring in col`` test, so the value is
        literal text rather than a regular expression. A column whose name does not
        contain `substring` is kept unchanged. When no column matches, a copy of
        `df` is returned rather than `df` itself.

        Args:
            substring (str): The text to search for; any column containing this
                string will be removed.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe without the matching columns;
            the input is not modified. With `inplace=True`, the receiver is mutated in place
            and None is returned.

        Example:
        ```
            Column Removal:
                'user_id'         ->  (dropped)
                'user_metadata'   ->  (dropped)
                'created_at'      ->  'created_at' (kept)

            Usage:
                df.drop_by_substring("user")
        ```
        """
        return self._finish(_columns.drop_by_substring(self, substring), inplace)


    @_shares_doc(_columns.drop_CLASS_columns)
    def drop_CLASS_columns(self, inplace: bool = False) -> Self | None:
        """
        Drop all columns that contain the substring "__CLASS__" from the data.

        Equivalent to `drop_by_substring(df, "__CLASS__")`; the marker is matched
        literally.

        Args:
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe without the matching columns;
            the input is not modified. With `inplace=True`, the receiver is mutated in place
            and None is returned.

        Example:
        ```
            Column Removal:
                'metadata.__CLASS__'  ->  (dropped)
                'object.__CLASS__id'  ->  (dropped)
                'user_name'           ->  'user_name' (kept)

            Usage:
                df.drop_CLASS_columns()
        ```
        """
        return self._finish(_columns.drop_CLASS_columns(self), inplace)


    @_shares_doc(_columns.rename_by_substring)
    def rename_by_substring(self, old_substring: str, new_substring: str, inplace: bool = False) -> Self | None:
        """
        Rename columns by replacing a specific substring with a new one.

        Args:
            old_substring (str): The text to search for within the column names.
                Matched literally and replaced everywhere it occurs.
            new_substring (str): The text to replace the old substring with.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with renamed columns;
            the input is not modified. Columns without the substring are kept
            unchanged, and when no column name contains `old_substring` a copy of
            the input is returned. With `inplace=True`, the receiver is mutated in
            place and None is returned.

        Example:
        ```
            Column Transformation:
                'user_display_name'  ->  'user_name'
                'post_display_name'  ->  'post_name'
                'created_at'         ->  'created_at' (unchanged)

            Usage:
                df.rename_by_substring("display_name", "name")
        ```
        """
        return self._finish(_columns.rename_by_substring(self, old_substring, new_substring), inplace)


    @_shares_doc(_columns.rename_all_DOTS)
    def rename_all_DOTS(self, unified_separator: str = "_", inplace: bool = False) -> Self | None:
        """
        Rename columns by replacing all occurrences of dots ('.') with a unified separator.

        Args:
            unified_separator (str): The new string to replace dots with.
                Defaults to "_".
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with renamed columns;
            the input is not modified. Column names without a dot are kept
            unchanged. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Example:
        ```
            Column Transformation:
                'location.display_name'  ->  'location_display_name'
                'user.id'                ->  'user_id'
                'status'                 ->  'status' (unchanged)

            Usage:
                df.rename_all_DOTS(unified_separator = "_")
        ```
        """
        return self._finish(_columns.rename_all_DOTS(self, unified_separator), inplace)


    @_shares_doc(_columns.reorder_columns)
    def reorder_columns(self, *first_cols, inplace: bool = False) -> Self | None:
        """
        Reorder the dataframe by moving a specified list of columns to the front.

        Any columns not mentioned in `first_cols` will be appended to the end
        preserving their original relative order.

        Args:
            first_cols (tuple): Column names that should appear first. Names that
                are not present in `df.columns` are ignored.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with reordered columns;
            the input is not modified. Unlisted columns keep their relative order
            at the end, and when none of `first_cols` exist a copy of the input is
            returned. With `inplace=True`, the receiver is mutated in place and None
            is returned.

        Example:
        ```
            Initial Columns: ['C', 'A', 'D', 'B']

            Operation: reorder_columns('A', 'B')
            Result:    ['A', 'B', 'C', 'D']

            Usage:
                df.reorder_columns("id", "timestamp")
        ```
        """
        return self._finish(_columns.reorder_columns(self, *first_cols), inplace)


    @_shares_doc(_columns.melt_transform_pivot)
    def melt_transform_pivot(
        self,
        id_vars: list | str,
        value_vars: list | str | None = None,
        transform_func: Callable | None = None,
        aggfunc: str | Callable = 'first',
        var_name: str = 'variable_name',
        value_name: str = 'variable_value',
        pivot_index: list | str | None = None,
        pivot_columns: list | str | None = None,
        inplace: bool = False,
        **kwargs
    ) -> Self | None:
        """
        Reshape selected columns to long format, transform their values, and
        pivot them back to wide format.

        Notes:
            This helper is useful when the same vectorized operation should be
            applied to several value columns through one temporary long-form
            series. Duplicate identifier/value-column pairs are resolved with
            `aggfunc`, so the output can have fewer rows than the input and has a
            fresh RangeIndex. By default, the method pivots back using `id_vars`
            as rows and the melted variable column (`var_name`) as output columns.
            Use `pivot_index` and `pivot_columns` only when you want a different
            pivot layout from the melted dataframe.

            The standalone function never modifies `df`.

        Args:
            id_vars (list | str): Column(s) to use as identifier variables.
            value_vars (list | str | None): Column(s) to unpivot. If None, uses all columns
                that are not set as `id_vars`.
            transform_func (Callable | None): Function applied to the melted
                value series before pivoting back. The function should accept a
                pandas Series and return a same-length array-like or Series.
                Defaults to None.
            aggfunc (str | callable): Aggregation function to use when pivoting back
                in case of duplicate identifiers. Defaults to 'first'.
            var_name (str): Name to use for the 'variable' column. Defaults to 'variable_name'.
            value_name (str): Name to use for the 'value' column. Defaults to 'variable_value'.
            pivot_index (list | str | None): Column(s) from the melted dataframe
                to use as pivot index. Allowed columns are `id_vars` and
                `var_name`. Defaults to `id_vars`, unless `pivot_columns` is
                provided, then it uses the remaining `id_vars` plus `var_name`.
            pivot_columns (list | str | None): Column(s) from the melted
                dataframe to use as pivot columns. Allowed columns are `id_vars`
                and `var_name`. Defaults to `var_name`.
            **kwargs: Additional keyword arguments to pass to `transform_func`.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new, reshaped dataframe; the input is
            not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Raises:
            TypeError: If a column argument has an invalid type, if `aggfunc`
                is invalid, or if `transform_func` is provided but is not
                callable.
            ValueError: If `id_vars`, `value_vars`, `var_name`, or
                `value_name` is invalid, if identifier/value/pivot columns
                overlap incorrectly, or if `transform_func` returns invalid
                output. A failure raised by `pandas.DataFrame.pivot_table` is
                also reported as `ValueError`.
            RuntimeError: If `transform_func` raises an exception.

        Example:
        ```
            # Bulk clean 3 columns simultaneously by making them uppercase
            df.melt_transform_pivot(
                id_vars="user_id",
                value_vars=["col1", "col2", "col3"],
                transform_func=lambda s: s.str.upper()
            )
        ```
        """
        result = _columns.melt_transform_pivot(
            self,
            id_vars,
            value_vars = value_vars,
            transform_func = transform_func,
            aggfunc = aggfunc,
            var_name = var_name,
            value_name = value_name,
            pivot_index = pivot_index,
            pivot_columns = pivot_columns,
            **kwargs
        )
        return self._finish(result, inplace)


    @_shares_doc(_columns.move_column)
    def move_column(self, col_to_move: str, col_target: str, position: str = "after", inplace: bool = False) -> Self | None:
        """
        Move a specific column to a new position relative to a target column.

        Args:
            col_to_move (str): The name of the column you want to relocate.
            col_target (str): The reference column where the move will happen.
            position (str): Whether to place the column "after" or "before" the
                target column. Defaults to "after".
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with the column moved;
            the input is not modified. If either column is absent, an unchanged
            copy is returned. With `inplace=True`, the receiver is mutated in place
            and None is returned.

        Raises:
            ValueError: If the `position` argument is not 'after' or 'before'.
                The check runs after the missing-column check, so an unknown
                column returns a copy rather than raising.

        Example:
        ```
            Initial Columns: ['A', 'B', 'C', 'D']

            Operation: move_column(col_to_move='A', col_target='C', position='after')
            Result:    ['B', 'C', 'A', 'D']

            Usage:
                df.move_column("user_id", "user_name", position="before")
        ```
        """
        return self._finish(_columns.move_column(self, col_to_move, col_target, position), inplace)


    @_shares_doc(_columns.align_lat_lng)
    def align_lat_lng(self, inplace: bool = False) -> Self | None:
        """
        Standardize the coordinate order by moving the 'longitude' column
        immediately after the 'latitude' column.

        .. note::
        This method strictly expects the column names to be exactly **'latitude'**
        and **'longitude'** (case-sensitive). If the columns are named differently
        (e.g., 'lat' or 'LONG'), the alignment will not occur.

        Args:
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with aligned coordinate
            columns; the input is not modified, and when either column is absent an
            unchanged copy is returned. With `inplace=True`, the receiver is
            mutated in place and None is returned.

        Example:
        ```
            Column Reordering:
                ['longitude', 'id', 'latitude']  ->  ['id', 'latitude', 'longitude']

            Usage:
                df.align_lat_lng()
        ```
        """
        return self._finish(_columns.align_lat_lng(self), inplace)


    @_shares_doc(_text.extract_keywords)
    def extract_keywords(
            self,
            *source_cols,
            inplace: bool = False,
            remove_extracted: bool = False,
            use_regex: bool = False,
            **target_cols_and_keywords
    ) -> Self | None:
        """
        Search for keywords or regular expressions across source columns and extract them into new target columns.
        Matches are case-insensitive and are formatted to Title Case in the target column.

        Notes:
            - **Keyword Priority**: Keywords are extracted based on list order. The first item in the list has the highest precedence.
            - **Non-Destructive Updates**: If this method is called multiple times targeting the exact same output column.
                Subsequent calls will only populate empty cells (NaNs) and will NEVER overwrite previously extracted values.
            - **Literal Matching**: Keywords are treated as literal text (e.g., `C++`, `.NET`),
              and will not be interpreted as regular expressions unless `use_regex` is set to True.
            - **Title-Casing**: The extracted value is the matched keyword rendered in
              Title Case. Under `use_regex=True` the first capture group of the match
              is used instead; a pattern with no capture group is wrapped so the whole
              pattern is captured, and a pattern with a group yields that group only.
            - **Text Coercion**: Source columns are converted to strings only
              for matching, so numeric/object columns do not break text search.
            - **Performance**: Each unique combined text is matched once and the
              results are mapped back to every row. Literal keywords are matched
              with one combined pattern (or an Aho-Corasick automaton when the
              optional `pyahocorasick` dependency is installed).
            - **Optional Dependency**: Literal matching uses `pyahocorasick` when
              it is installed and every keyword is ASCII; otherwise it falls back to
              one combined regular expression. Both paths return the same result and
              neither raises when the dependency is missing.
            - Source columns that are absent from `df` are ignored. When none of
              them are present, an unchanged copy of `df` is returned.
            - The standalone function never modifies `df`.

        Args:
            *source_cols: Variable number of column names to search within. Column
                names that do not exist in `df` are ignored.
            remove_extracted (bool): If True, removes the matched keywords from the
                original source columns to clean the text. Defaults to False.
            use_regex (bool): If True, treats the input strings in **target_cols_and_keywords
                as regular expressions for pattern extraction. Defaults to False.
            **target_cols_and_keywords: Keyword arguments where the key is the new
                column name and the value is a list of strings to search for. A
                single string is treated as a one-item list.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with the extracted columns; the
            input is not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Example:
        ```
            Initial Column:
                'description': ["Blue Suede Shoes", "Red Cotton Shirt"]

            Operation:
                extract_keywords('description', colors=['blue', 'red'], remove_extracted=True)

            Result:
                'description': ["Suede Shoes", "Cotton Shirt"]
                'colors':      ["Blue", "Red"]

            Usage:
                df.extract_keywords("comments", "tags", categories=["urgent", "review"])
        ```
        """
        result = _text.extract_keywords(
            self,
            *source_cols,
            remove_extracted = remove_extracted,
            use_regex = use_regex,
            **target_cols_and_keywords
        )
        return self._finish(result, inplace)


    @_shares_doc(_columns.split_list_objects)
    def split_list_objects(
            self,
            source_col: str,
            remove_source_col: bool = False,
            explode_rows: bool = False,
            cartesian_explode: bool = False,
            inplace: bool = False,
            **target_cols_and_indices
    ) -> Self | None:
        """
        Extract specific elements from lists stored within a column into new columns.

        This method allows you to pull items out of list-like objects by their index.
        It can either join multiple indices into a string, explode them into parallel
        separate rows, or perform a sequential cartesian product explosion.

        Notes:
            - **String Joining**: When providing a list of indices with
              `explode_rows=False`, valid extracted elements are joined
              into a single comma-separated string (NaNs are ignored).
            - **Cartesian vs. Parallel Explode**: When exploding multiple columns,
              `cartesian_explode=False` (default) explodes them in parallel (requires
              lists to be of equal length). `cartesian_explode=True` explodes them
              sequentially, creating a cross-join (cartesian product) of all elements.
            - **Scalar Indices**: A scalar index extracts one element per row and
              does not explode, even when `explode_rows=True`.
            - **Sentinel Values**: An index of `None` or `'all'` copies the whole
              source list into the target column.
            - Exploding rows changes the row count and resets the index.
            - The standalone function never modifies `df`. A missing `source_col` returns an
              unchanged copy.

        Args:
            source_col (str): The name of the column containing list-like objects.
            remove_source_col (bool): If True, deletes the original source column after
                extraction. Defaults to False.
            explode_rows (bool): If True, and an index list is provided, expands the
                dataframe so each extracted element gets its own row. With no target
                columns it explodes `source_col` itself. Defaults to False.
            cartesian_explode (bool): If True and multiple target columns are exploded,
                performs a sequential explode resulting in a cartesian product. Defaults to False.
            **target_cols_and_indices: Keyword arguments where the key is the new
                column name and the value is the index (int), the sentinel `None` or
                `'all'`, or a list of indices (list) to extract from the source list.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with the extracted columns; the
            input is not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Example:
        ```
            Initial Data:
                'data_list': [['A', 'B', 'C'], ['X', 'Y']]

            Operation:
                split_list_objects('data_list', first_val=0, second_val=1)

            Result:
                'data_list': [['A', 'B', 'C'], ['X', 'Y']]
                'first_val': ['A', 'X']
                'second_val': ['B', 'Y']

            Usage:
                # Extract index 0 and 1 into 2 new columns 'lat' and 'long'
                df.split_list_objects("coordinates", remove_source_col=True, lat=[0], long=[1])

                # Extract and explode in parallel
                df.split_list_objects("skills", explode_rows=True, tech=[0, 1], soft=[2, 3])

                # Extract and explode generating all combinations (Cartesian Product)
                df.split_list_objects("attributes", explode_rows=True, cartesian_explode=True, colors=[0, 1], sizes=[2, 3])
        ```
        """
        result = _columns.split_list_objects(
            self,
            source_col,
            remove_source_col = remove_source_col,
            explode_rows = explode_rows,
            cartesian_explode = cartesian_explode,
            **target_cols_and_indices
        )
        return self._finish(result, inplace)


    @_shares_doc(_translate.impute_by_language)
    def impute_by_language(
            self,
            reference_col: str,
            *target_cols,
            target_lang: str = 'en',
            inplace: bool = False
    ) -> Self | None:
        """
        Impute missing or inconsistent values in target columns based on a reference column
        and a preferred language.

        Notes:
            - **Dependencies**: This method requires the `langdetect` library.
                It will raise an ImportError if not installed.
            - **Resolution Hierarchy**: The method determines the correct translation using a 3-pass fallback strategy:
                1. Exact Match: Checks if the target value matches the reference column (ignoring hyphens and case).
                2. AI Detection: Uses `langdetect` to verify if the text matches the `target_lang`.
                3. Auto-Generation: If no valid translation is found, it generates a fallback name by title-casing the reference column.
            - **Deterministic Output**:
                The `langdetect` seed is fixed to 0 to ensure consistent results across multiple runs.
            - The standalone function never modifies `df`. A missing `reference_col` or a
                target column that is not present in `df` is skipped, and a frame
                with no valid target column is returned unchanged.

        Args:
            reference_col (str): The column used as a key (e.g., 'category_slug').
            *target_cols: One or more columns to be updated/imputed (e.g., 'category_name').
                Names that do not exist in `df` are skipped.
            target_lang (str): The ISO 639-1 language code to prefer. Defaults to 'en'.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with imputed columns; the input
            is not modified. With `inplace=True`, the receiver is mutated in place and None
            is returned.

        Raises:
            ImportError: If the optional `langdetect` dependency is not
                installed.

        Example:
        ```
            Initial Data:
                'slug': ['red-apple', 'red-apple', 'green-pear']
                'name': [NaN,         'Red Apple', 'Pear (FR)']

            Operation:
                df.impute_by_language('slug', 'name', target_lang='en')

            Result:
                'name': ['Red Apple', 'Red Apple', 'Green Pear']

            Usage:
                df.impute_by_language("city_id", "city_name", target_lang="ar")
        ```
        """
        result = _translate.impute_by_language(self, reference_col, *target_cols, target_lang = target_lang)
        return self._finish(result, inplace)


    @_shares_doc(_translate.translate_conditional_column)
    def translate_conditional_column(
        self,
        partition_col: str,
        detect_col: str,
        target_col: str,
        target_lang: str = 'en',
        sample_size: int = 10,
        number_of_samples: int = 3,
        threshold: float = 0.5,
        save_every: int = 1000,
        inplace: bool = False,
        random_state: int | np.random.Generator | np.random.RandomState | None = 0,
        provider: Translator | None = None,
    ) -> Self | None:
        """
        Conditionally translate values in a target column based on language detection of a sample.

        This method groups data by `partition_col`, samples text from `detect_col` to determine
        if the language matches `target_lang`. If the percentage of matches is below the
        `threshold`, the unique values in `target_col` for that partition are translated.
        Results are cached to minimize API calls.

        A partition is skipped when it has no detectable text, and its rows keep
        their original values. A translated value is Title-Cased, and a value
        that came back empty or as an error string is left untranslated and
        uncached. The standalone function never modifies `df`; when any of the three
        required columns is missing an unchanged copy is returned.

        Args:
            partition_col (str): The column used to group or partition the data (e.g., 'category' or 'group_id').
            detect_col (str): The column used to sample text for language detection.
            target_col (str): The column containing the values that need translation.
            target_lang (str): The ISO language code to check for and translate into. Defaults to 'en'.
            sample_size (int): Number of rows to sample from each partition for detection. Defaults to 10.
            number_of_samples (int): Number of independent language-detection
                samples to run per partition. Defaults to 3.
            threshold (float): The required ratio (0.0 to 1.0) of `target_lang` matches to skip translation.
                Defaults to 0.5.
            save_every (int): Cache checkpoint frequency while translating.
                Defaults to 1000.
            random_state (int | numpy.random.Generator | numpy.random.RandomState | None):
                Seed or generator for partition sampling. One generator is drawn
                from for every sample, so repeated samples differ while repeated
                calls with the same seed are reproducible. Pass None for
                unseeded sampling. Defaults to 0.
            provider (Translator | None): Translation provider. Defaults to
                Google Translate through `deep-translator`.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with translated values; the
            input is not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Raises:
            ValueError: If `threshold` is not between 0.0 and 1.0.
            ValueError: If `sample_size`, `number_of_samples`, or `save_every`
                is not a positive integer.
            ImportError: If the optional `langdetect` dependency is not
                installed. The default provider also requires `deep-translator`,
                imported lazily when a translation is actually needed.

        Example:
        ```
            Scenario:
                Translate 'category_name' only for groups where the 'description'
                is not primarily in English.

            Usage:
                df.translate_conditional_column(
                    partition_col="group_id",
                    detect_col="description",
                    target_col="category_name",
                    target_lang="en",
                    threshold=0.7
                )
        ```
        """
        result = _translate.translate_conditional_column(
            self,
            partition_col,
            detect_col,
            target_col,
            target_lang = target_lang,
            sample_size = sample_size,
            number_of_samples = number_of_samples,
            threshold = threshold,
            save_every = save_every,
            random_state = random_state,
            provider = provider,
            cache_manager = self.cache_manager,
        )
        return self._finish(result, inplace)


    @_shares_doc(_translate.translate_categorical_column)
    def translate_categorical_column(
            self,
            target_col: str,
            target_lang: str = 'en',
            save_every: int = 1000,
            inplace: bool = False,
            provider: Translator | None = None,
    ) -> Self | None:
        """
        Translate all unique categories in a specific column using an automated translator.

        This method optimizes performance and API usage by translating only unique
        values (categories) and utilizing a caching mechanism to avoid re-translating
        previously processed strings.

        Notes:
            Cache keys are stored as strings so non-string categories remain
            reusable after the cache is saved and loaded again.
            The standalone function never modifies `df`. A missing `target_col` or a column
            with no non-null values returns an unchanged copy, and a translation
            that came back empty is left untranslated and uncached.

        Args:
            target_col (str): The name of the column containing categorical text to translate.
            target_lang (str): The ISO language code for the target language.
                Defaults to 'en'.
            save_every (int): Cache checkpoint frequency while translating.
                Defaults to 1000.
            provider (Translator | None): Translation provider. Defaults to
                Google Translate through `deep-translator`.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with translated values; the
            input is not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Raises:
            ValueError: If `save_every` is not a positive integer.
            ImportError: If the default provider's optional `deep-translator`
                dependency is not installed and no `provider` is given.

        Example:
        ```
            Initial Column:
                'status': ["مكتمل", "قيد الانتظار", "مكتمل"]

            Operation:
                translate_categorical_column(target_col='status', target_lang='en')

            Result:
                'status': ["Completed", "Pending", "Completed"]

            Usage:
                df.translate_categorical_column("product_category", target_lang="fr")
        ```
        """
        result = _translate.translate_categorical_column(
            self,
            target_col,
            target_lang = target_lang,
            save_every = save_every,
            provider = provider,
            cache_manager = self.cache_manager,
        )
        return self._finish(result, inplace)


    @_shares_doc(_text.truncate_after_substring)
    def truncate_after_substring(self, regex: bool = True, inplace: bool = False, **target_cols_and_substrings) -> Self | None:
        """
        Remove specific substrings and everything following them from target columns.

        Each named column is processed independently. The first occurrence of each
        substring cuts the text, and the remaining text is stripped of surrounding
        whitespace. Column names that are absent from `df` are ignored, and with no
        keyword arguments an unchanged copy of `df` is returned.

        Args:
            regex (bool): Passed to `pandas.Series.str.split`. When True,
                substring values are interpreted as regular expressions.
                Defaults to True.
            **target_cols_and_substrings: Keyword arguments where the key is the column
                name and the value is a string or a list of strings at which to cut off the text.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with truncated columns; the
            input is not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Example:
        ```
            Initial Data:
                'title': ['Software Engineer - Remote', 'Data Analyst (Junior)']
                'company': ['Tech Corp, LLC', 'Data Inc.']

            Operation:
                df.truncate_after_substring(
                    title=['-', '('],
                    company=','
                )

            Result:
                'title': ['Software Engineer', 'Data Analyst']
                'company': ['Tech Corp', 'Data Inc']
        ```
        """
        return self._finish(_text.truncate_after_substring(self, regex = regex, **target_cols_and_substrings), inplace)


    @_shares_doc(_geocode.fill_missing_coordinates)
    def fill_missing_coordinates(
        self,
        *fallback_cols: str,
        lat_col: str,
        long_col: str,
        save_every: int = 1000,
        user_agent: str = "data_cleaning_core_geocoder",
        retry_not_found: bool = False,
        inplace: bool = False,
        provider: Geocoder | None = None,
    ) -> Self | None:
        """
        Fill missing latitude and longitude values by geocoding fallback location
        text.

        Notes:
            The method builds a location query from the supplied fallback
            columns, caches geocoding results, and progressively drops the
            leftmost (most specific) part of a failed query, e.g.
            `"street, city, country"` -> `"city, country"` -> `"country"`.
            Existing valid coordinates are preserved and only missing
            coordinate fields are updated.

            Queries that cannot be resolved are cached as `null`, so later runs
            do not re-query them. Network or service errors are not cached.

            The query is built from the fallback columns in order, joined with
            `", "`, skipping null, empty, `"nan"`/`"none"`, and purely numeric
            values. A failed query drops its leftmost comma-separated part and is
            retried until it resolves or runs out of parts.

            The standalone function never modifies `df`. A missing coordinate column or no
            usable fallback column returns an unchanged copy; an internal helper
            query column is always removed before returning.

        Args:
            *fallback_cols: Ordered columns used to build the geocoding query.
                Names that do not exist in `df` are ignored.
            lat_col (str): Latitude column name.
            long_col (str): Longitude column name.
            save_every (int): Cache checkpoint frequency while geocoding.
                Defaults to 1000.
            user_agent (str): User agent sent to Nominatim by the default
                provider. Its usage policy asks for one that identifies your
                application. Defaults to `"data_cleaning_core_geocoder"`.
            retry_not_found (bool): If True, re-query locations previously
                cached as not found. Defaults to False.
            provider (Geocoder | None): Geocoding provider. Defaults to
                Nominatim through `geopy`, rate-limited to one request per
                second.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with completed
            coordinates; the input is not modified and existing valid coordinates
            are preserved. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Raises:
            ValueError: If `save_every` is not a positive integer.
            ImportError: If the default provider's optional `geopy` dependency
                is not installed and no `provider` is given.
        """
        result = _geocode.fill_missing_coordinates(
            self,
            *fallback_cols,
            lat_col = lat_col,
            long_col = long_col,
            save_every = save_every,
            user_agent = user_agent,
            retry_not_found = retry_not_found,
            provider = provider,
            cache_manager = self.cache_manager,
        )
        return self._finish(result, inplace)


    @_shares_doc(_currency.convert_to_usd)
    def convert_to_usd(
        self,
        *target_cols,
        country_col: str,
        year_col: str,
        new_cols: bool = True,
        round_decimals: int | None = None,
        inplace: bool = False,
        provider: RateSource | None = None,
    ) -> Self | None:
        """
        Convert numeric salary-like columns into USD using country currency codes
        and year-based exchange rates.

        Notes:
            Currency codes and exchange rates are cached to reduce repeated
            lookups. For non-USD currencies, the yearly mean rate of the
            requested year is used, falling back to earlier years (down to the
            earliest year in the data) when a year has no data. Uncached years
            are downloaded once per currency across the whole range needed.
            Unknown countries and past years without data are cached as misses;
            network errors are not cached.

            A row whose country is already USD is divided by 1.0 without any
            lookup. A row whose currency is unknown, or whose year has no rate
            anywhere in the lookback range, gets `NaN` rather than its original
            value. Conversion divides the value by the rate, so the rate is the
            amount of local currency per one USD.

            The standalone function never modifies `df`. Missing `country_col` or `year_col`,
            no valid target column, or an empty frame returns an unchanged copy
            (a warning is logged for the first two).

        Args:
            *target_cols: Numeric columns to convert. Names that do not exist in
                `df` are ignored.
            country_col (str): Column containing the country name used to infer
                the local currency.
            year_col (str): Column containing the reference year for historical
                exchange rates.
            new_cols (bool): If True, create new `<column>_usd` columns.
                Otherwise overwrite the original columns. Defaults to True.
            round_decimals (int | None): Optional number of decimal places to
                round the converted values to. Defaults to None.
            provider (RateSource | None): Exchange-rate provider. Defaults to
                Yahoo Finance through `yfinance`.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with converted values; the input
            is not modified. With `inplace=True`, the receiver is mutated in place and None
            is returned.

        Raises:
            ImportError: If the optional `pycountry` or `Babel` dependency is not
                installed, or if the default provider's optional `yfinance`
                dependency is not installed and no `provider` is given.
        """
        result = _currency.convert_to_usd(
            self,
            *target_cols,
            country_col = country_col,
            year_col = year_col,
            new_cols = new_cols,
            round_decimals = round_decimals,
            provider = provider,
            cache_manager = self.cache_manager,
        )
        return self._finish(result, inplace)


    @_shares_doc(_stats.handle_outliers)
    def handle_outliers(
        self,
        *target_cols,
        hierarchy_cols: list,
        min_samples: int = 5,
        inplace: bool = False,
        get_hierarchical_stats: bool = False
    ) -> Self | tuple[Self, Self] | None:
        """
        Replace outlier values with missing values using hierarchical IQR rules.

        Notes:
            - The method starts with the full grouping hierarchy and progressively
                relaxes it by removing the last grouping column at each pass. Within
                every valid group, values outside the 1.5 IQR bounds are converted
                to `NaN`. Values replaced at one level are excluded from the
                quartiles of later levels.
            - A row is judged only at the most specific level where its group has
                at least `min_samples` non-null values. Groups that are too small
                fall through to the next coarser level.
            - Target columns that are not present in `df` are ignored.
            - `min_samples` is not validated; it is compared against group sizes
                as given. When `hierarchy_cols` is empty a warning is logged and
                the values are returned unchanged.
            - The standalone function never modifies `df`.

        Args:
            *target_cols: Numeric columns to evaluate for outliers. Names that do
                not exist in `df` are ignored.
            hierarchy_cols (list): Ordered grouping columns used to define peer
                groups. A single string is treated as a one-item list.
            min_samples (int): Minimum number of non-null rows required for a group
                to be considered valid. Defaults to 5.
            get_hierarchical_stats (bool): If True, also return the hierarchical
                statistics computed from the original data before outliers are
                replaced. The default `median` strategy is used. Defaults to
                False.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new cleaned dataframe, or
            `(cleaned_dataframe, statistics)` when `get_hierarchical_stats=True`;
            the input is not modified. With `inplace=True`, the receiver is mutated
            in place and the statistics dataframe is returned when
            `get_hierarchical_stats=True`, otherwise None.
        """
        outcome = _stats.handle_outliers(
            self,
            *target_cols,
            hierarchy_cols = hierarchy_cols,
            min_samples = min_samples,
            get_hierarchical_stats = get_hierarchical_stats,
        )
        return self._finish_with_stats(outcome, inplace, get_hierarchical_stats)


    @_shares_doc(_stats.drop_outliers)
    def drop_outliers(
        self,
        *target_cols,
        hierarchy_cols: list,
        min_samples: int = 5,
        inplace: bool = False,
        get_hierarchical_stats: bool = False
    ) -> Self | tuple[Self, Self] | None:
        """
        Remove rows that contain outlier values based on hierarchical IQR rules.

        Notes:
            - This method shares the same grouping logic as `handle_outliers`, but
                instead of replacing detected outliers with `NaN`, it drops the
                affected rows after scanning all requested target columns. Rows are
                dropped by position, so a duplicated index label never removes its
                twin row.
            - Outliers are accumulated across every target column, so a row is
                dropped when any requested column flags it.
            - Target columns that are not present in `df` are ignored.
            - `min_samples` is not validated; it is compared against group sizes
                as given. When `hierarchy_cols` is empty a warning is logged and
                no rows are dropped.
            - The standalone function never modifies `df`.

        Args:
            *target_cols: Numeric columns to inspect for outliers. Names that do
                not exist in `df` are ignored.
            hierarchy_cols (list): Ordered grouping columns used to define peer
                groups. A single string is treated as a one-item list.
            min_samples (int): Minimum number of non-null rows required for a group
                to be considered valid. Defaults to 5.
            get_hierarchical_stats (bool): If True, also return the hierarchical
                statistics computed from the original data before outlier rows are
                dropped. The default `median` strategy is used. Defaults to
                False.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new filtered dataframe, or
            `(filtered_dataframe, statistics)` when `get_hierarchical_stats=True`;
            the input is not modified. With `inplace=True`, the receiver is mutated
            in place and the statistics dataframe is returned when
            `get_hierarchical_stats=True`, otherwise None.
        """
        outcome = _stats.drop_outliers(
            self,
            *target_cols,
            hierarchy_cols = hierarchy_cols,
            min_samples = min_samples,
            get_hierarchical_stats = get_hierarchical_stats,
        )
        return self._finish_with_stats(outcome, inplace, get_hierarchical_stats)


    @_shares_doc(_stats.fill_missing)
    def fill_missing(
        self,
        *target_cols,
        strategy: str = 'median',
        hierarchy_cols: list | str | None = None,
        min_samples: int = 1,
        fallback_global: bool = False,
        inplace: bool = False,
        get_hierarchical_stats: bool = False
    ) -> Self | tuple[Self, Self] | None:
        """
        Impute missing values by progressively relaxing a grouping hierarchy.

        Notes:
            - Supported strategies are `median`, `mean`, and `mode`. The method
                attempts imputation using the full hierarchy first, then removes the
                last grouping column one level at a time until no grouping columns
                remain or the column is fully imputed. The `mod` alias is
                normalized to `mode`.
            - Unfilled values remain `NaN` by default unless `fallback_global=True`
                is set, in which case any remaining `NaN` values after exhausting the
                hierarchy are filled using the column-wide statistic.
            - A single string `hierarchy_cols` is treated as a one-item list.
                Hierarchy columns that are not present in `df` are ignored.
            - Target columns that are not present in `df` are ignored; when none are
                valid a warning is logged and an unchanged copy is returned.
            - The standalone function never modifies `df`. Statistics always come from `df`
                itself, so this method does not prevent leakage from a test set.

        Args:
            *target_cols: Columns whose missing values should be filled. Names that
                do not exist in `df` are ignored.
            strategy (str): Aggregation strategy to use. Supported values are
                `median`, `mean`, `mode`, and `mod`. The value is lowercased before
                validation. Defaults to `median`.
            hierarchy_cols (list | str, optional): Grouping columns that define
                the imputation hierarchy. A single string is treated as a
                one-item list, and missing columns are ignored. Defaults to None,
                which skips the hierarchy and only imputes when
                `fallback_global=True`.
            min_samples (int): Minimum number of non-null observations required
                for a group to supply an imputation statistic. Groups with fewer
                observations fall through to coarser hierarchy levels. Defaults
                to 1.
            fallback_global (bool): If True, fill remaining missing values using
                the column-wide statistic after the hierarchy is exhausted, or
                perform column-wide imputation when `hierarchy_cols=None`.
                Defaults to False.
            get_hierarchical_stats (bool): If True, also return the existing
                hierarchical statistics computed from the original data before
                imputation. The requested `strategy` is used. Defaults to
                False.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new imputed dataframe, or
            `(imputed_dataframe, statistics)` when `get_hierarchical_stats=True`;
            the input is not modified. With `inplace=True`, the receiver is mutated
            in place and the statistics dataframe is returned when
            `get_hierarchical_stats=True`, otherwise None.

        Raises:
            ValueError: If `strategy` is not one of the supported values, or if
                `min_samples` is not an integer greater than or equal to 1
                (booleans are rejected).

        Example:
        ```
            df.fill_missing(
                "salary_min",
                "salary_max",
                strategy="median",
                hierarchy_cols=["country", "title", "company_name"]
            )
        ```
        """
        outcome = _stats.fill_missing(
            self,
            *target_cols,
            strategy = strategy,
            hierarchy_cols = hierarchy_cols,
            min_samples = min_samples,
            fallback_global = fallback_global,
            get_hierarchical_stats = get_hierarchical_stats,
        )
        return self._finish_with_stats(outcome, inplace, get_hierarchical_stats)



    @_shares_doc(_stats.fill_missing_from)
    def fill_missing_from(
        self,
        dataset: Any,
        *target_cols: Any,
        match_cols: dict[str, str] | None = None,
        targets: Any = None,
        strategy: str = 'median',
        hierarchy_cols: list | str | None = None,
        min_samples: int = 1,
        fallback_global: bool = False,
        inplace: bool = False,
        get_hierarchical_stats: bool = False,
    ) -> Self | tuple[Self, Self] | None:
        """
        Impute missing values using statistics calculated from a reference dataset.

        Statistics are computed exclusively from `dataset` to avoid statistical
        leakage from `df`, making this suitable for train/test workflows. The
        reference dataset is never modified, and the target DataFrame's index,
        row order, and un-imputed values are preserved.

        Notes:
            - Supported strategies are `median`, `mean`, and `mode` (with alias `mod`).
                When `hierarchy_cols` are specified, imputation evaluates the most
                specific grouping level first, then progressively drops grouping columns
                until the column is fully imputed or the hierarchy is exhausted.
            - Groups in `dataset` with fewer than `min_samples` non-null observations
                do not supply an imputation statistic, falling through to coarser levels.
                If a group exists in `df` but has no matching rows (or insufficient samples)
                in `dataset`, it falls through to coarser levels.
            - Unfilled values remain `NaN` by default unless `fallback_global=True` is
                specified, in which case any remaining `NaN` values after exhausting the
                hierarchy are filled using the reference dataset's column-wide statistic.
                When `hierarchy_cols=None` and `fallback_global=True`, plain column-wide
                imputation is performed using reference statistics.
            - `target_cols` accepts individual names and nested lists/tuples/sets,
                which are flattened. Duplicates are removed in first-seen order. The
                `targets` keyword accepts a single name or an iterable and is combined
                with `*target_cols`.
            - `match_cols` maps target column names to reference column names and
                applies to both target and hierarchy columns. When omitted, identical
                column names are used. When `get_hierarchical_stats=True`, the
                returned statistics report target and hierarchy column names in the
                target `df` spelling.
            - Target columns that are not present in `df` are ignored; when none are
                valid a warning is logged and an unchanged copy is returned. Hierarchy
                columns must exist in both `df` and `dataset`.
            - The standalone function never modifies `df`, and `dataset` is never modified.

        Args:
            dataset (pd.DataFrame | BaseData): Reference dataset used to compute
                imputation statistics. Must not be empty and is never modified.
            *target_cols: Columns in `df` whose missing values should be filled.
                May also be supplied via the `targets` keyword argument.
            match_cols (dict[str, str] | None, optional): Mapping of column names
                from target `df` to reference `dataset` in the format
                `{target_col: reference_col}`. Applied to both target columns
                and hierarchy columns. When omitted, identical column names are used.
                Defaults to None.
            targets (Any, optional): Alternative way to specify target columns
                (e.g., a single column name or iterable of column names). Defaults to None.
            strategy (str): Aggregation strategy to use. Supported values are
                `median`, `mean`, `mode`, and `mod`. The value is lowercased before
                validation. Defaults to `median`.
            hierarchy_cols (list | str, optional): Grouping columns that define
                the imputation hierarchy in `df`. A single string is treated as a
                one-item list.
            min_samples (int): Minimum number of non-null observations required
                in `dataset` for a reference group to supply an imputation
                statistic. Defaults to 1.
            fallback_global (bool): If True, fill remaining missing values using
                the column-wide reference statistic after the hierarchy is
                exhausted, or perform column-wide imputation when `hierarchy_cols=None`.
                Defaults to False.
            get_hierarchical_stats (bool): If True, also return the hierarchical
                statistics computed from `dataset`. Defaults to False.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new imputed dataframe, or
            `(imputed_dataframe, statistics)` when `get_hierarchical_stats=True`;
            neither `df` nor `dataset` is modified. With `inplace=True`, the
            receiver is mutated in place, `dataset` is still not modified, and the
            statistics dataframe is returned when `get_hierarchical_stats=True`,
            otherwise None.

        Raises:
            ValueError: If `dataset` is missing or empty, contains duplicate column
                names, if `df` contains duplicate column names, if specified
                columns are missing from either dataset, if target and hierarchy
                columns overlap, or if `min_samples < 1`.
            TypeError: If `dataset` is not a DataFrame, if `match_cols` is not a
                dict or contains non-string keys/values, or if columns have
                incompatible data types for numeric strategies.

        Examples:
        ```
            # Impute test data using median statistics from train data
            test_imputed = test_df.bynat.fill_missing_from(
                train_df,
                "salary",
                strategy="median",
                hierarchy_cols=["country", "title"],
                fallback_global=True,
            )

            # Impute when schemas use different column names
            test_imputed = test_df.bynat.fill_missing_from(
                train_df,
                "salary",
                match_cols={"salary": "wage", "country": "nation"},
                strategy="mean",
                hierarchy_cols=["country"],
            )
        ```
        """
        outcome = _stats.fill_missing_from(
            self,
            dataset,
            *target_cols,
            match_cols = match_cols,
            targets = targets,
            strategy = strategy,
            hierarchy_cols = hierarchy_cols,
            min_samples = min_samples,
            fallback_global = fallback_global,
            get_hierarchical_stats = get_hierarchical_stats,
        )
        return self._finish_with_stats(outcome, inplace, get_hierarchical_stats)

    @_shares_doc(_stats.get_hierarchical_stats)
    def get_hierarchical_stats(
        self,
        *target_cols,
        strategy: str | Iterable[str] = 'median',
        hierarchy_cols: list | str | None = None,
        output_type = None,
    ) -> Any:
        """
        Extract statistics for each progressively relaxed hierarchy level.

        The full valid hierarchy is aggregated first, then its last grouping
        column is removed for each subsequent level. No global level is added,
        matching :meth:`fill_missing`. ``group_key`` is always a tuple,
        including for one-column hierarchies. The source object is not modified.

        ``strategy`` accepts one string or an iterable of strings. Supported
        values are ``median``, ``mean``, ``mode``, and the ``mod`` alias for
        ``mode``. Requested strategies are normalized to canonical values,
        deduplicated in first-seen order, and emitted in strategy-then-target-
        then-hierarchy order. Every emitted row has one unique logical key:
        ``(hierarchy_level, hierarchy_columns, group_key, target_column,
        strategy)``.

        By default, ``output_type`` is ``None`` and the result uses the same
        ``BaseData``-family type as ``df`` when its constructor signature can
        bind ``data=``. A signature-incompatible default subclass falls back to
        a plain ``pandas.DataFrame``. If the signature accepts ``data=`` but the
        constructor raises, that original constructor exception propagates.
        Explicit output types propagate construction errors directly. Supported
        explicit types are ``pandas.DataFrame``, ``dict``, and BaseData-family
        classes. Dict conversion derives keys from the actual dataframe columns.

        Missing target values are ignored by ``mean`` and ``median``; groups
        containing only null targets still produce a row with a null statistic.
        ``mode`` excludes null target values and performs one grouped count per
        target and hierarchy level, avoiding an N*T melt intermediate at the
        cost of additional groupby operations. Groups without a non-null target
        have no mode row, and ties use deterministic group-count ordering.
        Null hierarchy values remain valid grouping keys.

        Args:
            *target_cols: Target columns from which statistics are extracted.
                Columns that are not present are ignored; if none are valid,
                an empty result is returned.
            strategy (str | iterable[str]): One strategy or an ordered iterable
                of strategies. ``mod`` is normalized to ``mode`` and repeated
                canonical values are emitted once. Defaults to ``median``.
            hierarchy_cols (list | str, optional): Grouping columns defining
                the hierarchy. A single string is normalized to a one-item
                list, and missing columns are ignored. Duplicate valid names
                are removed while preserving their first-seen order. Each
                successive level removes the last remaining grouping column.
                Target columns may not overlap the valid hierarchy columns.
            output_type (type | None, optional): Result type. ``None`` uses
                the type of ``df`` when supported, with a plain DataFrame
                fallback. ``pandas.DataFrame``, ``dict``, and BaseData-family
                classes are supported. Defaults to ``None``.

        Returns:
            pandas.DataFrame | BaseData | dict: Statistics in the requested
            output schema. Empty and invalid-result cases use the requested
            output type whenever possible.

        Raises:
            TypeError: If `strategy` is neither a string nor an iterable of
                strings, or if `output_type` is not a supported type.
            ValueError: If a requested strategy is not supported, if a strategy
                iterable is empty, or if a target column overlaps a valid
                hierarchy column. Construction errors from an explicitly
                requested `output_type` propagate unchanged.

        Examples:
        ```
            default_stats = df.get_hierarchical_stats(
                "salary_min",
                hierarchy_cols=["country", "title", "company_name"],
            )
            dataframe_stats = df.get_hierarchical_stats(
                "salary_min",
                strategy="mean",
                hierarchy_cols="country",
                output_type=pd.DataFrame,
            )
            dict_stats = df.get_hierarchical_stats(
                "salary_min",
                hierarchy_cols="country",
                output_type=dict,
            )
        ```
        """
        return _stats.get_hierarchical_stats(
            self,
            *target_cols,
            strategy = strategy,
            hierarchy_cols = hierarchy_cols,
            output_type = output_type,
        )


    def profile(
        self,
        *columns: Any,
        output_type = None,
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
            summary_frame = profile(
                self,
                *columns,
                output_type=pd.DataFrame,
            )
            return output_type(data=summary_frame)

        return profile(
            self,
            *columns,
            output_type=output_type,
        )


    @_shares_doc(_text.categorize_by_reference)
    def categorize_by_reference(
        self,
        *source_cols: str,
        target_col: str,
        reference: dict,
        default_category: str = 'Other',
        inplace: bool = False
    ) -> Self | None:
        """
        Categorize text data into broader groups based on a reference lexicon dictionary.

        This method scans one or more source text columns for specific keywords defined in a
        lexicon dictionary. If a match is found, the dictionary's key (the category)
        is assigned to a new target column.

        Notes:
            - Matching is case-insensitive and restricted to whole words, so
              'React' does not trigger on 'Reactor' and 'score' does not trigger
              on 'under_score'.
            - The implementation builds an Aho-Corasick automaton and evaluates
              each unique combined text once, then maps results back to all rows.
            - Longer keywords take precedence over shorter ones (e.g., "Data Analyst"
              matches before "Data"). On an equal-length tie the category listed
              later in `reference` wins.
            - Empty keyword lists and blank keyword values are ignored safely.
            - A keyword value that is not a list is treated as a one-item list.
            - A missing `reference` column match, an empty `reference`, or a
              `reference` that is not a dictionary assigns `default_category` to
              every row.
            - Source columns that are absent from `df` are ignored. When none of
              them are present, an unchanged copy of `df` is returned.
            - The standalone function never modifies `df`.

        Args:
            *source_cols (str): Source columns containing the raw text to search.
                Names that do not exist in `df` are ignored.
            target_col (str): The new or existing column where categories will be saved.
            reference (dict): A dictionary where keys are category names and values
                are lists of keywords to search for. A non-list value is treated as
                a one-item list, and a non-dictionary value is treated as empty.
            default_category (str): The fallback value if no keywords are matched.
                Defaults to 'Other'.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with the category column; the
            input is not modified. With `inplace=True`, the receiver is mutated in place and
            None is returned.

        Raises:
            ImportError: If the optional `pyahocorasick` dependency is not
                installed. The dependency is required for this method; there is no
                regex fallback.

        Example:
        ```
            reference = {
                "Data": ["data analyst", "business intelligence"],
                "Software": ["python developer", "backend engineer"]
            }

            jobs.categorize_by_reference(
                "title",
                "description",
                target_col = "field_label",
                reference = reference
            )
        ```
        """
        result = _text.categorize_by_reference(
            self,
            *source_cols,
            target_col = target_col,
            reference = reference,
            default_category = default_category,
        )
        return self._finish(result, inplace)


    @_shares_doc(_nlp.extract_entities_nlp)
    def extract_entities_nlp(
        self,
        *source_cols,
        lexicon_source: str | os.PathLike | dict,
        spacy_model: str = "en_core_web_sm",
        exclude_pos: set | list | tuple | str | None = None,
        disable: Iterable[str] | str | None = ('parser', 'ner'),
        save_every: int = 1000,
        inplace: bool = False,
        noisy_terms: set | None = None,
        **target_cols_and_json_keys
    ) -> Self | None:
        """
        Extract entities from free text by matching against a cached lexicon with
        spaCy tokenization and lemmatization.

        Notes:
            Terms are loaded from a JSON file or dictionary, grouped by target
            output column, and matched across the combined source text. Results
            are cached per unique text snippet so repeat runs avoid reprocessing
            the same content. Cache buckets include the target column, model
            identifier, and normalized disabled components, so configurations do
            not reuse one another's results.

            The `disable` parameter controls which spaCy pipeline components are
            disabled during both lexicon and text processing. Its default is
            `("parser", "ner")`. The components available for disabling depend
            on the selected spaCy model.

            The following components cannot be disabled because they may be
            required to provide token annotations or representations used by
            lemmatization and entity matching:
                - `tok2vec`
                - `tagger`
                - `attribute_ruler`
                - `lemmatizer`
                - `morphologizer`

            spaCy pipeline components may depend on one another. For example,
            some lemmatizers require POS annotations provided by `tagger` and
            `attribute_ruler`, or by `morphologizer`, depending on the model.
            Disabling a component may also affect other pipeline outputs.

            Components not present in the selected model are not disabled.
            Requesting an unknown component logs a warning listing the unknown
            names and the components available in the loaded pipeline; processing
            continues.

        Args:
            *source_cols: Text columns whose combined content will be searched.
            lexicon_source (str | os.PathLike | dict): Path to a lexicon JSON
                file or a preloaded dictionary with equivalent structure.
            spacy_model (str): Installed spaCy model name or model path.
                Defaults to `"en_core_web_sm"`.
            exclude_pos (set | list | tuple | str | None): Optional POS tag or
                tags to ignore for single-token matches, for example
                `{"VERB", "ADV"}`. Defaults to None.
            disable (Iterable[str] | str | None): spaCy pipeline components to
                disable during both lexicon and text processing. Accepts None,
                one component name, or an iterable of component names.
                Defaults to `("parser", "ner")`. The components `tok2vec`,
                `tagger`, `attribute_ruler`, `lemmatizer`, and `morphologizer`
                cannot be disabled. Unknown component names generate a warning
                and are otherwise ignored.
            save_every (int): Cache checkpoint frequency during NLP processing.
                Defaults to 1000.
            noisy_terms (set | None): Terms that should be ignored even if they
                are matched. Terms are compared case-insensitively. Defaults
                to None.
            **target_cols_and_json_keys: Mapping where each key is an output
                column name and each value is a lexicon key or list of keys to
                collect terms from.
            inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
                standalone function has no such parameter and always returns a new
                frame. When True, the receiver is mutated in place. Defaults to
                False.

        Returns:
            With `inplace=False` (default), a new dataframe with extracted entity-list
            columns; the input is not modified. With `inplace=True`, the receiver is mutated
            in place and None is returned.

        Raises:
            ValueError: If `disable` contains a required spaCy component, a
                component name is empty, `save_every` is not a positive integer,
                no target column/JSON key keyword argument is supplied, or no
                valid terms are extracted from the requested lexicon keys. A
                non-string or blank `spacy_model` also raises `ValueError`.
            TypeError: If `disable` is not None, a string, or an iterable of
                strings, or if the misspelled `noisey_terms` keyword is used.
            ImportError: If the optional `spacy` dependency is not installed.
            OSError: If the spaCy model cannot be loaded.

        Example:
        ```
            search_dataframe.extract_entities_nlp(
                "title",
                "description",
                lexicon_source="skills_lexicon.json",
                basic_skills=["skills", "technologies"]
            )
        ```
        """
        if "noisey_terms" in target_cols_and_json_keys:
            raise TypeError(
                "extract_entities_nlp() got an unexpected keyword argument "
                "'noisey_terms'; did you mean 'noisy_terms'?"
            )
        result = _nlp.extract_entities_nlp(
            self,
            *source_cols,
            lexicon_source = lexicon_source,
            spacy_model = spacy_model,
            exclude_pos = exclude_pos,
            disable = disable,
            save_every = save_every,
            noisy_terms = noisy_terms,
            cache_manager = self.cache_manager,
            **target_cols_and_json_keys
        )
        return self._finish(result, inplace)


    @_shares_doc(io.save_to_json)
    def save_to_json(
            self,
            file_path: str | os.PathLike,
            orient: str = 'records',
            append: bool = False,
            force_ascii: bool = False,
            indent: int = 4
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
        return io.save_to_json(self, file_path, orient = orient, append = append, force_ascii = force_ascii, indent = indent)


    @_shares_doc(io.save_to_sql)
    def save_to_sql(
            self,
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
            index: bool = False
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
        return io.save_to_sql(
            self,
            table_name,
            database_type,
            database_user,
            database_password,
            database_host,
            database_port,
            database_name,
            database_driver = database_driver,
            columns_types = columns_types,
            chunk_size = chunk_size,
            fast_executemany = fast_executemany,
            if_exists = if_exists,
            index = index,
        )



class JsonFile(BaseData):
    """
    Load a JSON file into a `BaseData` frame.

    The payload is flattened with `pandas.json_normalize` by
    `bynat.cleaning.io.read_json`, so nested objects become dotted column
    names.

    Args:
        data: Tabular data passed to `pandas.DataFrame`, or a path to a JSON
            file. A string or path-like `data` that names an existing file is
            treated as `json_file_path`; one that does not exist raises
            `FileNotFoundError`.
        json_file_path (str | os.PathLike | None): Path to the JSON file.
            Ignored when `data` already holds tabular data.
        key (str | None): Optional top-level key whose value holds the
            records, for dictionary payloads. Defaults to None.
        cache_dir (str | os.PathLike | None): Directory for the cache
            manager. Defaults to None, which uses `BYNAT_CACHE_DIR` or the
            default directory.
        *args: Additional positional arguments forwarded to `pandas.DataFrame`.
        **kwargs: Additional keyword arguments forwarded to `pandas.DataFrame`.

    Raises:
        FileNotFoundError: If a path-like `data` or `json_file_path` does not
            exist.
        TypeError: If `key` is given for a non-dictionary payload.
        KeyError: If `key` is not in the payload.
    """

    def __init__(
        self,
        data = None,
        json_file_path: str | os.PathLike | None = None,
        key: str | None = None,
        cache_dir: str | os.PathLike | None = None,
        *args,
        **kwargs
    ) -> None:
        """
        Load the JSON payload and delegate to `BaseData`.

        Args:
            data: See the class docstring.
            json_file_path: See the class docstring.
            key: See the class docstring.
            cache_dir: See the class docstring.
            *args: Forwarded to `pandas.DataFrame`.
            **kwargs: Forwarded to `pandas.DataFrame`.

        Raises:
            FileNotFoundError: If a path-like `data` or `json_file_path` does
                not exist.
            TypeError: If `key` is given for a non-dictionary payload.
            KeyError: If `key` is not in the payload.
        """
        if data is not None and json_file_path is None:
            if isinstance(data, (str, os.PathLike)):
                path = os.fspath(data)

                if os.path.isfile(path):
                    json_file_path = path
                    data = None

                else:
                    raise FileNotFoundError(f"JSON file not found: {path}")

        if data is None and json_file_path is not None:
            data = io.read_json(json_file_path, key = key)

        super().__init__(data = data, cache_dir = cache_dir, *args, **kwargs)


class CsvFile(BaseData):
    """
    Load a CSV file into a `BaseData` frame.

    Parsing is delegated to `pandas.read_csv` through
    `bynat.cleaning.io.read_csv`, so every `pandas.read_csv` keyword is
    accepted.

    Args:
        data: Tabular data passed to `pandas.DataFrame`, or a path to a CSV
            file. A string or path-like `data` that names an existing file is
            treated as `csv_file_path`; one that does not exist raises
            `FileNotFoundError`.
        csv_file_path (str | os.PathLike | None): Path to the CSV file.
            Ignored when `data` already holds tabular data.
        cache_dir (str | os.PathLike | None): Directory for the cache
            manager. Defaults to None, which uses `BYNAT_CACHE_DIR` or the
            default directory.
        read_kwargs (dict | None): Keyword arguments forwarded to
            `pandas.read_csv`. Defaults to None (no extra options).
        *args: Additional positional arguments forwarded to `pandas.DataFrame`.
        **kwargs: Additional keyword arguments forwarded to `pandas.DataFrame`.

    Raises:
        FileNotFoundError: If a path-like `data` or `csv_file_path` does not
            exist.
    """

    def __init__(
        self,
        data = None,
        csv_file_path: str | os.PathLike | None = None,
        cache_dir: str | os.PathLike | None = None,
        read_kwargs: dict | None = None,
        *args,
        **kwargs
    ) -> None:
        """
        Load the CSV payload and delegate to `BaseData`.

        Args:
            data: See the class docstring.
            csv_file_path: See the class docstring.
            cache_dir: See the class docstring.
            read_kwargs: See the class docstring.
            *args: Forwarded to `pandas.DataFrame`.
            **kwargs: Forwarded to `pandas.DataFrame`.

        Raises:
            FileNotFoundError: If a path-like `data` or `csv_file_path` does
                not exist.
        """
        if read_kwargs is None:
            read_kwargs = {}

        if data is not None and csv_file_path is None:
            if isinstance(data, (str, os.PathLike)):
                path = os.fspath(data)

                if os.path.isfile(path):
                    csv_file_path = path
                    data = None

                else:
                    raise FileNotFoundError(f"CSV file not found: {path}")

        if data is None and csv_file_path is not None:
            data = io.read_csv(csv_file_path, **read_kwargs)

        super().__init__(data = data, cache_dir = cache_dir, *args, **kwargs)
