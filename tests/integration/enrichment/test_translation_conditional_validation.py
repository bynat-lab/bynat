import sys
import types

import pandas as pd
import pytest

from bynat.cleaning import BaseData


@pytest.mark.parametrize("threshold", [-0.1, 1.1], ids=["below-range", "above-range"])
def test_translate_conditional_column_rejects_out_of_range_threshold(tmp_path, threshold):
    frame = pd.DataFrame({"partition": ["a"], "detect": ["hello"], "label": ["x"]})

    with pytest.raises(ValueError, match="threshold"):
        frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "partition", "detect", "label", threshold=threshold
        )


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        pytest.param("sample_size", 0, id="sample-size-zero"),
        pytest.param("sample_size", -1, id="sample-size-negative"),
        pytest.param("sample_size", 2.5, id="sample-size-float"),
        pytest.param("number_of_samples", 0, id="number-of-samples-zero"),
        pytest.param("save_every", 0, id="save-every-zero"),
    ],
)
def test_translate_conditional_column_rejects_non_positive_integer_parameters(
    tmp_path, parameter, value
):
    frame = pd.DataFrame({"partition": ["a"], "detect": ["hello"], "label": ["x"]})

    with pytest.raises(ValueError, match=parameter):
        frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "partition", "detect", "label", **{parameter: value}
        )


def test_translate_conditional_missing_langdetect_raises_documented_import_error(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "langdetect", None)
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    frame = BaseData(
        {"partition": ["group"], "description": ["text"], "label": ["value"]},
        cache_dir=tmp_path,
    )

    with pytest.raises(ImportError, match="langdetect"):
        frame.translate_conditional_column(
            partition_col="partition",
            detect_col="description",
            target_col="label",
            sample_size=1,
            number_of_samples=1,
        )


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
