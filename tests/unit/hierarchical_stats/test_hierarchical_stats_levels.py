import pandas as pd

from bynat.cleaning import BaseData
from tests.shared.constants import OUTPUT_COLUMNS


def test_get_hierarchical_stats_returns_median_levels_and_preserves_source(tmp_path):
    frame = BaseData(
        {
            "region": ["East", "East", "East", "West", None, None],
            "department": ["A", "A", "B", "A", "A", None],
            "score": [1, None, 5, 3, None, 7],
        },
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)
    original_columns = frame.columns.copy()
    original_index = frame.index.copy()

    result = frame.get_hierarchical_stats(
        "score", strategy="median", hierarchy_cols=["region", "department"]
    )

    assert type(result) is BaseData
    assert list(result.columns) == OUTPUT_COLUMNS
    assert result["target_column"].unique().tolist() == ["score"]
    assert result["strategy"].unique().tolist() == ["median"]
    assert result["hierarchy_level"].tolist() == [2, 2, 2, 2, 2, 1, 1, 1]
    assert result["hierarchy_columns"].tolist() == [
        ("region", "department"),
        ("region", "department"),
        ("region", "department"),
        ("region", "department"),
        ("region", "department"),
        ("region",),
        ("region",),
        ("region",),
    ]
    assert result["group_key"].tolist()[:3] == [
        ("East", "A"),
        ("East", "B"),
        ("West", "A"),
    ]
    assert pd.isna(result.iloc[3]["group_key"][0])
    assert result.iloc[3]["group_key"][1] == "A"
    assert pd.isna(result.iloc[4]["group_key"][0])
    assert pd.isna(result.iloc[4]["group_key"][1])
    assert result["statistic"].tolist()[:3] == [1.0, 5.0, 3.0]
    assert pd.isna(result.iloc[3]["statistic"])
    assert result.iloc[4]["statistic"] == 7.0
    assert result["statistic"].tolist()[5:] == [3.0, 3.0, 7.0]
    pd.testing.assert_frame_equal(frame, original)
    pd.testing.assert_index_equal(frame.columns, original_columns)
    pd.testing.assert_index_equal(frame.index, original_index)


def test_get_hierarchical_stats_supports_mean_multiple_targets_and_string_hierarchy(tmp_path):
    frame = BaseData(
        {
            "group": ["a", "a", "b"],
            "first": [1, None, 5],
            "second": [10, 20, None],
        },
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats(
        "first", "second", strategy="mean", hierarchy_cols="group"
    )

    assert list(result.columns) == OUTPUT_COLUMNS
    assert result["hierarchy_level"].tolist() == [1, 1, 1, 1]
    assert result["hierarchy_columns"].tolist() == [("group",)] * 4
    assert result["group_key"].tolist() == [("a",), ("b",), ("a",), ("b",)]
    assert result["target_column"].tolist() == ["first", "first", "second", "second"]
    assert result["strategy"].tolist() == ["mean"] * 4
    assert result["statistic"].tolist()[:3] == [1.0, 5.0, 15.0]
    assert pd.isna(result.iloc[3]["statistic"])


def test_get_hierarchical_stats_handles_null_values_and_empty_groups(tmp_path):
    frame = BaseData(
        {
            "group": ["filled", "empty", None],
            "value": [4, None, None],
        },
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats("value", hierarchy_cols="group")

    assert result["group_key"].tolist()[:2] == [("empty",), ("filled",)]
    assert pd.isna(result.iloc[2]["group_key"][0])
    assert pd.isna(result.iloc[0]["statistic"])
    assert result.iloc[1]["statistic"] == 4.0
    assert pd.isna(result.iloc[2]["statistic"])


def test_get_hierarchical_stats_supports_ordered_multiple_strategies(tmp_path):
    frame = BaseData(
        {
            "group": ["a", "a", "b", "b"],
            "first": [1, 3, 5, 7],
            "second": [10, 10, 20, 30],
        },
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats(
        "first",
        "second",
        strategy=["mode", "mean", "median"],
        hierarchy_cols="group",
    )

    assert list(result.columns) == OUTPUT_COLUMNS
    assert result["strategy"].tolist() == [
        "mode",
        "mode",
        "mode",
        "mode",
        "mean",
        "mean",
        "mean",
        "mean",
        "median",
        "median",
        "median",
        "median",
    ]
    assert result["target_column"].tolist() == [
        "first",
        "first",
        "second",
        "second",
        "first",
        "first",
        "second",
        "second",
        "first",
        "first",
        "second",
        "second",
    ]
    assert not result.duplicated(
        subset=["hierarchy_level", "hierarchy_columns", "group_key", "target_column", "strategy"]
    ).any()
