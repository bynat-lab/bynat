"""Reusable, application-independent DataFrame analytics helpers for categorical distributions, numerical aggregations, time-series bucketing, single-metric KPI cards, and histogram binning."""

from typing import Any

import pandas as pd

from ._insights import (
    build_bins,
    build_categorical_distribution,
    build_kpi_value,
    build_numerical_aggregation,
    build_time_series,
)

__all__ = ["Analyzer"]


class Analyzer:
    """
    Provide reusable analytics helpers for dashboard and API responses.

    Notes:
        The analyzer holds a defensive copy of the source data, so its methods
        never mutate the DataFrame passed to the constructor. Every method
        returns a plain, JSON-serializable response dictionary.

        Methods in this class support a common workflow:
        1. Apply filters.
        2. Compute optional rule-based transformations.
        3. Return serializable data structures for frontend consumption.

        Missing or empty inputs produce empty payloads (`{"data": []}`, or
        `{"data": None, "title": ...}` for `get_kpi_value`) rather than
        raising. Invalid filters, unsafe expressions, missing columns, and
        failing aggregations are logged as warnings and skipped. An empty
        frame after filtering returns an empty payload silently.
    """

    def __init__(self, dataframe: pd.DataFrame) -> None:
        """
        Initialize the analyzer with a defensive copy of source data.

        Args:
            dataframe (pd.DataFrame): Input dataset used by analytics methods.
                It is copied, so later changes to the caller's frame are not
                seen by the analyzer.

        Returns:
            None

        Raises:
            TypeError: If `dataframe` is not a `pandas.DataFrame`.
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame.")
        self.dataframe: pd.DataFrame = dataframe.copy()

    def get_categorical_distribution(
        self,
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
        return build_categorical_distribution(
            self.dataframe,
            x_col,
            top_n=top_n,
            show_others=show_others,
            filters=filters,
            rules=rules,
            orient=orient,
            **kwargs,
        )

    def get_numerical_aggregation(
        self,
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
        return build_numerical_aggregation(
            self.dataframe,
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

    def get_time_series(
        self,
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
        return build_time_series(
            self.dataframe,
            date_col,
            time_period=time_period,
            num_col=num_col,
            agg_func=agg_func,
            filters=filters,
            rules=rules,
            orient=orient,
            **kwargs,
        )

    def get_kpi_value(
        self,
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
        return build_kpi_value(
            self.dataframe,
            column,
            agg_func=agg_func,
            round_value=round_value,
            filters=filters,
            **kwargs,
        )

    def get_bins(
        self,
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
        return build_bins(
            self.dataframe,
            col,
            bins=bins,
            filters=filters,
            rules=rules,
            orient=orient,
            **kwargs,
        )