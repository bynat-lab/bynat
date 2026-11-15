import json
import sqlite3

import pytest

from bynat.caching import CacheManager

pytestmark = pytest.mark.integration


def test_legacy_migration_imports_supported_values_and_maps_filename(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "translate_cache.json").write_text(
        json.dumps({
            "status": {"pending": "Pending", "missing": None},
            "coordinates": {"home": [1.5, 2], "nested": {"ok": True}},
        }),
        encoding="utf-8",
    )

    manager = CacheManager(cache_dir)
    manager._migrate_legacy_json_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT func_name, bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall()
        marker = connection.execute(
            "SELECT source_name FROM migration_metadata"
        ).fetchall()

    assert rows == [
        ("translate", "coordinates", "home", "[1.5, 2]"),
        ("translate", "coordinates", "nested", '{"ok": true}'),
        ("translate", "status", "missing", "null"),
        ("translate", "status", "pending", '"Pending"'),
    ]
    assert marker == [("translate_cache.json",)]


def test_legacy_migration_is_idempotent_and_existing_rows_win(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    manager = CacheManager(cache_dir)
    manager._initialize_sqlite()
    with sqlite3.connect(manager._get_database_path()) as connection:
        connection.execute(
            "INSERT INTO cache_entries VALUES (?, ?, ?, ?, ?)",
            ("translate", "status", "pending", '"fresh"', "old"),
        )
        connection.commit()
    (cache_dir / "translate_cache.json").write_text(
        '{"status": {"pending": "stale", "new": 3}}', encoding="utf-8"
    )

    manager._migrate_legacy_json_cache("translate")
    manager._migrate_legacy_json_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'status' AND key = 'pending'"
        ).fetchone() == ('"fresh"',)
        assert connection.execute(
            "SELECT count(*) FROM cache_entries"
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT count(*) FROM migration_metadata"
        ).fetchone() == (1,)


def test_missing_legacy_source_does_not_create_database_or_marker(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    manager._migrate_legacy_json_cache("missing")

    assert not (tmp_path / "cache").exists()
