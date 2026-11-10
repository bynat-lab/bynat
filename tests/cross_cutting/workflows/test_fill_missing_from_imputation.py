"""Core reference-based missing value imputation workflows and contracts."""

import numpy as np
import pandas as pd
import pytest

from tests.shared.constants import OUTPUT_COLUMNS

pytestmark = pytest.mark.integration



def test_fill_missing_from_basic_imputation():
    """Test basic column-wide and 1-level hierarchical reference imputation with mean, median, mode."""
    train = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary": [10.0, 30.0, 100.0, 300.0],
        "category": ["A", "A", "B", "B"],
    })
    test = pd.DataFrame({
        "country": ["EG", "US", "DE"],
        "salary": [np.nan, np.nan, np.nan],
        "category": [None, None, None],
    })
    train_before = train.copy(deep=True)
    test_before = test.copy(deep=True)

    res_median = test.bynat.fill_missing_from(
        train,
        "salary",
        strategy="median",
        hierarchy_cols=["country"],
        fallback_global=True,
    )
    assert res_median["salary"].tolist() == [20.0, 200.0, 65.0]

    res_mean = test.bynat.fill_missing_from(
        train,
        "salary",
        strategy="mean",
        hierarchy_cols=["country"],
        fallback_global=False,
    )
    assert res_mean["salary"].iloc[0] == 20.0
    assert res_mean["salary"].iloc[1] == 200.0
    assert pd.isna(res_mean["salary"].iloc[2])

    res_mode = test.bynat.fill_missing_from(
        train,
        "category",
        strategy="mode",
        hierarchy_cols=["country"],
        fallback_global=True,
    )
    assert res_mode["category"].tolist() == ["A", "B", "A"]

    res_mod = test.bynat.fill_missing_from(
        train,
        "category",
        strategy="mod",
        hierarchy_cols=["country"],
        fallback_global=True,
    )
    assert res_mod["category"].tolist() == ["A", "B", "A"]

    pd.testing.assert_frame_equal(test, test_before)
    pd.testing.assert_frame_equal(train, train_before)


def test_fill_missing_from_hierarchical_fallthrough_and_min_samples():
    """Test multi-level hierarchies and min_samples fallthrough using reference statistics."""
    train = pd.DataFrame({
        "country": ["EG", "EG", "EG", "US", "US"],
        "city": ["Cairo", "Cairo", "Alex", "NYC", "NYC"],
        "score": [10.0, 14.0, 50.0, 100.0, 200.0],
    })

    test = pd.DataFrame({
        "country": ["EG", "EG", "US", "UK"],
        "city": ["Cairo", "Alex", "LA", "London"],
        "score": [np.nan, np.nan, np.nan, np.nan],
    })
    train_before = train.copy(deep=True)
    test_before = test.copy(deep=True)

    res = test.bynat.fill_missing_from(
        train,
        "score",
        strategy="median",
        hierarchy_cols=["country", "city"],
        min_samples=2,
        fallback_global=True,
    )

    assert res["score"].tolist() == [12.0, 14.0, 150.0, 50.0]

    res_no_global = test.bynat.fill_missing_from(
        train,
        "score",
        strategy="median",
        hierarchy_cols=["country", "city"],
        min_samples=2,
        fallback_global=False,
    )
    assert res_no_global["score"].iloc[:3].tolist() == [12.0, 14.0, 150.0]
    assert pd.isna(res_no_global["score"].iloc[3])

    pd.testing.assert_frame_equal(test, test_before)
    pd.testing.assert_frame_equal(train, train_before)


def test_fill_missing_from_match_cols():
    """Test match_cols mapping between target and reference schemas."""
    train = pd.DataFrame({
        "nation": ["EG", "EG", "US", "US"],
        "town": ["Cairo", "Cairo", "NYC", "NYC"],
        "income": [10.0, 20.0, 100.0, 200.0],
    })

    test = pd.DataFrame({
        "country": ["EG", "US", "DE"],
        "city": ["Cairo", "NYC", "Berlin"],
        "salary": [np.nan, np.nan, np.nan],
    })
    train_before = train.copy(deep=True)
    test_before = test.copy(deep=True)

    mapping = {
        "country": "nation",
        "city": "town",
        "salary": "income",
    }

    res = test.bynat.fill_missing_from(
        train,
        "salary",
        match_cols=mapping,
        strategy="median",
        hierarchy_cols=["country", "city"],
        fallback_global=True,
    )

    assert res["salary"].tolist() == [15.0, 150.0, 60.0]

    res_targets = test.bynat.fill_missing_from(
        train,
        targets=["salary"],
        match_cols=mapping,
        strategy="mean",
        hierarchy_cols=["country"],
        fallback_global=True,
    )
    assert res_targets["salary"].tolist() == [15.0, 150.0, 82.5]

    pd.testing.assert_frame_equal(test, test_before)
    pd.testing.assert_frame_equal(train, train_before)


