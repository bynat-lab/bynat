import numpy as np
import pandas as pd

from bynat.cleaning import _stats


def test_fill_missing_uppercase_strategy_matches_lowercase():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None]})
    before = frame.copy(deep=True)

    upper = frame.bynat.fill_missing("v", strategy="MEDIAN", hierarchy_cols=["g"])
    lower = frame.bynat.fill_missing("v", strategy="median", hierarchy_cols=["g"])

    pd.testing.assert_frame_equal(upper, lower)
    assert upper["v"].tolist() == [1.0, 1.0]
    pd.testing.assert_frame_equal(frame, before)


def test_fill_missing_without_missing_values_returns_an_independent_copy():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    before = frame.copy(deep=True)

    result = frame.bynat.fill_missing("v", hierarchy_cols=["g"])

    assert result is not frame
    pd.testing.assert_frame_equal(result, frame)
    pd.testing.assert_frame_equal(frame, before)


def test_fill_missing_min_samples_and_fallback_global_reproduction():
    from bynat.cleaning import _stats

    df1 = pd.DataFrame({
        "country": ["EG", "EG", "EG", "US", "US", "DE"],
        "salary":  [10.0, 14.0, np.nan, 70.0, 90.0, np.nan],
    })
    df1_before = df1.copy(deep=True)

    default_res = _stats.fill_missing(df1, "salary", strategy="median", hierarchy_cols=["country"])
    assert pd.isna(default_res.loc[5, "salary"])
    assert default_res.loc[2, "salary"] == 12.0

    fallback_res = _stats.fill_missing(
        df1, "salary", strategy="median", hierarchy_cols=["country"], fallback_global=True
    )
    assert fallback_res.loc[2, "salary"] == 12.0
    assert fallback_res.loc[5, "salary"] == 42.0

    df2 = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary":  [10.0, np.nan, 1000.0, np.nan],
    })
    df2_before = df2.copy(deep=True)
    res_min1 = _stats.fill_missing(df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=1)
    assert res_min1.loc[1, "salary"] == 10.0
    assert res_min1.loc[3, "salary"] == 1000.0

    res_min2 = _stats.fill_missing(df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=2)
    assert pd.isna(res_min2.loc[1, "salary"])
    assert pd.isna(res_min2.loc[3, "salary"])

    res_min2_fallback = _stats.fill_missing(
        df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=2, fallback_global=True
    )
    assert res_min2_fallback.loc[1, "salary"] == 505.0
    assert res_min2_fallback.loc[3, "salary"] == 505.0

    res_none_default = _stats.fill_missing(df1, "salary", strategy="median")
    assert pd.isna(res_none_default.loc[2, "salary"])
    assert pd.isna(res_none_default.loc[5, "salary"])

    res_none_global = _stats.fill_missing(df1, "salary", strategy="median", fallback_global=True)
    assert res_none_global.loc[2, "salary"] == 42.0
    assert res_none_global.loc[5, "salary"] == 42.0

    pd.testing.assert_frame_equal(df1, df1_before)
    pd.testing.assert_frame_equal(df2, df2_before)


def test_fill_missing_all_strategies_with_fallbacks():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "num":   [10.0, np.nan, 50.0, np.nan],
        "cat":   ["x", None, "y", None],
    })
    original = df.copy(deep=True)

    res_mean = df.bynat.fill_missing(
        "num", strategy="mean", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res_mean["num"].tolist() == [10.0, 30.0, 50.0, 30.0]

    res_mode = df.bynat.fill_missing(
        "cat", strategy="mode", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res_mode["cat"].tolist() == ["x", "x", "y", "x"]

    res_mod = df.bynat.fill_missing(
        "cat", strategy="mod", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res_mod["cat"].tolist() == ["x", "x", "y", "x"]

    pd.testing.assert_frame_equal(df, original)


def test_fill_missing_all_nan_column():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "val":   [np.nan, np.nan, np.nan, np.nan],
    })
    original = df.copy(deep=True)
    res = df.bynat.fill_missing(
        "val", strategy="median", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res["val"].isna().all()
    pd.testing.assert_frame_equal(df, original)


def test_fill_missing_mode_all_nan_col():
    df = pd.DataFrame({"g": ["a", "b"], "v": [np.nan, np.nan]})
    result = _stats.fill_missing(df, "v", strategy="mode", hierarchy_cols=["g"])
    pd.testing.assert_frame_equal(result, df)
