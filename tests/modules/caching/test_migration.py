import json
import logging
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _rows, _seed_cache_entries


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

        # PRAGMA rows are keyed by column name: the schema contract is which
        # columns exist, their types, and their NOT NULL / primary-key roles,
        # not the physical column order. A behavior-preserving reorder of the
        # DDL must not fail this test; dropping a column, relaxing NOT NULL, or
        # changing the primary-key membership must.
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
            assert row[3] == 1, name  # NOT NULL
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
        assert metadata_columns["source_name"][5] == 1  # PRIMARY KEY
        assert metadata_columns["migrated_at"][2] == "TEXT"
        assert metadata_columns["migrated_at"][3] == 1  # NOT NULL
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
    import importlib

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


# ``delete_column_cache`` is validated through two sequential ``CacheManager``
# instances rather than real processes. The D-06 identity-scope rule asks which
# rows a bucket deletion removes, and that set is a deterministic function of the
# deleting manager's in-memory baseline snapshot: ``save_function_cache`` only
# ever issues per-identity ``DELETE`` rows, so a key that is absent from the
# baseline is never a deletion target regardless of when it was committed. Two
# managers sharing one SQLite file reproduce the exact shared-state interaction a
# race would (one manager commits rows the other never saw), while the set of
# rows deleted depends only on each manager's baseline, not on process
# scheduling. The genuine cross-process atomicity of those committed writes is
# already covered by the multiprocessing migration tests and SQLite's
# ``BEGIN IMMEDIATE``; re-proving it here would add nondeterminism without
# exercising any additional branch of the identity-scope rule.


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

    # Every row of the named bucket is removed row-by-row and the change commits,
    # so the deletion is durable on the next manager that reads the same database.
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

    # Only the named bucket's rows are removed; unrelated buckets are untouched.
    assert _rows(manager) == [
        ("coordinates", "home", "[1.5, 2]"),
        ("meta", "count", "3"),
    ]


def test_delete_column_cache_leaves_unrelated_function_intact(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    # Two independent function caches share one database; the deleting manager
    # loads only "translate", so its baseline never knows the other function.
    _seed_cache_entries(manager, "translate", [("status", "pending", '"Pending"')])
    _seed_cache_entries(manager, "summarize", [("notes", "body", '"Body"')])

    manager.delete_column_cache("translate", "status")

    # ``save_function_cache`` only issues per-identity DELETEs tagged with the
    # loading func_name, so the unrelated function's row is never a delete
    # target: only the "translate" row is gone, "summarize" survives.
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

    # A bucket that is not present deletes nothing and persists nothing; the sole
    # existing row is unchanged.
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
    # Load first so the baseline is captured with the real connection, then hold
    # it to prove the failed deletion does not advance it.
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
            # The first commit belongs to _initialize_sqlite; the deletion
            # transaction's commit is the second and fails.
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
    # The in-memory bucket stays deleted, but the transaction rolled back, so the
    # baseline is unchanged and the rows survive for a later retry.
    assert "status" not in manager.caches["translate"]
    assert manager._baselines["translate"] is baseline_before
    assert _rows(manager) == [
        ("status", "done", '"Done"'),
        ("status", "pending", '"Pending"'),
    ]

    monkeypatch.undo()
    manager.save_function_cache("translate")

    # The retry re-diffs against the same unchanged baseline and now succeeds.
    assert _rows(manager) == []
    assert manager._baselines["translate"] == {}
