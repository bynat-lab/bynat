import sys
import warnings

import pandas as pd
import pytest

from bynat.cleaning import BaseData


def test_impute_by_language_exact_detection_and_generated_fallback(fake_langdetect):
    fake_langdetect.detect = lambda text: "en" if text == "Pear (FR)" else "ar"
    frame = pd.DataFrame(
        {
            "slug": ["red-apple", "green-pear", "yellow-banana", "red-apple", "one-two"],
            "name": [None, "Pear (FR)", "موز", "Red Apple", "123"],
            "extra": [1, 2, 3, 4, 5],
        },
        index=pd.Index([3, 4, 5, 6, 7], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.impute_by_language("slug", "name", target_lang="en")

    expected = pd.DataFrame(
        {
            "slug": ["red-apple", "green-pear", "yellow-banana", "red-apple", "one-two"],
            "name": ["Red Apple", "Pear (FR)", "Yellow Banana", "Red Apple", "One Two"],
            "extra": [1, 2, 3, 4, 5],
        },
        index=pd.Index([3, 4, 5, 6, 7], name="row"),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    assert fake_langdetect.DetectorFactory.seed == 0
    pd.testing.assert_frame_equal(frame, before)

    again = frame.bynat.impute_by_language("slug", "name", target_lang="en")
    pd.testing.assert_frame_equal(again, result)


def test_impute_by_language_honors_target_lang(fake_langdetect):
    fake_langdetect.detect = lambda text: "en"
    frame = pd.DataFrame({"slug": ["green-pear"], "name": ["English Label"]})

    kept = frame.bynat.impute_by_language("slug", "name", target_lang="en")
    generated = frame.bynat.impute_by_language("slug", "name", target_lang="ar")

    assert kept["name"].tolist() == ["English Label"]
    assert generated["name"].tolist() == ["Green Pear"]


@pytest.mark.usefixtures("fake_langdetect")
def test_impute_by_language_skips_missing_columns():
    frame = pd.DataFrame({"slug": ["a-b"], "name": [None], "other": [1]})
    before = frame.copy(deep=True)

    missing_target = frame.bynat.impute_by_language("slug", "missing")
    missing_reference = frame.bynat.impute_by_language("missing", "name")

    assert missing_target is not frame
    assert missing_reference is not frame
    pd.testing.assert_frame_equal(missing_target, frame)
    pd.testing.assert_frame_equal(missing_reference, frame)
    pd.testing.assert_frame_equal(frame, before)


def test_impute_by_language_inplace_matches_the_copy_result(tmp_path, fake_langdetect):
    fake_langdetect.detect = lambda text: "en"
    frame = BaseData({"slug": ["a-b"], "name": [None]}, cache_dir=tmp_path)
    expected = frame.impute_by_language("slug", "name")

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.impute_by_language("slug", "name", inplace=True)

    assert returned is None
    pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(expected))


def test_impute_by_language_missing_reference_returns_before_optional_import(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "langdetect", None)
    frame = BaseData({"category": ["pending"]}, cache_dir=tmp_path)

    result = frame.impute_by_language("missing")
    assert result is not frame
    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(frame))
    assert frame.impute_by_language("missing", inplace=True) is None