def test_fill_missing_from_edge_cases():
    """Test empty target, no-missing target, all-missing target, and all-null reference column."""
    train = pd.DataFrame({
        "g": ["a", "b"],
        "num": [10.0, 20.0],
        "all_null": [np.nan, np.nan],
    })
    train_before = train.copy(deep=True)

    empty_target = pd.DataFrame(columns=["g", "num"])
    empty_before = empty_target.copy(deep=True)
    res_empty = empty_target.bynat.fill_missing_from(train, "num")
    assert res_empty.empty
    assert list(res_empty.columns) == ["g", "num"]
    pd.testing.assert_frame_equal(empty_target, empty_before)

    clean_target = pd.DataFrame({"g": ["a", "b"], "num": [1.0, 2.0]})
    clean_before = clean_target.copy(deep=True)
    res_clean = clean_target.bynat.fill_missing_from(train, "num")
    assert res_clean["num"].tolist() == [1.0, 2.0]
    pd.testing.assert_frame_equal(clean_target, clean_before)

    all_null_target = pd.DataFrame({"g": ["a", "b"], "num": [np.nan, np.nan]})
    all_null_before = all_null_target.copy(deep=True)
    res_all_null = all_null_target.bynat.fill_missing_from(train, "num", hierarchy_cols=["g"])
    assert res_all_null["num"].tolist() == [10.0, 20.0]
    pd.testing.assert_frame_equal(all_null_target, all_null_before)

    target_for_null_ref = pd.DataFrame({"g": ["a", "b"], "all_null": [np.nan, np.nan]})
    null_ref_before = target_for_null_ref.copy(deep=True)
    res_ref_null = target_for_null_ref.bynat.fill_missing_from(
        train, "all_null", hierarchy_cols=["g"], fallback_global=True
    )
    assert res_ref_null["all_null"].isna().all()
    pd.testing.assert_frame_equal(target_for_null_ref, null_ref_before)

    pd.testing.assert_frame_equal(train, train_before)


def test_fill_missing_from_index_preservation():
    """Test index and row-order preservation with named, duplicate, and MultiIndex objects."""
    train = pd.DataFrame({"g": ["a", "b"], "v": [10.0, 20.0]})
    train_before = train.copy(deep=True)

    for idx in [
        pd.Index(range(100, 104), name="row_id"),
        pd.Index([0, 0, 1, 1], name="dup_id"),
        pd.MultiIndex.from_tuples([("A", 1), ("A", 2), ("B", 1), ("B", 2)], names=["lvl1", "lvl2"]),
    ]:
        target = pd.DataFrame(
            {"g": ["a", "a", "b", "b"], "v": [np.nan, 5.0, np.nan, 15.0], "extra": [1, 2, 3, 4]},
            index=idx,
        )
        target_before = target.copy(deep=True)
        res = target.bynat.fill_missing_from(train, "v", hierarchy_cols=["g"])
        pd.testing.assert_index_equal(res.index, target.index)
        assert res["v"].tolist() == [10.0, 5.0, 20.0, 15.0]
        assert res["extra"].tolist() == [1, 2, 3, 4]
        pd.testing.assert_frame_equal(target, target_before)

    pd.testing.assert_frame_equal(train, train_before)


def test_existing_fill_missing_remains_unchanged():
    """Regression test ensuring existing fill_missing behavior remains unchanged."""
    df = pd.DataFrame({
        "country": ["EG", "EG", "EG", "US", "US", "DE"],
        "salary": [10.0, 14.0, np.nan, 70.0, 90.0, np.nan],
    })
    original = df.copy(deep=True)

    res = df.bynat.fill_missing("salary", strategy="median", hierarchy_cols=["country"])
    assert res.loc[2, "salary"] == 12.0
    assert pd.isna(res.loc[5, "salary"])
    pd.testing.assert_frame_equal(df, original)


def test_fill_missing_from_stats_reverse_map_match_cols():
    train = pd.DataFrame({"nation": ["EG", "EG", "US"], "wage": [10.0, 20.0, 30.0]})
    target = pd.DataFrame({"country": ["EG", "US"], "salary": [None, None]})
    before = target.copy(deep=True)

    result, stats_result = target.bynat.fill_missing_from(
        train,
        "salary",
        match_cols={"salary": "wage", "country": "nation"},
        hierarchy_cols=["country"],
        get_hierarchical_stats=True,
    )

    assert result["salary"].tolist() == [15.0, 30.0]
    assert list(stats_result.columns) == OUTPUT_COLUMNS
    assert stats_result["target_column"].tolist() == ["salary", "salary"]
    assert stats_result["hierarchy_columns"].tolist() == [("country",), ("country",)]
    assert stats_result["group_key"].tolist() == [("EG",), ("US",)]
    assert stats_result["strategy"].tolist() == ["median", "median"]
    assert stats_result["statistic"].tolist() == [15.0, 30.0]
    pd.testing.assert_frame_equal(target, before)
