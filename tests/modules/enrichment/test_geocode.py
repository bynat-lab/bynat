"""Geocoding providers and offline geocode query caching."""

import json
import sqlite3

import pandas as pd
import pytest

from bynat.caching import CacheManager
from bynat.cleaning import BaseData
from bynat.cleaning.enrich import geocode
from tests.modules.enrichment.helpers import install_fake_module

pytestmark = pytest.mark.unit


_install = install_fake_module


class DictGeocoder:
    def __init__(self, known):
        self.known = known
        self.calls = []

    def geocode(self, query):
        self.calls.append(query)
        return self.known.get(query)


def test_fill_missing_coordinates_constructs_the_default_nominatim_geocoder(monkeypatch, tmp_path):
    geolocators = []

    class FakeLocation:
        latitude = 10.0
        longitude = 20.0

    class FakeNominatim:
        def __init__(self, user_agent):
            self.user_agent = user_agent
            geolocators.append(self)

        def geocode(self, query):
            return FakeLocation() if query == "Paris" else None

    class FakeRateLimiter:
        def __init__(self, function, min_delay_seconds):
            self.function = function
            self.min_delay_seconds = min_delay_seconds

        def __call__(self, query):
            return self.function(query)

    _install(monkeypatch, "geopy.geocoders", Nominatim=FakeNominatim)
    _install(monkeypatch, "geopy.extra.rate_limiter", RateLimiter=FakeRateLimiter)
    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})
    original = frame.copy(deep=True)
    located = frame.bynat.with_cache(tmp_path / "geocode").fill_missing_coordinates(
        "city", lat_col="lat", long_col="lng"
    )

    assert located[["lat", "lng"]].iloc[0].tolist() == [10.0, 20.0]
    assert [geolocator.user_agent for geolocator in geolocators] == [
        "data_cleaning_core_geocoder"
    ]
    pd.testing.assert_frame_equal(frame, original)


def test_fill_missing_coordinates_defaults_to_nominatim_geocoder(monkeypatch, tmp_path):
    geolocators = []

    class FakeLocation:
        latitude = 48.8566
        longitude = 2.3522

    class FakeNominatim:
        def __init__(self, user_agent):
            self.user_agent = user_agent
            geolocators.append(self)

        def geocode(self, query):
            return FakeLocation() if query == "Paris" else None

    class FakeRateLimiter:
        def __init__(self, function, min_delay_seconds):
            self.function = function
            self.min_delay_seconds = min_delay_seconds

        def __call__(self, query):
            return self.function(query)

    _install(monkeypatch, "geopy.geocoders", Nominatim=FakeNominatim)
    _install(monkeypatch, "geopy.extra.rate_limiter", RateLimiter=FakeRateLimiter)
    manager = CacheManager(cache_dir=tmp_path / "cache")
    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})
    original = frame.copy(deep=True)

    located = geocode.fill_missing_coordinates(
        frame,
        "city",
        lat_col="lat",
        long_col="lng",
        provider=None,
        cache_manager=manager,
    )

    assert located[["lat", "lng"]].iloc[0].tolist() == [48.8566, 2.3522]
    assert len(geolocators) == 1
    assert geolocators[0].user_agent == "data_cleaning_core_geocoder"
    pd.testing.assert_frame_equal(frame, original)




def test_fill_missing_coordinates_accepts_a_plain_provider(tmp_path):
    geocoder = DictGeocoder({"Springfield, USA": (39.8, -89.6)})
    frame = pd.DataFrame(
        {
            "street": ["1 Main St", "Nowhere Rd"],
            "city": ["Springfield", "Atlantis"],
            "country": ["USA", None],
            "lat": [None, None],
            "lng": [None, None],
        }
    )
    original = frame.copy(deep=True)

    result = frame.bynat.with_cache(tmp_path).fill_missing_coordinates(
        "street", "city", "country", lat_col="lat", long_col="lng", provider=geocoder
    )

    assert result[["lat", "lng"]].iloc[0].tolist() == [39.8, -89.6]
    assert result[["lat", "lng"]].iloc[1].isna().all()
    assert geocoder.calls == ["1 Main St, Springfield, USA", "Springfield, USA", "Nowhere Rd, Atlantis", "Atlantis"]

    geocoder.calls.clear()
    frame.bynat.with_cache(tmp_path).fill_missing_coordinates(
        "street", "city", "country", lat_col="lat", long_col="lng", provider=geocoder, retry_not_found=True
    )
    assert geocoder.calls == ["Nowhere Rd, Atlantis", "Atlantis"]
    pd.testing.assert_frame_equal(frame, original)


