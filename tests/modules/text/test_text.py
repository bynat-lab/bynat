"""Text transformations: truncate_after_substring literal and regex delimiters."""

import warnings

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData

pytestmark = pytest.mark.unit



def test_truncate_after_substring_literal_delimiters():
    frame = pd.DataFrame(
        {
            "title": ["Software Engineer - Remote", "Data Analyst (Junior)", np.nan],
            "company": ["Tech Corp, LLC", "Data Inc.", "X"],
        },
        index=pd.Index([2, 4, 6], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.truncate_after_substring(
        regex=False, title=["-", "("], company=","
    )

    index = pd.Index([2, 4, 6], name="row")
    expected = pd.DataFrame(
        {
            "title": pd.Series(
                ["Software Engineer", "Data Analyst", np.nan], index=index, dtype=object
            ),
            "company": pd.Series(["Tech Corp", "Data Inc.", "X"], index=index, dtype=object),
        }
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)

    assert list(frame.bynat.truncate_after_substring(regex=False, missing="-").columns) == [
        "title",
        "company",
    ]
    no_targets = frame.bynat.truncate_after_substring()
    assert no_targets is not frame
    pd.testing.assert_frame_equal(no_targets, frame)


def test_truncate_after_substring_regex_delimiters():
    frame = pd.DataFrame(
        {
            "text": ["foo -- bar", "baz", np.nan],
            "title": ["Data Analyst (Junior)", "x", np.nan],
        }
    )
    before = frame.copy(deep=True)

    result = frame.bynat.truncate_after_substring(regex=True, text=r"--\s*", title=r"\(")

    index = pd.Index([0, 1, 2])
    expected = pd.DataFrame(
        {
            "text": pd.Series(["foo", "baz", np.nan], index=index, dtype=object),
            "title": pd.Series(["Data Analyst", "x", np.nan], index=index, dtype=object),
        }
    )
    pd.testing.assert_frame_equal(result, expected)
    pd.testing.assert_frame_equal(frame, before)




def test_basedata_extract_keywords_helper(tmp_path):
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

    keywords = frame.extract_keywords("description", colors=["blue", "red"])
    assert keywords["colors"].tolist() == ["Blue", "Red"]

    pd.testing.assert_frame_equal(frame, original)


def _truncate_frame(tmp_path):
    return BaseData(
        {
            "title": ["a.b-c", "x-y", np.nan],
            "note": ["a.b-c", "x.y.z", np.nan],
        },
        index=pd.Index([2, 4, 6], name="row"),
        cache_dir=tmp_path,
    )


def test_basedata_truncate_after_substring_positional_regex_is_literal(tmp_path):
    frame = _truncate_frame(tmp_path)
    before = frame.copy(deep=True)

    result = frame.truncate_after_substring(False, title="-")

    assert type(result) is type(frame)
    assert result is not frame
    expected = before.copy(deep=True)
    expected["title"] = pd.Series(["a.b", "x", np.nan], index=frame.index, dtype=object)
    pd.testing.assert_frame_equal(result, expected)
    pd.testing.assert_frame_equal(frame, before)
    pd.testing.assert_index_equal(result.index, frame.index)


def test_basedata_truncate_after_substring_keyword_regex_matches_positional(tmp_path):
    frame = _truncate_frame(tmp_path)

    positional = frame.truncate_after_substring(False, title="-")
    keyword = frame.truncate_after_substring(regex=False, title="-")

    assert type(keyword) is type(frame)
    pd.testing.assert_frame_equal(keyword, positional)


def test_basedata_truncate_after_substring_default_returns_new_object(tmp_path):
    frame = _truncate_frame(tmp_path)
    before = frame.copy(deep=True)

    result = frame.truncate_after_substring(title="-")

    assert result is not frame
    assert type(result) is type(frame)
    assert result["title"].tolist()[:2] == ["a.b", "x"]
    assert pd.isna(result["title"].iloc[2])
    pd.testing.assert_frame_equal(frame, before)


def test_basedata_truncate_after_substring_inplace_true_mutates_same_object(tmp_path):
    frame = _truncate_frame(tmp_path)
    frame_id = id(frame)
    frame_type = type(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.truncate_after_substring(regex=False, title="-", inplace=True)

    assert returned is None
    assert id(frame) == frame_id
    assert type(frame) is frame_type
    assert frame["title"].tolist()[:2] == ["a.b", "x"]
    assert pd.isna(frame["title"].iloc[2])
    assert frame["note"].tolist()[:2] == ["a.b-c", "x.y.z"]


def test_basedata_truncate_after_substring_positional_inplace(tmp_path):
    frame = _truncate_frame(tmp_path)
    frame_id = id(frame)
    frame_type = type(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.truncate_after_substring(False, True, title="-")

    assert returned is None
    assert id(frame) == frame_id
    assert type(frame) is frame_type
    assert frame["title"].tolist()[:2] == ["a.b", "x"]
    assert pd.isna(frame["title"].iloc[2])
    assert frame["note"].tolist()[:2] == ["a.b-c", "x.y.z"]

    frame_copy = _truncate_frame(tmp_path)
    before = frame_copy.copy(deep=True)

    result = frame_copy.truncate_after_substring(False, False, title="-")

    assert result is not frame_copy
    assert type(result) is type(frame_copy)
    assert result["title"].tolist()[:2] == ["a.b", "x"]
    pd.testing.assert_frame_equal(frame_copy, before)


def test_basedata_truncate_after_substring_skips_missing_and_preserves_nan_index(tmp_path):
    frame = _truncate_frame(tmp_path)
    before = frame.copy(deep=True)

    missing = frame.truncate_after_substring(regex=False, missing="-")

    assert type(missing) is type(frame)
    pd.testing.assert_frame_equal(missing, before)
    pd.testing.assert_index_equal(missing.index, frame.index)

    no_targets = frame.truncate_after_substring()

    assert no_targets is not frame
    assert type(no_targets) is type(frame)
    pd.testing.assert_frame_equal(no_targets, before)
    assert no_targets["title"].isna().tolist() == [False, False, True]


def test_basedata_truncate_after_substring_positional_argument_is_regex_not_inplace(tmp_path):
    frame = _truncate_frame(tmp_path)
    before = frame.copy(deep=True)

    result = frame.truncate_after_substring("title")

    assert result is not None
    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(result, before)
    pd.testing.assert_frame_equal(frame, before)


def test_basedata_truncate_after_substring_regex_true_and_false_differ_on_dot(tmp_path):
    frame = BaseData(
        {"title": ["a.b-c", "x.y.z", np.nan]},
        index=pd.Index([0, 1, 2]),
        cache_dir=tmp_path,
    )

    positional_literal = frame.truncate_after_substring(False, title=".")
    keyword_literal = frame.truncate_after_substring(regex=False, title=".")
    regex_default = frame.truncate_after_substring(title=".")

    expected_literal = pd.DataFrame(
        {"title": pd.Series(["a", "x", np.nan], dtype=object)}
    )
    expected_regex = pd.DataFrame(
        {"title": pd.Series(["", "", np.nan], dtype=object)}
    )
    pd.testing.assert_frame_equal(positional_literal, expected_literal)
    pd.testing.assert_frame_equal(keyword_literal, expected_literal)
    pd.testing.assert_frame_equal(regex_default, expected_regex)

