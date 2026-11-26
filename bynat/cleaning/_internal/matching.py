"""Keyword and pattern matching helpers for the text cleaning functions."""

import re
from collections.abc import Sequence
from typing import cast

import numpy as np
import pandas as pd

from .optional import try_import

__all__ = [
    "apply_removal_patterns",
    "first_literal_matches",
    "first_regex_matches",
]

_WHITESPACE = re.compile(r'\s+')


def is_ascii_word_char(char: str) -> bool:
    """Match `\\w` for an ASCII character."""
    return char.isalnum() or char == '_'


def first_literal_matches(texts: pd.Index | np.ndarray, keywords: Sequence[str]) -> list[int | None]:
    """
    Return, for each text, the index of the highest-priority keyword that
    occurs as a case-insensitive whole word, or None.

    One zero-width alternation finds every candidate start position, so
    overlapping keywords are all seen while each text is scanned once. Pure
    ASCII texts use an Aho-Corasick automaton instead when the optional
    `pyahocorasick` dependency is installed and every keyword is ASCII; both
    paths give the same result.
    """
    pattern = re.compile(
        r"(?=(?<!\w)(?:" + "|".join(f"({re.escape(word)})" for word in keywords) + r")(?!\w))",
        re.IGNORECASE,
    )

    automaton = None
    ahocorasick = try_import("ahocorasick") if all(word.isascii() for word in keywords) else None

    if ahocorasick is not None:
        automaton = ahocorasick.Automaton()
        priorities: dict[str, int] = {}

        for priority, word in enumerate(keywords):
            priorities.setdefault(word.lower(), priority)

        for word_lower, priority in priorities.items():
            automaton.add_word(word_lower, (len(word_lower), priority))

        automaton.make_automaton()

    matches: list[int | None] = []

    for text in texts:
        best: int | None = None

        if automaton is not None and text.isascii():
            text_lower = text.lower()
            text_len = len(text_lower)

            for end_index, (word_len, priority) in automaton.iter(text_lower):
                if best is not None and priority >= best:
                    continue

                start_index = end_index - word_len + 1

                if start_index > 0 and is_ascii_word_char(text_lower[start_index - 1]):
                    continue

                if end_index + 1 < text_len and is_ascii_word_char(text_lower[end_index + 1]):
                    continue

                best = priority

        else:
            for match in pattern.finditer(text):
                # Exactly one keyword group takes part in every match.
                priority = cast(int, match.lastindex) - 1

                if best is None or priority < best:
                    best = priority

                    if best == 0:
                        break

        matches.append(best)

    return matches


def first_regex_matches(texts: pd.Index | np.ndarray, patterns: Sequence[re.Pattern]) -> pd.Series:
    """
    Return the first capture group of the highest-priority matching pattern
    for each text, or NaN, using `Series.str.extract` semantics.
    """
    found = pd.Series(np.nan, index = range(len(texts)), dtype = object)
    unresolved = pd.Series(texts, dtype = object)

    for compiled in patterns:
        if unresolved.empty:
            break

        extracted_match = unresolved.str.extract(compiled, expand = True)

        if extracted_match.empty:
            continue

        match_col = extracted_match.iloc[:, 0]
        hit = match_col.notna()

        found.loc[match_col.index[hit]] = match_col[hit]
        unresolved = unresolved[~hit]

    return found


def apply_removal_patterns(series: pd.Series, patterns: Sequence[re.Pattern]) -> pd.Series:
    """Apply removal patterns and whitespace cleanup once per unique text."""
    text = series.astype(str)
    uniques = text.unique()
    cleaned = {}

    for value in uniques:
        stripped = value

        for compiled in patterns:
            stripped = compiled.sub('', stripped)

        cleaned[value] = _WHITESPACE.sub(' ', stripped).strip()

    return text.map(cleaned)
