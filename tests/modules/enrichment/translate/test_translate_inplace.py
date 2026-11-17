"""`translate` in-place identity and mutation of the wrapped frame."""

import warnings

import pandas as pd
import pytest

from tests.modules.enrichment.helpers import DictTranslator, install_langdetect

pytestmark = pytest.mark.unit


def test_translate_inplace_categorical_column_mutates_the_wrapped_frame(tmp_path):
    translator = DictTranslator({"a": "A"})
    frame = pd.DataFrame({"status": ["a"]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).translate_categorical_column(
            "status", provider=translator, inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert frame["status"].tolist() == ["A"]


def test_translate_inplace_conditional_column_mutates_the_wrapped_frame(tmp_path, monkeypatch):
    install_langdetect(monkeypatch, lambda text: "ar")
    translator = DictTranslator({"a": "A"})
    frame = pd.DataFrame({"part": ["p", "p"], "detect": ["a", "a"], "target": [None, "a"]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "part",
            "detect",
            "target",
            provider=translator,
            sample_size=1,
            number_of_samples=1,
            inplace=True,
        )

    assert returned is None
    assert id(frame) == original_id
    assert pd.isna(frame["target"].iloc[0])
    assert frame["target"].iloc[1] == "A"
    assert frame["detect"].tolist() == ["a", "a"]


def test_translate_inplace_impute_by_language_mutates_the_wrapped_frame(fake_langdetect):
    frame = pd.DataFrame({"slug": ["red-apple"], "name": [None]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.impute_by_language("slug", "name", target_lang="en", inplace=True)

    assert returned is None
    assert id(frame) == original_id
    assert frame["name"].tolist() == ["Red Apple"]
