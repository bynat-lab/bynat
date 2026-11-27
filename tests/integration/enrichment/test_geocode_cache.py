import json
import sqlite3

import pandas as pd

from bynat.cleaning import BaseData
from tests.integration.enrichment.helpers import Location, install_fake_module

_install = install_fake_module


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


def test_fill_missing_coordinates_shortens_queries_and_caches_misses(monkeypatch, tmp_path):
    calls, agents = [], []
    _install_geopy(monkeypatch, {"Springfield, USA": Location(39.8, -89.6)}, calls, agents)

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

    with sqlite3.connect(frame.cache_manager._storage.get_database_path()) as connection:
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
