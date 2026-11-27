import warnings

import pandas as pd
import pytest

import bynat  # noqa: F401  # registers the DataFrame accessor used by these tests
from tests.integration.enrichment.helpers import (
    DictTranslator,
    Geocoder,
    Location,
    RateSource,
    install_currency_lookup,
    install_langdetect,
    install_spacy,
)

pytestmark = pytest.mark.unit


def test_currency_inplace_convert_to_usd_mutates_the_wrapped_frame(tmp_path, monkeypatch):
    install_currency_lookup(monkeypatch)
    rates = RateSource({("EGP", 2020): 17.0})
    frame = pd.DataFrame({"country": ["Egypt"], "year": [2020], "salary": [170.0]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).convert_to_usd(
            "salary", country_col="country", year_col="year", provider=rates, inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert frame["salary_usd"].tolist() == [10.0]


def test_geocode_inplace_fill_missing_coordinates_mutates_the_wrapped_frame(tmp_path):
    geocoder = Geocoder({"Paris": Location(10.0, 20.0)})
    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).fill_missing_coordinates(
            "city", lat_col="lat", long_col="lng", provider=geocoder, inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert frame["lat"].tolist() == [10.0]
    assert frame["lng"].tolist() == [20.0]


def test_nlp_inplace_extract_entities_mutates_the_wrapped_frame(tmp_path, monkeypatch):
    install_spacy(monkeypatch)
    lexicon = {"skills": ["python"]}
    frame = pd.DataFrame({"text": ["python developer"]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).extract_entities_nlp(
            "text", lexicon_source=lexicon, skills="skills", inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert "inplace" not in frame.columns
    assert "skills" in frame.columns


def test_translate_inplace_categorical_column_mutates_the_wrapped_frame(tmp_path):
    translator = DictTranslator({"a": "A"})
    frame = pd.DataFrame({"status": ["a"]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).translate_categorical_column(
            "status", provider=translator, inplace=True
        )

    assert returned is None
    assert id(frame) == original_id
    assert frame["status"].tolist() == ["A"]


def test_translate_inplace_conditional_column_mutates_the_wrapped_frame(tmp_path, monkeypatch):
    install_langdetect(monkeypatch, lambda text: "ar")
    translator = DictTranslator({"a": "A"})
    frame = pd.DataFrame({"part": ["p", "p"], "detect": ["a", "a"], "target": [None, "a"]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.with_cache(tmp_path).translate_conditional_column(
            "part",
            "detect",
            "target",
            provider=translator,
            sample_size=1,
            number_of_samples=1,
            inplace=True,
        )

    assert returned is None
    assert id(frame) == original_id
    assert pd.isna(frame["target"].iloc[0])
    assert frame["target"].iloc[1] == "A"
    assert frame["detect"].tolist() == ["a", "a"]


def test_translate_inplace_impute_by_language_mutates_the_wrapped_frame(fake_langdetect):
    frame = pd.DataFrame({"slug": ["red-apple"], "name": [None]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.impute_by_language("slug", "name", target_lang="en", inplace=True)

    assert returned is None
    assert id(frame) == original_id
    assert frame["name"].tolist() == ["Red Apple"]
