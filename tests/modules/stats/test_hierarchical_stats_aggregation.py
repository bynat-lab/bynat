"""Hierarchical statistics aggregation contracts: levels, targets, null handling, and structural integrity."""

import ast
import inspect
import textwrap

import pandas as pd
import pytest

from bynat.cleaning import BaseData, stats
from tests.shared.constants import OUTPUT_COLUMNS

pytestmark = pytest.mark.unit



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


def test_get_hierarchical_stats_returns_fixed_empty_schema_for_invalid_inputs(tmp_path, caplog):
    frame = BaseData({"group": ["a"], "value": [1]}, cache_dir=tmp_path)

    no_target = frame.get_hierarchical_stats("missing", hierarchy_cols="group")
    assert list(no_target.columns) == OUTPUT_COLUMNS
    assert no_target.empty
    assert caplog.messages == ["No valid target columns found for statistics extraction."]

    with pytest.raises(ValueError, match="Invalid strategy 'sum'"):
        frame.get_hierarchical_stats("value", strategy="sum", hierarchy_cols="group")

    no_hierarchy = frame.get_hierarchical_stats("value", hierarchy_cols="missing")
    assert list(no_hierarchy.columns) == OUTPUT_COLUMNS
    assert no_hierarchy.empty

    empty_frame = BaseData({"group": [], "value": []}, cache_dir=tmp_path)
    empty_result = empty_frame.get_hierarchical_stats("value", hierarchy_cols="group")
    assert list(empty_result.columns) == OUTPUT_COLUMNS
    assert empty_result.empty


def test_get_hierarchical_stats_does_not_change_fill_missing_behavior(tmp_path):
    frame = BaseData(
        {
            "region": ["East", "East", "West"],
            "score": [1, None, 3],
        },
        cache_dir=tmp_path,
    )

    extracted = frame.get_hierarchical_stats("score", hierarchy_cols="region")
    imputed = frame.fill_missing("score", hierarchy_cols="region")

    assert extracted["statistic"].tolist() == [1.0, 3.0]
    assert imputed["score"].tolist() == [1.0, 1.0, 3.0]
    assert frame["score"].iloc[0] == 1.0
    assert pd.isna(frame["score"].iloc[1])
    assert frame["score"].iloc[2] == 3.0


def test_get_hierarchical_stats_has_no_nested_functions_or_apply_lambda():
    source = textwrap.dedent(inspect.getsource(stats.get_hierarchical_stats))
    tree = ast.parse(source)

    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
        if node is not tree.body[0]
    )
    assert not any(isinstance(node, ast.Lambda) for node in ast.walk(tree))
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "apply"
        for node in ast.walk(tree)
    )


def test_get_hierarchical_stats_deduplicates_hierarchy_columns_without_adding_levels(
    tmp_path,
):
    frame = BaseData(
        {
            "region": ["East", "East", "West"],
            "department": ["A", "B", "A"],
            "value": [1, 3, 5],
        },
        cache_dir=tmp_path,
    )

    expected = frame.get_hierarchical_stats(
        "value", hierarchy_cols=["region", "department"]
    )
    duplicate_hierarchy = frame.get_hierarchical_stats(
        "value", hierarchy_cols=["region", "region", "department", "region"]
    )

    pd.testing.assert_frame_equal(duplicate_hierarchy, expected)
    assert duplicate_hierarchy["hierarchy_columns"].tolist() == [
        ("region", "department"),
        ("region", "department"),
        ("region", "department"),
        ("region",),
        ("region",),
    ]


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


def test_get_hierarchical_stats_non_numeric_target_mode_is_allowed():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", "y", "z"]})

    result = stats.get_hierarchical_stats(frame, "label", strategy="mode", hierarchy_cols=["g"])

    assert result["statistic"].tolist() == ["x", "z"]


def test_get_hierarchical_stats_skips_missing_targets():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 3.0]})

    result = stats.get_hierarchical_stats(frame, "v", "missing", hierarchy_cols=["g"])

    assert result["target_column"].unique().tolist() == ["v"]
