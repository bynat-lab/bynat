import json
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _seed_cache_entries

pytestmark = pytest.mark.integration



def test_cache_round_trip_via_sqlite(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("translate", "status")
    bucket["pending"] = "Pending"
    manager.save_function_cache("translate")

    reloaded = CacheManager(tmp_path / "cache")
    assert reloaded.load_function_cache("translate") == {
        "status": {"pending": "Pending"},
    }
    assert not (tmp_path / "cache" / "translate_cache.json").exists()
    assert (tmp_path / "cache" / "cache.sqlite3").exists()


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


def test_cache_rejects_empty_and_path_like_keys(tmp_path):
    manager = CacheManager(tmp_path)

    with pytest.raises(ValueError):
        manager.load_function_cache("   ")
    with pytest.raises(ValueError):
        manager.load_function_cache("nested/cache")
    with pytest.raises(TypeError):
        manager.get_column_cache("function", 123)


def test_cache_directory_is_created_on_save_not_construction(tmp_path):
    cache_dir = tmp_path / "not-yet-created"
    CacheManager(cache_dir)
    assert not cache_dir.exists()

    manager = CacheManager(cache_dir)
    manager.caches["function"] = {"column": {"key": "value"}}
    manager.save_function_cache("function")
    assert (cache_dir / "cache.sqlite3").exists()


def test_cache_dir_defaults_to_environment_variable_then_legacy_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BYNAT_CACHE_DIR", raising=False)
    assert CacheManager().cache_dir_path == str(tmp_path / "Settings" / "Cache Data" / "Automated")

    monkeypatch.setenv("BYNAT_CACHE_DIR", str(tmp_path / "from-env"))
    assert CacheManager().cache_dir_path == str(tmp_path / "from-env")
    assert CacheManager(tmp_path / "explicit").cache_dir_path == str(tmp_path / "explicit")


def test_rebuild_function_cache_from_sqlite(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    manager._initialize_sqlite()

    created_at = "2026-01-01T00:00:00+00:00"
    rows = [
        ("translate", "status", "pending", '"Pending"', created_at),
        ("translate", "status", "missing", "null", created_at),
        ("translate", "coordinates", "home", "[1.5, 2]", created_at),
        ("translate", "coordinates", "nested", '{"ok": true}', created_at),
        ("translate", "meta", "count", "3", created_at),
        ("other", "status", "pending", '"other"', created_at),
    ]

    with sqlite3.connect(manager._get_database_path()) as connection:
        connection.executemany(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        connection.commit()

    assert manager._rebuild_function_cache_from_sqlite("translate") == {
        "status": {"pending": "Pending", "missing": None},
        "coordinates": {"home": [1.5, 2], "nested": {"ok": True}},
        "meta": {"count": 3},
    }


def test_rebuild_function_cache_from_sqlite_is_empty_without_rows(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    manager._initialize_sqlite()

    assert manager._rebuild_function_cache_from_sqlite("unused") == {}


def test_load_function_cache_migrates_legacy_json_through_public_path(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "translate_cache.json").write_text(
        json.dumps({"status": {"pending": "Pending", "missing": None}}),
        encoding="utf-8",
    )

    manager = CacheManager(cache_dir)

    assert manager.load_function_cache("translate") == {
        "status": {"pending": "Pending", "missing": None}
    }

    assert (cache_dir / "cache.sqlite3").exists()
    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall()
        marker = connection.execute(
            "SELECT source_name FROM migration_metadata"
        ).fetchall()

    assert rows == [
        ("status", "missing", "null"),
        ("status", "pending", '"Pending"'),
    ]
    assert marker == [("translate_cache.json",)]


def test_load_function_cache_missing_function_returns_empty_and_builds_backend(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    assert not (cache_dir / "cache.sqlite3").exists()

    assert manager.load_function_cache("ghost") == {}
    assert (cache_dir / "cache.sqlite3").exists()

    assert manager.load_function_cache("another-ghost") == {}


def test_load_function_cache_reads_sqlite_authoritatively(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    manager._initialize_sqlite()

    created_at = "2026-01-01T00:00:00+00:00"
    with sqlite3.connect(manager._get_database_path()) as connection:
        connection.execute(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            ("translate", "status", "pending", '"Pending"', created_at),
        )
        connection.commit()

    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}


def test_load_function_cache_memoizes_and_preserves_mutations(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    first = manager.load_function_cache("translate")
    first["status"] = {"pending": "Pending"}

    second = manager.load_function_cache("translate")

    assert second is first
    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}


def test_get_column_cache_returns_existing_bucket_identity(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    func_cache = manager.load_function_cache("translate")

    first = manager.get_column_cache("translate", "status")
    first["pending"] = "Pending"

    second = manager.get_column_cache("translate", "status")
    assert second is first
    assert func_cache["status"] is second


def test_get_column_cache_creates_missing_bucket(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("translate", "status")
    assert bucket == {}
    assert isinstance(bucket, dict)

    bucket["pending"] = "Pending"
    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}

    other = manager.get_column_cache("translate", "coordinates")
    assert other == {}
    assert other is not bucket


def test_get_column_cache_preserves_explicit_none_value(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    bucket = manager.get_column_cache("translate", "status")

    bucket["missing"] = None

    assert "missing" in bucket
    assert bucket["missing"] is None
    assert dict(bucket) == {"missing": None}
    assert list(bucket) == ["missing"]
    bucket["pending"] = "Pending"
    assert sorted(bucket) == ["missing", "pending"]

    assert manager.get_column_cache("translate", "status") == {"missing": None, "pending": "Pending"}


def test_get_column_cache_missing_function_creates_empty_bucket(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("ghost", "status")
    assert bucket == {}

    bucket["pending"] = "Pending"
    assert manager.get_column_cache("ghost", "status") is bucket
    assert manager.load_function_cache("ghost") == {"status": {"pending": "Pending"}}


def test_cache_manager_constructor_validation_rejects_non_string_and_empty():
    with pytest.raises(TypeError, match="cache_dir must be a string or path-like object"):
        CacheManager(12345)

    with pytest.raises(ValueError, match="cache_dir cannot be empty"):
        CacheManager("   ")


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

