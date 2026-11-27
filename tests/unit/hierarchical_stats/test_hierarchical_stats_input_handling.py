import pandas as pd
import pytest

from bynat.cleaning import BaseData, _stats
from tests.shared.constants import OUTPUT_COLUMNS


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


def test_get_hierarchical_stats_non_numeric_target_mode_is_allowed():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", "y", "z"]})

    result = _stats.get_hierarchical_stats(frame, "label", strategy="mode", hierarchy_cols=["g"])

    assert result["statistic"].tolist() == ["x", "z"]


def test_get_hierarchical_stats_skips_missing_targets():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 3.0]})

    result = _stats.get_hierarchical_stats(frame, "v", "missing", hierarchy_cols=["g"])

    assert result["target_column"].unique().tolist() == ["v"]
