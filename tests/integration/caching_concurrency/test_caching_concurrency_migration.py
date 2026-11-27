import json
import multiprocessing
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.integration.caching_persistence.helpers import (
    _migrate_legacy_cache,
)

pytestmark = pytest.mark.slow


def _run_legacy_migration(cache_dir, func_name, start_event, result_queue):
    try:
        start_event.wait(10)
        _migrate_legacy_cache(CacheManager(cache_dir), func_name)
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


@pytest.mark.parametrize(
    "func_names",
    [pytest.param(["same"], id="same-source"), pytest.param(["left", "right"], id="disjoint-sources")],
)
def test_legacy_migration_is_safe_for_concurrent_sources(tmp_path, func_names):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    for func_name in func_names:
        (cache_dir / f"{func_name}_cache.json").write_text(
            json.dumps({"bucket": {f"key-{func_name}": func_name}}), encoding="utf-8"
        )

    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_run_legacy_migration,
            args=(str(cache_dir), func_name, start_event, result_queue),
        )
        for func_name in func_names * 2
    ]
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(20)
        assert not process.is_alive()
    assert [result_queue.get(timeout=2) for _ in processes] == ["ok"] * len(processes)

    with sqlite3.connect(cache_dir / "cache.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (len(func_names),)
        assert connection.execute("SELECT count(*) FROM migration_metadata").fetchone() == (len(func_names),)
