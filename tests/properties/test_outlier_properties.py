import pandas as pd
from hypothesis import given
from hypothesis import strategies as st

from bynat.cleaning import _stats


@st.composite
def outlier_frames(draw, min_rows=10, max_rows=35):
    n = draw(st.integers(min_value=min_rows, max_value=max_rows))
    groups = draw(st.lists(st.sampled_from(["grp1", "grp2"]), min_size=n, max_size=n))
    normal_vals = draw(
        st.lists(
            st.floats(min_value=10.0, max_value=20.0, allow_nan=False, allow_infinity=False),
            min_size=n,
            max_size=n,
        )
    )
    val_series = list(normal_vals)
    if n > 6:
        val_series[0] = 50000.0
    return pd.DataFrame(
        {
            "grp": pd.Series(groups, dtype="object"),
            "measure": pd.Series(val_series, dtype="float64"),
        }
    )


@given(df=outlier_frames())
def test_handle_outliers_properties(df):
    original = df.copy(deep=True)
    result = _stats.handle_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df

    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert list(result.columns) == list(df.columns)

    run_repeat = _stats.handle_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)
    pd.testing.assert_frame_equal(run_repeat, result)


@given(df=outlier_frames())
def test_drop_outliers_properties(df):
    original = df.copy(deep=True)
    result = _stats.drop_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df

    assert len(result) <= len(df)
    assert result.index.isin(df.index).all()
    assert list(result.columns) == list(df.columns)

    run_repeat = _stats.drop_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)
    pd.testing.assert_frame_equal(run_repeat, result)
