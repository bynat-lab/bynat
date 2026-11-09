"""Outlier-method contracts: hierarchy validation, min_samples boundary, and invalid inputs."""

import logging

import pandas as pd
import pytest

from bynat.cleaning import stats

MIN_SAMPLES_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="PD-02: handle_outliers/drop_outliers do not validate min_samples; "
    "see docs/temb/TEST-02-phase1-audit.md (MS-3a)",
)

INVALID_MIN_SAMPLES = [
    pytest.param(True, id="bool-true"),
    pytest.param(False, id="bool-false"),
    pytest.param(0, id="zero"),
    pytest.param(-1, id="negative"),
    pytest.param(2.5, id="float"),
    pytest.param("5", id="string"),
]


@MIN_SAMPLES_XFAIL
@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_handle_outliers_rejects_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    with pytest.raises(ValueError, match="min_samples"):
        stats.handle_outliers(frame, "v", hierarchy_cols=["g"], min_samples=value)


@MIN_SAMPLES_XFAIL
@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_drop_outliers_rejects_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    with pytest.raises(ValueError, match="min_samples"):
        stats.drop_outliers(frame, "v", hierarchy_cols=["g"], min_samples=value)


@pytest.mark.parametrize(
    ("min_samples", "evaluated"),
    [
        pytest.param(6, True, id="exactly-min_samples"),
        pytest.param(7, False, id="above-min_samples"),
    ],
)
def test_handle_outliers_min_samples_boundary(min_samples, evaluated):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    result = stats.handle_outliers(frame, "v", hierarchy_cols=["g"], min_samples=min_samples)

    assert bool(result["v"].isna().iloc[-1]) is evaluated


def test_min_samples_counts_only_non_null_observations():
    frame = pd.DataFrame(
        {
            "g": ["a", "a", "a", "b", "b"],
            "v": [1.0, 3.0, None, 10.0, None],
        }
    )

    result = stats.fill_missing(frame, "v", hierarchy_cols=["g"], min_samples=2)

    assert result.loc[2, "v"] == 2.0
    assert pd.isna(result.loc[4, "v"])


@pytest.mark.parametrize("method_name", ["handle_outliers", "drop_outliers"])
@pytest.mark.parametrize("hierarchy_cols", [[], None], ids=["empty-list", "none"])
def test_outlier_methods_warn_and_return_an_unchanged_copy_without_hierarchy(
    caplog, method_name, hierarchy_cols
):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    original = frame.copy(deep=True)

    with caplog.at_level(logging.WARNING, logger="bynat.cleaning.Cleaning"):
        result = getattr(stats, method_name)(frame, "v", hierarchy_cols=hierarchy_cols)

    assert result is not frame
    pd.testing.assert_frame_equal(result, original)
    assert "No hierarchy columns provided." in caplog.text


@pytest.mark.parametrize("method_name", ["handle_outliers", "drop_outliers"])
def test_outlier_methods_raise_keyerror_for_a_missing_named_hierarchy(method_name):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})

    with pytest.raises(KeyError, match="missing_hierarchy"):
        getattr(stats, method_name)(frame, "v", hierarchy_cols=["missing_hierarchy"])
