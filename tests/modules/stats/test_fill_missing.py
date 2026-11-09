"""fill_missing contracts: strategy normalization, min_samples, non-numeric targets."""

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData, stats

pytestmark = pytest.mark.unit


INVALID_MIN_SAMPLES = [
    pytest.param(True, id="bool-true"),
    pytest.param(False, id="bool-false"),
    pytest.param(0, id="zero"),
    pytest.param(-1, id="negative"),
    pytest.param(2.5, id="float"),
    pytest.param("5", id="string"),
]




@pytest.mark.parametrize(
    ("min_samples", "expected_last"),
    [pytest.param(2, 2.0, id="boundary_included"), pytest.param(3, np.nan, id="boundary_excluded")],
)
def test_fill_missing_min_samples_counts_only_non_null_observations(min_samples, expected_last):
    frame = pd.DataFrame({"g": ["a", "a", "a"], "v": [1.0, 3.0, None]})
    before = frame.copy(deep=True)

    result = frame.bynat.fill_missing("v", hierarchy_cols=["g"], min_samples=min_samples)

    expected = pd.Series([1.0, 3.0, expected_last], name="v", index=frame.index)
    pd.testing.assert_series_equal(result["v"], expected)
    pd.testing.assert_frame_equal(frame, before)


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


@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_fill_missing_and_fill_missing_from_reject_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None]})
    reference = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})

    with pytest.raises(ValueError, match="min_samples must be an integer"):
        stats.fill_missing(frame, "v", hierarchy_cols="g", min_samples=value)

    with pytest.raises(ValueError, match="min_samples must be an integer"):
        stats.fill_missing_from(frame, reference, "v", hierarchy_cols="g", min_samples=value)




def test_fill_missing_non_numeric_target_with_hierarchy_raises_typeerror():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})

    with pytest.raises(TypeError):
        stats.fill_missing(frame, "label", strategy="median", hierarchy_cols=["g"])


def test_fill_missing_non_numeric_target_with_fallback_global_raises_typeerror():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})

    with pytest.raises(TypeError):
        stats.fill_missing(frame, "label", strategy="median", fallback_global=True)


def test_fill_missing_non_numeric_target_without_hierarchy_is_unchanged():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})
    original = frame.copy(deep=True)

    result = stats.fill_missing(frame, "label", strategy="median")

    pd.testing.assert_frame_equal(result, original)


def test_fill_missing_non_numeric_all_nan_target_does_not_raise():
    frame = pd.DataFrame({"g": ["a", "a"], "label": [None, None]})

    result = stats.fill_missing(frame, "label", strategy="median", hierarchy_cols=["g"])

    assert result["label"].isna().all()




def test_fill_missing_skips_missing_targets_and_fills_valid_ones():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None], "w": [None, None]})
    original = frame.copy(deep=True)

    result = stats.fill_missing(frame, "v", "missing", hierarchy_cols=["g"])

    assert result["v"].tolist() == [1.0, 1.0]
    assert "missing" not in result.columns
    pd.testing.assert_frame_equal(frame, original)




