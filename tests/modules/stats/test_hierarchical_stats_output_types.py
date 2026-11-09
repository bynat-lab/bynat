"""Hierarchical statistics output type contracts: DataFrame, dict, BaseData family, and subclass preservation."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData, CsvFile, JsonFile
from tests.shared.constants import OUTPUT_COLUMNS


def test_get_hierarchical_stats_supports_explicit_dataframe_and_dict_outputs(tmp_path):
    frame = BaseData(
        {
            "region": ["East", "East", "West"],
            "score": [1, 3, 5],
        },
        cache_dir=tmp_path,
    )

    dataframe_result = frame.get_hierarchical_stats(
        "score",
        strategy="mean",
        hierarchy_cols="region",
        output_type=pd.DataFrame,
    )
    dict_result = frame.get_hierarchical_stats(
        "score",
        strategy="mean",
        hierarchy_cols="region",
        output_type=dict,
    )

    assert type(dataframe_result) is pd.DataFrame
    assert list(dataframe_result.columns) == OUTPUT_COLUMNS
    assert list(dict_result) == OUTPUT_COLUMNS
    assert dict_result["hierarchy_level"] == [1, 1]
    assert dict_result["hierarchy_columns"] == [("region",), ("region",)]
    assert dict_result["group_key"] == [("East",), ("West",)]
    assert dict_result["target_column"] == ["score", "score"]
    assert dict_result["strategy"] == ["mean", "mean"]
    assert dict_result["statistic"] == [2.0, 5.0]


@pytest.mark.parametrize("output_type", [JsonFile, CsvFile])
def test_get_hierarchical_stats_supports_explicit_basedata_family_outputs(
    tmp_path, output_type
):
    frame = BaseData(
        {"group": ["a", "b"], "value": [1, 2]},
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats(
        "value",
        hierarchy_cols="group",
        output_type=output_type,
    )

    assert type(result) is output_type
    assert list(result.columns) == OUTPUT_COLUMNS
    assert result["group_key"].tolist() == [("a",), ("b",)]


def test_get_hierarchical_stats_preserves_custom_basedata_subclass_by_default(tmp_path):
    class CustomBaseData(BaseData):
        pass

    frame = CustomBaseData(
        {"group": ["a"], "value": [1]},
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats("value", hierarchy_cols="group")

    assert type(result) is CustomBaseData
    assert list(result.columns) == OUTPUT_COLUMNS


def test_get_hierarchical_stats_returns_requested_type_for_empty_results(tmp_path):
    frame = BaseData({"group": ["a"], "value": [1]}, cache_dir=tmp_path)

    dataframe_result = frame.get_hierarchical_stats(
        "missing", hierarchy_cols="group", output_type=pd.DataFrame
    )
    dict_result = frame.get_hierarchical_stats(
        "missing", hierarchy_cols="group", output_type=dict
    )

    assert type(dataframe_result) is pd.DataFrame
    assert dataframe_result.empty
    assert dict_result == {column: [] for column in OUTPUT_COLUMNS}


def test_get_hierarchical_stats_default_fallback_requires_data_signature(tmp_path):
    class NoDataParameter(BaseData):
        def __init__(self, frame, **kwargs):
            super().__init__(data=frame, **kwargs)

    frame = NoDataParameter(
        {"group": ["a", "a", "b"], "value": [1, None, 3]},
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats("value", hierarchy_cols="group")

    assert type(result) is pd.DataFrame
    assert result["statistic"].tolist() == [1.0, 3.0]


def test_get_hierarchical_stats_propagates_internal_constructor_errors(tmp_path):
    class ConstructorFailure(BaseData):
        def __init__(self, data=None, *args, **kwargs):
            if isinstance(data, pd.DataFrame):
                raise TypeError("constructor internal failure")
            super().__init__(data=data, *args, **kwargs)

    frame = ConstructorFailure(
        {"group": ["a", "a", "b"], "value": [1, None, 3]},
        cache_dir=tmp_path,
    )

    with pytest.raises(TypeError, match="constructor internal failure"):
        frame.get_hierarchical_stats("value", hierarchy_cols="group")


def test_get_hierarchical_stats_all_output_types_keep_multi_strategy_schema(tmp_path):
    frame = BaseData({"group": ["a", "b"], "value": [1, 2]}, cache_dir=tmp_path)

    for output_type in (pd.DataFrame, dict, BaseData, JsonFile, CsvFile):
        result = frame.get_hierarchical_stats(
            "value",
            strategy=["mean", "median"],
            hierarchy_cols="group",
            output_type=output_type,
        )
        if output_type is dict:
            assert list(result) == OUTPUT_COLUMNS
            assert result["strategy"] == ["mean", "mean", "median", "median"]
        else:
            assert type(result) is output_type
            assert list(result.columns) == OUTPUT_COLUMNS
            assert result["strategy"].tolist() == ["mean", "mean", "median", "median"]


def test_get_hierarchical_stats_falls_back_to_dataframe_for_incompatible_default_subclass(
    tmp_path,
):
    class NoIntermediateConstruction(BaseData):
        def __init__(self, frame, **kwargs):
            super().__init__(data=frame, **kwargs)

    frame = NoIntermediateConstruction(
        {"group": ["a", "a", "b"], "value": [1, None, 3]},
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats("value", hierarchy_cols="group")

    assert type(result) is pd.DataFrame
    assert result["group_key"].tolist() == [("a",), ("b",)]
    assert result["statistic"].tolist() == [1.0, 3.0]
