import logging
from typing import Any

import pandas as pd
import pytest

from bynat.analytics import Analyzer


def test_analytics_filters_basic_predicates() -> None:
    df = pd.DataFrame({
        "category": ["A", "B", "A", "C", "D"],
        "val": [10, 20, 30, 40, 50],
    })
    analyzer = Analyzer(df)

    res_eq = analyzer.get_categorical_distribution("category", filters={"category": "A"})
    assert res_eq["data"] == [{"x": "A", "y": 2}]

    res_isin = analyzer.get_categorical_distribution("category", filters={"category": ["A", "B"]})
    assert sum(item["y"] for item in res_isin["data"]) == 3

    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {">": 30}})["data"] == 90
    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {"<": 20}})["data"] == 10
    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {">=": 40}})["data"] == 90
    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {"<=": 20}})["data"] == 30
    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {"==": 30}})["data"] == 30
    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {"!=": 50}})["data"] == 100
    assert analyzer.get_kpi_value("val", agg_func="sum", filters={"val": {">": 10, "<=": 30}})["data"] == 50


def test_analytics_filters_contains_and_unknowns(caplog: pytest.LogCaptureFixture) -> None:
    df = pd.DataFrame({"text": ["Hello World", "a+b (c).", "baz"], "val": [1, 2, 3]})
    analyzer = Analyzer(df)

    res_ws = analyzer.get_kpi_value("val", agg_func="sum", filters={"text": {"contains": "  hello world  "}})
    assert res_ws["data"] == 1

    res_regex_lit = analyzer.get_kpi_value("val", agg_func="sum", filters={"text": {"contains": "a+b (c)."}})
    assert res_regex_lit["data"] == 2

    res_unk = analyzer.get_kpi_value("val", agg_func="sum", filters={"unknown_col": 5, "val": {"unknown_op": 10}})
    assert res_unk["data"] == 6

    with caplog.at_level(logging.WARNING, logger="bynat.analytics.analyzer"):
        res_err = analyzer.get_kpi_value("val", agg_func="sum", filters={"val": (1, 2, 3, 4)})
        assert res_err["data"] == 6
        assert any(record.levelname == "WARNING" for record in caplog.records)


def test_analytics_filters_nullable_and_bad_threshold() -> None:
    df = pd.DataFrame({
        "num": pd.Series([10, 20, pd.NA], dtype="Int64"),
        "txt": pd.Series(["apple", "banana", pd.NA], dtype="string"),
    })
    analyzer = Analyzer(df)

    res_eq = analyzer.get_kpi_value("num", agg_func="sum", filters={"num": {"==": 10}})
    assert res_eq["data"] == 10

    res_ne = analyzer.get_kpi_value("num", agg_func="sum", filters={"num": {"!=": 10}})
    assert res_ne["data"] == 20

    res_mixed = analyzer.get_kpi_value(
        "num",
        agg_func="sum",
        filters={"num": {">": "not-a-number"}, "txt": {"contains": "ANANA"}},
    )
    assert res_mixed["data"] == 20


def test_analytics_rules_execution() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    analyzer = Analyzer(df)

    rules: list[dict[str, Any]] = [
        {"where": "x == 1", "set_col": "y", "set_value": 99},
        {"new_col": "y_doubled", "expression": "y * 2"},
        {"source_col": "y", "method": "cumsum", "new_col": "y_cum"},
    ]
    res = analyzer.get_numerical_aggregation("a", "b", rules=rules, agg_func="sum")
    by_x = {row["x"]: row for row in res["data"]}
    assert by_x[1]["y"] == 99
    assert by_x[1]["y_doubled"] == 198
    assert [row["y_cum"] for row in res["data"]] == [30, 50, 149]


def test_analytics_safe_expression_blocking() -> None:
    from bynat.analytics._internal.security import is_safe_expression

    for bad in ["__import__('os')", "@df", "import os", "lambda x: x", "a + 1; b", "", "   ", None, 123]:
        assert is_safe_expression(bad) is False
    assert is_safe_expression("a + 1") is True


def test_analytics_rules_malformed_logging(caplog: pytest.LogCaptureFixture) -> None:
    analyzer = Analyzer(pd.DataFrame({"a": ["A", "B"], "b": [1, 2]}))

    bad_rules: list[Any] = [
        "not-a-dict",
        {"missing_keys": 1},
        {"where": "__import__('os')", "set_col": "y", "set_value": 0},
        {"new_col": "x2", "expression": "__import__('os')"},
        {"source_col": "y", "method": "dtype", "new_col": "bad_attr"},
        {"source_col": "missing", "method": "abs", "new_col": "bad_src"},
        {"new_col": "z", "expression": "nonexistent_col + 1"},
    ]

    with caplog.at_level(logging.WARNING, logger="bynat.analytics.analyzer"):
        res = analyzer.get_categorical_distribution("a", rules=bad_rules)
        assert len(res["data"]) == 2
        assert any(record.levelname == "WARNING" for record in caplog.records)


def test_missing_requested_columns_warn_and_return_empty_payloads(caplog):
    analyzer = Analyzer(pd.DataFrame({"present": [1, 2]}))

    with caplog.at_level(logging.WARNING, logger="bynat.analytics._insights"):
        results = [
            analyzer.get_categorical_distribution("missing"),
            analyzer.get_numerical_aggregation("missing", "present"),
            analyzer.get_time_series("missing"),
            analyzer.get_kpi_value("missing", agg_func="sum"),
            analyzer.get_bins("missing"),
        ]

    assert results == [
        {"data": []},
        {"data": []},
        {"data": []},
        {"data": None, "title": "missing"},
        {"data": []},
    ]
    assert [record.getMessage() for record in caplog.records] == [
        "Column 'missing' not found",
        "Columns ['missing'] not found",
        "Column 'missing' not found",
        "Column 'missing' not found",
        "Column 'missing' not found",
    ]
