"""Reusable, application-independent DataFrame analytics helpers for categorical distributions, numerical aggregations, time-series bucketing, single-metric KPI cards, and histogram binning."""

import logging
import operator
from typing import Any, cast

import numpy as np
import pandas as pd

__all__ = ["Analyzer"]

logger = logging.getLogger(__name__)


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
        raising. Invalid filters, unsafe expressions, and failing
        aggregations are logged as warnings and skipped.
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

    def _is_safe_expression(self, expression: Any) -> bool:
        """
        Perform a lightweight safety check for dynamic eval expressions.

        Notes:
            This is a guardrail, not a full sandbox. It blocks clearly risky
            tokens and non-string payloads before passing expressions to
            `DataFrame.eval`.

            Blocked tokens are `__`, `@`, `import`, `lambda`, and `;`
            (matched case-insensitively). A blank or non-string expression is
            also rejected.

        Args:
            expression (Any): Candidate expression text.

        Returns:
            bool: True if the expression passes basic safety checks, otherwise
            False.
        """
        if not isinstance(expression, str) or not expression.strip():
            return False

        blocked_tokens = ["__", "@", "import", "lambda", ";"]
        lowered = expression.lower()

        return not any(token in lowered for token in blocked_tokens)

    def _apply_filters(self, dataframe: pd.DataFrame, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        """
        Filter a dataframe using equality, membership, and operator predicates.

        Notes:
            - Scalar values apply equality filtering.
            - List values apply membership filtering via `isin`.
            - Dict values apply operator filters, for example:
              `{"salary": {">=": 5000, "<": 10000}}`.
            - Supported operators are: `>`, `<`, `>=`, `<=`, `!=`, `==`,
              and `contains` (case-insensitive literal substring match).
            - Comparison operators coerce both sides with `pd.to_numeric`;
              a non-numeric comparison value skips that operator.
            - Filters are applied in mapping order, so each predicate narrows
              the rows the next one sees.
            - Unknown columns are ignored safely.
            - Invalid/unsupported operations are logged and skipped without
              raising.
            - `filters=None` and an empty dict return the frame unchanged.

        Args:
            dataframe (pd.DataFrame): Dataframe to filter.
            filters (dict[str, Any] | None): Mapping from column name to filter
                value/list. Defaults to None.

        Returns:
            pd.DataFrame: Filtered copy of `dataframe`. The input is not
            modified.
        """
        if not filters:
            return dataframe

        filtered_dataframe = dataframe.copy()

        op_map = {
            ">": operator.gt,
            "<": operator.lt,
            ">=": operator.ge,
            "<=": operator.le,
            "!=": operator.ne,
            "==": operator.eq,
        }

        for col, value in filters.items():
            if col in filtered_dataframe.columns:
                col_series = filtered_dataframe[col]
                if isinstance(value, list):
                    filtered_dataframe = filtered_dataframe[col_series.isin(value)]

                elif isinstance(value, dict):
                    for op, val in value.items():
                        if op in op_map or op == "contains":
                            try:
                                if op == "contains":
                                    mask = col_series.fillna("").astype(str).str.contains(str(val).strip(), case=False, na=False, regex=False)

                                elif op in {">", "<", ">=", "<="}:
                                    func = op_map[op]

                                    left = pd.to_numeric(col_series, errors="coerce")
                                    right = pd.to_numeric(pd.Series([val]), errors="coerce").iloc[0]

                                    if pd.isna(right):
                                        continue

                                    mask = func(left, right).fillna(False)

                                else:
                                    func = op_map[op]
                                    mask = pd.Series(func(col_series, val), index=col_series.index).fillna(False).astype(bool)

                                filtered_dataframe = filtered_dataframe[mask]
                                col_series = filtered_dataframe[col]

                            except Exception as e:
                                logger.warning("Failed to apply filter for col %r, operator %r with value %r. Error: %s", col, op, val, e)
                                continue

                else:
                    try:
                        mask = pd.Series(col_series == value, index=col_series.index).fillna(False).astype(bool)
                        filtered_dataframe = filtered_dataframe[mask]
                    except Exception as e:
                        logger.warning("Failed to apply filter for col %r, operator '==' with value %r. Error: %s", col, value, e)
                        continue

        return filtered_dataframe

    def _apply_computed_rules(self, dataframe: pd.DataFrame, rules: list[dict[str, Any]] | None = None) -> pd.DataFrame:
        """
        Apply dynamic post-processing rules to a dataframe.

        Notes:
            Supported rule styles:
            - Conditional set: `{"where": "...", "set_col": "...", "set_value": ...}`
            - Expression column: `{"new_col": "...", "expression": "..."}`
            - Series method: `{"source_col": "...", "method": "...", "new_col": "..."}`
            Invalid rules are skipped safely.

            A rule missing a required key, an expression rejected by
            `_is_safe_expression`, an unknown `source_col`, and a non-callable
            `method` are all skipped. `where` and `expression` values are
            evaluated with `DataFrame.eval`. `rules=None` and an empty list
            return the frame unchanged.

        Args:
            dataframe (pd.DataFrame): Dataframe to transform.
            rules (list[dict[str, Any]] | None): Rule definitions to apply.
                Defaults to None.

        Returns:
            pd.DataFrame: Transformed copy of `dataframe`. The input is not
            modified.
        """
        if not rules:
            return dataframe

        result_dataframe = dataframe.copy()

        for rule in rules:
            if not isinstance(rule, dict):
                continue

            context_key = (
                "set_col" if "set_col" in rule else
                "new_col" if "new_col" in rule else
                "source_col" if "source_col" in rule else
                "rule"
            )
            context_value = rule.get(context_key, rule)

            try:
                if "where" in rule:
                    required = {"where", "set_col", "set_value"}
                    if not required.issubset(rule.keys()):
                        continue

                    if not self._is_safe_expression(rule["where"]):
                        continue

                    mask = result_dataframe.eval(rule["where"])
                    result_dataframe.loc[mask, rule["set_col"]] = rule["set_value"]

                elif "expression" in rule:
                    required = {"new_col", "expression"}
                    if not required.issubset(rule.keys()):
                        continue

                    if not self._is_safe_expression(rule["expression"]):
                        continue

                    expr = f"{rule['new_col']} = {rule['expression']}"
                    result_dataframe.eval(expr, inplace=True)

                elif "method" in rule:
                    required = {"source_col", "method", "new_col"}
                    if not required.issubset(rule.keys()):
                        continue

                    src = rule["source_col"]
                    method_name = rule["method"]

                    if src not in result_dataframe.columns:
                        continue

                    method = getattr(result_dataframe[src], method_name, None)
                    if method is None or not callable(method):
                        continue

                    result_dataframe[rule["new_col"]] = method()

            except Exception as e:
                logger.warning("Failed to compute rules for context %r, value %r. Error: %s", context_key, context_value, e)
                continue

        return result_dataframe

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
            - An empty filtered frame or a missing `x_col` returns
              `{"data": []}`.
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
        data = self._apply_filters(self.dataframe, filters)

        if data.empty or x_col not in data.columns:
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

        grouped = self._apply_computed_rules(grouped, rules)

        response = {"data": grouped.to_dict(orient=cast(Any, orient))}

        if kwargs:
            response.update(kwargs)

        return response

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
            - An empty filtered frame, a missing `x_col` or `y_col`, or a
              failing `agg_func` returns `{"data": []}`. The failure is logged
              as a warning.
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
        data = self._apply_filters(self.dataframe, filters)
        if data.empty or x_col not in data.columns or y_col not in data.columns:
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

        grouped = self._apply_computed_rules(grouped, rules)

        response = {"data": grouped.to_dict(orient=cast(Any, orient))}

        if kwargs:
            response.update(kwargs)

        return response

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
            bucket row count is used. A missing `num_col`, a failing
            `agg_func`, or an empty frame returns `{"data": []}`; the failure
            is logged as a warning.

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
        data = self._apply_filters(self.dataframe, filters)
        if data.empty or date_col not in data.columns:
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

        grouped = self._apply_computed_rules(grouped, rules)

        response = {"data": grouped.to_dict(orient=cast(Any, orient))}

        if kwargs:
            response.update(kwargs)

        return response

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
        or a non-scalar result yields `None` (logged as a warning for the
        latter two). NumPy scalars are converted to Python scalars, a null
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
        data = self._apply_filters(self.dataframe, filters)

        value: Any
        if agg_func == "count":
            value = len(data)
        else:
            if column not in data.columns:
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
            - An empty filtered frame, a missing `col`, a non-positive or
              non-integer `bins` (booleans included), or no numeric values
              returns `{"data": []}`.

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
        data = self._apply_filters(self.dataframe, filters)

        if data.empty or col not in data.columns:
            return {"data": []}

        if isinstance(bins, bool) or not isinstance(bins, int) or bins <= 0:
            return {"data": []}

        numeric_values = pd.to_numeric(data[col], errors="coerce").dropna()
        if numeric_values.empty:
            return {"data": []}

        counts, bin_edges = np.histogram(numeric_values, bins=bins)

        bin_labels = [f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}" for i in range(len(bin_edges) - 1)]
        grouped = pd.DataFrame({"x": bin_labels, "y": counts})

        grouped = self._apply_computed_rules(grouped, rules)

        response = {"data": grouped.to_dict(orient=cast(Any, orient))}

        if kwargs:
            response.update(kwargs)

        return response
