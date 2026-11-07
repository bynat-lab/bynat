"""Comprehensive tests for reference-based missing value imputation (fill_missing_from)."""

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData, stats


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

    # Hierarchical median with fallback_global=True
    res_median = test.bynat.fill_missing_from(
        train,
        "salary",
        strategy="median",
        hierarchy_cols=["country"],
        fallback_global=True,
    )
    # EG median is 20.0, US median is 200.0, DE is not in train so falls back to global train median (65.0)
    assert res_median["salary"].tolist() == [20.0, 200.0, 65.0]

    # Hierarchical mean with fallback_global=False
    res_mean = test.bynat.fill_missing_from(
        train,
        "salary",
        strategy="mean",
        hierarchy_cols=["country"],
        fallback_global=False,
    )
    # EG mean is 20.0, US mean is 200.0, DE stays NaN
    assert res_mean["salary"].iloc[0] == 20.0
    assert res_mean["salary"].iloc[1] == 200.0
    assert pd.isna(res_mean["salary"].iloc[2])

    # Hierarchical mode with fallback_global=True
    res_mode = test.bynat.fill_missing_from(
        train,
        "category",
        strategy="mode",
        hierarchy_cols=["country"],
        fallback_global=True,
    )
    # EG mode is 'A', US mode is 'B', DE falls back to global train mode ('A' due to tie-break)
    assert res_mode["category"].tolist() == ["A", "B", "A"]

    # Alias 'mod'
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


def test_fill_missing_from_prevents_statistical_leakage():
    """Verify that target DataFrame values never affect calculated statistics and train is immutable."""
    train = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary": [10.0, 20.0, 100.0, 200.0],
    })
    train_copy = train.copy()

    # Target contains extreme values and different distribution
    test = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary": [999999.0, np.nan, -999999.0, np.nan],
    })
    test_before = test.copy(deep=True)

    res = test.bynat.fill_missing_from(
        train,
        "salary",
        strategy="median",
        hierarchy_cols=["country"],
    )

    # Imputed values must come strictly from train: EG median is 15.0, US median is 150.0
    # The 999999.0 in test must not skew EG's median!
    assert res["salary"].tolist() == [999999.0, 15.0, -999999.0, 150.0]

    # Reference dataset must remain completely unmodified
    pd.testing.assert_frame_equal(train, train_copy)
    pd.testing.assert_frame_equal(test, test_before)


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

    # With min_samples=2:
    # Level 2 ('country', 'city'):
    # ('EG', 'Cairo') has 2 rows in train (>= 2) -> median 12.0
    # ('EG', 'Alex') has 1 row in train (< 2) -> not filled, falls through
    # ('US', 'LA') not in train at level 2 -> not filled, falls through
    # ('UK', 'London') not in train at level 2 -> not filled, falls through
    # Level 1 ('country'):
    # 'EG' has 3 rows in train (>= 2) -> median of [10, 14, 50] is 14.0. Row 1 ('Alex') filled with 14.0!
    # 'US' has 2 rows in train (>= 2) -> median of [100, 200] is 150.0. Row 2 ('LA') filled with 150.0!
    # 'UK' not in train -> not filled
    # Global fallback:
    # 'UK' filled with reference global median of [10, 14, 50, 100, 200] = 50.0
    res = test.bynat.fill_missing_from(
        train,
        "score",
        strategy="median",
        hierarchy_cols=["country", "city"],
        min_samples=2,
        fallback_global=True,
    )

    assert res["score"].tolist() == [12.0, 14.0, 150.0, 50.0]

    # Without global fallback, UK stays NaN
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
    # Reference uses 'nation', 'town', 'income'
    train = pd.DataFrame({
        "nation": ["EG", "EG", "US", "US"],
        "town": ["Cairo", "Cairo", "NYC", "NYC"],
        "income": [10.0, 20.0, 100.0, 200.0],
    })

    # Target uses 'country', 'city', 'salary'
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

    # Alternative targets argument
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


