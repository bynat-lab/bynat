import multiprocessing

import pytest

from bynat.caching import CacheManager
from tests.integration.caching_persistence.helpers import (
    _seed_cache_entries,
)

pytestmark = pytest.mark.slow


def _concurrent_save_worker(cache_dir, func_name, bucket, key, value, start_event, result_queue):
    """Spawned worker: load the shared baseline, then commit one disjoint key.

    The baseline is loaded before the start event so both workers capture the
    same pre-save snapshot; the event then releases them to write and commit
    their disjoint keys concurrently against the same SQLite cache.
    """
    try:
        manager = CacheManager(cache_dir)
        live = manager.load_function_cache(func_name)
        start_event.wait(10)
        live.setdefault(bucket, {})[key] = value
        manager.save_function_cache(func_name)
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


def _first_writer_worker(cache_dir, func_name, bucket, key, value_a,
                         first_loaded_event, second_loaded_event, committed_event, result_queue):
    """First writer: load the shared baseline, then commit ``value_a`` and signal.

    The baseline is loaded before ``first_loaded_event`` is set, so the second
    writer cannot commit until this process has captured the same seeded
    snapshot. Waiting on ``second_loaded_event`` before the first commit
    guarantees *both* processes diff against the identical baseline, so the
    interaction is not an artifact of one worker reading a mid-write database.
    After ``save_function_cache`` returns (the row is durable) ``committed_event``
    is set; the second writer only writes after that, so the write order is
    enforced by events rather than left to scheduling.
    """
    try:
        manager = CacheManager(cache_dir)
        live = manager.load_function_cache(func_name)
        first_loaded_event.set()
        if not second_loaded_event.wait(10):
            result_queue.put("timeout: second writer never loaded")
            return
        live.setdefault(bucket, {})[key] = value_a
        manager.save_function_cache(func_name)
        committed_event.set()
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


def _second_writer_worker(cache_dir, func_name, bucket, key, value_b,
                          first_loaded_event, second_loaded_event, committed_event, result_queue):
    """Second writer: load the shared baseline, wait for the first commit, then commit ``value_b``.

    Loads the same seeded baseline and signals ``second_loaded_event``. It then
    blocks on ``committed_event`` — set by the first writer only after
    ``value_a`` is durable — so ``value_b`` is written to the same
    ``(func_name, bucket, key)`` strictly after ``value_a``. This process's
    baseline predates both commits and never shared memory with the first
    writer, so it overwrites the seeded value rather than the first writer's,
    and the last committed write wins.
    """
    try:
        manager = CacheManager(cache_dir)
        live = manager.load_function_cache(func_name)
        second_loaded_event.set()
        if not first_loaded_event.wait(10):
            result_queue.put("timeout: first writer never loaded")
            return
        if not committed_event.wait(10):
            result_queue.put("timeout: first writer never committed")
            return
        live.setdefault(bucket, {})[key] = value_b
        manager.save_function_cache(func_name)
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


def test_save_function_cache_is_safe_for_concurrent_disjoint_saves(tmp_path):
    cache_dir = tmp_path / "cache"
    # Establish a shared baseline in the SQLite cache before any worker starts,
    # so each worker's load captures the same snapshot to diff against.
    seed = CacheManager(cache_dir)
    _seed_cache_entries(seed, "translate", [("bucket", "base", '"base"')])

    context = multiprocessing.get_context("spawn")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_concurrent_save_worker,
            args=(str(cache_dir), "translate", "bucket", key, value, start_event, result_queue),
        )
        for key, value in (("left", "worker-left"), ("right", "worker-right"))
    ]
    try:
        for process in processes:
            process.start()
        start_event.set()
        for process in processes:
            process.join(20)
            assert not process.is_alive()
        assert [result_queue.get(timeout=2) for _ in processes] == ["ok", "ok"]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(5)

    # Both disjoint writes committed through separate processes survive reload.
    reloaded = CacheManager(cache_dir).load_function_cache("translate")
    assert reloaded == {"bucket": {"base": "base", "left": "worker-left", "right": "worker-right"}}


def test_save_function_cache_last_committed_writer_wins_same_key_across_processes(tmp_path):
    cache_dir = tmp_path / "cache"
    # Seed the shared baseline row before either worker starts, so each worker's
    # load captures the same pre-write snapshot to diff against.
    seed = CacheManager(cache_dir)
    _seed_cache_entries(seed, "translate", [("bucket", "target", '"base"')])

    context = multiprocessing.get_context("spawn")
    first_loaded_event = context.Event()
    second_loaded_event = context.Event()
    committed_event = context.Event()
    result_queue = context.Queue()

    first_writer = context.Process(
        target=_first_writer_worker,
        args=(str(cache_dir), "translate", "bucket", "target", "A",
              first_loaded_event, second_loaded_event, committed_event, result_queue),
    )
    second_writer = context.Process(
        target=_second_writer_worker,
        args=(str(cache_dir), "translate", "bucket", "target", "B",
              first_loaded_event, second_loaded_event, committed_event, result_queue),
    )

    try:
        # Ordering is driven entirely by the workers through the events: both
        # load the same baseline, the first writer commits A, then — only after
        # the commit signal — the second writer commits B. The parent only
        # starts the workers, waits on bounded joins, and reads their reports.
        first_writer.start()
        second_writer.start()
        for process in (first_writer, second_writer):
            process.join(20)
            assert not process.is_alive()
        results = [result_queue.get(timeout=2) for _ in range(2)]
        assert all(result == "ok" for result in results), results
    finally:
        for process in (first_writer, second_writer):
            if process.is_alive():
                process.terminate()
                process.join(5)

    # The second writer committed value B strictly after the first writer's
    # value A to the same (func_name, bucket, key); the last committed writer
    # wins on reload, and the seeded baseline value is gone.
    reloaded = CacheManager(cache_dir).load_function_cache("translate")
    assert reloaded == {"bucket": {"target": "B"}}
