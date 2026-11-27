import warnings

import numpy as np
import pandas as pd

from bynat.cleaning import BaseData
from tests.shared.constants import OUTPUT_COLUMNS


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
