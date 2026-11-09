"""Hierarchical statistics validation contracts: invalid output types, target/hierarchy overlap, and strategy validation."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData, stats


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
