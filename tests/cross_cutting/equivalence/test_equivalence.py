"""Equivalence tests: optimized implementations against the 0.3.0 algorithms."""

import string

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import stats, text
from tests.cross_cutting.equivalence._bench_refs import (
    _legacy_drop_outliers,
    _legacy_extract_keywords,
    _legacy_handle_outliers,
)

# ---------------------------------------------------------------------------
# 0.3.0 reference implementations live in `benchmarks/reference_impls.py`,
# kept verbatim apart from `self` -> `df`, and are shared with the benchmarks.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# extract_keywords
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# hierarchical IQR outliers
# ---------------------------------------------------------------------------


def _outlier_frame(seed):
    rng = np.random.default_rng(seed)
    size = 400
    frame = pd.DataFrame(
        {
            "country": rng.choice(["EG", "US", "FR", None], size=size),
            "title": rng.choice(list(string.ascii_lowercase[:6]) + [None], size=size),
            "company": rng.choice(list("pqrstuvw"), size=size),
            "salary": rng.lognormal(10, 1, size=size),
            "bonus": rng.normal(100, 30, size=size),
        }
    )
    frame.loc[rng.random(size) < 0.08, "salary"] = np.nan
    frame.loc[rng.random(size) < 0.05, "bonus"] = rng.normal(1000, 10)
    frame.index = pd.Index(rng.integers(0, 50, size=size), name="dup")
    return frame


# On pandas 2 the 0.3.0 merge mishandles NaN group keys (it raises or misses
# matches), so the legacy comparison only runs where the old code was right.
_LEGACY_RELIABLE = pytest.mark.skipif(
    int(pd.__version__.split(".")[0]) < 3,
    reason="the 0.3.0 merge mishandles NaN group keys on pandas 2",
)


def _brute_force_outliers(df, target_cols, hierarchy_cols, min_samples, blank_found):
    """Row-by-row reference for the hierarchical IQR rules, written for clarity."""
    work = df.reset_index(drop=True).copy()
    flagged = np.zeros(len(work), dtype=bool)

    def key_of(row, cols):
        return tuple("<NA>" if pd.isna(row[col]) else row[col] for col in cols)

    for target_col in target_cols:
        processed = np.zeros(len(work), dtype=bool)

        for level in range(len(hierarchy_cols), 0, -1):
            cols = hierarchy_cols[:level]
            groups = {}

            for position in range(len(work)):
                groups.setdefault(key_of(work.iloc[position], cols), []).append(position)

            for positions in groups.values():
                values = work[target_col].iloc[positions]

                if values.count() < min_samples:
                    continue

                q1, q3 = values.quantile(0.25), values.quantile(0.75)
                lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
                found = [
                    position for position in positions
                    if not processed[position]
                    and pd.notna(work[target_col].iloc[position])
                    and not (lower <= work[target_col].iloc[position] <= upper)
                ]

                for position in found:
                    flagged[position] = True

                    if blank_found:
                        work.loc[position, target_col] = np.nan

                processed[positions] = True

    return flagged, work


@pytest.mark.parametrize("seed", [0, 1])
@pytest.mark.parametrize("min_samples", [3, 20])
def test_outliers_match_a_brute_force_reference(seed, min_samples):
    frame = _outlier_frame(seed).iloc[:150]
    original = frame.copy(deep=True)
    hierarchy = ["country", "title"]

    _, expected_handled = _brute_force_outliers(frame, ["bonus", "salary"], hierarchy, min_samples, True)
    flagged, _ = _brute_force_outliers(frame, ["bonus", "salary"], hierarchy, min_samples, False)

    handled = stats.handle_outliers(frame, "bonus", "salary", hierarchy_cols=hierarchy, min_samples=min_samples)
    dropped = stats.drop_outliers(frame, "bonus", "salary", hierarchy_cols=hierarchy, min_samples=min_samples)

    pd.testing.assert_frame_equal(handled.reset_index(drop=True), expected_handled)
    pd.testing.assert_frame_equal(dropped, frame.iloc[np.flatnonzero(~flagged)])
    pd.testing.assert_frame_equal(frame, original)


@_LEGACY_RELIABLE
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
@pytest.mark.parametrize("min_samples", [1, 3, 5, 20])
def test_handle_and_drop_outliers_match_legacy(seed, min_samples):
    frame = _outlier_frame(seed)
    original = frame.copy(deep=True)
    hierarchy = ["country", "title", "company"]

    pd.testing.assert_frame_equal(
        stats.handle_outliers(frame, "salary", "bonus", "salary", hierarchy_cols=hierarchy, min_samples=min_samples),
        _legacy_handle_outliers(frame, "salary", "bonus", "salary", hierarchy_cols=hierarchy, min_samples=min_samples),
    )
    pd.testing.assert_frame_equal(
        stats.drop_outliers(frame, "salary", "bonus", hierarchy_cols=hierarchy, min_samples=min_samples),
        _legacy_drop_outliers(frame, "salary", "bonus", hierarchy_cols=hierarchy, min_samples=min_samples),
    )
    pd.testing.assert_frame_equal(frame, original)


@_LEGACY_RELIABLE
def test_outliers_match_legacy_with_categorical_hierarchy():
    frame = _outlier_frame(7)
    frame["country"] = frame["country"].astype(pd.CategoricalDtype(["EG", "US", "FR", "ZZ"]))
    original = frame.copy(deep=True)

    pd.testing.assert_frame_equal(
        stats.handle_outliers(frame, "bonus", hierarchy_cols=["country", "title"], min_samples=4),
        _legacy_handle_outliers(frame, "bonus", hierarchy_cols=["country", "title"], min_samples=4),
    )
    pd.testing.assert_frame_equal(frame, original)


def test_outlier_masks_do_not_merge(monkeypatch):
    frame = _outlier_frame(0)
    original = frame.copy(deep=True)

    def unexpected_merge(*args, **kwargs):
        pytest.fail("the one-pass IQR must not merge bounds back")

    monkeypatch.setattr(pd.DataFrame, "merge", unexpected_merge)
    stats.drop_outliers(frame, "bonus", hierarchy_cols=["country", "title"])
    pd.testing.assert_frame_equal(frame, original)
