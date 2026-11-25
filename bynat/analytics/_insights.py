"""
Private core logic for the analytics package.

This module implements the computations behind the public
:class:`bynat.analytics.analyzer.Analyzer` methods: categorical distributions,
numerical aggregations, time-series bucketing, single-metric KPI cards, and
histogram binning. Every function takes the source dataframe as its first
argument and never mutates it.

This module is private and not part of the public API. Use
:class:`Analyzer` instead.
"""

import logging
from typing import Any, cast

import numpy as np
import pandas as pd

from ._internal import apply_computed_rules, apply_filters

logger = logging.getLogger(__name__)


def build_categorical_distribution(
    dataframe: pd.DataFrame,
    x_col: str,
    top_n: int | None = None,
    show_others: bool = False,
    filters: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    orient: str = "records",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Build distribution counts for a categorical column.

    Rows are counted with `value_counts()` and returned in descending count
    order. With `show_others=True` the rows beyond `top_n` are collapsed into a
    single `"Others"` row carrying `is_others=True` and an `others_breakdown`
    list of the collapsed `{"x", "y"}` rows; the retained rows get
    `is_others=False` and `others_breakdown=None`. `show_others` has no effect
    when `top_n` is None or the number of categories does not exceed it.

    Args:
        dataframe (pd.DataFrame): Source dataset (not mutated).
        x_col (str): Categorical column to aggregate.
        top_n (int | None): Optional limit for top categories.
        show_others (bool): Collapse categories outside `top_n` into `"Others"`.
        filters (dict[str, Any] | None): Optional pre-aggregation filters.
        rules (list[dict[str, Any]] | None): Optional computed rules applied to
            the result.
        orient (str): Output orientation for `DataFrame.to_dict`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response with a `"data"` key, plus any `kwargs` entries.
        An empty filtered frame or a missing `x_col` returns `{"data": []}`.
    """
    data = apply_filters(dataframe, filters)

    if data.empty:
        return {"data": []}

    if x_col not in data.columns:
        logger.warning("Column %r not found", x_col)
        return {"data": []}

    grouped = data[x_col].value_counts().reset_index()
    grouped.columns = pd.Index(["x", "y"])

    if top_n and show_others and len(grouped) > top_n:
        top_df = grouped.head(top_n).copy()
        others_df = grouped.iloc[top_n:].copy()

        others_val = others_df["y"].sum()

        others_breakdown = others_df[["x", "y"]].to_dict(orient=cast(Any, orient))

        others_row = pd.DataFrame({
            "x": ["Others"],
            "y": [others_val],
            "is_others": [True],
            "others_breakdown": [others_breakdown],
        })

        top_df["is_others"] = False
        top_df["others_breakdown"] = None

        grouped = pd.concat([top_df, others_row], ignore_index=True)

    elif top_n:
        grouped = grouped.head(top_n)

    grouped = apply_computed_rules(grouped, rules)

    response = {"data": grouped.to_dict(orient=cast(Any, orient))}

    if kwargs:
        response.update(kwargs)

    return response


def build_numerical_aggregation(
    dataframe: pd.DataFrame,
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

    Rows with a null `y_col` are dropped before grouping, and the groups are
    returned sorted by aggregated value in descending order. Numeric results
    are rounded to `round_value` decimals. With `show_others=True` the groups
    beyond `top_n` are collapsed into one `"Others"` row whose value is
    recomputed from the underlying rows (not summed from the rounded group
    values) and whose `others_breakdown` lists the collapsed `{"x", "y"}` rows;
    the retained rows get `is_others=False` and `others_breakdown=None`.

    Args:
        dataframe (pd.DataFrame): Source dataset (not mutated).
        x_col (str): Grouping column.
        y_col (str): Numeric column to aggregate.
        agg_func (str): Aggregation function name (e.g. `mean`, `sum`, `median`).
        round_value (int): Decimal places used when the aggregated value is numeric.
        top_n (int | None): Optional cap for highest `y` rows.
        show_others (bool): Collapse categories outside `top_n` into `"Others"`.
        filters (dict[str, Any] | None): Optional filters applied before aggregation.
        rules (list[dict[str, Any]] | None): Optional computed rules on output rows.
        orient (str): Output orientation for `DataFrame.to_dict`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response with a `"data"` key, plus any `kwargs` entries.
        An empty filtered frame, a missing `x_col` or `y_col`, or a failing
        `agg_func` returns `{"data": []}` (the failure is logged as a warning).
    """
    data = apply_filters(dataframe, filters)

    if data.empty:
        return {"data": []}

    missing = [c for c in (x_col, y_col) if c not in data.columns]
    if missing:
        logger.warning("Columns %r not found", missing)
        return {"data": []}

    valid_data = data.dropna(subset=[y_col])

    try:
        grouped = valid_data.groupby(x_col, observed=True)[y_col].agg(agg_func).reset_index()
    except Exception as e:
        logger.warning("Failed to get numerical aggregation, aggregate function's value: %r, cols: [%r, %r]. Error: %s", agg_func, x_col, y_col, e)
        return {"data": []}

    if pd.api.types.is_numeric_dtype(grouped[y_col]):
        grouped[y_col] = grouped[y_col].round(round_value)

    grouped.columns = pd.Index(["x", "y"])
    grouped = grouped.sort_values(by="y", ascending=False)

    if top_n and show_others and len(grouped) > top_n:
        top_df = grouped.head(top_n).copy()
        others_df = grouped.iloc[top_n:].copy()
        others_categories = others_df["x"].tolist()
        others_source = valid_data[valid_data[x_col].isin(others_categories)]

        others_val = others_source[y_col].agg(agg_func)
        if isinstance(others_val, np.generic):
            others_val = others_val.item()
        if isinstance(others_val, float):
            others_val = round(others_val, round_value)

        others_breakdown = others_df[["x", "y"]].to_dict(orient=cast(Any, orient))

        others_row = pd.DataFrame({
            "x": ["Others"],
            "y": [others_val],
            "is_others": [True],
            "others_breakdown": [others_breakdown],
        })

        top_df["is_others"] = False
        top_df["others_breakdown"] = None

        grouped = pd.concat([top_df, others_row], ignore_index=True)

    elif top_n:
        grouped = grouped.head(top_n)

    grouped = apply_computed_rules(grouped, rules)

    response = {"data": grouped.to_dict(orient=cast(Any, orient))}

    if kwargs:
        response.update(kwargs)

    return response


def build_time_series(
    dataframe: pd.DataFrame,
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

    The date column is parsed with `pd.to_datetime(errors="coerce")` and rows
    whose date is missing or unparseable are dropped. Timezone-aware values are
    converted to naive local time before bucketing. The result is reindexed
    onto a complete date range between the first and last bucket, so gaps
    appear as rows with `y=0`, and the `x` labels are sorted ascending.

    `time_period` is matched case-insensitively: `M` monthly (`YYYY-MM`),
    `Y` yearly (`YYYY`), `H` hourly (`YYYY-MM-DD HH:00`), and any other value
    falls back to daily buckets (`YYYY-MM-DD`). With `num_col` set and
    `agg_func != "count"`, the numeric column is aggregated per bucket and
    rounded to whole numbers; otherwise the bucket row count is used.

    Args:
        dataframe (pd.DataFrame): Source dataset (not mutated).
        date_col (str): Source datetime/date column used for time bucketing.
        time_period (str): Time bucket granularity.
        num_col (str | None): Optional numeric column for non-count aggregation.
        agg_func (str): Aggregation function for `num_col`.
        filters (dict[str, Any] | None): Optional filters applied before aggregation.
        rules (list[dict[str, Any]] | None): Optional computed rules on output rows.
        orient (str): Output orientation for `DataFrame.to_dict`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response with a `"data"` key, plus any `kwargs` entries.
        A missing `date_col` or `num_col`, a failing `agg_func`, or an empty
        frame returns `{"data": []}` (a failing aggregation is logged as a warning).
    """
    data = apply_filters(dataframe, filters)

    if data.empty:
        return {"data": []}

    if date_col not in data.columns:
        logger.warning("Column %r not found", date_col)
        return {"data": []}

    data = data.dropna(subset=[date_col]).copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna(subset=[date_col])

    if data[date_col].dt.tz is not None:
        data[date_col] = data[date_col].dt.tz_localize(None)

    if data.empty:
        return {"data": []}

    if time_period.upper() == "M":
        data["time_x"] = data[date_col].dt.to_period("M").dt.to_timestamp()
        freq = "MS"
        date_format = "%Y-%m"

    elif time_period.upper() == "Y":
        data["time_x"] = data[date_col].dt.to_period("Y").dt.to_timestamp()
        freq = "YS"
        date_format = "%Y"

    elif time_period.upper() == "H":
        data["time_x"] = data[date_col].dt.floor("h")
        freq = "h"
        date_format = "%Y-%m-%d %H:00"

    else:
        data["time_x"] = data[date_col].dt.floor("d")
        freq = "D"
        date_format = "%Y-%m-%d"

    if num_col and agg_func != "count":
        if num_col not in data.columns:
            logger.warning("Column %r not found", num_col)
            return {"data": []}

        try:
            grouped = data.groupby("time_x", observed=True)[num_col].agg(agg_func).reset_index()
        except Exception as e:
            logger.warning("Failed to get time series, aggregate function's value: %r, cols: [%r, %r]. Error: %s", agg_func, date_col, num_col, e)
            return {"data": []}

        if pd.api.types.is_numeric_dtype(grouped[num_col]):
            grouped[num_col] = grouped[num_col].round(0)

        grouped.columns = pd.Index(["time_x", "y"])

    else:
        grouped = data.groupby("time_x", observed=True).size().reset_index(name="y")
        grouped.columns = pd.Index(["time_x", "y"])

    if not grouped.empty:
        min_date = grouped["time_x"].min()
        max_date = grouped["time_x"].max()

        full_date_range = pd.date_range(start=min_date, end=max_date, freq=freq)

        grouped = grouped.set_index("time_x").reindex(full_date_range, fill_value=0).reset_index()
        grouped.columns = pd.Index(["x", "y"])

        grouped["x"] = grouped["x"].dt.strftime(date_format)
    else:
        grouped.columns = pd.Index(["x", "y"])

    grouped = grouped.sort_values(by="x", ascending=True)

    grouped = apply_computed_rules(grouped, rules)

    response = {"data": grouped.to_dict(orient=cast(Any, orient))}

    if kwargs:
        response.update(kwargs)

    return response


def build_kpi_value(
    dataframe: pd.DataFrame,
    column: str,
    agg_func: str = "count",
    round_value: int = 2,
    filters: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Compute a single KPI metric card.

    With `agg_func="count"` the value is the number of filtered rows and
    `column` is only used as the default title. Otherwise the value is
    `data[column].agg(agg_func)`; a missing column, a failing aggregation, or a
    non-scalar result yields `None` (logged as a warning for the latter two).
    NumPy scalars are converted to Python scalars, a null value becomes `None`,
    a float is rounded to `round_value` when that is non-zero, and other
    numeric values are converted to `int`.

    Args:
        dataframe (pd.DataFrame): Source dataset (not mutated).
        column (str): Source column used when `agg_func` is not `count`. Also
            the default card title.
        agg_func (str): Aggregation function name; `count` uses row count.
        round_value (int): Decimal places for float results. `0` skips rounding.
        filters (dict[str, Any] | None): Optional filters applied before computation.
        **kwargs: Optional metadata for the card. `title` customizes the KPI
            title and is removed from the extra metadata; every other entry is
            copied into the card.

    Returns:
        dict[str, Any]: KPI payload containing `"data"`, `"title"`, and any
        additional metadata.
    """
    data = apply_filters(dataframe, filters)

    value: Any
    if agg_func == "count":
        value = len(data)
    else:
        if column not in data.columns:
            logger.warning("Column %r not found", column)
            value = None

        else:
            try:
                value = data[column].agg(agg_func)
                if isinstance(value, (pd.Series, pd.DataFrame, np.ndarray)):
                    logger.warning("KPI aggregation for column %r with func %r returned non-scalar result.", column, agg_func)
                    value = None
            except Exception as e:
                logger.warning("Failed to get kpi value, aggregate function's value: %r, col: [%r]. Error: %s", agg_func, column, e)
                value = None

    if value is not None and pd.isna(value):
        value = None
    elif isinstance(value, np.generic):
        value = value.item()

    rounded_data: Any
    if value is None:
        rounded_data = None
    elif isinstance(value, float) and round_value:
        rounded_data = round(value, round_value)
    elif isinstance(value, (float, np.int64, int)):
        rounded_data = int(value)
    else:
        rounded_data = value

    kpi_card = {
        "data": rounded_data,
        "title": kwargs.pop("title", column),
    }

    if kwargs:
        kpi_card.update(kwargs)

    return kpi_card


def build_bins(
    dataframe: pd.DataFrame,
    col: str,
    bins: int = 10,
    filters: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
    orient: str = "records",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Create histogram bins for a numeric column.

    The column is coerced with `pd.to_numeric(errors="coerce")` and nulls are
    dropped, so non-numeric text is ignored rather than raising. Bins come from
    `numpy.histogram`, and each row's `x` label is the `"<lower>-<upper>"` bin
    range formatted to two decimals.

    Args:
        dataframe (pd.DataFrame): Source dataset (not mutated).
        col (str): Numeric source column.
        bins (int): Number of histogram bins.
        filters (dict[str, Any] | None): Optional filters applied before binning.
        rules (list[dict[str, Any]] | None): Optional computed rules on output rows.
        orient (str): Output orientation for `DataFrame.to_dict`.
        **kwargs: Extra metadata merged into the returned response object.

    Returns:
        dict[str, Any]: Response with a `"data"` key, plus any `kwargs` entries.
        An empty filtered frame, a missing `col`, a non-positive or non-integer
        `bins` (booleans included), or no numeric values returns `{"data": []}`.
    """
    data = apply_filters(dataframe, filters)

    if data.empty:
        return {"data": []}

    if col not in data.columns:
        logger.warning("Column %r not found", col)
        return {"data": []}

    if isinstance(bins, bool) or not isinstance(bins, int) or bins <= 0:
        return {"data": []}

    numeric_values = pd.to_numeric(data[col], errors="coerce").dropna()
    if numeric_values.empty:
        return {"data": []}

    counts, bin_edges = np.histogram(numeric_values, bins=bins)

    bin_labels = [f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}" for i in range(len(bin_edges) - 1)]
    grouped = pd.DataFrame({"x": bin_labels, "y": counts})

    grouped = apply_computed_rules(grouped, rules)

    response = {"data": grouped.to_dict(orient=cast(Any, orient))}

    if kwargs:
        response.update(kwargs)

    return response