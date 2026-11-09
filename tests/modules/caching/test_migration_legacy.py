import json
import logging
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _rows, _seed_cache_entries


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


@pytest.mark.parametrize("content", ["{not json", "[1, 2]"])
def test_legacy_migration_quarantines_corrupt_source_without_marker(tmp_path, content, caplog):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source = cache_dir / "broken_cache.json"
    source.write_text(content, encoding="utf-8")

    CacheManager(cache_dir)._migrate_legacy_json_cache("broken")

    assert not source.exists()
    assert len(list(cache_dir.glob("broken_cache.json.corrupt.*"))) == 1
    assert "marker" not in caplog.text.lower()
    assert not (cache_dir / "cache.sqlite3").exists()


def test_legacy_migration_preserves_unsupported_source_for_retry(tmp_path, caplog):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source = cache_dir / "translate_cache.json"
    source.write_text('{"status": ["bad"]}', encoding="utf-8")
    manager = CacheManager(cache_dir)

    manager._migrate_legacy_json_cache("translate")
    assert source.exists()
    assert "unsupported" in caplog.text
    assert not (cache_dir / "cache.sqlite3").exists()

    source.write_text('{"status": {"ok": null}}', encoding="utf-8")
    manager._migrate_legacy_json_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (1,)


def test_legacy_migration_rolls_back_and_can_retry_after_partial_insert_failure(
    tmp_path, monkeypatch
):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "translate_cache.json").write_text(
        '{"status": {"a": 1, "b": 2}}', encoding="utf-8"
    )
    manager = CacheManager(cache_dir)
    real_connect = manager._connect_sqlite
    state = {"failed": False, "inserted_rows": 0}

    class PartiallyFailingConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, parameters=()):
            return self.connection.execute(statement, parameters)

        def executemany(self, statement, parameters):
            if not state["failed"] and "INSERT OR IGNORE" in statement:
                rows = list(parameters)
                self.connection.execute(statement, rows[0])
                state["inserted_rows"] = 1
                state["failed"] = True
                raise sqlite3.OperationalError("insert failure")
            return self.connection.executemany(statement, parameters)

        def __getattr__(self, name):
            return getattr(self.connection, name)

    monkeypatch.setattr(
        manager, "_connect_sqlite", lambda: PartiallyFailingConnection(real_connect())
    )
    with pytest.raises(sqlite3.OperationalError, match="insert failure"):
        manager._migrate_legacy_json_cache("translate")

    assert state["inserted_rows"] == 1
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM migration_metadata").fetchone() == (0,)

    manager._migrate_legacy_json_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY key"
        ).fetchall() == [("status", "a", "1"), ("status", "b", "2")]
        assert connection.execute(
            "SELECT source_name FROM migration_metadata"
        ).fetchall() == [("translate_cache.json",)]


def test_legacy_migration_rolls_back_and_can_retry_after_marker_insert_failure(
    tmp_path, monkeypatch
):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "translate_cache.json").write_text(
        '{"status": {"a": 1, "b": 2}}', encoding="utf-8"
    )
    manager = CacheManager(cache_dir)
    real_connect = manager._connect_sqlite
    state = {"failed": False, "entry_rows": 0, "marker_attempted": False}

    class MarkerFailingConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, parameters=()):
            normalized = " ".join(statement.split()).upper()
            if not state["failed"] and normalized.startswith(
                "INSERT INTO MIGRATION_METADATA"
            ):
                state["failed"] = True
                state["marker_attempted"] = True
                raise sqlite3.OperationalError("marker insert failure")
            return self.connection.execute(statement, parameters)

        def executemany(self, statement, parameters):
            if "INSERT OR IGNORE" in statement:
                rows = list(parameters)
                state["entry_rows"] = len(rows)
                return self.connection.executemany(statement, rows)
            return self.connection.executemany(statement, parameters)

        def __getattr__(self, name):
            return getattr(self.connection, name)

    monkeypatch.setattr(
        manager, "_connect_sqlite", lambda: MarkerFailingConnection(real_connect())
    )
    with pytest.raises(sqlite3.OperationalError, match="marker insert failure"):
        manager._migrate_legacy_json_cache("translate")

    assert state["entry_rows"] == 2
    assert state["marker_attempted"]
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM migration_metadata").fetchone() == (0,)

    manager._migrate_legacy_json_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (2,)
        assert connection.execute(
            "SELECT source_name FROM migration_metadata"
        ).fetchall() == [("translate_cache.json",)]


