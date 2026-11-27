import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData


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


@pytest.mark.parametrize(
    "index",
    [
        pytest.param(pd.Index(range(10, 16), name="row_id"), id="named-range-index"),
        pytest.param(
            pd.MultiIndex.from_tuples([("k", i) for i in range(6)], names=["k", "i"]),
            id="named-multi-index",
        ),
        pytest.param(pd.Index([0, 0, 1, 1, 2, 2]), id="duplicate-label-index"),
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