@pytest.mark.parametrize(
    "index",
    [
        pd.Index(range(10, 16), name="row_id"),
        pd.MultiIndex.from_tuples([("k", i) for i in range(6)], names=["k", "i"]),
        pd.Index([0, 0, 1, 1, 2, 2]),
    ],
)
def test_hierarchy_methods_support_named_multi_and_duplicate_indexes(tmp_path, index):
    frame = BaseData(
        {"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]},
        index=index,
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    handled = frame.handle_outliers("v", hierarchy_cols=["g"])
    dropped = frame.drop_outliers("v", hierarchy_cols=["g"])

    assert handled["v"].isna().tolist() == [False] * 5 + [True]
    pd.testing.assert_index_equal(handled.index, index)
    assert dropped["v"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]
    pd.testing.assert_index_equal(dropped.index, index[:5])
    pd.testing.assert_frame_equal(frame, original)

    in_place = frame.copy()
    assert in_place.drop_outliers("v", hierarchy_cols=["g"], inplace=True) is None
    pd.testing.assert_frame_equal(in_place, dropped)

    modes = BaseData(
        {"g": ["a"] * 6, "c": ["x", "x", "y", None, "x", None]},
        index=index,
        cache_dir=tmp_path,
    ).fill_missing("c", strategy="mode", hierarchy_cols=["g"])

    assert modes["c"].tolist() == ["x", "x", "y", "x", "x", "x"]
    pd.testing.assert_index_equal(modes.index, index)


def test_fill_missing_rejects_unknown_strategy(tmp_path):
    frame = BaseData({"g": ["a", "a"], "v": [1.0, None]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid strategy 'sum'"):
        frame.fill_missing("v", strategy="sum", hierarchy_cols="g")


def test_fill_missing_min_samples_and_fallback_global_reproduction():
    from bynat.cleaning import stats

    df1 = pd.DataFrame({
        "country": ["EG", "EG", "EG", "US", "US", "DE"],
        "salary":  [10.0, 14.0, np.nan, 70.0, 90.0, np.nan],
    })
    df1_before = df1.copy(deep=True)

    default_res = stats.fill_missing(df1, "salary", strategy="median", hierarchy_cols=["country"])
    assert pd.isna(default_res.loc[5, "salary"])
    assert default_res.loc[2, "salary"] == 12.0

    fallback_res = stats.fill_missing(
        df1, "salary", strategy="median", hierarchy_cols=["country"], fallback_global=True
    )
    assert fallback_res.loc[2, "salary"] == 12.0
    assert fallback_res.loc[5, "salary"] == 42.0

    df2 = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary":  [10.0, np.nan, 1000.0, np.nan],
    })
    df2_before = df2.copy(deep=True)
    res_min1 = stats.fill_missing(df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=1)
    assert res_min1.loc[1, "salary"] == 10.0
    assert res_min1.loc[3, "salary"] == 1000.0

    res_min2 = stats.fill_missing(df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=2)
    assert pd.isna(res_min2.loc[1, "salary"])
    assert pd.isna(res_min2.loc[3, "salary"])

    res_min2_fallback = stats.fill_missing(
        df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=2, fallback_global=True
    )
    assert res_min2_fallback.loc[1, "salary"] == 505.0
    assert res_min2_fallback.loc[3, "salary"] == 505.0

    res_none_default = stats.fill_missing(df1, "salary", strategy="median")
    assert pd.isna(res_none_default.loc[2, "salary"])
    assert pd.isna(res_none_default.loc[5, "salary"])

    res_none_global = stats.fill_missing(df1, "salary", strategy="median", fallback_global=True)
    assert res_none_global.loc[2, "salary"] == 42.0
    assert res_none_global.loc[5, "salary"] == 42.0

    pd.testing.assert_frame_equal(df1, df1_before)
    pd.testing.assert_frame_equal(df2, df2_before)


def test_fill_missing_validates_min_samples(tmp_path):
    frame = BaseData({"g": ["a", "a"], "v": [1.0, None]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=0)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=-3)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=True)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples="2")


def test_fill_missing_hierarchical_fallthrough_multi_level():
    df = pd.DataFrame({
        "country": ["EG", "EG", "EG", "EG", "US", "US"],
        "city":    ["Cairo", "Cairo", "Alex", "Alex", "NYC", "NYC"],
        "salary":  [100.0, np.nan, 20.0, 40.0, 500.0, np.nan],
    })
    original = df.copy(deep=True)

    res_no_global = df.bynat.fill_missing(
        "salary", strategy="median", hierarchy_cols=["country", "city"], min_samples=2
    )
    assert res_no_global.loc[1, "salary"] == 40.0
    assert pd.isna(res_no_global.loc[5, "salary"])

    res_global = df.bynat.fill_missing(
        "salary", strategy="median", hierarchy_cols=["country", "city"], min_samples=2, fallback_global=True
    )
    assert res_global.loc[1, "salary"] == 40.0
    assert res_global.loc[5, "salary"] == 70.0

    pd.testing.assert_frame_equal(df, original)


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


def test_basedata_fill_missing_helper(tmp_path):
    frame = BaseData(
        {
            "id": [1, 2],
            "description": ["Blue shoes", "red shirt"],
            "items": [["A", "B"], ["C", "D"]],
            "group": ["x", "x"],
            "score": [1, None],
            "left": ["a", "b"],
            "right": ["c", "d"],
        },
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    imputed = frame.fill_missing("score", hierarchy_cols="group")
    assert imputed["score"].tolist() == [1.0, 1.0]

    pd.testing.assert_frame_equal(frame, original)


def test_fill_missing_mode_all_nan_col():
    df = pd.DataFrame({"g": ["a", "b"], "v": [np.nan, np.nan]})
    result = stats.fill_missing(df, "v", strategy="mode", hierarchy_cols=["g"])
    pd.testing.assert_frame_equal(result, df)

