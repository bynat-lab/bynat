import importlib
import sqlite3

import pytest

from bynat.caching import CacheManager

pytestmark = pytest.mark.integration



def test_sqlite_initialization_is_lazy_until_explicitly_requested(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    assert not cache_dir.exists()

    manager._initialize_sqlite()

    assert (cache_dir / "cache.sqlite3").exists()


def test_sqlite_schema_has_required_tables_columns_keys_and_index(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    manager._initialize_sqlite()

    with sqlite3.connect(manager._get_database_path()) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"cache_entries", "migration_metadata"}.issubset(tables)

        cache_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(cache_entries)")
        }
        assert set(cache_columns) == {
            "func_name",
            "bucket",
            "key",
            "value_json",
            "created_at",
        }
        for name, row in cache_columns.items():
            assert row[2] == "TEXT", name
            assert row[3] == 1, name
        primary_key_columns = {
            name for name, row in cache_columns.items() if row[5]
        }
        assert primary_key_columns == {"func_name", "bucket", "key"}

        metadata_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(migration_metadata)")
        }
        assert set(metadata_columns) == {"source_name", "migrated_at"}
        assert metadata_columns["source_name"][2] == "TEXT"
        assert metadata_columns["source_name"][5] == 1
        assert metadata_columns["migrated_at"][2] == "TEXT"
        assert metadata_columns["migrated_at"][3] == 1
        assert metadata_columns["migrated_at"][5] == 0

        indexes = connection.execute(
            "PRAGMA index_list(cache_entries)"
        ).fetchall()
        index_names = {row[1] for row in indexes}
        assert "idx_cache_entries_func_bucket" in index_names
        indexed_columns = {
            row[2]
            for row in connection.execute(
                "PRAGMA index_info(idx_cache_entries_func_bucket)"
            )
        }
        assert indexed_columns == {"func_name", "bucket"}


def test_sqlite_connection_configures_timeout_wal_and_full_synchronous(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    (tmp_path / "cache").mkdir()

    connection = manager._connect_sqlite()
    try:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
    finally:
        connection.close()


def test_sqlite_connection_closes_when_pragma_configuration_fails(tmp_path, monkeypatch):
    caching_module = importlib.import_module("bynat.caching.Caching")

    class FailingConnection:
        def __init__(self):
            self.execute_calls = []
            self.close_called = False

        def execute(self, statement):
            self.execute_calls.append(statement)
            if len(self.execute_calls) == 2:
                raise sqlite3.OperationalError("PRAGMA failure")
            return None

        def close(self):
            self.close_called = True

    connection = FailingConnection()
    monkeypatch.setattr(caching_module.sqlite3, "connect", lambda *args, **kwargs: connection)

    with pytest.raises(sqlite3.OperationalError, match="PRAGMA failure"):
        CacheManager(tmp_path / "cache")._connect_sqlite()

    assert connection.close_called


def test_sqlite_initialization_rolls_back_and_closes_on_failure(tmp_path, monkeypatch):
    manager = CacheManager(tmp_path / "cache")

    class FailingConnection:
        def __init__(self):
            self.rollback_called = False
            self.close_called = False

        def execute(self, statement):
            if statement == "BEGIN IMMEDIATE":
                return None
            raise sqlite3.OperationalError("schema failure")

        def rollback(self):
            self.rollback_called = True

        def close(self):
            self.close_called = True

    connection = FailingConnection()
    monkeypatch.setattr(manager, "_connect_sqlite", lambda: connection)

    with pytest.raises(sqlite3.OperationalError, match="schema failure"):
        manager._initialize_sqlite()

    assert connection.rollback_called
    assert connection.close_called


def test_sqlite_initialization_rolls_back_real_ddl_on_later_schema_failure(tmp_path, monkeypatch):
    manager = CacheManager(tmp_path / "cache")
    (tmp_path / "cache").mkdir()
    real_connection = sqlite3.connect(manager._get_database_path())

    class FailingSchemaConnection:
        def __init__(self, connection):
            self.connection = connection
            self.first_ddl_completed = False
            self.rollback_called = False
            self.close_called = False

        def execute(self, statement):
            normalized = " ".join(statement.split()).upper()
            if normalized.startswith("CREATE TABLE"):
                result = self.connection.execute(statement)
                self.first_ddl_completed = True
                return result
            if normalized.startswith("CREATE INDEX"):
                raise sqlite3.OperationalError("later schema failure")
            return self.connection.execute(statement)

        def rollback(self):
            self.rollback_called = True
            self.connection.rollback()

        def close(self):
            self.close_called = True
            self.connection.close()

        def commit(self):
            return self.connection.commit()

    connection = FailingSchemaConnection(real_connection)
    monkeypatch.setattr(manager, "_connect_sqlite", lambda: connection)

    with pytest.raises(sqlite3.OperationalError, match="later schema failure"):
        manager._initialize_sqlite()

    assert connection.first_ddl_completed
    assert connection.rollback_called
    assert connection.close_called

    with sqlite3.connect(manager._get_database_path()) as inspection:
        schema_objects = inspection.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE type IN ('table', 'index') "
            "AND name IN ('cache_entries', 'migration_metadata', 'idx_cache_entries_func_bucket')"
        ).fetchall()
    assert schema_objects == []


def test_sqlite_initialization_rolls_back_and_closes_when_commit_fails(tmp_path, monkeypatch):
    manager = CacheManager(tmp_path / "cache")

    class CommitFailingConnection:
        def __init__(self):
            self.rollback_called = False
            self.close_called = False

        def execute(self, statement):
            return None

        def commit(self):
            raise sqlite3.OperationalError("commit failure")

        def rollback(self):
            self.rollback_called = True

        def close(self):
            self.close_called = True

    connection = CommitFailingConnection()
    monkeypatch.setattr(manager, "_connect_sqlite", lambda: connection)

    with pytest.raises(sqlite3.OperationalError, match="commit failure"):
        manager._initialize_sqlite()

    assert connection.rollback_called
    assert connection.close_called


def test_repeated_sqlite_initialization_is_safe(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    manager._initialize_sqlite()
    manager._initialize_sqlite()

    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type IN ('table', 'index') AND name IN "
            "('cache_entries', 'migration_metadata', 'idx_cache_entries_func_bucket')"
        ).fetchone()[0] == 3
