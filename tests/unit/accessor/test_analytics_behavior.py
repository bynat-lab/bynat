import pandas as pd
import pytest

from bynat.cleaning import BaseData
from bynat.profiling import ProfileReport
from bynat.profiling import profile as profiling_profile


@pytest.fixture()
def frame():
    return pd.DataFrame({
        "region": ["north", "south", "north", "east"],
        "revenue": [10.0, 20.5, 30.25, 40.0],
        "order_date": pd.to_datetime([
            "2026-01-05", "2026-01-20", "2026-02-11", "2026-02-28",
        ]),
    })


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


def test_accessor_profile_returns_profiling_report_without_mutating_input():
    frame = pd.DataFrame({
        "age": [25, 30, None, 40, 30],
        "city": ["Cairo", "Alex", "Cairo", "Giza", "Alex"],
    })
    original = frame.copy(deep=True)

    report = frame.bynat.profile()

    assert type(report) is ProfileReport
    assert report.dataset.row_count == 5
    assert report.dataset.missing_count == 1
    assert report.columns["age"].stats["median"] == 30.0
    pd.testing.assert_frame_equal(frame, original)


def test_accessor_profile_adapts_basedata_output_type_to_the_requested_subclass(tmp_path):
    frame = pd.DataFrame({"x": [1, 2, 3]})
    expected = profiling_profile(frame, output_type=pd.DataFrame)

    class _Subclass(BaseData):
        pass

    for output_type in (BaseData, _Subclass):
        result = frame.bynat.profile(output_type=output_type)
        assert type(result) is output_type
        pd.testing.assert_frame_equal(pd.DataFrame(result), expected)


def test_accessor_profile_column_selection_and_missing_column_error():
    frame = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})

    subset = frame.bynat.profile("a", "c")
    assert subset.dataset.column_count == 2
    assert list(subset.columns) == ["a", "c"]
    assert list(frame.bynat.profile(["b"]).columns) == ["b"]

    with pytest.raises(KeyError, match="not found in DataFrame"):
        frame.bynat.profile("missing")
