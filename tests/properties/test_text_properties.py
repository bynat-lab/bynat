import pandas as pd
from hypothesis import given
from hypothesis import strategies as st

from bynat.cleaning import _columns, _text


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
    result = _columns.rename_by_substring(df, substr, "NEW")

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

    result = _columns.reorder_columns(df, *reordered_spec)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df
    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert set(result.columns) == set(df.columns)
    assert list(result.columns) == reordered_spec

    result2 = _columns.reorder_columns(result, *reordered_spec)
    pd.testing.assert_frame_equal(result2, result)


@given(df=text_frames(), delim=st.sampled_from(["--", "/", "|", "_"]))
def test_truncate_after_substring_properties(df, delim):
    original = df.copy(deep=True)
    result = _text.truncate_after_substring(df, regex=False, title=delim)

    pd.testing.assert_frame_equal(df, original)
    assert result is not df
    pd.testing.assert_index_equal(result.index, df.index)
    assert len(result) == len(df)
    assert list(result.columns) == list(df.columns)

    result2 = _text.truncate_after_substring(result, regex=False, title=delim)
    pd.testing.assert_frame_equal(result2, result)


@given(df=list_object_frames())
def test_split_list_objects_properties(df):
    original = df.copy(deep=True)

    result_joined = _columns.split_list_objects(
        df, "items", first=0, second=1
    )
    pd.testing.assert_frame_equal(df, original)
    assert result_joined is not df
    pd.testing.assert_index_equal(result_joined.index, df.index)
    assert len(result_joined) == len(df)
    assert "first" in result_joined.columns
    assert "second" in result_joined.columns

    result_exploded = _columns.split_list_objects(
        df, "items", explode_rows=True, first=[0, 1]
    )
    pd.testing.assert_frame_equal(df, original)
    assert result_exploded is not df
    assert len(result_exploded) >= len(df)
    assert list(result_exploded.index) == list(range(len(result_exploded)))
