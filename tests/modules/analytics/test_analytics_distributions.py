import logging

import pandas as pd
import pytest

from bynat.analytics import Analyzer

pytestmark = pytest.mark.unit


def test_analytics_categorical_distribution_counts_and_top_n() -> None:
    df = pd.DataFrame({
        "cat": ["Apple", "Banana", "Apple", "Cherry", "Date", "Apple"],
        "val": [1, 2, 3, 4, 5, 6],
    })
    analyzer = Analyzer(df)

    res_no_others = analyzer.get_categorical_distribution("cat", top_n=2, show_others=False)
    assert len(res_no_others["data"]) == 2
    assert res_no_others["data"][0] == {"x": "Apple", "y": 3}

    res_with_others = analyzer.get_categorical_distribution("cat", top_n=2, show_others=True)
    others_rows = [item for item in res_with_others["data"] if item["x"] == "Others"]
    assert len(others_rows) == 1
    assert others_rows[0]["y"] == 2
    assert others_rows[0]["is_others"] is True
    assert len(others_rows[0]["others_breakdown"]) == 2

    res_small = analyzer.get_categorical_distribution("cat", top_n=10, show_others=True)
    assert not any(item["x"] == "Others" for item in res_small["data"])


def test_analytics_categorical_distribution_unicode_null_and_options() -> None:
    df = pd.DataFrame({"cat": ["café", "東京", "café", "Übung"], "val": [1, 2, 3, 4]})
    analyzer = Analyzer(df)

    res = analyzer.get_categorical_distribution(
        "cat",
        filters={"val": {">": 1}},
        rules=[{"new_col": "scaled", "expression": "y * 10"}],
        orient="records",
        custom_meta="abc",
    )
    assert res["custom_meta"] == "abc"
    assert any(row["x"] == "東京" and row["scaled"] == 10 for row in res["data"])

    df_null = pd.DataFrame({"cat": [None, None], "val": [1, 2]})
    assert Analyzer(df_null).get_categorical_distribution("cat") == {"data": []}


def test_analytics_numerical_aggregation_funcs_and_others_weighting(caplog: pytest.LogCaptureFixture) -> None:
    df = pd.DataFrame({
        "cat": ["B", "A", "A", "A", "C"],
        "val": [200.0, 30.0, 30.0, 30.0, 10.0],
        "cat_obj": pd.Categorical(["X", "Y", "Y", "Y", "Z"], categories=["X", "Y", "Z", "Unused"]),
    })
    analyzer = Analyzer(df)

    expected = {"mean": 200.0, "sum": 200.0, "median": 200.0, "min": 200.0, "max": 200.0}
    for func, b_val in expected.items():
        res = analyzer.get_numerical_aggregation("cat", "val", agg_func=func, round_value=1)
        by_x = {row["x"]: row["y"] for row in res["data"]}
        assert by_x["B"] == b_val

    res_topn = analyzer.get_numerical_aggregation("cat", "val", top_n=1, show_others=True, agg_func="mean")
    assert len(res_topn["data"]) == 2
    others = res_topn["data"][1]
    assert others["x"] == "Others"
    assert others["y"] == 25.0
    assert others["is_others"] is True
    assert len(others["others_breakdown"]) == 2

    res_topn_false = analyzer.get_numerical_aggregation("cat_obj", "val", top_n=2, show_others=False, agg_func="mean")
    assert len(res_topn_false["data"]) == 2

    df_nan = pd.DataFrame({"cat": ["A", "B"], "val": [None, None]})
    assert Analyzer(df_nan).get_numerical_aggregation("cat", "val", agg_func="mean") == {"data": []}

    with caplog.at_level(logging.WARNING, logger="bynat.analytics.analyzer"):
        res_bad = analyzer.get_numerical_aggregation("cat", "val", agg_func="invalid_func")
        assert res_bad == {"data": []}
        assert any(record.levelname == "WARNING" for record in caplog.records)
