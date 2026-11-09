import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _seed_cache_entries

pytestmark = pytest.mark.integration



def test_load_function_cache_records_baseline_matching_loaded_state(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    _seed_cache_entries(
        manager,
        "translate",
        [
            ("coordinates", "home", "[1.5, 2]"),
            ("status", "nested", '{"ok": true}'),
        ],
    )

    loaded = manager.load_function_cache("translate")

    assert manager._baselines["translate"] == {
        "coordinates": {"home": [1.5, 2]},
        "status": {"nested": {"ok": True}},
    }
    assert manager._baselines["translate"] == loaded


def test_baseline_is_deep_copy_and_survives_nested_mutation(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    _seed_cache_entries(
        manager,
        "translate",
        [
            ("coordinates", "home", "[1.5, 2]"),
            ("status", "nested", '{"ok": true}'),
        ],
    )

    loaded = manager.load_function_cache("translate")

    loaded["coordinates"]["home"].append(99)
    loaded["coordinates"]["home"][0] = 0
    loaded["status"]["nested"]["ok"] = False
    loaded["status"]["nested"]["extra"] = "added"
    loaded["coordinates"]["new"] = {"deep": [1, 2]}

    assert manager._baselines["translate"] == {
        "coordinates": {"home": [1.5, 2]},
        "status": {"nested": {"ok": True}},
    }


def test_separate_functions_have_separate_baselines(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    _seed_cache_entries(
        manager,
        "translate",
        [("status", "pending", '"Pending"')],
    )
    _seed_cache_entries(
        manager,
        "other",
        [("status", "pending", '"Other"')],
    )

    translate = manager.load_function_cache("translate")
    manager.load_function_cache("other")

    assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}
    assert manager._baselines["other"] == {"status": {"pending": "Other"}}
    assert manager._baselines["translate"] is not manager._baselines["other"]
    assert manager._baselines["translate"] != manager._baselines["other"]

    translate["status"]["pending"] = "Done"
    assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}
    assert manager._baselines["other"] == {"status": {"pending": "Other"}}


def test_save_detects_nested_mutation_and_writes_only_changed_entries(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    seed_at = "2026-01-01T00:00:00+00:00"
    manager._initialize_sqlite()
    with sqlite3.connect(manager._get_database_path()) as connection:
        connection.execute(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            ("translate", "coordinates", "home", "[1.5, 2]", seed_at),
        )
        connection.execute(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            ("translate", "status", "nested", '{"ok": true}', seed_at),
        )
        connection.commit()

    live = manager.load_function_cache("translate")
    live["status"]["nested"]["ok"] = False
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        by_key = {
            row[1]: row
            for row in connection.execute(
                "SELECT bucket, key, value_json, created_at FROM cache_entries"
            ).fetchall()
        }

    assert by_key["home"] == ("coordinates", "home", "[1.5, 2]", seed_at)
    assert by_key["nested"][2] == '{"ok": false}'
    assert by_key["nested"][3] != seed_at


def test_save_advances_baseline_after_success(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(manager, "translate", [("status", "pending", '"Pending"')])

    live = manager.load_function_cache("translate")
    assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}

    live["status"]["pending"] = "Done"
    live["status"]["extra"] = "Added"
    manager.save_function_cache("translate")

    assert manager._baselines["translate"] == {"status": {"pending": "Done", "extra": "Added"}}

    live["status"]["pending"] = "Later"
    assert manager._baselines["translate"] == {"status": {"pending": "Done", "extra": "Added"}}


def test_save_conflict_update_last_writer_wins_and_disjoint_merge(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(manager, "translate", [("bucket", "a", '"A0"'), ("bucket", "c", '"C0"')])

    left = CacheManager(cache_dir)
    right = CacheManager(cache_dir)
    left_live = left.load_function_cache("translate")
    right_live = right.load_function_cache("translate")

    left_live["bucket"]["a"] = "A1"
    left.save_function_cache("translate")
    right_live["bucket"]["c"] = "C1"
    right.save_function_cache("translate")

    reloaded = CacheManager(cache_dir).load_function_cache("translate")
    assert reloaded == {"bucket": {"a": "A1", "c": "C1"}}

    left_live["bucket"]["a"] = "A2"
    left.save_function_cache("translate")
    right_live["bucket"]["a"] = "A3"
    right.save_function_cache("translate")

    reloaded = CacheManager(cache_dir).load_function_cache("translate")
    assert reloaded["bucket"]["a"] == "A3"
    assert reloaded["bucket"]["c"] == "C1"
