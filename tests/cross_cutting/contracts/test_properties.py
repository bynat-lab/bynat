import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bynat.cleaning import columns, stats, text
from tests.modules.enrichment.helpers import DictTranslator, install_langdetect

pytestmark = pytest.mark.property


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


@st.composite
def text_frames(draw, min_rows=1, max_rows=25):
    n = draw(st.integers(min_value=min_rows, max_value=max_rows))
    delims = ["--", "/", "|", "_"]
    texts = []
    for _ in range(n):
        has_delim = draw(st.booleans())
        prefix = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5))
        suffix = draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=5))
        if has_delim:
            d = draw(st.sampled_from(delims))
            texts.append(f"{prefix}{d}{suffix}")
        else:
            texts.append(prefix)
    return pd.DataFrame({"title": pd.Series(texts, dtype="string"), "other": list(range(n))})


@st.composite
def list_object_frames(draw, min_rows=1, max_rows=20):
    n = draw(st.integers(min_value=min_rows, max_value=max_rows))
    list_items = []
    for _ in range(n):
        tokens = [draw(st.text(alphabet="xyz", min_size=1, max_size=3)) for _ in range(3)]
        list_items.append(tokens)
    return pd.DataFrame({"items": list_items, "score": list(range(n))})


@given(df=numeric_hierarchy_frames(), strategy=st.sampled_from(["median", "mean", "mode"]))
def test_fill_missing_properties(df, strategy):
    original = df.copy(deep=True)
    result = stats.fill_missing(df, "metric", hierarchy_cols=["region", "sub"], strategy=strategy, fallback_global=True)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df

    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert list(result.columns) == list(df.columns)

    result2 = stats.fill_missing(result, "metric", hierarchy_cols=["region", "sub"], strategy=strategy, fallback_global=True)
    pd.testing.assert_frame_equal(result2, result)


@given(
    target_df=numeric_hierarchy_frames(min_rows=1, max_rows=15),
    ref_df=numeric_hierarchy_frames(min_rows=1, max_rows=15),
    strategy=st.sampled_from(["median", "mean", "mode"]),
)
def test_fill_missing_from_properties(target_df, ref_df, strategy):
    target_orig = target_df.copy(deep=True)
    ref_orig = ref_df.copy(deep=True)

    result = stats.fill_missing_from(
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

    result2 = stats.fill_missing_from(
        result,
        ref_df,
        "metric",
        hierarchy_cols=["region"],
        strategy=strategy,
        fallback_global=True,
    )
    pd.testing.assert_frame_equal(result2, result)


@given(df=outlier_frames())
def test_handle_outliers_properties(df):
    original = df.copy(deep=True)
    result = stats.handle_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df

    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert list(result.columns) == list(df.columns)

    run_repeat = stats.handle_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)
    pd.testing.assert_frame_equal(run_repeat, result)


@given(df=outlier_frames())
def test_drop_outliers_properties(df):
    original = df.copy(deep=True)
    result = stats.drop_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df

    assert len(result) <= len(df)
    assert result.index.isin(df.index).all()
    assert list(result.columns) == list(df.columns)

    run_repeat = stats.drop_outliers(df, "measure", hierarchy_cols=["grp"], min_samples=3)
    pd.testing.assert_frame_equal(run_repeat, result)


@given(
    col_names=st.lists(
        st.text(alphabet="abcdefgh", min_size=2, max_size=6),
        unique=True,
        min_size=2,
        max_size=6,
    ),
    row_count=st.integers(min_value=1, max_value=15),
)
def test_rename_by_substring_properties(col_names, row_count):
    df = pd.DataFrame(
        {col: list(range(row_count)) for col in col_names},
        index=[f"row_{i}" for i in range(row_count)],
    )
    original = df.copy(deep=True)
    substr = col_names[0][:2]
    result = columns.rename_by_substring(df, substr, "NEW")

    pd.testing.assert_frame_equal(df, original)
    assert result is not df
    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert len(result.columns) == len(df.columns)

    expected_cols = [c.replace(substr, "NEW") for c in col_names]
    assert list(result.columns) == expected_cols


@given(
    col_names=st.lists(
        st.text(alphabet="abcdefgh", min_size=2, max_size=5),
        unique=True,
        min_size=2,
        max_size=5,
    ),
    row_count=st.integers(min_value=1, max_value=10),
)
def test_reorder_columns_properties(col_names, row_count):
    df = pd.DataFrame({col: list(range(row_count)) for col in col_names})
    original = df.copy(deep=True)
    reordered_spec = list(reversed(col_names))

    result = columns.reorder_columns(df, *reordered_spec)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df
    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert set(result.columns) == set(df.columns)
    assert list(result.columns) == reordered_spec

    result2 = columns.reorder_columns(result, *reordered_spec)
    pd.testing.assert_frame_equal(result2, result)


@given(df=text_frames(), delim=st.sampled_from(["--", "/", "|", "_"]))
def test_truncate_after_substring_properties(df, delim):
    original = df.copy(deep=True)
    result = text.truncate_after_substring(df, regex=False, title=delim)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df
    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert list(result.columns) == list(df.columns)

    result2 = text.truncate_after_substring(result, regex=False, title=delim)
    pd.testing.assert_frame_equal(result2, result)


@given(df=list_object_frames())
def test_split_list_objects_properties(df):
    original = df.copy(deep=True)

    result_joined = columns.split_list_objects(
        df, "items", first=0, second=1
    )
    pd.testing.assert_frame_equal(df, original)
    assert result_joined is not df
    pd.testing.assert_index_equal(result_joined.index, df.index)
    assert len(result_joined) == len(df)
    assert "first" in result_joined.columns
    assert "second" in result_joined.columns

    result_exploded = columns.split_list_objects(
        df, "items", explode_rows=True, first=[0, 1]
    )
    pd.testing.assert_frame_equal(df, original)
    assert result_exploded is not df
    assert len(result_exploded) >= len(df)
    assert list(result_exploded.index) == list(range(len(result_exploded)))


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(seed=st.integers(min_value=0, max_value=5000))
def test_translate_conditional_column_determinism_property(monkeypatch, tmp_path, seed):
    install_langdetect(monkeypatch, lambda t: "ar" if "arabic" in t else "en")
    translator = DictTranslator({"arabic_word": "english_word", "hello": "hello"})

    df = pd.DataFrame(
        {
            "part": ["p1", "p1", "p2", "p2"] * 4,
            "detect": ["arabic text", "arabic more", "english word", "english more"] * 4,
            "target": ["arabic_word", "arabic_word", "hello", "hello"] * 4,
        }
    )
    original = df.copy(deep=True)

    cache_dir1 = tmp_path / f"c1_{seed}"
    cache_dir2 = tmp_path / f"c2_{seed}"

    res1 = df.bynat.with_cache(cache_dir1).translate_conditional_column(
        "part", "detect", "target", sample_size=2, number_of_samples=2, random_state=seed, provider=translator
    )
    res2 = df.bynat.with_cache(cache_dir2).translate_conditional_column(
        "part", "detect", "target", sample_size=2, number_of_samples=2, random_state=seed, provider=translator
    )

    pd.testing.assert_frame_equal(df, original)
    pd.testing.assert_frame_equal(res1, res2)
