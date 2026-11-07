import json
import multiprocessing
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _rows, _seed_cache_entries


def _run_legacy_migration(cache_dir, func_name, start_event, result_queue):
    try:
        start_event.wait(10)
        CacheManager(cache_dir)._migrate_legacy_json_cache(func_name)
        result_queue.put("ok")
    except Exception as error:  # pragma: no cover - reported to the parent
        result_queue.put(f"{type(error).__name__}: {error}")


@pytest.mark.parametrize("func_names", [["same"], ["left", "right"]])
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


# The sequential test above reproduces the stale-baseline interaction with two
# managers in a single process. The same identity-scope rule can also be proven
# across genuine separate processes without any scheduling assumption: spawned
# workers coordinate purely through events, so the ordering is *enforced* rather
# than raced. The deleting worker loads its baseline, then signals readiness; the
# adding worker waits for that signal before committing a new key, then signals
# completion; only then does the deleting worker call ``delete_column_cache``.
# Each step happens-before the next across the process boundary, so this adds no
# nondeterminism while exercising a real second address space — the deleting
# process holds an independent deep-copy baseline that never shared memory with
# the adding process, and the added key is provably durable before deletion runs.


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
