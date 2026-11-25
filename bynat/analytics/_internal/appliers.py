"""Dynamic filter and computed-rule appliers used by the analytics core logic."""

import logging
import operator
from typing import Any

import pandas as pd

from .security import is_safe_expression

__all__ = ["apply_filters", "apply_computed_rules"]

logger = logging.getLogger(__name__)


def apply_filters(dataframe: pd.DataFrame, filters: dict[str, Any] | None = None) -> pd.DataFrame:
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


def apply_computed_rules(dataframe: pd.DataFrame, rules: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    """
    Apply dynamic post-processing rules to a dataframe.

    Notes:
        Supported rule styles:
        - Conditional set: `{"where": "...", "set_col": "...", "set_value": ...}`
        - Expression column: `{"new_col": "...", "expression": "..."}`
        - Series method: `{"source_col": "...", "method": "...", "new_col": "..."}`
        Invalid rules are skipped safely.

        A rule missing a required key, an expression rejected by
        `is_safe_expression`, an unknown `source_col`, and a non-callable
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

                if not is_safe_expression(rule["where"]):
                    continue

                mask = result_dataframe.eval(rule["where"])
                result_dataframe.loc[mask, rule["set_col"]] = rule["set_value"]

            elif "expression" in rule:
                required = {"new_col", "expression"}
                if not required.issubset(rule.keys()):
                    continue

                if not is_safe_expression(rule["expression"]):
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