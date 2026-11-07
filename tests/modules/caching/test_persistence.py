import json
import sqlite3

import pytest

from bynat.caching import CacheManager
from tests.modules.caching.helpers import _seed_cache_entries


def test_cache_round_trip_via_sqlite(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("translate", "status")
    bucket["pending"] = "Pending"
    manager.save_function_cache("translate")

    reloaded = CacheManager(tmp_path / "cache")
    assert reloaded.load_function_cache("translate") == {
        "status": {"pending": "Pending"},
    }
    # The entry now lives in SQLite rather than a JSON cache file.
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
    live["status"]["done"] = "Yes"          # changed
    live["status"]["new"] = "Fresh"          # added
    del live["status"]["stale"]              # removed
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY bucket, key"
        ).fetchall()

    # The changed and added entries are written and the removed key is deleted,
    # all within one save.
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
    del live["coordinates"]                  # the whole bucket is gone
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        identities = connection.execute(
            "SELECT bucket, key FROM cache_entries ORDER BY bucket, key"
        ).fetchall()
        # Removal is per-identity, never a broad bucket delete, so a DELETE on
        # the bucket column alone would be detectable; here every coordinates
        # row is gone while unrelated rows survive.
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
    del live["status"]["done"]               # removal with no additions or changes
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        rows = connection.execute(
            "SELECT bucket, key, value_json FROM cache_entries ORDER BY key"
        ).fetchall()

    # A save carrying only a removal is not short-circuited by an early return.
    assert rows == [("status", "pending", '"Pending"')]


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
            # The first commit belongs to _initialize_sqlite; the removal
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
    manager.save_function_cache("translate")

    assert "commit failure" in caplog.text
    # The deletion is rolled back, so the row survives and the baseline is not
    # advanced, leaving the pending removal for a later retry.
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

    # After a successful removal the baseline advances and no longer lists it.
    assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}

    # Re-adding the key is now a fresh addition against the advanced baseline and
    # is re-persisted rather than treated as a no-op.
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


@pytest.mark.parametrize(
    "content, expected_log",
    [
        ("{not valid json", "is corrupted; moved it to"),
        ("", "is corrupted; moved it to"),
        # A valid-but-non-object top-level value is now reported by the accepted
        # legacy migration helper, which still quarantines and replaces it.
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

    # Saving afterwards persists a fresh entry in SQLite and leaves the
    # quarantined copy alone.
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

    # The failed serialization leaves the baseline unchanged and the pending
    # in-memory change in place, so a later serializable save can persist it.
    assert manager._baselines["function"] is baseline_before
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute("SELECT count(*) FROM cache_entries").fetchone() == (0,)

    manager.get_column_cache("function", "column")["bad"] = "now serializable"
    manager.save_function_cache("function")
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'bad'"
        ).fetchone() == ('"now serializable"',)


def test_cache_directory_is_created_on_save_not_construction(tmp_path):
    cache_dir = tmp_path / "not-yet-created"
    CacheManager(cache_dir)
    assert not cache_dir.exists()

    manager = CacheManager(cache_dir)
    # In-memory changes exist without a prior load; saving them creates the
    # backend directory and SQLite database.
    manager.caches["function"] = {"column": {"key": "value"}}
    manager.save_function_cache("function")
    assert (cache_dir / "cache.sqlite3").exists()


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
    # The previously committed rows survive and the baseline is not advanced, so
    # the pending in-memory change is preserved for a later retry.
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
            # The first commit belongs to _initialize_sqlite; the write
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
    manager.save_function_cache("function")

    assert "commit failure" in caplog.text
    # The rows inserted inside the failed transaction are rolled back, leaving
    # only the previously committed value behind.
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

    # Serialization runs before any DB write, so a value that cannot be
    # serialized aborts the whole save without opening a connection. The
    # previously committed checkpoint and the baseline must be untouched.
    manager.get_column_cache("function", "column")["bad"] = object()
    manager.save_function_cache("function")

    assert "Could not save cache for" in caplog.text
    with sqlite3.connect(manager._get_database_path()) as connection:
        assert connection.execute(
            "SELECT value_json FROM cache_entries WHERE bucket = 'column' AND key = 'good'"
        ).fetchone() == ('"value"',)
    assert manager._baselines["function"] is baseline_before


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
        # Multiple buckets, explicit None, list and dict values, plus a scalar.
        ("translate", "status", "pending", '"Pending"', created_at),
        ("translate", "status", "missing", "null", created_at),
        ("translate", "coordinates", "home", "[1.5, 2]", created_at),
        ("translate", "coordinates", "nested", '{"ok": true}', created_at),
        ("translate", "meta", "count", "3", created_at),
        # A different function must not leak into the rebuild.
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

    # First public access migrates the legacy JSON and returns it as a dict.
    assert manager.load_function_cache("translate") == {
        "status": {"pending": "Pending", "missing": None}
    }

    # The backend was created and the read is now backed by SQLite rows.
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

    # A missing function returns an empty dict yet still creates the backend.
    assert manager.load_function_cache("ghost") == {}
    assert (cache_dir / "cache.sqlite3").exists()

    # A second missing function also returns empty without error.
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

    # No legacy JSON file exists; the public read is served from SQLite.
    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}


