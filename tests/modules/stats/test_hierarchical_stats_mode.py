import pandas as pd
import pytest

from bynat.cleaning import BaseData
from tests.shared.constants import OUTPUT_COLUMNS


def test_get_hierarchical_stats_mode_matches_tie_breaking_and_normalizes_mod(tmp_path):
    frame = BaseData(
        {
            "group": ["x", "x", "x", "y", "y", None],
            "label": ["b", "a", None, "c", "c", "z"],
        },
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats("label", strategy="mod", hierarchy_cols="group")
    direct_mode = frame.get_hierarchical_stats(
        "label", strategy="mode", hierarchy_cols="group"
    )

    assert result["strategy"].tolist() == ["mode"] * 3
    pd.testing.assert_frame_equal(direct_mode, result)
    assert result["group_key"].tolist()[:2] == [("x",), ("y",)]
    assert pd.isna(result.iloc[2]["group_key"][0])
    assert result["statistic"].tolist() == ["a", "c", "z"]


def test_get_hierarchical_stats_mode_returns_all_targets_at_every_hierarchy_level(
    tmp_path,
):
    frame = BaseData(
        {
            "region": ["East", "East", "West", "West"],
            "department": ["A", "B", "A", "B"],
            "first": ["x", "x", "y", "y"],
            "second": ["m", "m", "n", "n"],
        },
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats(
        "first",
        "second",
        strategy="mode",
        hierarchy_cols=["region", "department"],
    )

    assert result["target_column"].tolist() == ["first"] * 6 + ["second"] * 6
    assert result["hierarchy_level"].tolist() == [2, 2, 2, 2, 1, 1] * 2
    assert result["hierarchy_columns"].tolist() == [
        ("region", "department"),
        ("region", "department"),
        ("region", "department"),
        ("region", "department"),
        ("region",),
        ("region",),
    ] * 2
    assert result["group_key"].tolist() == [
        ("East", "A"),
        ("East", "B"),
        ("West", "A"),
        ("West", "B"),
        ("East",),
        ("West",),
    ] * 2
    assert result["strategy"].tolist() == ["mode"] * 12
    assert result["statistic"].tolist() == [
        "x",
        "x",
        "y",
        "y",
        "x",
        "y",
        "m",
        "m",
        "n",
        "n",
        "m",
        "n",
    ]


def test_get_hierarchical_stats_mode_allows_hierarchy_column_named_count(tmp_path):
    frame = BaseData(
        {
            "_count": ["a", "a", "b", "b"],
            "label": ["x", "x", "y", None],
        },
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats(
        "label", strategy="mode", hierarchy_cols="_count"
    )

    assert result["group_key"].tolist() == [("a",), ("b",)]
    assert result["statistic"].tolist() == ["x", "y"]


def test_get_hierarchical_stats_mode_has_no_melt_and_keeps_null_groups(tmp_path, monkeypatch):
    frame = BaseData(
        {
            "group": ["a"] * 100 + ["b"] * 100 + [None],
            "label": ["x"] * 60 + ["y"] * 40 + ["z"] * 100 + [None],
        },
        cache_dir=tmp_path,
    )

    def unexpected_melt(*args, **kwargs):
        pytest.fail("mode aggregation must not materialize a melt intermediate")

    monkeypatch.setattr(pd.DataFrame, "melt", unexpected_melt)
    result = frame.get_hierarchical_stats("label", strategy="mode", hierarchy_cols="group")

    assert result["group_key"].tolist() == [("a",), ("b",)]
    assert result["statistic"].tolist() == ["x", "z"]


def test_get_hierarchical_stats_mode_empty_valid_values_returns_empty_rows(tmp_path):
    frame = BaseData(
        {"group": ["a", "b", None], "label": [None, None, None]},
        cache_dir=tmp_path,
    )

    result = frame.get_hierarchical_stats("label", strategy="mode", hierarchy_cols="group")

    assert result.empty
    assert list(result.columns) == OUTPUT_COLUMNS
