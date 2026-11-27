import importlib

import pandas as pd
import pytest

from bynat._accessors import BynatAccessor
from bynat.cleaning import _columns, _stats, _text
from bynat.cleaning.enrich import _currency, _geocode, _nlp

_DOUBLE_Y_RULE = [{"new_col": "double_y", "expression": "y * 2"}]


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


@pytest.fixture()
def frame():
    return pd.DataFrame({
        "region": ["north", "south", "north", "east"],
        "revenue": [10.0, 20.5, 30.25, 40.0],
        "order_date": pd.to_datetime([
            "2026-01-05", "2026-01-20", "2026-02-11", "2026-02-28",
        ]),
    })


BUILD_NAMES = {
    "get_categorical_distribution": "build_categorical_distribution",
    "get_numerical_aggregation": "build_numerical_aggregation",
    "get_time_series": "build_time_series",
    "get_kpi_value": "build_kpi_value",
    "get_bins": "build_bins",
}


@pytest.mark.parametrize(("method_name", "args", "kwargs"), DELEGATION_CASES)
@pytest.mark.integration
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


@pytest.mark.unit
def test_accessor_methods_delegate_to_functional_module_apis():
    from bynat.cleaning.enrich import _translate

    dataframe_module = importlib.import_module("bynat._accessors.dataframe")

    expected = {
        "drop_by_substring": _columns.drop_by_substring,
        "drop_CLASS_columns": _columns.drop_CLASS_columns,
        "rename_by_substring": _columns.rename_by_substring,
        "rename_all_DOTS": _columns.rename_all_DOTS,
        "reorder_columns": _columns.reorder_columns,
        "melt_transform_pivot": _columns.melt_transform_pivot,
        "move_column": _columns.move_column,
        "align_lat_lng": _columns.align_lat_lng,
        "split_list_objects": _columns.split_list_objects,
        "extract_keywords": _text.extract_keywords,
        "truncate_after_substring": _text.truncate_after_substring,
        "categorize_by_reference": _text.categorize_by_reference,
        "handle_outliers": _stats.handle_outliers,
        "drop_outliers": _stats.drop_outliers,
        "fill_missing": _stats.fill_missing,
        "fill_missing_from": _stats.fill_missing_from,
        "get_hierarchical_stats": _stats.get_hierarchical_stats,
        "impute_by_language": _translate.impute_by_language,
        "translate_conditional_column": _translate.translate_conditional_column,
        "translate_categorical_column": _translate.translate_categorical_column,
        "fill_missing_coordinates": _geocode.fill_missing_coordinates,
        "convert_to_usd": _currency.convert_to_usd,
        "extract_entities_nlp": _nlp.extract_entities_nlp,
        "save_to_json": dataframe_module._save_to_json,
        "save_to_sql": dataframe_module._save_to_sql,
    }

    for name, implementation in expected.items():
        assert getattr(BynatAccessor, name).__wrapped__ is implementation, name


@pytest.mark.unit
def test_accessor_profile_owns_its_interface_and_calls_the_shared_core():
    dataframe_module = importlib.import_module("bynat._accessors.dataframe")
    builders = importlib.import_module("bynat.profiling._builders")

    assert BynatAccessor.profile.__wrapped__ is dataframe_module.profile
    assert dataframe_module.build_report is builders.build_report
    assert not hasattr(dataframe_module, "_profiling_profile")
    assert not hasattr(dataframe_module, "is_basedata_type")
