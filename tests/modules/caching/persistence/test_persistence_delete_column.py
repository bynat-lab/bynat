import logging
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _rows, _seed_cache_entries

pytestmark = pytest.mark.integration


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
