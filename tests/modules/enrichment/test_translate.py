"""Translation providers, the shared cached-lookup engine, and batched external calls."""

import sys
import threading
import types
import warnings

import numpy as np
import pandas as pd
import pytest

from bynat.caching import CacheManager
from bynat.cleaning import BaseData
from bynat.cleaning.enrich import (
    Geocoder,
    GoogleTranslatorProvider,
    NominatimGeocoder,
    RateSource,
    Translator,
    YFinanceRateSource,
    engine,
)
from bynat.cleaning.enrich.engine import SKIP, _cached_map, _rate_limited_map


class DictTranslator:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def translate(self, text, target_lang):
        self.calls.append((text, target_lang))
        return self.mapping.get(text)


class BatchTranslator(DictTranslator):
    def __init__(self, mapping):
        super().__init__(mapping)
        self.batches = []

    def translate(self, text, target_lang):
        pytest.fail("translate_batch should be preferred")

    def translate_batch(self, texts, target_lang):
        self.batches.append((list(texts), target_lang))
        return [self.mapping.get(text) for text in texts]


def _install(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def test_default_providers_satisfy_the_protocols():
    assert issubclass(GoogleTranslatorProvider, Translator)
    assert issubclass(NominatimGeocoder, Geocoder)
    assert issubclass(YFinanceRateSource, RateSource)


def test_documented_enrich_exports_include_the_default_providers():
    import bynat.cleaning.enrich as enrich

    assert set(enrich.__all__) == {
        "Translator",
        "Geocoder",
        "RateSource",
        "GoogleTranslatorProvider",
        "NominatimGeocoder",
        "YFinanceRateSource",
    }
    for name in enrich.__all__:
        assert callable(getattr(enrich, name))


# Each public enrichment method builds its documented real default provider.
def test_translate_categorical_column_constructs_the_default_google_translator(monkeypatch, tmp_path):
    translators = []

    class FakeGoogleTranslator:
        def __init__(self, source, target):
            translators.append((source, target))

        def translate(self, text):
            return text.upper()

    _install(monkeypatch, "deep_translator", GoogleTranslator=FakeGoogleTranslator)
    frame = pd.DataFrame({"status": ["abc", "abc"]})
    original = frame.copy(deep=True)
    translated = frame.bynat.with_cache(tmp_path / "translate").translate_categorical_column("status")

    assert translated["status"].tolist() == ["ABC", "ABC"]
    assert translators == [("auto", "en")]
    pd.testing.assert_frame_equal(frame, original)


# ---------------------------------------------------------------------------
# translation
# ---------------------------------------------------------------------------


def test_translate_categorical_column_accepts_a_plain_provider(tmp_path):
    translator = DictTranslator({"مكتمل": "Completed", "قيد الانتظار": "Pending"})
    frame = pd.DataFrame({"status": ["مكتمل", "قيد الانتظار", "مكتمل", None]})
    original = frame.copy(deep=True)

    result = frame.bynat.with_cache(tmp_path).translate_categorical_column(
        "status", target_lang="en", provider=translator
    )

    assert result["status"].tolist()[:3] == ["Completed", "Pending", "Completed"]
    assert sorted(translator.calls) == sorted([("مكتمل", "en"), ("قيد الانتظار", "en")])
    pd.testing.assert_frame_equal(frame, original)


def test_translate_skips_and_does_not_cache_empty_translations(tmp_path):
    translator = DictTranslator({"a": "A", "b": ""})
    frame = pd.DataFrame({"letter": ["a", "b"]})
    original = frame.copy(deep=True)

    result = frame.bynat.with_cache(tmp_path).translate_categorical_column("letter", provider=translator)
    frame.bynat.with_cache(tmp_path).translate_categorical_column("letter", provider=translator)

    assert result["letter"].tolist() == ["A", "b"]
    assert [call[0] for call in translator.calls] == ["a", "b", "b"]
    pd.testing.assert_frame_equal(frame, original)


def test_translate_batch_is_used_in_save_every_chunks(tmp_path):
    translator = BatchTranslator({value: value.upper() for value in "abcde"})
    frame = pd.DataFrame({"letter": list("abcdea")})
    original = frame.copy(deep=True)

    result = frame.bynat.with_cache(tmp_path).translate_categorical_column(
        "letter", save_every=2, provider=translator
    )

    assert result["letter"].tolist() == list("ABCDEA")
    assert translator.batches == [(["a", "b"], "en"), (["c", "d"], "en"), (["e"], "en")]
    pd.testing.assert_frame_equal(frame, original)


def test_default_google_provider_uses_one_translator_per_thread(monkeypatch):
    created = []

    class GoogleTranslator:
        def __init__(self, source, target):
            created.append((threading.get_ident(), source, target))

        def translate(self, text):
            return text.upper()

    _install(monkeypatch, "deep_translator", GoogleTranslator=GoogleTranslator)
    provider = GoogleTranslatorProvider()

    assert provider.translate("a", "en") == "A"
    assert provider.translate("b", "en") == "B"
    assert provider.translate("c", "fr") == "C"
    assert [entry[1:] for entry in created] == [("auto", "en"), ("auto", "fr")]

    worker = threading.Thread(target=provider.translate, args=("d", "en"))
    worker.start()
    worker.join()

    assert len(created) == 3
    assert created[-1][0] != created[0][0]


def test_rate_limited_map_runs_calls_concurrently():
    # Deterministic rendezvous: every call registers itself and waits for the
    # release event, so the test observes all three calls in flight together
    # before releasing them. A serialized implementation never reaches the
    # rendezvous and fails on the wait below rather than on a barrier timeout.
    lock = threading.Lock()
    in_flight = []
    all_in_flight = threading.Event()
    release = threading.Event()

    def call(item):
        with lock:
            in_flight.append(item)
            if len(in_flight) == 3:
                all_in_flight.set()
        release.wait()
        return item * 2

    results = {}

    def run():
        results["value"] = _rate_limited_map(call, [1, 2, 3], max_workers=3)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert all_in_flight.wait(30), "the three calls did not run concurrently"
    finally:
        release.set()
    worker.join(30)
    assert not worker.is_alive()

    assert results["value"] == [2, 4, 6]


def test_rate_limited_map_spaces_call_starts(monkeypatch):
    clock = {"now": 100.0}
    sleeps = []

    def sleep(seconds):
        sleeps.append(round(seconds, 6))
        clock["now"] += seconds

    monkeypatch.setattr(engine.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(engine.time, "sleep", sleep)

    results = _rate_limited_map(lambda item: item, ["a", "b", "c"], max_workers=1, min_interval=0.2)

    assert results == ["a", "b", "c"]
    assert sleeps == [0.2, 0.2]


def test_rate_limited_map_returns_exceptions_in_place():
    def call(item):
        if item == 2:
            raise RuntimeError("boom")
        return item

    results = _rate_limited_map(call, [1, 2, 3], max_workers=2)

    assert results[0] == 1 and results[2] == 3
    assert isinstance(results[1], RuntimeError)


def _install_langdetect(monkeypatch, detect):
    class DetectorFactory:
        seed = None

    _install(monkeypatch, "langdetect", DetectorFactory=DetectorFactory, detect=detect)


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
    # One generator feeds every sample, so repeated samples differ.
    assert len(set(first[:4])) > 1
    # Partitions are sampled in first-seen order, each from its own rows.
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
    # detect_even marks a sampled text as foreign only when every sampled index is
    # even, so the seeded sample sequence decides which partitions are translated.
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

    # With seed 6 the samples for partition 'a' are ['a1 . a2', 'a3 . a1', 'a3 . a1'],
    # so 'a' reads as English and stays untranslated; partition 'b' reads as foreign
    # and is translated. The whole target column is title-cased as well; this test
    # pins that observed behavior, which the docstring and README do not state.
    assert result["t"].tolist() == ["A0", "A1", "A2", "A3", "B0", "B1", "B2", "B3"]
    # One provider call per unique value of the translated partition only.
    assert translator.calls == [("b0", "en"), ("b1", "en"), ("b2", "en"), ("b3", "en")]

    # An integer seed selects the same Generator path and reproduces the same output.
    # A fresh cache directory is used so the comparison is not masked by cached translations.
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

    # A RandomState is accepted as the same kind of generator input. Its legacy sampling
    # stream differs from the Generator stream for the same seed, so both partitions read
    # as English here and nothing is translated.
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

    # A RandomState must be consumed directly rather than coerced through default_rng:
    # NumPy coerces a legacy RandomState to a Generator, whose sampling stream differs.
    # With seed 4 the legacy stream marks partition 'b' as foreign, while the coerced
    # stream reads both partitions as English, so deleting the explicit
    # Generator/RandomState branch fails this assertion.
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


def test_translate_categorical_column_translates_each_unique_value_once(monkeypatch, tmp_path):
    calls = []

    class GoogleTranslator:
        def __init__(self, source, target):
            assert (source, target) == ("auto", "en")

        def translate(self, text):
            calls.append(text)
            return {"مكتمل": "Completed", "قيد الانتظار": "Pending"}[text]

    _install(monkeypatch, "deep_translator", GoogleTranslator=GoogleTranslator)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    frame = BaseData({"status": ["مكتمل", "قيد الانتظار", "مكتمل", None]}, cache_dir=tmp_path)
    original = frame.copy(deep=True)
    result = frame.translate_categorical_column("status")

    assert result["status"].tolist()[:3] == ["Completed", "Pending", "Completed"]
    assert pd.isna(result["status"].iloc[3])
    assert sorted(calls) == sorted(["مكتمل", "قيد الانتظار"])
    pd.testing.assert_frame_equal(frame, original)

    # A second frame with the same cache directory needs no translator calls.
    calls.clear()
    again = BaseData({"status": ["مكتمل"]}, cache_dir=tmp_path).translate_categorical_column("status")
    assert again["status"].tolist() == ["Completed"]
    assert calls == []


# ---------------------------------------------------------------------------
# the engine
# ---------------------------------------------------------------------------


def test_cached_map_checkpoints_skips_and_retries_failures(monkeypatch, tmp_path):
    manager = CacheManager(tmp_path)
    saves = []
    original_save = manager.save_function_cache
    monkeypatch.setattr(manager, "save_function_cache", lambda name: saves.append(name) or original_save(name))
    started = []

    def fetch(value):
        if value == "boom":
            raise RuntimeError("transient")
        if value == "skip":
            return SKIP
        return value.upper()

    series = pd.Series(["a", "b", "boom", "skip", "c", "a", None])
    cache = _cached_map(
        series, fetch, "bucket", 2, cache_manager=manager, func_name="demo", on_fetch_start=started.append
    )

    assert cache == {"a": "A", "b": "B", "c": "C"}
    assert started == [5]
    assert saves == ["demo", "demo"]

    reloaded = CacheManager(tmp_path).get_column_cache("demo", "bucket")
    assert reloaded == {"a": "A", "b": "B", "c": "C"}

    started.clear()
    _cached_map(["a", "c"], fetch, "bucket", 2, cache_manager=manager, func_name="demo", on_fetch_start=started.append)
    assert started == []


def test_cached_map_multi_bucket_requires_every_bucket(tmp_path):
    manager = CacheManager(tmp_path)
    manager.get_column_cache("demo", "left")["x"] = 1
    fetched = []

    def fetch_many(chunk):
        fetched.extend(chunk)
        return [{"left": value * 2, "right": value * 3} for value in chunk]

    caches = _cached_map(
        ["x", "y"], None, ("left", "right"), 10, cache_manager=manager, func_name="demo", fetch_many=fetch_many
    )

    assert fetched == ["x", "y"]
    assert caches["left"] == {"x": "xx", "y": "yy"}
    assert caches["right"] == {"x": "xxx", "y": "yyy"}


def test_cached_map_batch_failure_leaves_the_chunk_uncached(tmp_path):
    manager = CacheManager(tmp_path)

    def fetch_many(chunk):
        if "bad" in chunk:
            raise RuntimeError("batch failed")
        return [value.upper() for value in chunk]

    cache = _cached_map(
        ["ok", "bad", "fine"], None, "bucket", 2, cache_manager=manager, func_name="demo", fetch_many=fetch_many
    )

    assert cache == {"fine": "FINE"}


def test_cached_map_rejects_batches_with_the_wrong_length(tmp_path):
    manager = CacheManager(tmp_path)

    cache = _cached_map(
        ["a", "b"], None, "bucket", 5, cache_manager=manager, func_name="demo", fetch_many=lambda chunk: ["A"]
    )

    assert cache == {}


# ---------------------------------------------------------------------------
# impute_by_language
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_langdetect(monkeypatch):
    module = types.ModuleType("langdetect")

    class DetectorFactory:
        seed = None

    module.DetectorFactory = DetectorFactory
    module.LangDetectException = Exception
    module.detect = lambda text: "en"
    monkeypatch.setitem(sys.modules, "langdetect", module)
    return module


def test_impute_by_language_exact_detection_and_generated_fallback(fake_langdetect):
    fake_langdetect.detect = lambda text: "en" if text == "Pear (FR)" else "ar"
    frame = pd.DataFrame(
        {
            "slug": ["red-apple", "green-pear", "yellow-banana", "red-apple", "one-two"],
            "name": [None, "Pear (FR)", "موز", "Red Apple", "123"],
            "extra": [1, 2, 3, 4, 5],
        },
        index=pd.Index([3, 4, 5, 6, 7], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.impute_by_language("slug", "name", target_lang="en")

    # Pass 1 (exact, case- and hyphen-insensitive): "Red Apple" -> "Red Apple".
    # Pass 2 (detection): "Pear (FR)" is detected as English and kept.
    # Pass 3 (generation): the remaining references are title-cased.
    # Numeric text is never sent to the detector.
    expected = pd.DataFrame(
        {
            "slug": ["red-apple", "green-pear", "yellow-banana", "red-apple", "one-two"],
            "name": ["Red Apple", "Pear (FR)", "Yellow Banana", "Red Apple", "One Two"],
            "extra": [1, 2, 3, 4, 5],
        },
        index=pd.Index([3, 4, 5, 6, 7], name="row"),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    assert fake_langdetect.DetectorFactory.seed == 0
    pd.testing.assert_frame_equal(frame, before)

    # The seed makes repeated runs deterministic.
    again = frame.bynat.impute_by_language("slug", "name", target_lang="en")
    pd.testing.assert_frame_equal(again, result)


def test_impute_by_language_honors_target_lang(fake_langdetect):
    fake_langdetect.detect = lambda text: "en"
    frame = pd.DataFrame({"slug": ["green-pear"], "name": ["English Label"]})

    kept = frame.bynat.impute_by_language("slug", "name", target_lang="en")
    generated = frame.bynat.impute_by_language("slug", "name", target_lang="ar")

    assert kept["name"].tolist() == ["English Label"]
    assert generated["name"].tolist() == ["Green Pear"]


def test_impute_by_language_skips_missing_columns(fake_langdetect):
    frame = pd.DataFrame({"slug": ["a-b"], "name": [None], "other": [1]})
    before = frame.copy(deep=True)

    missing_target = frame.bynat.impute_by_language("slug", "missing")
    missing_reference = frame.bynat.impute_by_language("missing", "name")

    assert missing_target is not frame
    assert missing_reference is not frame
    pd.testing.assert_frame_equal(missing_target, frame)
    pd.testing.assert_frame_equal(missing_reference, frame)
    pd.testing.assert_frame_equal(frame, before)


def test_impute_by_language_inplace_matches_the_copy_result(tmp_path, fake_langdetect):
    fake_langdetect.detect = lambda text: "en"
    frame = BaseData({"slug": ["a-b"], "name": [None]}, cache_dir=tmp_path)
    expected = frame.impute_by_language("slug", "name")

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.impute_by_language("slug", "name", inplace=True)

    assert returned is None
    pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(expected))


# ---------------------------------------------------------------------------
# translate_conditional_column -- documented argument validation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Optional dependencies -- documented failures at method use
# ---------------------------------------------------------------------------


def test_impute_by_language_missing_reference_returns_before_optional_import(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "langdetect", None)
    frame = BaseData({"category": ["pending"]}, cache_dir=tmp_path)

    result = frame.impute_by_language("missing")
    assert result is not frame
    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(frame))
    assert frame.impute_by_language("missing", inplace=True) is None


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


def test_optional_integration_reports_missing_dependency_at_method_use(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    frame = BaseData({"category": ["pending"]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="deep-translator"):
        frame.translate_categorical_column("category")


def test_optional_categorization_reports_missing_dependency_at_method_use(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "ahocorasick", None)
    frame = BaseData({"description": ["python developer"]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="pyahocorasick"):
        frame.categorize_by_reference(
            "description",
            target_col="category",
            reference={"Software": ["python developer"]},
        )
