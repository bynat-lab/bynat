"""Provider protocols for external services, and the default implementations."""

import threading
from collections.abc import Mapping
from typing import Protocol, runtime_checkable

import pandas as pd

from .._internal import import_optional

__all__ = [
    "Geocoder",
    "GoogleTranslatorProvider",
    "NominatimGeocoder",
    "RateSource",
    "Translator",
    "YFinanceRateSource",
]


@runtime_checkable
class Translator(Protocol):
    """
    Translate one text into `target_lang`.

    A provider may also define `translate_batch(texts, target_lang)`
    returning one translation per text; it is then used instead of calling
    `translate` per text. Without it, `translate` runs in a thread pool sized
    by the optional `max_workers` attribute (default 1), with call starts
    spaced by the optional `min_interval` attribute in seconds (default 0).
    Return a falsy value to leave a text untranslated and uncached.

    Notes:
        Implementations are checked structurally (`isinstance` works through
        `@runtime_checkable`), so a class with a matching `translate` method
        satisfies the protocol without inheriting from it.
    """

    def translate(self, text: str, target_lang: str) -> str | None:
        """Translate one text into `target_lang`; a falsy return is left uncached."""
        ...


@runtime_checkable
class Geocoder(Protocol):
    """
    Resolve a location query to `(latitude, longitude)`, or None when not found.

    Notes:
        A `None` return value is cached as a not-found result by
        `fill_missing_coordinates`, so it is not re-queried on later runs
        unless `retry_not_found=True`.
    """

    def geocode(self, query: str) -> tuple[float, float] | None:
        """Resolve `query`, or return None when it is not found."""
        ...


@runtime_checkable
class RateSource(Protocol):
    """
    Return the mean exchange rate of one USD in `currency` for each year
    between `start_year` and `end_year` inclusive. Years without data are
    left out.

    Notes:
        The returned mapping is keyed by integer year. A rate is expressed as
        the amount of `currency` per one USD, so `convert_to_usd` divides by
        it.
    """

    def yearly_rates(self, currency: str, start_year: int, end_year: int) -> Mapping[int, float]:
        """Return the mean rate per year in the inclusive range; years without data are omitted."""
        ...


class GoogleTranslatorProvider:
    """
    Default `Translator`, backed by `deep_translator.GoogleTranslator`.

    `GoogleTranslator` keeps per-request state on the instance, so each
    worker thread gets its own translator. Up to four requests run at once,
    started at most five per second, the same request rate as the previous
    sequential loop with a 0.2-second pause.

    Attributes:
        max_workers (int): Maximum concurrent translation calls. Class
            attribute, default 4.
        min_interval (float): Minimum seconds between call starts. Class
            attribute, default 0.2.

    Raises:
        ImportError: On construction if the optional `deep-translator`
            dependency is not installed.
    """

    max_workers = 4
    min_interval = 0.2

    def __init__(self, feature: str = "translation") -> None:
        """
        Import `deep_translator` and prepare per-thread translators.

        Args:
            feature (str): Feature name used in the `ImportError` message
                when the dependency is missing. Defaults to "translation".

        Raises:
            ImportError: If `deep_translator` is not installed.
        """
        self._module = import_optional("deep_translator", "deep-translator", feature)
        self._local = threading.local()

    def translate(self, text: str, target_lang: str) -> str | None:
        """
        Translate one text into `target_lang`.

        One `GoogleTranslator` instance is created per target language per
        thread and reused for later calls.

        Args:
            text (str): Text to translate.
            target_lang (str): ISO language code of the target language.

        Returns:
            The translated text, or whatever `GoogleTranslator.translate`
            returns (including `None`).
        """
        translators = self._local.__dict__.setdefault("translators", {})
        translator = translators.get(target_lang)

        if translator is None:
            translator = self._module.GoogleTranslator(source = 'auto', target = target_lang)
            translators[target_lang] = translator

        return translator.translate(text)


class NominatimGeocoder:
    """
    Default `Geocoder`, backed by geopy's Nominatim with a rate limiter.

    Raises:
        ImportError: On construction if the optional `geopy` dependency is
            not installed.
    """

    def __init__(
        self,
        user_agent: str = "data_cleaning_core_geocoder",
        min_delay_seconds: float = 1,
        feature: str = "fill_missing_coordinates",
    ) -> None:
        """
        Build a rate-limited Nominatim geolocator.

        Args:
            user_agent (str): User agent sent to Nominatim. Its usage policy
                asks for one that identifies your application. Defaults to
                `"data_cleaning_core_geocoder"`.
            min_delay_seconds (float): Minimum delay between requests.
                Defaults to 1.
            feature (str): Feature name used in the `ImportError` message
                when the dependency is missing. Defaults to
                `"fill_missing_coordinates"`.

        Raises:
            ImportError: If `geopy` is not installed.
        """
        geocoders = import_optional("geopy.geocoders", "geopy", feature)
        rate_limiter = import_optional("geopy.extra.rate_limiter", "geopy", feature)

        geolocator = geocoders.Nominatim(user_agent = user_agent)
        self._geocode = rate_limiter.RateLimiter(geolocator.geocode, min_delay_seconds = min_delay_seconds)

    def geocode(self, query: str) -> tuple[float, float] | None:
        """
        Resolve one location query.

        Args:
            query (str): Location text to resolve.

        Returns:
            `(latitude, longitude)` as floats, or None when Nominatim finds
            no match.
        """
        location = self._geocode(query)

        if not location:
            return None

        return (location.latitude, location.longitude)


class YFinanceRateSource:
    """
    Default `RateSource`, backed by Yahoo Finance history through `yfinance`.

    One `Ticker(...).history` download covers the whole year range, and the
    yearly means are computed from its daily closes.

    Raises:
        ImportError: On construction if the optional `yfinance` dependency is
            not installed.
    """

    def __init__(self, feature: str = "convert_to_usd") -> None:
        """
        Import `yfinance`.

        Args:
            feature (str): Feature name used in the `ImportError` message
                when the dependency is missing. Defaults to
                `"convert_to_usd"`.

        Raises:
            ImportError: If `yfinance` is not installed.
        """
        self._yfinance = import_optional("yfinance", "yfinance", feature)

    def yearly_rates(self, currency: str, start_year: int, end_year: int) -> dict[int, float]:
        """
        Return the mean daily close of `currency` per USD for each year.

        Downloads one history range covering `start_year` through
        `end_year` and averages the daily closes per calendar year. Years
        outside the requested range, and years whose mean is missing, are
        omitted from the result.

        Args:
            currency (str): ISO 4217 currency code, for example `"EGP"`.
            start_year (int): First year to include, inclusive.
            end_year (int): Last year to include, inclusive.

        Returns:
            dict[int, float]: Mapping of year to mean rate. Empty when the
            download returns no history.

        Raises:
            Exception: Whatever `yfinance` raises for the download propagates
            to the caller, which treats it as a transient error and does not
            cache it.
        """
        ticker = self._yfinance.Ticker(f"{currency}=X")
        history = ticker.history(start = f"{start_year}-01-01", end = f"{end_year}-12-31")

        if history is None or history.empty:
            return {}

        closes = history['Close']
        years = pd.DatetimeIndex(closes.index).year
        means = closes.groupby(years).mean()

        return {
            int(year): float(rate)
            for year, rate in means.items()
            if pd.notna(rate) and start_year <= int(year) <= end_year
        }
