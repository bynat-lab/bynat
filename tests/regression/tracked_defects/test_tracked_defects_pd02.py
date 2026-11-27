import pandas as pd
import pytest

from bynat.cleaning import _stats

pytestmark = pytest.mark.unit


MIN_SAMPLES_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="PD-02: handle_outliers/drop_outliers do not validate min_samples (MS-3a)",
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
        _stats.handle_outliers(frame, "v", hierarchy_cols=["g"], min_samples=value)


@MIN_SAMPLES_XFAIL
@pytest.mark.parametrize("value", INVALID_MIN_SAMPLES)
def test_drop_outliers_rejects_invalid_min_samples(value):
    frame = pd.DataFrame({"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})

    with pytest.raises(ValueError, match="min_samples"):
        _stats.drop_outliers(frame, "v", hierarchy_cols=["g"], min_samples=value)
