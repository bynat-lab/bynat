"""Currency conversion providers and offline exchange-rate caching."""

import json
import sqlite3
import types

import pandas as pd

from bynat.cleaning import BaseData
from bynat.cleaning.enrich import YFinanceRateSource
from tests.modules.enrichment.helpers import install_fake_module

_install = install_fake_module


class FakeRates:
    def __init__(self, rates, fail=()):
        self.rates = rates
        self.fail = set(fail)
        self.calls = []

    def yearly_rates(self, currency, start_year, end_year):
        self.calls.append((currency, start_year, end_year))
        if currency in self.fail:
            raise ConnectionError("offline")
        return {
            year: rate
            for (code, year), rate in self.rates.items()
            if code == currency and start_year <= year <= end_year
        }


def _install_currency_lookup(monkeypatch):
    class Country:
        def __init__(self, alpha_2):
            self.alpha_2 = alpha_2

    def search_fuzzy(name):
        if name == "Atlantis":
            raise LookupError(name)
        return [Country({"Egypt": "EG", "United States": "US", "France": "FR"}[name])]

    _install(monkeypatch, "pycountry", countries=types.SimpleNamespace(search_fuzzy=search_fuzzy))
    _install(monkeypatch, "babel")
    _install(
        monkeypatch,
        "babel.numbers",
        get_territory_currencies=lambda alpha_2: {"EG": ["EGP"], "US": ["USD"], "FR": ["EUR"]}[alpha_2],
    )


def test_convert_to_usd_constructs_the_default_yfinance_rate_source(monkeypatch, tmp_path):
    downloads = []

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start, end):
            downloads.append((self.symbol, start, end))
            index = pd.to_datetime(["2020-06-01"])
            return pd.DataFrame({"Close": [2.0]}, index=index)

    _install_currency_lookup(monkeypatch)
    _install(monkeypatch, "yfinance", Ticker=FakeTicker)
    frame = pd.DataFrame({"country": ["Egypt"], "year": [2020], "salary": [100.0]})
    original = frame.copy(deep=True)
    converted = frame.bynat.with_cache(tmp_path / "currency").convert_to_usd(
        "salary", country_col="country", year_col="year"
    )

    assert converted["salary_usd"].tolist() == [50.0]
    assert downloads == [("EGP=X", "2020-01-01", "2020-12-31")]
    pd.testing.assert_frame_equal(frame, original)




def test_convert_to_usd_downloads_once_per_currency(monkeypatch, tmp_path):
    _install_currency_lookup(monkeypatch)
    rates = FakeRates({("EGP", 2019): 17.0, ("EGP", 2021): 20.0, ("EUR", 2020): 0.5})
    frame = pd.DataFrame(
        {
            "country": ["Egypt", "Egypt", "Egypt", "France", "United States", "Atlantis"],
            "year": [2020, 2021, 2019, 2020, 2020, 2020],
            "salary": [170.0, 200.0, 34.0, 10.0, 100.0, 1.0],
        }
    )
    original = frame.copy(deep=True)

    result = frame.bynat.with_cache(tmp_path).convert_to_usd(
        "salary", country_col="country", year_col="year", provider=rates
    )

    assert result["salary_usd"].tolist()[:5] == [10.0, 10.0, 2.0, 20.0, 100.0]
    assert pd.isna(result["salary_usd"].iloc[5])
    assert sorted(rates.calls) == [("EGP", 2019, 2021), ("EUR", 2019, 2020)]

    rates.calls.clear()
    frame.bynat.with_cache(tmp_path).convert_to_usd("salary", country_col="country", year_col="year", provider=rates)
    assert rates.calls == []
    pd.testing.assert_frame_equal(frame, original)


def test_convert_to_usd_does_not_cache_provider_failures(monkeypatch, tmp_path):
    _install_currency_lookup(monkeypatch)
    frame = pd.DataFrame({"country": ["Egypt"], "year": [2020], "salary": [170.0]})
    original = frame.copy(deep=True)
    accessor = frame.bynat.with_cache(tmp_path)

    offline = FakeRates({}, fail={"EGP"})
    first = accessor.convert_to_usd("salary", country_col="country", year_col="year", provider=offline)

    online = FakeRates({("EGP", 2020): 17.0})
    second = accessor.convert_to_usd("salary", country_col="country", year_col="year", provider=online)

    assert first["salary_usd"].isna().all()
    assert second["salary_usd"].tolist() == [10.0]
    assert online.calls == [("EGP", 2020, 2020)]
    pd.testing.assert_frame_equal(frame, original)


