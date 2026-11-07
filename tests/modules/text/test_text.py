"""Text transformations: truncate_after_substring literal and regex delimiters."""

import sys
import types

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData

# ---------------------------------------------------------------------------
# truncate_after_substring
# ---------------------------------------------------------------------------


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
            # The helper casts targeted columns to object before splitting.
            "title": pd.Series(
                ["Software Engineer", "Data Analyst", np.nan], index=index, dtype=object
            ),
            "company": pd.Series(["Tech Corp", "Data Inc.", "X"], index=index, dtype=object),
        }
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)

    # A missing target column is skipped; a call with no targets is a copy.
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


# ---------------------------------------------------------------------------
# BaseData-level text helpers
# ---------------------------------------------------------------------------


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


def test_translate_conditional_safe_partition_does_not_import_deep_translator(monkeypatch, tmp_path):
    detect_calls = []

    class DetectorFactory:
        seed = None

    langdetect = types.ModuleType("langdetect")
    langdetect.DetectorFactory = DetectorFactory
    langdetect.detect = lambda text: detect_calls.append(text) or "en"

    class FailingGoogleTranslator:
        def __init__(self, *args, **kwargs):
            pytest.fail("deep-translator should not be required for a safe partition")

    deep_translator = types.ModuleType("deep_translator")
    deep_translator.GoogleTranslator = FailingGoogleTranslator
    monkeypatch.setitem(sys.modules, "langdetect", langdetect)
    monkeypatch.setitem(sys.modules, "deep_translator", deep_translator)

    frame = BaseData(
        {"partition": ["safe"], "description": ["already English"], "label": ["Existing Label"]},
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    result = frame.translate_conditional_column(
        partition_col="partition",
        detect_col="description",
        target_col="label",
        sample_size=1,
        number_of_samples=2,
        threshold=1.0,
        save_every=1,
    )

    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(frame))
    assert DetectorFactory.seed == 0
    assert len(detect_calls) == 2
    pd.testing.assert_frame_equal(frame, original)
