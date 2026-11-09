import sys
import types

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData
from tests.modules.enrichment.helpers import DictTranslator, _install_langdetect

pytestmark = pytest.mark.unit



def test_translate_conditional_column_sampling_is_reproducible(monkeypatch, tmp_path):
    seen = []
    _install_langdetect(monkeypatch, lambda text: seen.append(text) or "en")
    frame = pd.DataFrame(
        {
            "partition": ["p1"] * 20 + ["p2"] * 20,
            "description": [f"text {i}" for i in range(40)],
            "label": ["x"] * 40,
        }
    )

    def run(random_state):
        seen.clear()
        frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "partition", "description", "label", sample_size=3, number_of_samples=4, random_state=random_state
        )
        return list(seen)

    first = run(0)
    assert run(0) == first
    assert run(1) != first
    assert len(set(first[:4])) > 1
    row_numbers = [[int(part.split()[1]) for part in sample.split(" . ")] for sample in first]
    assert all(number < 20 for sample in row_numbers[:4] for number in sample)
    assert all(number >= 20 for sample in row_numbers[4:] for number in sample)


def test_translate_conditional_column_translates_only_foreign_partitions(monkeypatch, tmp_path):
    _install_langdetect(monkeypatch, lambda text: "en" if "hello" in text else "ar")
    translator = DictTranslator({"قطة": "cat"})
    frame = pd.DataFrame(
        {
            "partition": ["en", "en", "ar", "ar", None],
            "description": ["hello", "hello there", "مرحبا", "مرحبا بك", "x"],
            "label": ["dog", "dog", "قطة", "قطة", "قطة"],
        }
    )

    result = frame.bynat.with_cache(tmp_path).translate_conditional_column(
        "partition", "description", "label", sample_size=2, number_of_samples=2, provider=translator
    )

    assert result["label"].tolist() == ["Dog", "Dog", "Cat", "Cat", "Cat"]
    assert translator.calls == [("قطة", "en")]


def test_translate_conditional_column_accepts_a_generator(monkeypatch, tmp_path):
    def detect_even(text):
        indices = [int(part.strip()[-1]) for part in text.split(" . ")]
        return "ar" if all(index % 2 == 0 for index in indices) else "en"

    _install_langdetect(monkeypatch, detect_even)
    frame = pd.DataFrame(
        {
            "p": ["a"] * 4 + ["b"] * 4,
            "d": ["a0", "a1", "a2", "a3", "b0", "b1", "b2", "b3"],
            "t": ["a0", "a1", "a2", "a3", "b0", "b1", "b2", "b3"],
        }
    )

    translator = DictTranslator({value: value.upper() for value in ("a0", "a1", "a2", "a3", "b0", "b1", "b2", "b3")})
    generator = np.random.default_rng(6)

    original = frame.copy(deep=True)
    result = frame.bynat.with_cache(tmp_path).translate_conditional_column(
        "p",
        "d",
        "t",
        sample_size=2,
        number_of_samples=3,
        threshold=0.5,
        random_state=generator,
        provider=translator,
    )
    assert result is not frame
    pd.testing.assert_frame_equal(frame, original)

    assert result["t"].tolist() == ["A0", "A1", "A2", "A3", "B0", "B1", "B2", "B3"]
    assert translator.calls == [("b0", "en"), ("b1", "en"), ("b2", "en"), ("b3", "en")]

    translator.calls.clear()
    seeded = frame.bynat.with_cache(tmp_path / "seeded").translate_conditional_column(
        "p",
        "d",
        "t",
        sample_size=2,
        number_of_samples=3,
        threshold=0.5,
        random_state=6,
        provider=translator,
    )
    assert seeded["t"].tolist() == result["t"].tolist()
    assert translator.calls == [("b0", "en"), ("b1", "en"), ("b2", "en"), ("b3", "en")]

    translator.calls.clear()
    legacy = frame.bynat.with_cache(tmp_path / "legacy").translate_conditional_column(
        "p",
        "d",
        "t",
        sample_size=2,
        number_of_samples=3,
        threshold=0.5,
        random_state=np.random.RandomState(6),
        provider=translator,
    )
    assert legacy["t"].tolist() == ["a0", "a1", "a2", "a3", "b0", "b1", "b2", "b3"]
    assert translator.calls == []

    translator.calls.clear()
    direct = frame.bynat.with_cache(tmp_path / "direct").translate_conditional_column(
        "p",
        "d",
        "t",
        sample_size=2,
        number_of_samples=3,
        threshold=0.5,
        random_state=np.random.RandomState(4),
        provider=translator,
    )
    assert direct["t"].tolist() == ["A0", "A1", "A2", "A3", "B0", "B1", "B2", "B3"]
    assert translator.calls == [("b0", "en"), ("b1", "en"), ("b2", "en"), ("b3", "en")]


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
