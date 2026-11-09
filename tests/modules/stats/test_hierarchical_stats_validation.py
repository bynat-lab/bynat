"""Hierarchical statistics validation contracts: invalid output types, target/hierarchy overlap, and strategy validation."""

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData, stats

pytestmark = pytest.mark.unit



def test_get_hierarchical_stats_rejects_invalid_output_type_before_aggregation(tmp_path):
    frame = BaseData({"group": ["a"], "value": [1]}, cache_dir=tmp_path)

    with pytest.raises(TypeError, match="output_type"):
        frame.get_hierarchical_stats(
            "missing",
            hierarchy_cols="group",
            output_type="records",
        )


@pytest.mark.parametrize("strategy", ["median", "mode"])
def test_get_hierarchical_stats_rejects_target_hierarchy_overlap_before_aggregation(
    monkeypatch, tmp_path, strategy
):
    frame = BaseData(
        {"group": ["a", "a"], "value": [1, 2]},
        cache_dir=tmp_path,
    )

    def unexpected_aggregation(*args, **kwargs):
        pytest.fail("aggregation should not run before input validation")

    monkeypatch.setattr(pd.DataFrame, "groupby", unexpected_aggregation)
    monkeypatch.setattr(pd.DataFrame, "melt", unexpected_aggregation)

    with pytest.raises(
        ValueError, match="target columns cannot overlap hierarchy columns"
    ):
        frame.get_hierarchical_stats(
            "group", strategy=strategy, hierarchy_cols=["group"]
        )


def test_get_hierarchical_stats_rejects_non_string_strategy_values_before_aggregation(
    monkeypatch, tmp_path
):
    frame = BaseData({"group": ["a"], "value": [1]}, cache_dir=tmp_path)

    def unexpected_aggregation(*args, **kwargs):
        pytest.fail("aggregation should not run before input validation")

    monkeypatch.setattr(pd.DataFrame, "groupby", unexpected_aggregation)
    monkeypatch.setattr(pd.DataFrame, "melt", unexpected_aggregation)

    with pytest.raises(TypeError, match="strategy must be a string or an iterable"):
        frame.get_hierarchical_stats("value", strategy=["mean", 1], hierarchy_cols="group")


@pytest.mark.parametrize("strategy", ["median", "mean"])
def test_get_hierarchical_stats_non_numeric_target_raises_typeerror(strategy):
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", "y", "z"]})

    with pytest.raises(TypeError):
        stats.get_hierarchical_stats(frame, "label", strategy=strategy, hierarchy_cols=["g"])


def test_get_hierarchical_stats_rejects_non_iterable_strategy():
    frame = pd.DataFrame({"g": ["a"], "v": [1.0]})

    with pytest.raises(TypeError, match="strategy must be a string or an iterable"):
        stats.get_hierarchical_stats(frame, "v", strategy=5, hierarchy_cols=["g"])


def test_get_hierarchical_stats_rejects_empty_strategy_iterable():
    frame = pd.DataFrame({"g": ["a"], "v": [1.0]})

    with pytest.raises(ValueError, match="at least one strategy"):
        stats.get_hierarchical_stats(frame, "v", strategy=[], hierarchy_cols=["g"])


def test_get_hierarchical_stats_rejects_unknown_strategy():
    frame = pd.DataFrame({"g": ["a"], "v": [1.0]})

    with pytest.raises(ValueError, match="Invalid strategy 'bogus'"):
        stats.get_hierarchical_stats(frame, "v", strategy="bogus", hierarchy_cols=["g"])


def test_get_hierarchical_stats_empty_or_no_hierarchy_explicit_output_type():
    empty_df = pd.DataFrame({"g": pd.Series([], dtype="object"), "v": pd.Series([], dtype="float64")})
    res_df = stats.get_hierarchical_stats(empty_df, "v", hierarchy_cols=["g"], output_type=pd.DataFrame)
    assert isinstance(res_df, pd.DataFrame)
    assert res_df.empty

    res_dict = stats.get_hierarchical_stats(pd.DataFrame({"v": [1.0]}), "v", hierarchy_cols=[], output_type=dict)
    assert isinstance(res_dict, dict)


def test_get_hierarchical_stats_internal_count_column_collision():
    df = pd.DataFrame(
        {
            "g": ["a", "a", "b"],
            "v": ["x", "x", "y"],
            "_hierarchical_stats_count": [10, 20, 30],
        }
    )
    result = stats.get_hierarchical_stats(df, "v", strategy="mode", hierarchy_cols=["g"])
    assert not result.empty


def test_fill_missing_nonexistent_target_with_hierarchical_stats():
    df = pd.DataFrame({"g": ["a", "b"], "v": [1.0, np.nan]})
    result, stat_df = stats.fill_missing(df, "nonexistent", hierarchy_cols=["g"], get_hierarchical_stats=True)
    pd.testing.assert_frame_equal(result, df)
    assert stat_df.empty


def test_fill_missing_mode_all_nan_col():
    df = pd.DataFrame({"g": ["a", "b"], "v": [np.nan, np.nan]})
    result = stats.fill_missing(df, "v", strategy="mode", hierarchy_cols=["g"])
    pd.testing.assert_frame_equal(result, df)


def test_outlier_masks_skips_missing_target_columns():
    df = pd.DataFrame({"g": ["a"] * 10, "val": [10.0] * 10})
    result = stats.handle_outliers(df, "missing_col", hierarchy_cols=["g"])
    pd.testing.assert_frame_equal(result, df)

