import pandas as pd
import pytest

from bynat.analytics import Analyzer
from bynat.cleaning.base import BaseData


def test_analytics_contract_constructor_type_errors() -> None:
    for invalid in [None, {"a": [1]}, [1, 2, 3], pd.Series([1, 2, 3])]:
        with pytest.raises(TypeError):
            Analyzer(invalid)  # type: ignore[arg-type]


def test_analytics_contract_defensive_copy() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    analyzer = Analyzer(df)
    pd.testing.assert_frame_equal(analyzer.dataframe, df)

    df.loc[0, "a"] = 999
    assert analyzer.dataframe.loc[0, "a"] == 1


def test_analytics_contract_immutability_across_methods() -> None:
    df = pd.DataFrame({"cat": ["A", "B", "A"], "val": [10, 20, 30], "dt": pd.date_range("2026-01-01", periods=3)})
    analyzer = Analyzer(df)
    original_df = analyzer.dataframe.copy()

    _ = analyzer.get_categorical_distribution("cat", filters={"cat": "A"}, rules=[{"new_col": "doubled", "expression": "y * 2"}])
    _ = analyzer.get_numerical_aggregation("cat", "val", agg_func="mean", filters={"val": {">": 5}}, rules=[{"new_col": "doubled", "expression": "y * 2"}])
    _ = analyzer.get_time_series("dt", time_period="M", num_col="val", agg_func="sum", filters={"val": {">": 5}}, rules=[{"new_col": "doubled", "expression": "y * 2"}])
    _ = analyzer.get_kpi_value("val", agg_func="sum", filters={"cat": "A"})
    _ = analyzer.get_bins("val", bins=2, filters={"val": {">": 5}}, rules=[{"new_col": "doubled", "expression": "y * 2"}])

    pd.testing.assert_frame_equal(analyzer.dataframe, original_df)


def test_analytics_contract_base_data_compatibility() -> None:
    base_df = BaseData({"a": [1, 2, 3], "val": [10, 20, 30]})
    analyzer = Analyzer(pd.DataFrame(base_df))
    assert isinstance(analyzer.dataframe, pd.DataFrame)
    kpi = analyzer.get_kpi_value("val", agg_func="sum")
    assert kpi["data"] == 60


def test_analytics_contract_empty_and_zero_column_dataframes() -> None:
    for df in [pd.DataFrame(), pd.DataFrame(index=[0, 1]), pd.DataFrame({"other": [1, 2]})]:
        analyzer = Analyzer(df)
        assert analyzer.get_categorical_distribution("missing") == {"data": []}
        assert analyzer.get_numerical_aggregation("missing", "other") == {"data": []}
        assert analyzer.get_numerical_aggregation("other", "missing") == {"data": []}
        assert analyzer.get_time_series("missing") == {"data": []}
        assert analyzer.get_kpi_value("missing", agg_func="sum") == {"data": None, "title": "missing"}
        assert analyzer.get_bins("missing", bins=2) == {"data": []}


def test_analytics_contract_output_keys_and_orients() -> None:
    df = pd.DataFrame({"cat": ["A", "B"], "val": [10, 20]})
    analyzer = Analyzer(df)

    res_records = analyzer.get_categorical_distribution("cat", orient="records", title="Cat Title", unit="items")
    assert isinstance(res_records["data"], list)
    assert res_records["title"] == "Cat Title"
    assert res_records["unit"] == "items"

    for orient in ["list", "dict", "index"]:
        res_map = analyzer.get_categorical_distribution("cat", orient=orient)
        assert isinstance(res_map["data"], dict)

    res_split = analyzer.get_categorical_distribution("cat", orient="split")
    assert isinstance(res_split["data"], dict)
    assert set(res_split["data"].keys()) == {"index", "columns", "data"}

    kpi = analyzer.get_kpi_value("val", agg_func="sum", title="Total Val", subtitle="USD")
    assert kpi == {"data": 30, "title": "Total Val", "subtitle": "USD"}
