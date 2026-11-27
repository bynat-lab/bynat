import pandas as pd
import pytest

from bynat.cleaning import BaseData, _stats

INVALID_MIN_SAMPLES = [
    pytest.param(True, id="bool-true"),
    pytest.param(False, id="bool-false"),
    pytest.param(0, id="zero"),
    pytest.param(-1, id="negative"),
    pytest.param(2.5, id="float"),
    pytest.param("5", id="string"),
]


@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_fill_missing_and_fill_missing_from_reject_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None]})
    reference = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})

    with pytest.raises(ValueError, match="min_samples must be an integer"):
        _stats.fill_missing(frame, "v", hierarchy_cols="g", min_samples=value)

    with pytest.raises(ValueError, match="min_samples must be an integer"):
        _stats.fill_missing_from(frame, reference, "v", hierarchy_cols="g", min_samples=value)


def test_fill_missing_non_numeric_target_with_hierarchy_raises_typeerror():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})

    with pytest.raises(TypeError):
        _stats.fill_missing(frame, "label", strategy="median", hierarchy_cols=["g"])


def test_fill_missing_non_numeric_target_with_fallback_global_raises_typeerror():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})

    with pytest.raises(TypeError):
        _stats.fill_missing(frame, "label", strategy="median", fallback_global=True)


def test_fill_missing_non_numeric_target_without_hierarchy_is_unchanged():
    frame = pd.DataFrame({"g": ["a", "a", "b"], "label": ["x", None, "y"]})
    original = frame.copy(deep=True)

    result = _stats.fill_missing(frame, "label", strategy="median")

    pd.testing.assert_frame_equal(result, original)


def test_fill_missing_non_numeric_all_nan_target_does_not_raise():
    frame = pd.DataFrame({"g": ["a", "a"], "label": [None, None]})

    result = _stats.fill_missing(frame, "label", strategy="median", hierarchy_cols=["g"])

    assert result["label"].isna().all()


def test_fill_missing_skips_missing_targets_and_fills_valid_ones():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None], "w": [None, None]})
    original = frame.copy(deep=True)

    result = _stats.fill_missing(frame, "v", "missing", hierarchy_cols=["g"])

    assert result["v"].tolist() == [1.0, 1.0]
    assert "missing" not in result.columns
    pd.testing.assert_frame_equal(frame, original)


def test_fill_missing_rejects_unknown_strategy(tmp_path):
    frame = BaseData({"g": ["a", "a"], "v": [1.0, None]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid strategy 'sum'"):
        frame.fill_missing("v", strategy="sum", hierarchy_cols="g")


def test_fill_missing_validates_min_samples(tmp_path):
    frame = BaseData({"g": ["a", "a"], "v": [1.0, None]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=0)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=-3)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=True)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples="2")