def test_legacy_migration_rolls_back_and_can_retry_after_commit_failure(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "translate_cache.json").write_text(
        '{"status": {"ok": true}}', encoding="utf-8"
    )
    manager = CacheManager(cache_dir)
    real_connect = manager._connect_sqlite
    state = {"commits": 0}

    class CommitFailingConnection:
        def __init__(self, connection):
            self.connection = connection

        def commit(self):
            state["commits"] += 1
            if state["commits"] == 2:
                raise sqlite3.OperationalError("commit failure")
            return self.connection.commit()

        def __getattr__(self, name):
            return getattr(self.connection, name)

    monkeypatch.setattr(
        manager, "_connect_sqlite", lambda: CommitFailingConnection(real_connect())
    )
    with pytest.raises(sqlite3.OperationalError, match="commit failure"):
        manager._migrate_legacy_json_cache("translate")

    monkeypatch.undo()
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM migration_metadata").fetchone() == (0,)
    manager._migrate_legacy_json_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM migration_metadata").fetchone() == (1,)




def test_delete_column_cache_persists_existing_bucket_removal(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [
            ("status", "pending", '"Pending"'),
            ("status", "done", '"Done"'),
            ("coordinates", "home", "[1.5, 2]"),
        ],
    )

    manager.delete_column_cache("translate", "status")

    assert _rows(manager) == [("coordinates", "home", "[1.5, 2]")]

    reloaded = CacheManager(cache_dir)
    assert "status" not in reloaded.load_function_cache("translate")


def test_delete_column_cache_leaves_unrelated_buckets_intact(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [
            ("status", "pending", '"Pending"'),
            ("coordinates", "home", "[1.5, 2]"),
            ("meta", "count", "3"),
        ],
    )

    manager.delete_column_cache("translate", "status")

    assert _rows(manager) == [
        ("coordinates", "home", "[1.5, 2]"),
        ("meta", "count", "3"),
    ]


def test_delete_column_cache_leaves_unrelated_function_intact(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(manager, "translate", [("status", "pending", '"Pending"')])
    _seed_cache_entries(manager, "summarize", [("notes", "body", '"Body"')])

    manager.delete_column_cache("translate", "status")

    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT func_name, bucket, key, value_json "
            "FROM cache_entries ORDER BY func_name, bucket, key"
        ).fetchall()

    assert rows == [("summarize", "notes", "body", '"Body"')]


def test_delete_column_cache_missing_bucket_is_a_no_op(tmp_path, caplog):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(manager, "translate", [("status", "pending", '"Pending"')])

    with caplog.at_level(logging.INFO, logger="bynat.caching.Caching"):
        manager.delete_column_cache("translate", "missing")

    assert "No cache found for column 'missing'" in caplog.text
    assert _rows(manager) == [("status", "pending", '"Pending"')]


def test_delete_column_cache_failed_transaction_is_retryable(tmp_path, monkeypatch, caplog):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [("status", "pending", '"Pending"'), ("status", "done", '"Done"')],
    )
    manager.load_function_cache("translate")
    baseline_before = manager._baselines["translate"]

    real_connect = manager._connect_sqlite
    state = {"commits": 0}

    class CommitFailingConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, parameters=()):
            return self.connection.execute(statement, parameters)

        def executemany(self, statement, parameters):
            return self.connection.executemany(statement, parameters)

        def commit(self):
            state["commits"] += 1
            if state["commits"] == 2:
                raise sqlite3.OperationalError("commit failure")
            return self.connection.commit()

        def rollback(self):
            return self.connection.rollback()

        def close(self):
            return self.connection.close()

        def __getattr__(self, name):
            return getattr(self.connection, name)

    monkeypatch.setattr(
        manager, "_connect_sqlite", lambda: CommitFailingConnection(real_connect())
    )
    manager.delete_column_cache("translate", "status")

    assert "commit failure" in caplog.text
    assert "status" not in manager.caches["translate"]
    assert manager._baselines["translate"] is baseline_before
    assert _rows(manager) == [
        ("status", "done", '"Done"'),
        ("status", "pending", '"Pending"'),
    ]

    monkeypatch.undo()
    manager.save_function_cache("translate")

    assert _rows(manager) == []
    assert manager._baselines["translate"] == {}
