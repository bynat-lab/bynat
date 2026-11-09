"""Text transformations: truncate_after_substring literal and regex delimiters."""

import numpy as np
import pandas as pd

from bynat.cleaning import BaseData


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