def test_load_function_cache_memoizes_and_preserves_mutations(tmp_path):
    cache_dir = tmp_path / "cache"
    manager = CacheManager(cache_dir)

    first = manager.load_function_cache("translate")
    first["status"] = {"pending": "Pending"}

    second = manager.load_function_cache("translate")

    # Memoized: same object, mutations preserved across calls.
    assert second is first
    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}


def test_get_column_cache_returns_existing_bucket_identity(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    func_cache = manager.load_function_cache("translate")

    first = manager.get_column_cache("translate", "status")
    first["pending"] = "Pending"

    # The second lookup returns the very same bucket object, and it is the one
    # stored inside the memoized function cache.
    second = manager.get_column_cache("translate", "status")
    assert second is first
    assert func_cache["status"] is second


def test_get_column_cache_creates_missing_bucket(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    bucket = manager.get_column_cache("translate", "status")
    assert bucket == {}
    assert isinstance(bucket, dict)

    # The freshly created bucket lives inside the function cache so mutations
    # are visible through the memoized mapping.
    bucket["pending"] = "Pending"
    assert manager.load_function_cache("translate") == {"status": {"pending": "Pending"}}

    # A different bucket for the same function is an independent empty dict.
    other = manager.get_column_cache("translate", "coordinates")
    assert other == {}
    assert other is not bucket


def test_get_column_cache_preserves_explicit_none_value(tmp_path):
    manager = CacheManager(tmp_path / "cache")
    bucket = manager.get_column_cache("translate", "status")

    bucket["missing"] = None

    # Ordinary mutable-dict behaviors all observe the explicit None value.
    assert "missing" in bucket            # membership
    assert bucket["missing"] is None      # get
    assert dict(bucket) == {"missing": None}  # equality
    assert list(bucket) == ["missing"]    # iteration
    bucket["pending"] = "Pending"
    assert sorted(bucket) == ["missing", "pending"]

    # The None value survives through the memoized function cache.
    assert manager.get_column_cache("translate", "status") == {"missing": None, "pending": "Pending"}


def test_get_column_cache_missing_function_creates_empty_bucket(tmp_path):
    manager = CacheManager(tmp_path / "cache")

    # A function with no cached entries yields an empty bucket that can be
    # populated in place, memoized within the manager.
    bucket = manager.get_column_cache("ghost", "status")
    assert bucket == {}

    bucket["pending"] = "Pending"
    assert manager.get_column_cache("ghost", "status") is bucket
    assert manager.load_function_cache("ghost") == {"status": {"pending": "Pending"}}


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

    # The baseline snapshot equals the state that was successfully loaded.
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

    # Mutate nested lists and dicts in place, plus add new nested entries.
    loaded["coordinates"]["home"].append(99)
    loaded["coordinates"]["home"][0] = 0
    loaded["status"]["nested"]["ok"] = False
    loaded["status"]["nested"]["extra"] = "added"
    loaded["coordinates"]["new"] = {"deep": [1, 2]}

    # The baseline snapshot is unchanged despite the nested mutations.
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

    # Mutating one function's live cache leaves the other function's baseline
    # untouched, proving the baselines are independent per function.
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
    # Mutate a nested dict field in place rather than reassigning the whole value.
    live["status"]["nested"]["ok"] = False
    manager.save_function_cache("translate")

    with sqlite3.connect(manager._get_database_path()) as connection:
        by_key = {
            row[1]: row
            for row in connection.execute(
                "SELECT bucket, key, value_json, created_at FROM cache_entries"
            ).fetchall()
        }

    # The untouched entry keeps its original value and timestamp.
    assert by_key["home"] == ("coordinates", "home", "[1.5, 2]", seed_at)
    # The nested mutation is detected, re-serialized, and rewritten with a fresh ts.
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

    # After a successful save the baseline advances to a snapshot of the live cache.
    assert manager._baselines["translate"] == {"status": {"pending": "Done", "extra": "Added"}}

    # The advanced baseline is a deep copy: later live mutations do not move it.
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

    # Disjoint keys written by two managers merge into one keyspace.
    left_live["bucket"]["a"] = "A1"
    left.save_function_cache("translate")
    right_live["bucket"]["c"] = "C1"
    right.save_function_cache("translate")

    reloaded = CacheManager(cache_dir).load_function_cache("translate")
    assert reloaded == {"bucket": {"a": "A1", "c": "C1"}}

    # The same key written by both managers resolves to the last committed writer.
    left_live["bucket"]["a"] = "A2"
    left.save_function_cache("translate")
    right_live["bucket"]["a"] = "A3"
    right.save_function_cache("translate")

    reloaded = CacheManager(cache_dir).load_function_cache("translate")
    assert reloaded["bucket"]["a"] == "A3"
    assert reloaded["bucket"]["c"] == "C1"
