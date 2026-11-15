import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _seed_cache_entries

pytestmark = pytest.mark.integration



def test_failed_removal_transaction_rolls_back_and_retries(tmp_path, monkeypatch, caplog):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    _seed_cache_entries(
        manager,
        "translate",
        [("status", "pending", '"Pending"'), ("status", "done", '"Done"')],
    )
    live = manager.load_function_cache("translate")
    baseline_before = manager._baselines["translate"]

    del live["status"]["done"]

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
    manager.save_function_cache("translate")

    assert "commit failure" in caplog.text
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'status' AND key = 'done'"
        ).fetchone() == ('"Done"',)
    assert manager._baselines["translate"] is baseline_before

    monkeypatch.undo()
    manager.save_function_cache("translate")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'status' AND key = 'done'"
        ).fetchone() is None
    assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}


@pytest.mark.parametrize(
    "content, expected_log",
    [
        ("{not valid json", "is corrupted; moved it to"),
        ("", "is corrupted; moved it to"),
        ("[1, 2]", "has an invalid top-level JSON value; moved it to"),
        (b"\xff\xfe garbage", "is corrupted; moved it to"),
    ],
)
def test_corrupt_cache_is_quarantined_and_replaced_with_empty_dict(tmp_path, caplog, content, expected_log):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_file = cache_dir / "broken_cache.json"
    if isinstance(content, bytes):
        cache_file.write_bytes(content)
    else:
        cache_file.write_text(content, encoding="utf-8")

    manager = CacheManager(cache_dir)
    assert manager.load_function_cache("broken") == {}
    assert expected_log in caplog.text

    quarantined = list(cache_dir.glob("broken_cache.json.corrupt.*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == (
        content if isinstance(content, bytes) else content.encode("utf-8")
    )

    manager.get_column_cache("broken", "column")["key"] = "value"
    manager.save_function_cache("broken")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall() == [("column", "key", '"value"')]
    assert quarantined[0].exists()


def test_save_unserializable_value_reports_error_without_raising(tmp_path, caplog):
    manager = CacheManager(tmp_path)
    manager.get_column_cache("function", "column")["bad"] = object()
    baseline_before = manager._baselines["function"]

    manager.save_function_cache("function")

    assert "Could not save cache for" in caplog.text

    assert manager._baselines["function"] is baseline_before
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (0,)

    manager.get_column_cache("function", "column")["bad"] = "now serializable"
    manager.save_function_cache("function")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'bad'"
        ).fetchone() == ('"now serializable"',)


def test_failed_db_save_keeps_baseline_and_rows_intact_for_retry(tmp_path, monkeypatch, caplog):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    manager.get_column_cache("function", "column")["good"] = "value"
    manager.save_function_cache("function")
    baseline_before = manager._baselines["function"]

    manager.get_column_cache("function", "column")["good"] = "updated"

    real_connect = manager._connect_sqlite

    class WriteFailingConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, statement, parameters=()):
            return self.connection.execute(statement, parameters)

        def executemany(self, statement, parameters):
            raise sqlite3.OperationalError("simulated write failure")

        def commit(self):
            return self.connection.commit()

        def rollback(self):
            return self.connection.rollback()

        def close(self):
            return self.connection.close()

        def __getattr__(self, name):
            return getattr(self.connection, name)

    monkeypatch.setattr(
        manager, "_connect_sqlite", lambda: WriteFailingConnection(real_connect())
    )
    manager.save_function_cache("function")

    assert "Could not save cache for" in caplog.text
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'good'"
        ).fetchone() == ('"value"',)
    assert manager._baselines["function"] is baseline_before

    monkeypatch.undo()
    manager.save_function_cache("function")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'good'"
        ).fetchone() == ('"updated"',)
    assert manager._baselines["function"] is not baseline_before


def test_save_transaction_rolls_back_on_commit_failure(tmp_path, monkeypatch, caplog):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    manager.get_column_cache("function", "column")["good"] = "value"
    manager.save_function_cache("function")
    baseline_before = manager._baselines["function"]

    manager.get_column_cache("function", "column")["good"] = "updated"

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
    manager.save_function_cache("function")

    assert "commit failure" in caplog.text
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'good'"
        ).fetchone() == ('"value"',)
    assert manager._baselines["function"] is baseline_before

    monkeypatch.undo()
    manager.save_function_cache("function")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'good'"
        ).fetchone() == ('"updated"',)


def test_save_serialization_failure_keeps_prior_checkpoint_readable(tmp_path, caplog):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)
    manager.get_column_cache("function", "column")["good"] = "value"
    manager.save_function_cache("function")
    baseline_before = manager._baselines["function"]

    manager.get_column_cache("function", "column")["bad"] = object()
    manager.save_function_cache("function")

    assert "Could not save cache for" in caplog.text
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'good'"
        ).fetchone() == ('"value"',)
    assert manager._baselines["function"] is baseline_before
