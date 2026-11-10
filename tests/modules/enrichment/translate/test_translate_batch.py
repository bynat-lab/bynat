import sys
import threading

import pandas as pd
import pytest

from bynat.cleaning import BaseData
from bynat.cleaning.enrich import (
    Geocoder,
    GoogleTranslatorProvider,
    NominatimGeocoder,
    RateSource,
    Translator,
    YFinanceRateSource,
)
from tests.modules.enrichment.helpers import (
    BatchTranslator,
    DictTranslator,
    install_fake_module,
)

pytestmark = pytest.mark.unit



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


def test_translate_categorical_column_constructs_the_default_google_translator(monkeypatch, tmp_path):
    translators = []

    class FakeGoogleTranslator:
        def __init__(self, source, target):
            translators.append((source, target))

        def translate(self, text):
            return text.upper()

    install_fake_module(monkeypatch, "deep_translator", GoogleTranslator=FakeGoogleTranslator)
    frame = pd.DataFrame({"status": ["abc", "abc"]})
    original = frame.copy(deep=True)
    translated = frame.bynat.with_cache(tmp_path / "translate").translate_categorical_column("status")

    assert translated["status"].tolist() == ["ABC", "ABC"]
    assert translators == [("auto", "en")]
    pd.testing.assert_frame_equal(frame, original)


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

    install_fake_module(monkeypatch, "deep_translator", GoogleTranslator=GoogleTranslator)
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


def test_translate_categorical_column_translates_each_unique_value_once(monkeypatch, tmp_path):
    calls = []

    class GoogleTranslator:
        def __init__(self, source, target):
            assert (source, target) == ("auto", "en")

        def translate(self, text):
            calls.append(text)
            return {"مكتمل": "Completed", "قيد الانتظار": "Pending"}[text]

    install_fake_module(monkeypatch, "deep_translator", GoogleTranslator=GoogleTranslator)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    frame = BaseData({"status": ["مكتمل", "قيد الانتظار", "مكتمل", None]}, cache_dir=tmp_path)
    original = frame.copy(deep=True)
    result = frame.translate_categorical_column("status")

    assert result["status"].tolist()[:3] == ["Completed", "Pending", "Completed"]
    assert pd.isna(result["status"].iloc[3])
    assert sorted(calls) == sorted(["مكتمل", "قيد الانتظار"])
    pd.testing.assert_frame_equal(frame, original)

    calls.clear()
    again = BaseData({"status": ["مكتمل"]}, cache_dir=tmp_path).translate_categorical_column("status")
    assert again["status"].tolist() == ["Completed"]
    assert calls == []


def test_optional_integration_reports_missing_dependency_at_method_use(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    frame = BaseData({"category": ["pending"]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="deep-translator"):
        frame.translate_categorical_column("category")
