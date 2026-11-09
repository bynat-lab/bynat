import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _seed_cache_entries

pytestmark = pytest.mark.integration


def test_save_persists_added_changed_and_removed_entries(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [
            ("status", "pending", '"Pending"'),
            ("status", "done", '"No"'),
            ("status", "stale", '"Old"'),
        ],
    )

    live = manager.load_function_cache("translate")
    live["status"]["done"] = "Yes"
    live["status"]["new"] = "Fresh"
    del live["status"]["stale"]
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall()

    assert rows == [
        ("status", "done", '"Yes"'),
        ("status", "new", '"Fresh"'),
        ("status", "pending", '"Pending"'),
    ]


def test_save_persists_entirely_removed_buckets(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [
            ("status", "pending", '"Pending"'),
            ("coordinates", "home", "[1.5, 2]"),
            ("coordinates", "nested", '{"ok": true}'),
        ],
    )

    live = manager.load_function_cache("translate")
    del live["coordinates"]
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        identities = connection.execute(
            "SELECT bucket, key FROM cache_entries ORDER BY bucket, key"
        ).fetchall()
        buckets = {row[0] for row in identities}

    assert identities == [("status", "pending")]
    assert "coordinates" not in buckets


def test_save_handles_deletion_only_transaction(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [("status", "pending", '"Pending"'), ("status", "done", '"Done"')],
    )

    live = manager.load_function_cache("translate")
    del live["status"]["done"]
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY key"
        ).fetchall()

    assert rows == [("status", "pending", '"Pending"')]


def test_save_advances_baseline_after_removal(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [("status", "pending", '"Pending"'), ("status", "done", '"Done"')],
    )

    live = manager.load_function_cache("translate")
    del live["status"]["done"]
    manager.save_function_cache("translate")

    assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}

    live["status"]["done"] = "Back"
    manager.save_function_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'status' AND key = 'done'"
        ).fetchone() == ('"Back"',)


def test_save_function_cache_handles_untracked_and_invalid_bucket_structures(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    manager.save_function_cache("never_registered")
    assert "never_registered" in manager.caches

    manager.caches["corrupt_func"] = {"bad_bucket": "not_a_dict"}
    manager.save_function_cache("corrupt_func")

    manager.caches["baseline_corrupt"] = {"valid_bucket": {"k": "v"}}
    manager._baselines["baseline_corrupt"] = {"bad_bucket": "not_a_dict"}
    manager.save_function_cache("baseline_corrupt")
    assert manager._baselines["baseline_corrupt"]["valid_bucket"] == {"k": "v"}


def test_save_function_cache_handles_failing_rollback_during_commit_error(tmp_path, monkeypatch):
    manager = CacheManager(tmp_path / "cache")
    bucket = manager.get_column_cache("translate", "status")
    bucket["k"] = "v"

    class FailingConnection:
        def execute(self, *args, **kwargs):
            pass

        def executemany(self, *args, **kwargs):
            pass

        def commit(self):
            raise sqlite3.OperationalError("commit failed")

        def rollback(self):
            raise sqlite3.OperationalError("rollback failed too")

        def close(self):
            pass

    monkeypatch.setattr(manager, "_connect_sqlite", lambda: FailingConnection())
    manager.save_function_cache("translate")
    assert manager._baselines["translate"] == {}
    assert manager.caches["translate"]["status"] == {"k": "v"}
