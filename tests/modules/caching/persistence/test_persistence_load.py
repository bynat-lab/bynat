import json
import sqlite3

import pytest

from bynat.caching import CacheManager

pytestmark = pytest.mark.integration


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
