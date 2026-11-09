"""Validation, BaseData, inplace, and edge contracts for fill_missing_from."""

import warnings

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData, stats
from tests.shared.constants import OUTPUT_COLUMNS


def test_fill_missing_from_validation():
    """Test validation of dataset, match_cols, hierarchy, types, and parameters."""
    valid_train = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [np.nan, 2.0]})

    with pytest.raises(ValueError, match="Reference dataset is required and cannot be None"):
        target.bynat.fill_missing_from(None, "v")

    with pytest.raises(TypeError, match="Reference dataset must be a pandas DataFrame"):
        target.bynat.fill_missing_from([1, 2, 3], "v")

    with pytest.raises(ValueError, match="Reference dataset cannot be empty"):
        target.bynat.fill_missing_from(pd.DataFrame(), "v")

    dup_train = pd.DataFrame([[1, 2]], columns=["v", "v"])
    with pytest.raises(ValueError, match="Reference dataset contains duplicate column names"):
        target.bynat.fill_missing_from(dup_train, "v")

    dup_target = pd.DataFrame([[1, 2]], columns=["v", "v"])
    with pytest.raises(ValueError, match="Target dataframe contains duplicate column names"):
        stats.fill_missing_from(dup_target, valid_train, "v")

    with pytest.raises(TypeError, match="match_cols must be a dictionary"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols="invalid")

    with pytest.raises(TypeError, match="match_cols keys and values must be strings"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols={1: "v"})

    with pytest.raises(ValueError, match="Target column 'nonexistent' specified in match_cols does not exist"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols={"nonexistent": "v"})

    with pytest.raises(ValueError, match="Reference column 'nonexistent' specified in match_cols does not exist"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols={"v": "nonexistent"})

    missing_ref_col = pd.DataFrame({"other": [1, 2]})
    with pytest.raises(ValueError, match="Reference column 'v' for target 'v' does not exist"):
        target.bynat.fill_missing_from(missing_ref_col, "v")

    with pytest.raises(ValueError, match="Hierarchy column 'missing_h' does not exist in target"):
        target.bynat.fill_missing_from(valid_train, "v", hierarchy_cols=["missing_h"])

    train_no_h = pd.DataFrame({"v": [1.0, 2.0]})
    with pytest.raises(ValueError, match="Hierarchy column 'g' .* does not exist in reference"):
        target.bynat.fill_missing_from(train_no_h, "v", hierarchy_cols=["g"])

    with pytest.raises(ValueError, match="target columns cannot overlap hierarchy columns"):
        target.bynat.fill_missing_from(valid_train, "g", hierarchy_cols=["g"])

    str_train = pd.DataFrame({"v": ["x", "y"]})
    str_target = pd.DataFrame({"v": ["x", None]})
    with pytest.raises(TypeError, match="must have a numeric dtype for strategy 'median'"):
        str_target.bynat.fill_missing_from(str_train, "v", strategy="median")

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        target.bynat.fill_missing_from(valid_train, "v", min_samples=0)

    with pytest.raises(ValueError, match="Invalid strategy 'unknown'"):
        target.bynat.fill_missing_from(valid_train, "v", strategy="unknown")


def test_fill_missing_from_basedata_and_contracts(tmp_path):
    """Test BaseData wrapper, inplace mutation, and get_hierarchical_stats contract."""
    train = BaseData({"g": ["a", "a", "b"], "v": [10.0, 20.0, 30.0]}, cache_dir=tmp_path)
    target = BaseData({"g": ["a", "b", "c"], "v": [np.nan, np.nan, np.nan]}, cache_dir=tmp_path)
    train_before = train.copy(deep=True)
    target_before = target.copy(deep=True)

    res, stats_df = target.fill_missing_from(
        train, "v", hierarchy_cols=["g"], strategy="mean", get_hierarchical_stats=True, fallback_global=True
    )
    assert isinstance(res, BaseData)
    assert isinstance(stats_df, pd.DataFrame)
    assert res["v"].tolist() == [15.0, 30.0, 20.0]
    assert "strategy" in stats_df.columns
    assert "statistic" in stats_df.columns
    assert set(stats_df["statistic"].tolist()) == {15.0, 30.0}
    pd.testing.assert_frame_equal(target, target_before)
    pd.testing.assert_frame_equal(train, train_before)

    mutating = target.copy()
    ret = mutating.fill_missing_from(train, "v", hierarchy_cols=["g"], inplace=True)
    assert ret is None
    assert mutating["v"].tolist()[:2] == [15.0, 30.0]
    assert pd.isna(mutating["v"].iloc[2])


def test_fill_missing_from_non_numeric_target_with_numeric_strategy_raises():
    train = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "a"], "v": ["x", None]})

    with pytest.raises(TypeError, match="numeric dtype"):
        target.bynat.fill_missing_from(train, "v", strategy="median", hierarchy_cols=["g"])


def test_fill_missing_from_inplace_with_stats_returns_stats_and_mutates(tmp_path):
    train = BaseData({"g": ["a", "a", "b"], "v": [10.0, 20.0, 30.0]}, cache_dir=tmp_path)
    frame = BaseData({"g": ["a", "b"], "v": [None, None]}, cache_dir=tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        stats_result = frame.fill_missing_from(
            train,
            "v",
            hierarchy_cols=["g"],
            get_hierarchical_stats=True,
            inplace=True,
        )

    assert type(stats_result) is BaseData
    assert list(stats_result.columns) == OUTPUT_COLUMNS
    assert frame["v"].tolist() == [15.0, 30.0]


def test_fill_missing_from_non_numeric_all_nan_target_is_exempt():
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": pd.Series([None, None], dtype=object)})

    result = stats.fill_missing_from(
        target, reference, "v", strategy="median", hierarchy_cols=["g"]
    )

    assert result["v"].tolist() == [1.0, 2.0]


def test_fill_missing_from_skips_missing_targets_and_fills_valid_ones():
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [None, None]})

    result = stats.fill_missing_from(target, reference, "v", "missing", hierarchy_cols=["g"])

    assert result["v"].tolist() == [1.0, 2.0]
    assert "missing" not in result.columns


def test_fill_missing_from_duplicate_targets_are_deduplicated():
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [None, None]})

    unique = stats.fill_missing_from(target, reference, "v", hierarchy_cols=["g"])
    duplicated = stats.fill_missing_from(target, reference, "v", "v", hierarchy_cols=["g"])

    pd.testing.assert_frame_equal(duplicated, unique)


@pytest.mark.parametrize(
    "match_cols",
    [
        pytest.param({"": "v"}, id="empty-key"),
        pytest.param({"v": ""}, id="empty-value"),
    ],
)
def test_fill_missing_from_rejects_empty_match_cols_strings(match_cols):
    reference = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [None, None]})

    with pytest.raises(ValueError, match="cannot be empty strings"):
        stats.fill_missing_from(target, reference, "v", match_cols=match_cols)
