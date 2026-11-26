"""Accessor analytics delegation: parity with `Analyzer`, signatures, and reserved `inplace`."""

import importlib
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

_DOUBLE_Y_RULE = [{"new_col": "double_y", "expression": "y * 2"}]

# Every declared Analyzer parameter is passed explicitly so the recorded call can be
# compared against the caller's arguments exactly, without relying on defaults.
DELEGATION_CASES = [
    pytest.param("get_categorical_distribution", ("region",),
                 {"top_n": 2, "show_others": True,
                  "filters": {"region": ["north", "south"]},
                  "rules": _DOUBLE_Y_RULE, "orient": "list", "title": "By region"},
                 id="categorical_distribution"),
    pytest.param("get_numerical_aggregation", ("region", "revenue"),
                 {"agg_func": "sum", "round_value": 1, "top_n": 2, "show_others": True,
                  "filters": {"region": ["north", "south"]},
                  "rules": _DOUBLE_Y_RULE, "orient": "list"},
                 id="numerical_aggregation"),
    pytest.param("get_time_series", ("order_date",),
                 {"time_period": "M", "num_col": "revenue", "agg_func": "sum",
                  "filters": {"region": "north"},
                  "rules": _DOUBLE_Y_RULE, "orient": "list"},
                 id="time_series"),
    pytest.param("get_kpi_value", ("revenue",),
                 {"agg_func": "sum", "round_value": 1, "filters": {"region": "north"},
                  "title": "Total revenue", "subtitle": "USD"},
                 id="kpi_value"),
    pytest.param("get_bins", ("revenue",),
                 {"bins": 2, "filters": {"region": "north"},
                  "rules": _DOUBLE_Y_RULE, "orient": "list", "unit": "orders"},
                 id="bins"),
]

INPLACE_CASES = [
    pytest.param("get_categorical_distribution", ("region",), id="categorical_distribution"),
    pytest.param("get_numerical_aggregation", ("region", "revenue"), id="numerical_aggregation"),
    pytest.param("get_time_series", ("order_date",), id="time_series"),
    pytest.param("get_kpi_value", ("revenue",), id="kpi_value"),
    pytest.param("get_bins", ("revenue",), id="bins"),
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


BUILD_NAMES = {
    "get_categorical_distribution": "build_categorical_distribution",
    "get_numerical_aggregation": "build_numerical_aggregation",
    "get_time_series": "build_time_series",
    "get_kpi_value": "build_kpi_value",
    "get_bins": "build_bins",
}


@pytest.mark.parametrize(("method_name", "args", "kwargs"), DELEGATION_CASES)
def test_accessor_analytics_delegates_to_shared_core_and_forwards_arguments(
    frame, method_name, args, kwargs, monkeypatch
):
    dataframe_module = importlib.import_module("bynat._accessors.dataframe")
    insights = importlib.import_module("bynat.analytics._insights")
    build_name = BUILD_NAMES[method_name]
    original = getattr(insights, build_name)
    calls = []

    def spy(dataframe, *call_args, **call_kwargs):
        calls.append((dataframe, call_args, dict(call_kwargs)))
        return original(dataframe, *call_args, **call_kwargs)

    monkeypatch.setattr(dataframe_module, build_name, spy)

    actual = getattr(frame.bynat, method_name)(*args, **kwargs)
    expected = original(frame.copy(), *args, **kwargs)

    assert len(calls) == 1
    receiver, forwarded_args, forwarded_kwargs = calls[0]
    assert isinstance(receiver, pd.DataFrame) and receiver.equals(frame) and receiver is not frame
    assert forwarded_args == args
    assert forwarded_kwargs == kwargs
    assert actual == expected


@pytest.mark.parametrize("method_name", ANALYTICS_METHODS)
def test_accessor_analytics_signatures_match_analyzer(method_name):
    analyzer_signature = inspect.signature(getattr(Analyzer, method_name))
    accessor_signature = inspect.signature(getattr(BynatAccessor, method_name))

    assert accessor_signature == analyzer_signature


@pytest.mark.parametrize("method_name", ANALYTICS_METHODS)
def test_accessor_analytics_docstring_summaries_match_analyzer(method_name):
    accessor_summary = inspect.getdoc(getattr(BynatAccessor, method_name)).splitlines()[0]
    analyzer_summary = inspect.getdoc(getattr(Analyzer, method_name)).splitlines()[0]
    assert accessor_summary == analyzer_summary


@pytest.mark.parametrize("inplace_value", [True, False], ids=["true", "false"])
@pytest.mark.parametrize(("method_name", "args"), INPLACE_CASES)
def test_accessor_analytics_rejects_reserved_inplace(frame, method_name, args, inplace_value):
    before = frame.copy(deep=True)

    with pytest.raises(TypeError, match="inplace"):
        getattr(frame.bynat, method_name)(*args, inplace=inplace_value)

    pd.testing.assert_frame_equal(frame, before)


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


def test_accessor_kpi_value_custom_title_and_extra_metadata(frame):
    result = frame.bynat.get_kpi_value(
        "revenue", agg_func="sum", title="Total revenue", subtitle="USD"
    )

    assert result == {"data": 100.75, "title": "Total revenue", "subtitle": "USD"}


def test_accessor_analytics_forwards_arbitrary_metadata(frame):
    result = frame.bynat.get_categorical_distribution(
        "region", title="By region", unit="orders"
    )

    assert set(result) == {"data", "title", "unit"}
    assert result["title"] == "By region"
    assert result["unit"] == "orders"


def test_accessor_analytics_missing_columns_return_documented_empty_payloads():
    frame = pd.DataFrame({"present": [1, 2]})

    assert frame.bynat.get_categorical_distribution("missing") == {"data": []}
    assert frame.bynat.get_numerical_aggregation("missing", "present") == {"data": []}
    assert frame.bynat.get_time_series("missing") == {"data": []}
    assert frame.bynat.get_kpi_value("missing", agg_func="sum") == {
        "data": None, "title": "missing",
    }
    assert frame.bynat.get_bins("missing") == {"data": []}
