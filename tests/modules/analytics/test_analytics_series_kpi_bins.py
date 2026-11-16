import logging
import re
import warnings

import pandas as pd
import pytest

from bynat.analytics import Analyzer

pytestmark = pytest.mark.unit


def test_analytics_time_series_periods_and_gap_filling(caplog: pytest.LogCaptureFixture) -> None:
    df = pd.DataFrame({
        "dt": ["2026-01-05", "2026-03-10", "2026-01-01"],
        "val": [10.4, 20.6, 30.0],
    })
    analyzer = Analyzer(df)

    res_m = analyzer.get_time_series("dt", time_period="M", num_col="val", agg_func="sum")
    assert res_m["data"] == [
        {"x": "2026-01", "y": 40.0},
        {"x": "2026-02", "y": 0.0},
        {"x": "2026-03", "y": 21.0},
    ]

    for period, pattern in [("Y", r"^\d{4}$"), ("H", r"^\d{4}-\d{2}-\d{2} \d{2}:00$"), ("D", r"^\d{4}-\d{2}-\d{2}$")]:
        res_p = analyzer.get_time_series("dt", time_period=period, agg_func="count")
        assert re.fullmatch(pattern, res_p["data"][0]["x"])

    assert analyzer.get_time_series("dt", time_period="M", num_col="missing", agg_func="sum") == {"data": []}
    assert analyzer.get_time_series("dt", time_period="M", agg_func="sum")["data"] == [
        {"x": "2026-01", "y": 2},
        {"x": "2026-02", "y": 0},
        {"x": "2026-03", "y": 1},
    ]

    df_bad_dt = pd.DataFrame({"dt": ["not-a-date", "2026-01-01"], "val": [1, 2]})
    assert Analyzer(df_bad_dt).get_time_series("dt", time_period="M", agg_func="count")["data"] == [{"x": "2026-01", "y": 1}]
    assert Analyzer(pd.DataFrame({"dt": ["not-a-date", "invalid"]})).get_time_series("dt") == {"data": []}

    with caplog.at_level(logging.WARNING, logger="bynat.analytics.analyzer"):
        res_bad_agg = analyzer.get_time_series("dt", time_period="M", num_col="val", agg_func="invalid_agg")
        assert res_bad_agg == {"data": []}
        assert any(record.levelname == "WARNING" for record in caplog.records)

    df_tz = pd.DataFrame({
        "dt": pd.date_range("2026-01-01", periods=3, tz="UTC"),
        "val": [10, 20, 30],
    })
    analyzer_tz = Analyzer(df_tz)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        res_tz = analyzer_tz.get_time_series("dt", time_period="M", num_col="val", agg_func="mean")
        assert res_tz["data"] == [{"x": "2026-01", "y": 20.0}]


def test_analytics_kpi_value_variants(caplog: pytest.LogCaptureFixture) -> None:
    df = pd.DataFrame({"val": [10.123, 20.456, None]})
    analyzer = Analyzer(df)

    assert analyzer.get_kpi_value("val", agg_func="count")["data"] == 3

    res_round2 = analyzer.get_kpi_value("val", agg_func="mean", round_value=2)
    assert res_round2["data"] == 15.29
    assert isinstance(res_round2["data"], float)

    res_round0 = analyzer.get_kpi_value("val", agg_func="mean", round_value=0)
    assert res_round0["data"] == 15
    assert isinstance(res_round0["data"], int)

    res_meta = analyzer.get_kpi_value("val", agg_func="count", title="My KPI", extra_meta=123)
    assert res_meta == {"data": 3, "title": "My KPI", "extra_meta": 123}

    assert analyzer.get_kpi_value("nonexistent", agg_func="sum") == {"data": None, "title": "nonexistent"}
    assert Analyzer(pd.DataFrame({"val": [None, None]})).get_kpi_value("val", agg_func="mean")["data"] is None

    with caplog.at_level(logging.WARNING, logger="bynat.analytics.analyzer"):
        res_bad_agg = analyzer.get_kpi_value("val", agg_func="invalid_func")
        res_non_scalar = analyzer.get_kpi_value("val", agg_func="describe")
        assert res_bad_agg["data"] is None
        assert res_non_scalar["data"] is None
        assert sum(record.levelname == "WARNING" for record in caplog.records) >= 2


def test_analytics_bins_histogram() -> None:
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 10, 20, 30, 40, 50]})
    analyzer = Analyzer(df)

    res = analyzer.get_bins(
        "val",
        bins=3,
        filters={"val": {">": 0}},
        rules=[{"new_col": "y2", "expression": "y * 2"}],
        orient="records",
        custom_meta="bin-test",
    )
    assert len(res["data"]) == 3
    assert sum(row["y"] for row in res["data"]) == 10
    assert res["custom_meta"] == "bin-test"
    for row in res["data"]:
        assert re.fullmatch(r"\d+\.\d{2}-\d+\.\d{2}", row["x"])
        assert row["y2"] == row["y"] * 2

    df_coerce = pd.DataFrame({"val": ["1", "2.5", "bad", "10"]})
    res_coerce = Analyzer(df_coerce).get_bins("val", bins=2)
    assert sum(row["y"] for row in res_coerce["data"]) == 3

    for bad_bins in [0, -2, "5", True, False]:
        assert analyzer.get_bins("val", bins=bad_bins) == {"data": []}  # type: ignore[arg-type]

    df_str = pd.DataFrame({"val": ["a", "b", "c"]})
    assert Analyzer(df_str).get_bins("val", bins=2) == {"data": []}
