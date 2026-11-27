import multiprocessing

import pytest

from bynat.caching import CacheManager
from tests.integration.caching_persistence.helpers import (
    _rows,
    _seed_cache_entries,
)

pytestmark = pytest.mark.slow


def _add_key_after_baseline_worker(cache_dir, func_name, bucket, key, value, baseline_event, commit_event, result_queue):
    """Adding worker: wait for the deleter's baseline, commit one new key, signal.

    ``baseline_event`` is set by the deleting worker once its baseline is loaded,
    so this add commits strictly after that snapshot. ``commit_event`` is set only
    after ``save_function_cache`` returns — i.e. after the new row is durable — so
    the deleting worker's later deletion is provably ordered after this commit.
    """
    try:
        manager = CacheManager(cache_dir)
        if not baseline_event.wait(10):
            result_queue.put("timeout: deleter baseline never captured")
            return
        live = manager.load_function_cache(func_name)
        live.setdefault(bucket, {})[key] = value
        manager.save_function_cache(func_name)
        commit_event.set()
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


def _load_baseline_then_delete_worker(cache_dir, func_name, bucket, baseline_event, commit_event, result_queue):
    """Deleting worker: load baseline, signal readiness, then delete after the add.

    The baseline is captured before ``baseline_event`` is set, so the adding
    worker cannot commit into the bucket until after this snapshot exists. The
    worker then blocks on ``commit_event`` — set by the adding worker only after
    its commit — so ``delete_column_cache`` runs strictly after the new key is
    durable while this process's baseline still predates it.
    """
    try:
        manager = CacheManager(cache_dir)
        manager.load_function_cache(func_name)
        baseline_event.set()
        if not commit_event.wait(10):
            result_queue.put("timeout: concurrent add never committed")
            return
        manager.delete_column_cache(func_name, bucket)
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


def test_delete_column_cache_stale_manager_preserves_concurrent_additions(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(manager, "translate", [("status", "known", '"Known"')])

    # The stale manager loads first, so its baseline only knows the pre-existing
    # key in the bucket.
    stale = CacheManager(cache_dir)
    stale.load_function_cache("translate")

    # A concurrent manager adds a fresh key to the same bucket and commits it
    # after the stale manager's baseline was captured.
    fresh = CacheManager(cache_dir)
    fresh_live = fresh.load_function_cache("translate")
    fresh_live["status"]["concurrent"] = "Concurrent"
    fresh.save_function_cache("translate")

    # The stale manager deletes the whole bucket. Because its baseline never saw
    # the concurrent key, only the known identity is deleted.
    stale.delete_column_cache("translate", "status")

    # The key added after the stale baseline survives; only the known row is gone.
    assert _rows(manager) == [("status", "concurrent", '"Concurrent"')]


def test_delete_column_cache_across_processes_preserves_concurrent_addition(tmp_path):
    cache_dir = tmp_path / "cache"
    # Seed the shared baseline before either worker starts, so the deleting
    # worker's load captures only this pre-existing key.
    seed = CacheManager(cache_dir)
    _seed_cache_entries(seed, "translate", [("status", "known", '"Known"')])

    context = multiprocessing.get_context("spawn")
    baseline_event = context.Event()
    commit_event = context.Event()
    result_queue = context.Queue()

    adder = context.Process(
        target=_add_key_after_baseline_worker,
        args=(str(cache_dir), "translate", "status", "concurrent", "Concurrent", baseline_event, commit_event, result_queue),
    )
    deleter = context.Process(
        target=_load_baseline_then_delete_worker,
        args=(str(cache_dir), "translate", "status", baseline_event, commit_event, result_queue),
    )

    try:
        # Order is driven entirely by the workers via the two events; the parent
        # only starts them, waits on bounded joins, and checks their reports.
        deleter.start()
        adder.start()
        for process in (adder, deleter):
            process.join(20)
            assert not process.is_alive()
        results = [result_queue.get(timeout=2) for _ in range(2)]
        assert all(result == "ok" for result in results), results
    finally:
        for process in (adder, deleter):
            if process.is_alive():
                process.terminate()
                process.join(5)

    # The add committed after the deleting process's baseline, so the identity
    # deletion removed only the seeded key; the concurrent key survives reload.
    assert _rows(seed) == [("status", "concurrent", '"Concurrent"')]
