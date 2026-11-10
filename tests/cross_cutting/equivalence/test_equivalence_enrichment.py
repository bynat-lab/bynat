import types

import pandas as pd
import pytest

from tests.cross_cutting.equivalence._bench_refs import (
    _legacy_convert_to_usd,
    _legacy_translate_categorical,
    _legacy_translate_conditional_column,
)
from tests.modules.enrichment.helpers import (
    BatchTranslator,
    DictTranslator,
    install_fake_module,
    install_langdetect,
)

pytestmark = pytest.mark.integration


class FakeRateSource:
    def __init__(self, rates):
        self.rates = rates
        self.calls = []

    def yearly_rates(self, code, start_year, end_year):
        self.calls.append((code, start_year, end_year))
        return {
            year: rate
            for (curr, year), rate in self.rates.items()
            if curr == code and start_year <= year <= end_year
        }


def _setup_currency_env(monkeypatch):
    class Country:
        def __init__(self, alpha_2):
            self.alpha_2 = alpha_2

    def search_fuzzy(name):
        mapping = {"Egypt": "EG", "United States": "US", "France": "FR", "Germany": "DE"}
        if name in mapping:
            return [Country(mapping[name])]
        raise LookupError(name)

    install_fake_module(monkeypatch, "pycountry", countries=types.SimpleNamespace(search_fuzzy=search_fuzzy))
    install_fake_module(monkeypatch, "babel")
    install_fake_module(
        monkeypatch,
        "babel.numbers",
        get_territory_currencies=lambda a2: {
            "EG": ["EGP"],
            "US": ["USD"],
            "FR": ["EUR"],
            "DE": ["EUR"],
        }.get(a2, []),
    )


def test_perf01_translate_categorical_matches_legacy(tmp_path):
    translator = BatchTranslator(
        {
            "سيارة": "Car",
            "طائرة": "Plane",
            "قطار": "Train",
            "سفينة": "Ship",
            "دراجة": "Bicycle",
        }
    )

    categories = ["سيارة", "طائرة", "قطار", "سفينة", "دراجة", None, "سيارة", "قطار"] * 5
    df = pd.DataFrame({"id": range(len(categories)), "transport": categories})
    original = df.copy(deep=True)

    expected = _legacy_translate_categorical(df, "transport", target_lang="en", provider=translator)

    cache_dir = tmp_path / "cache_perf01_trans"
    actual = df.bynat.with_cache(cache_dir).translate_categorical_column(
        "transport", target_lang="en", provider=translator, save_every=4
    )

    pd.testing.assert_frame_equal(df, original)
    pd.testing.assert_frame_equal(actual, expected)
    assert len(translator.batches) > 0


def test_perf01_convert_to_usd_matches_legacy(monkeypatch, tmp_path):
    _setup_currency_env(monkeypatch)

    rates_table = {
        ("EGP", 2021): 15.7,
        ("EGP", 2022): 19.1,
        ("EGP", 2023): 30.9,
        ("EUR", 2021): 0.85,
        ("EUR", 2022): 0.95,
        ("EUR", 2023): 0.92,
    }

    prod_source = FakeRateSource(rates_table)
    legacy_source = FakeRateSource(rates_table)

    country_to_curr = {"Egypt": "EGP", "United States": "USD", "France": "EUR", "Germany": "EUR"}

    records = [
        {"country": "Egypt", "year": 2021, "amount": 1570.0},
        {"country": "Egypt", "year": 2022, "amount": 1910.0},
        {"country": "Egypt", "year": 2023, "amount": 3090.0},
        {"country": "France", "year": 2021, "amount": 850.0},
        {"country": "France", "year": 2022, "amount": 950.0},
        {"country": "United States", "year": 2023, "amount": 500.0},
        {"country": "Germany", "year": 2023, "amount": 920.0},
    ] * 3
    df = pd.DataFrame(records)
    original = df.copy(deep=True)

    expected = _legacy_convert_to_usd(
        df,
        "amount",
        country_col="country",
        year_col="year",
        rate_source=legacy_source,
        country_to_currency=country_to_curr,
        new_cols=False,
        round_decimals=2,
    )

    cache_dir = tmp_path / "cache_perf01_curr"
    actual = df.bynat.with_cache(cache_dir).convert_to_usd(
        "amount",
        country_col="country",
        year_col="year",
        new_cols=False,
        provider=prod_source,
        round_decimals=2,
    )

    pd.testing.assert_frame_equal(df, original)
    pd.testing.assert_frame_equal(actual, expected)

    egp_calls = [c for c in prod_source.calls if c[0] == "EGP"]
    assert len(egp_calls) == 1
    assert egp_calls[0] == ("EGP", 2021, 2023)
    assert len(legacy_source.calls) > len(prod_source.calls)


def test_perf03_translate_conditional_partitioning_matches_legacy(monkeypatch, tmp_path):
    install_langdetect(monkeypatch, lambda t: "en" if "english" in t.lower() else "ar")
    translator = DictTranslator(
        {
            "تفاح": "Apple",
            "موز": "Banana",
            "برتقال": "Orange",
            "عنب": "Grape",
        }
    )

    def detect_func(t):
        return "en" if "english" in t.lower() else "ar"

    records = []
    for i in range(12):
        records.append({"cat": "en_group", "desc": f"english item {i}", "label": "apple"})
    for i in range(12):
        records.append({"cat": "ar_group", "desc": f"وصف عربي {i}", "label": "تفاح"})
    for i in range(8):
        records.append({"cat": "mixed_group", "desc": f"arabic description {i}", "label": "موز"})

    df = pd.DataFrame(records)
    original = df.copy(deep=True)

    seed = 123
    expected = _legacy_translate_conditional_column(
        df,
        "cat",
        "desc",
        "label",
        target_lang="en",
        sample_size=3,
        number_of_samples=3,
        threshold=0.5,
        random_state=seed,
        provider=translator,
        detect=detect_func,
    )

    cache_dir = tmp_path / "cache_perf03"
    actual = df.bynat.with_cache(cache_dir).translate_conditional_column(
        "cat",
        "desc",
        "label",
        target_lang="en",
        sample_size=3,
        number_of_samples=3,
        threshold=0.5,
        random_state=seed,
        provider=translator,
    )

    pd.testing.assert_frame_equal(df, original)
    pd.testing.assert_frame_equal(actual, expected)
