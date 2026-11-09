"""Statistical isolation and anti-leakage contracts for reference imputation."""

import numpy as np
import pandas as pd


def test_fill_missing_from_prevents_statistical_leakage():
    """Verify that target DataFrame values never affect calculated statistics and train is immutable."""
    train = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary": [10.0, 20.0, 100.0, 200.0],
    })
    train_copy = train.copy()

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

    assert res["salary"].tolist() == [999999.0, 15.0, -999999.0, 150.0]

    pd.testing.assert_frame_equal(train, train_copy)
    pd.testing.assert_frame_equal(test, test_before)
