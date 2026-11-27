import pandas as pd
from hypothesis import given
from hypothesis import strategies as st

from bynat.cleaning import _stats


@st.composite
def numeric_hierarchy_frames(draw, min_rows=1, max_rows=25):
    n = draw(st.integers(min_value=min_rows, max_value=max_rows))
    g1 = draw(st.lists(st.one_of(st.sampled_from(["North", "South", "East"]), st.none()), min_size=n, max_size=n))
    g2 = draw(st.lists(st.one_of(st.sampled_from(["X", "Y"]), st.none()), min_size=n, max_size=n))
    v = draw(
        st.lists(
            st.one_of(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False), st.none()),
            min_size=n,
            max_size=n,
        )
    )
    custom_index = draw(st.booleans())
    if custom_index and n > 0:
        index = [f"idx_{i}" for i in range(n)]
    else:
        index = None
    return pd.DataFrame(
        {
            "region": pd.Series(g1, dtype="string"),
            "sub": pd.Series(g2, dtype="string"),
            "metric": pd.Series(v, dtype="float64"),
        },
        index=index,
    )


@given(df=numeric_hierarchy_frames(), strategy=st.sampled_from(["median", "mean", "mode"]))
def test_fill_missing_properties(df, strategy):
    original = df.copy(deep=True)
    result = _stats.fill_missing(df, "metric", hierarchy_cols=["region", "sub"], strategy=strategy, fallback_global=True)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df

    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert list(result.columns) == list(df.columns)

    result2 = _stats.fill_missing(result, "metric", hierarchy_cols=["region", "sub"], strategy=strategy, fallback_global=True)
    pd.testing.assert_frame_equal(result2, result)


@given(
    target_df=numeric_hierarchy_frames(min_rows=1, max_rows=15),
    ref_df=numeric_hierarchy_frames(min_rows=1, max_rows=15),
    strategy=st.sampled_from(["median", "mean", "mode"]),
)
def test_fill_missing_from_properties(target_df, ref_df, strategy):
    target_orig = target_df.copy(deep=True)
    ref_orig = ref_df.copy(deep=True)

    result = _stats.fill_missing_from(
        target_df,
        ref_df,
        "metric",
        hierarchy_cols=["region"],
        strategy=strategy,
        fallback_global=True,
    )

    pd.testing.assert_frame_equal(target_df, target_orig)
    pd.testing.assert_frame_equal(ref_df, ref_orig)
    assert result is not target_df
    assert result is not ref_df

    pd.testing.assert_index_equal(result.index, target_df.index)
    assert len(result) == len(target_df)
    assert list(result.columns) == list(target_df.columns)

    result2 = _stats.fill_missing_from(
        result,
        ref_df,
        "metric",
        hierarchy_cols=["region"],
        strategy=strategy,
        fallback_global=True,
    )
    pd.testing.assert_frame_equal(result2, result)
