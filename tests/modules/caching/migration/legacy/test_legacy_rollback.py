import sqlite3

import pytest

from bynat.caching import CacheManager

pytestmark = pytest.mark.integration


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


def test_legacy_migration_unsupported_serialization_and_locking_retry(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source_file = cache_dir / "translate_cache.json"
    source_file.write_text('{"bucket": {"key": "val"}}', encoding="utf-8")
    manager = CacheManager(cache_dir)

    monkeypatch.setattr("json.dumps", lambda *a, **k: (_ for _ in ()).throw(TypeError("unsupported type")))
    manager._migrate_legacy_json_cache("translate")

    monkeypatch.undo()
    attempts = {"count": 0}
    real_init = manager._initialize_sqlite

    def flaky_init():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise sqlite3.OperationalError("database is locked")
        real_init()

    monkeypatch.setattr(manager, "_initialize_sqlite", flaky_init)
    manager._migrate_legacy_json_cache("translate")
    assert attempts["count"] == 2

    manager._migrate_legacy_cache("translate")
