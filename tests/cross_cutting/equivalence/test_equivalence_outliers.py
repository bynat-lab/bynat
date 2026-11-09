"""Equivalence tests: hierarchical IQR outlier implementation against legacy and brute-force references."""

import string

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import stats
from tests.cross_cutting.equivalence._bench_refs import (
    _legacy_drop_outliers,
    _legacy_handle_outliers,
)


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
