import numpy as np
import pandas as pd

from tests.shared.constants import OUTPUT_COLUMNS


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
