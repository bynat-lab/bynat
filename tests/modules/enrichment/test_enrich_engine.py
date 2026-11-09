import threading

import pandas as pd
import pytest

from bynat.caching import CacheManager
from bynat.cleaning.enrich import engine
from bynat.cleaning.enrich.engine import SKIP, _cached_map, _rate_limited_map

pytestmark = pytest.mark.unit



def test_rate_limited_map_runs_calls_concurrently():
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


@pytest.mark.mutation
def test_cached_map_rejects_batches_with_surplus_length(tmp_path):
    manager = CacheManager(tmp_path)

    cache = _cached_map(
        ["a", "b"], None, "bucket", 5, cache_manager=manager, func_name="demo", fetch_many=lambda chunk: ["A", "B", "C"]
    )
    assert cache == {}


@pytest.mark.mutation
def test_cached_map_does_not_save_when_nothing_unprocessed(tmp_path, monkeypatch):
    manager = CacheManager(tmp_path)
    saves = []
    monkeypatch.setattr(manager, "save_function_cache", lambda name: saves.append(name))

    cache = _cached_map(
        [], lambda v: v, "bucket", 5, cache_manager=manager, func_name="demo"
    )
    assert cache == {}
    assert saves == []