def test_geocoding_errors_are_not_cached(tmp_path):
    class FlakyGeocoder:
        calls = 0

        def geocode(self, query):
            FlakyGeocoder.calls += 1
            if FlakyGeocoder.calls == 1:
                raise TimeoutError("slow")
            return (1.0, 2.0)

    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})
    original = frame.copy(deep=True)
    accessor = frame.bynat.with_cache(tmp_path)

    first = accessor.fill_missing_coordinates("city", lat_col="lat", long_col="lng", provider=FlakyGeocoder())
    second = accessor.fill_missing_coordinates("city", lat_col="lat", long_col="lng", provider=FlakyGeocoder())

    assert first["lat"].isna().all()
    assert second[["lat", "lng"]].iloc[0].tolist() == [1.0, 2.0]
    pd.testing.assert_frame_equal(frame, original)


class _Location:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude


def _install_geopy(monkeypatch, known, calls, agents):
    class Nominatim:
        def __init__(self, user_agent):
            agents.append(user_agent)

        def geocode(self, query):
            calls.append(query)
            return known.get(query)

    class RateLimiter:
        def __init__(self, func, min_delay_seconds):
            self.func = func

        def __call__(self, query):
            return self.func(query)

    _install(monkeypatch, "geopy")
    _install(monkeypatch, "geopy.geocoders", Nominatim=Nominatim)
    _install(monkeypatch, "geopy.extra")
    _install(monkeypatch, "geopy.extra.rate_limiter", RateLimiter=RateLimiter)


def test_fill_missing_coordinates_shortens_queries_and_caches_misses(monkeypatch, tmp_path):
    calls, agents = [], []
    _install_geopy(monkeypatch, {"Springfield, USA": _Location(39.8, -89.6)}, calls, agents)

    frame = BaseData(
        {
            "street": ["1 Main St", "Nowhere Rd", None],
            "city": ["Springfield", "Atlantis", "Paris"],
            "country": ["USA", None, "France"],
            "lat": [None, None, 48.8],
            "lng": [None, None, 2.3],
        },
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    result = frame.fill_missing_coordinates(
        "street", "city", "country", lat_col="lat", long_col="lng", user_agent="bynat-tests"
    )

    assert agents == ["bynat-tests"]
    assert calls == [
        "1 Main St, Springfield, USA",
        "Springfield, USA",
        "Nowhere Rd, Atlantis",
        "Atlantis",
    ]
    assert result[["lat", "lng"]].iloc[0].tolist() == [39.8, -89.6]
    assert result[["lat", "lng"]].iloc[1].isna().all()
    assert result[["lat", "lng"]].iloc[2].tolist() == [48.8, 2.3]

    with sqlite3.connect(frame.cache_manager._get_database_path()) as connection:
        value_json = connection.execute(
            "SELECT value_json FROM cache_entries "
            "WHERE func_name = 'fill_missing_coordinates' "
            "AND bucket = 'geocode_queries' AND key = 'Nowhere Rd, Atlantis'"
        ).fetchone()[0]
    assert json.loads(value_json) is None

    calls.clear()
    frame.fill_missing_coordinates("street", "city", "country", lat_col="lat", long_col="lng")
    assert calls == []

    frame.fill_missing_coordinates(
        "street", "city", "country", lat_col="lat", long_col="lng", retry_not_found=True
    )
    assert calls == ["Nowhere Rd, Atlantis", "Atlantis"]
    pd.testing.assert_frame_equal(frame, original)




@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(2.5, id="float"),
        pytest.param("5", id="string"),
        pytest.param(True, id="bool"),
    ],
)
def test_fill_missing_coordinates_rejects_non_positive_integer_save_every(tmp_path, value):
    frame = pd.DataFrame({"city": ["Paris"], "lat": [None], "lng": [None]})

    with pytest.raises(ValueError, match="save_every"):
        frame.bynat.with_cache(tmp_path).fill_missing_coordinates(
            "city", lat_col="lat", long_col="lng", save_every=value
        )