def test_fill_missing_from_validation():
    """Test validation of dataset, match_cols, hierarchy, types, and parameters."""
    valid_train = pd.DataFrame({"g": ["a", "b"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "b"], "v": [np.nan, 2.0]})

    # dataset is None
    with pytest.raises(ValueError, match="Reference dataset is required and cannot be None"):
        target.bynat.fill_missing_from(None, "v")

    # dataset is not a DataFrame
    with pytest.raises(TypeError, match="Reference dataset must be a pandas DataFrame"):
        target.bynat.fill_missing_from([1, 2, 3], "v")  # type: ignore[arg-type]

    # dataset is empty
    with pytest.raises(ValueError, match="Reference dataset cannot be empty"):
        target.bynat.fill_missing_from(pd.DataFrame(), "v")

    # duplicate column names in dataset
    dup_train = pd.DataFrame([[1, 2]], columns=["v", "v"])
    with pytest.raises(ValueError, match="Reference dataset contains duplicate column names"):
        target.bynat.fill_missing_from(dup_train, "v")

    # duplicate column names in target df
    dup_target = pd.DataFrame([[1, 2]], columns=["v", "v"])
    with pytest.raises(ValueError, match="Target dataframe contains duplicate column names"):
        stats.fill_missing_from(dup_target, valid_train, "v")

    # match_cols not a dict
    with pytest.raises(TypeError, match="match_cols must be a dictionary"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols="invalid")  # type: ignore[arg-type]

    # match_cols invalid key type
    with pytest.raises(TypeError, match="match_cols keys and values must be strings"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols={1: "v"})  # type: ignore[arg-type]

    # match_cols target column not in target df
    with pytest.raises(ValueError, match="Target column 'nonexistent' specified in match_cols does not exist"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols={"nonexistent": "v"})

    # match_cols reference column not in reference dataset
    with pytest.raises(ValueError, match="Reference column 'nonexistent' specified in match_cols does not exist"):
        target.bynat.fill_missing_from(valid_train, "v", match_cols={"v": "nonexistent"})

    # target column missing in reference dataset
    missing_ref_col = pd.DataFrame({"other": [1, 2]})
    with pytest.raises(ValueError, match="Reference column 'v' for target 'v' does not exist"):
        target.bynat.fill_missing_from(missing_ref_col, "v")

    # hierarchy column missing in target
    with pytest.raises(ValueError, match="Hierarchy column 'missing_h' does not exist in target"):
        target.bynat.fill_missing_from(valid_train, "v", hierarchy_cols=["missing_h"])

    # hierarchy column missing in reference
    train_no_h = pd.DataFrame({"v": [1.0, 2.0]})
    with pytest.raises(ValueError, match="Hierarchy column 'g' .* does not exist in reference"):
        target.bynat.fill_missing_from(train_no_h, "v", hierarchy_cols=["g"])

    # target column overlaps hierarchy column
    with pytest.raises(ValueError, match="target columns cannot overlap hierarchy columns"):
        target.bynat.fill_missing_from(valid_train, "g", hierarchy_cols=["g"])

    # non-numeric column with numeric strategy
    str_train = pd.DataFrame({"v": ["x", "y"]})
    str_target = pd.DataFrame({"v": ["x", None]})
    with pytest.raises(TypeError, match="must have a numeric dtype for strategy 'median'"):
        str_target.bynat.fill_missing_from(str_train, "v", strategy="median")

    # min_samples invalid
    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        target.bynat.fill_missing_from(valid_train, "v", min_samples=0)

    # unknown strategy
    with pytest.raises(ValueError, match="Invalid strategy 'unknown'"):
        target.bynat.fill_missing_from(valid_train, "v", strategy="unknown")


def test_fill_missing_from_edge_cases():
    """Test empty target, no-missing target, all-missing target, and all-null reference column."""
    train = pd.DataFrame({
        "g": ["a", "b"],
        "num": [10.0, 20.0],
        "all_null": [np.nan, np.nan],
    })
    train_before = train.copy(deep=True)

    # Empty target DataFrame
    empty_target = pd.DataFrame(columns=["g", "num"])
    empty_before = empty_target.copy(deep=True)
    res_empty = empty_target.bynat.fill_missing_from(train, "num")
    assert res_empty.empty
    assert list(res_empty.columns) == ["g", "num"]
    pd.testing.assert_frame_equal(empty_target, empty_before)

    # Target has no missing values
    clean_target = pd.DataFrame({"g": ["a", "b"], "num": [1.0, 2.0]})
    clean_before = clean_target.copy(deep=True)
    res_clean = clean_target.bynat.fill_missing_from(train, "num")
    assert res_clean["num"].tolist() == [1.0, 2.0]
    pd.testing.assert_frame_equal(clean_target, clean_before)

    # Target has all missing values
    all_null_target = pd.DataFrame({"g": ["a", "b"], "num": [np.nan, np.nan]})
    all_null_before = all_null_target.copy(deep=True)
    res_all_null = all_null_target.bynat.fill_missing_from(train, "num", hierarchy_cols=["g"])
    assert res_all_null["num"].tolist() == [10.0, 20.0]
    pd.testing.assert_frame_equal(all_null_target, all_null_before)

    # Reference column contains entirely missing values
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
        assert res.index.equals(target.index)
        assert res["v"].tolist() == [10.0, 5.0, 20.0, 15.0]
        assert res["extra"].tolist() == [1, 2, 3, 4]
        pd.testing.assert_frame_equal(target, target_before)

    pd.testing.assert_frame_equal(train, train_before)


def test_fill_missing_from_basedata_and_contracts(tmp_path):
    """Test BaseData wrapper, inplace mutation, and get_hierarchical_stats contract."""
    train = BaseData({"g": ["a", "a", "b"], "v": [10.0, 20.0, 30.0]}, cache_dir=tmp_path)
    target = BaseData({"g": ["a", "b", "c"], "v": [np.nan, np.nan, np.nan]}, cache_dir=tmp_path)
    train_before = train.copy(deep=True)
    target_before = target.copy(deep=True)

    # get_hierarchical_stats=True
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

    # inplace=True
    mutating = target.copy()
    ret = mutating.fill_missing_from(train, "v", hierarchy_cols=["g"], inplace=True)
    assert ret is None
    assert mutating["v"].tolist()[:2] == [15.0, 30.0]
    assert pd.isna(mutating["v"].iloc[2])


def test_existing_fill_missing_remains_unchanged():
    """Regression test ensuring existing fill_missing behavior remains unchanged."""
    df = pd.DataFrame({
        "country": ["EG", "EG", "EG", "US", "US", "DE"],
        "salary": [10.0, 14.0, np.nan, 70.0, 90.0, np.nan],
    })
    original = df.copy(deep=True)

    # Existing fill_missing call without new parameters
    res = df.bynat.fill_missing("salary", strategy="median", hierarchy_cols=["country"])
    assert res.loc[2, "salary"] == 12.0
    assert pd.isna(res.loc[5, "salary"])
    pd.testing.assert_frame_equal(df, original)