def test_yfinance_rate_source_computes_yearly_means_from_one_download(monkeypatch):
    downloads = []

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start, end):
            downloads.append((self.symbol, start, end))
            index = pd.to_datetime(["2019-03-01", "2019-06-01", "2020-01-02", "2021-05-05"])
            return pd.DataFrame({"Close": [10.0, 20.0, 30.0, float("nan")]}, index=index)

    _install(monkeypatch, "yfinance", Ticker=Ticker)

    rates = YFinanceRateSource().yearly_rates("EGP", 2019, 2021)

    assert rates == {2019: 15.0, 2020: 30.0}
    assert downloads == [("EGP=X", "2019-01-01", "2021-12-31")]


def _install_currency(monkeypatch, history_by_ticker_year, fetches):
    class Country:
        def __init__(self, alpha_2):
            self.alpha_2 = alpha_2

    def search_fuzzy(name):
        if name == "Atlantis":
            raise LookupError(name)
        return [Country({"Egypt": "EG", "United States": "US"}[name])]

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, start, end):
            start_year, end_year = int(start[:4]), int(end[:4])
            fetches.append((self.symbol, start_year, end_year))
            dates, closes = [], []
            for year in range(start_year, end_year + 1):
                for day, close in enumerate(history_by_ticker_year.get((self.symbol, year), []), start=1):
                    dates.append(pd.Timestamp(year=year, month=1, day=day))
                    closes.append(close)
            return pd.DataFrame({"Close": closes}, index=pd.DatetimeIndex(dates))

    _install(monkeypatch, "pycountry", countries=types.SimpleNamespace(search_fuzzy=search_fuzzy))
    _install(monkeypatch, "babel")
    _install(
        monkeypatch,
        "babel.numbers",
        get_territory_currencies=lambda alpha_2: {"EG": ["EGP"], "US": ["USD"]}[alpha_2],
    )
    _install(monkeypatch, "yfinance", Ticker=Ticker)


def test_convert_to_usd_looks_back_and_caches_missing_years(monkeypatch, tmp_path):
    fetches = []
    _install_currency(monkeypatch, {("EGP=X", 2019): [16.0, 18.0]}, fetches)

    frame = BaseData(
        {
            "country": ["Egypt", "United States", "Atlantis"],
            "year": [2020, 2020, 2020],
            "salary": [170.0, 100.0, 50.0],
        },
        index=pd.Index(["a", "b", "c"], name="row"),
        cache_dir=tmp_path,
    )
    frame.loc["d"] = ["Egypt", 2019, 34.0]
    original = frame.copy(deep=True)

    result = frame.convert_to_usd("salary", country_col="country", year_col="year", round_decimals=2)

    assert result["salary_usd"].tolist()[:2] == [10.0, 100.0]
    assert pd.isna(result.loc["c", "salary_usd"])
    assert result.loc["d", "salary_usd"] == 2.0
    assert fetches == [("EGP=X", 2019, 2020)]

    with sqlite3.connect(frame.cache_manager._get_database_path()) as connection:
        currency_codes = {
            key: json.loads(value_json)
            for key, value_json in connection.execute(
                "SELECT key, value_json FROM cache_entries "
                "WHERE func_name = 'convert_to_usd' AND bucket = 'currency_codes'"
            )
        }
        exchange_rates = {
            key: json.loads(value_json)
            for key, value_json in connection.execute(
                "SELECT key, value_json FROM cache_entries "
                "WHERE func_name = 'convert_to_usd' AND bucket = 'exchange_rates'"
            )
        }
    assert currency_codes["Atlantis"] is None
    assert exchange_rates["EGP_2020"] is None
    assert exchange_rates["EGP_2019"] == 17.0

    fetches.clear()
    frame.convert_to_usd("salary", country_col="country", year_col="year")
    assert fetches == []
    pd.testing.assert_frame_equal(frame, original)
