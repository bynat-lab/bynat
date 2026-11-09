"""Equivalence tests: optimized extract_keywords implementation against legacy algorithms."""

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import text
from tests.cross_cutting.equivalence._bench_refs import _legacy_extract_keywords

_WORDS = ["red", "blue", "c++", ".net", "data", "data analyst", "analyst", "Ünïcode", "x_y", "big data"]


def _random_texts(rng, size):
    pool = _WORDS + ["the", "and", "reddish", "blues", "nets", "Data-Analyst", "RED", "BLUE", "ünïcode"]
    texts = []

    for _ in range(size):
        if rng.random() < 0.1:
            texts.append(None)
            continue

        words = rng.choice(pool, size=rng.integers(1, 6))
        separators = rng.choice([" ", ", ", "-", "/", "_"], size=len(words))
        texts.append("".join(f"{word}{sep}" for word, sep in zip(words, separators)).strip())

    return texts


@pytest.fixture(params=[0, 1, 2])
def keyword_frame(request):
    rng = np.random.default_rng(request.param)
    return pd.DataFrame(
        {
            "title": _random_texts(rng, 300),
            "body": _random_texts(rng, 300),
            "existing": rng.choice([None, "kept", "Other"], size=300),
        }
    )


@pytest.mark.parametrize("remove_extracted", [False, True])
@pytest.mark.parametrize(
    "keywords",
    [
        ["data", "data analyst", "analyst"],
        ["analyst", "data analyst", "data"],
        ["c++", ".net", "x_y", "Ünïcode"],
        ["RED", "red", "blue", "big data"],
    ],
)
def test_extract_keywords_literal_matches_legacy(keyword_frame, keywords, remove_extracted):
    original = keyword_frame.copy(deep=True)
    expected = _legacy_extract_keywords(
        keyword_frame, "title", "body", remove_extracted=remove_extracted, found=keywords
    )
    actual = text.extract_keywords(keyword_frame, "title", "body", remove_extracted=remove_extracted, found=keywords)

    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(keyword_frame, original)


@pytest.mark.parametrize("remove_extracted", [False, True])
@pytest.mark.parametrize(
    "patterns",
    [
        [r"(?i)(\bdata\b)", r"analyst"],
        [r"(red|blue)", r"(?P<lang>c\+\+|\.net)"],
        [r"b(lue)?", r"(?i)x_(y)"],
    ],
)
def test_extract_keywords_regex_matches_legacy(keyword_frame, patterns, remove_extracted):
    original = keyword_frame.copy(deep=True)
    expected = _legacy_extract_keywords(
        keyword_frame, "title", "body", remove_extracted=remove_extracted, use_regex=True, found=patterns
    )
    actual = text.extract_keywords(
        keyword_frame, "title", "body", remove_extracted=remove_extracted, use_regex=True, found=patterns
    )

    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(keyword_frame, original)


@pytest.mark.parametrize("use_regex", [False, True])
def test_extract_keywords_repeated_calls_into_existing_column_match_legacy(keyword_frame, use_regex):
    original = keyword_frame.copy(deep=True)
    first = ["blue"] if not use_regex else [r"(blue)"]
    second = ["red", "blue"] if not use_regex else [r"(red)", r"(blue)"]

    expected = _legacy_extract_keywords(keyword_frame, "title", use_regex=use_regex, existing=first)
    expected = _legacy_extract_keywords(expected, "body", use_regex=use_regex, existing=second)

    actual = text.extract_keywords(keyword_frame, "title", use_regex=use_regex, existing=first)
    actual = text.extract_keywords(actual, "body", use_regex=use_regex, existing=second)

    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(keyword_frame, original)


def test_extract_keywords_aho_corasick_and_regex_paths_agree(monkeypatch, keyword_frame):
    pytest.importorskip("ahocorasick")
    original = keyword_frame.copy(deep=True)
    keywords = ["data", "data analyst", "analyst", "c++", ".net", "x_y", "red"]

    with_automaton = text.extract_keywords(keyword_frame, "title", "body", found=keywords)
    monkeypatch.setattr(text, "_optional_ahocorasick", lambda: None)
    regex_only = text.extract_keywords(keyword_frame, "title", "body", found=keywords)

    pd.testing.assert_frame_equal(with_automaton, regex_only)
    pd.testing.assert_frame_equal(keyword_frame, original)


def test_extract_keywords_overlapping_keywords_respect_priority():
    frame = pd.DataFrame({"text": ["x ab c", "ab c x", "x ab"]})
    original = frame.copy(deep=True)

    result = text.extract_keywords(frame, "text", found=["ab c", "x ab"])

    assert result["found"].tolist() == ["Ab C", "Ab C", "X Ab"]
    pd.testing.assert_frame_equal(frame, original)
