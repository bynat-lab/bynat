import inspect

import pandas as pd
import pytest

from bynat._accessors import BynatAccessor
from bynat.analytics import Analyzer

pytestmark = pytest.mark.integration


ANALYTICS_METHODS = (
    "get_categorical_distribution",
    "get_numerical_aggregation",
    "get_time_series",
    "get_kpi_value",
    "get_bins",
)


PARITY_CASES = [
    pytest.param(
        "get_categorical_distribution", ("region",),
        {"top_n": 2, "show_others": True}, id="categorical_distribution",
    ),
    pytest.param(
        "get_numerical_aggregation", ("region", "revenue"),
        {"agg_func": "sum", "title": "Revenue by region"}, id="numerical_aggregation",
    ),
    pytest.param(
        "get_time_series", ("order_date",),
        {"time_period": "M", "num_col": "revenue", "agg_func": "sum"}, id="time_series",
    ),
    pytest.param(
        "get_kpi_value", ("revenue",),
        {"agg_func": "sum", "round_value": 1, "subtitle": "USD"}, id="kpi_value",
    ),
    pytest.param("get_bins", ("revenue",), {"bins": 2, "unit": "orders"}, id="bins"),
]


@pytest.fixture()
def frame():
    return pd.DataFrame({
        "region": ["north", "south", "north", "east"],
        "revenue": [10.0, 20.5, 30.25, 40.0],
        "order_date": pd.to_datetime([
            "2026-01-05", "2026-01-20", "2026-02-11", "2026-02-28",
        ]),
    })


@pytest.mark.parametrize(("method_name", "args", "kwargs"), PARITY_CASES)
def test_accessor_analytics_matches_canonical_analyzer(frame, method_name, args, kwargs):
    expected = getattr(Analyzer(frame), method_name)(*args, **kwargs)
    actual = getattr(frame.bynat, method_name)(*args, **kwargs)

    assert type(actual) is dict
    assert actual == expected
    assert "inplace" not in actual


@pytest.mark.parametrize("method_name", ANALYTICS_METHODS)
def test_accessor_analytics_signatures_match_analyzer(method_name):
    analyzer_signature = inspect.signature(getattr(Analyzer, method_name))
    accessor_signature = inspect.signature(getattr(BynatAccessor, method_name))

    assert accessor_signature == analyzer_signature


def test_accessor_analytics_default_calls_leave_the_wrapped_frame_unmodified(frame):
    before = frame.copy(deep=True)

    frame.bynat.get_categorical_distribution("region")
    frame.bynat.get_numerical_aggregation("region", "revenue")
    frame.bynat.get_time_series("order_date")
    frame.bynat.get_kpi_value("revenue")
    frame.bynat.get_bins("revenue")

    pd.testing.assert_frame_equal(frame, before)


def test_accessor_analytics_accepts_positional_arguments_like_analyzer(frame):
    analyzer_result = Analyzer(frame).get_numerical_aggregation("region", "revenue", "mean", 1)
    accessor_result = frame.bynat.get_numerical_aggregation("region", "revenue", "mean", 1)

    assert accessor_result == analyzer_result
