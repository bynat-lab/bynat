import numpy as np
import pandas as pd

from tests.integration.enrichment.helpers import DictTranslator, _install_langdetect


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
