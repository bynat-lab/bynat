"""TEST-02 Phase 3: real optional-dependency integration coverage.

Exercises the two optional extras that can be verified deterministically and
offline with local fixtures: ``categorization`` (pyahocorasick) and ``sql``
(SQLAlchemy with the standard-library SQLite driver). The remaining extras
(translation, geocoding, currency, nlp) call network services or need a
downloaded model, so they stay with the fake-module tests.

``pytest.importorskip`` isolates each real integration when its extra is
absent. Expected values are derived from the documented behavior.
"""

import sqlite3
import sys
from datetime import datetime

import pandas as pd
import pytest

from bynat.cleaning import BaseData


def _sqlite_arguments(database):
    return {
        "database_type": "sqlite",
        "database_user": "",
        "database_password": "",
        "database_host": "",
        "database_port": "",
        "database_name": str(database),
    }


def _fetch_rows(database, query):
    with sqlite3.connect(database) as connection:
        return connection.execute(query).fetchall()


# ---------------------------------------------------------------------------
# categorization: real pyahocorasick
# ---------------------------------------------------------------------------


def test_categorize_by_reference_prefers_the_longest_matching_keyword(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Data Analyst", "Data", "Data Analyst Assistant"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Data": ["data"], "Software": ["data analyst"]},
    )

    # "data analyst" is the longer match and wins even though "data" also
    # occurs; a shortest-match implementation would label these "Data".
    assert result["family"].tolist() == ["Software", "Data", "Software"]
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_respects_word_boundaries_and_case(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Reactor", "database", "SENIOR REACT DEVELOPER", "Chef"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Software": ["react", "python developer"]},
        default_category="Uncategorized",
    )

    # "react" does not match inside "Reactor" or "database"; the uppercase
    # text matches because the search is case-insensitive.
    assert result["family"].tolist() == [
        "Uncategorized",
        "Uncategorized",
        "Software",
        "Uncategorized",
    ]
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_combines_multiple_source_columns(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {
            "title": ["Data", "Senior", "Chef"],
            "description": ["Analyst", "React Developer", "Nowhere"],
        },
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        "description",
        target_col="family",
        reference={"Data": ["data analyst"], "Software": ["react developer"]},
    )

    assert result["family"].tolist() == ["Data", "Software", "Other"]
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_overwrites_an_existing_target_column(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Data Analyst", "Chef"], "family": ["old", "old"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Data": ["data analyst"]},
    )

    assert result["family"].tolist() == ["Data", "Other"]
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_ignores_blank_keywords(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["data analyst", "python developer", "chef"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Data": ["data", "", None, "   "], "Software": ["python developer"]},
    )

    assert result["family"].tolist() == ["Data", "Software", "Other"]
    pd.testing.assert_frame_equal(frame, before)


# ---------------------------------------------------------------------------
# sql: real SQLAlchemy with the local SQLite driver
# ---------------------------------------------------------------------------


def test_save_to_sql_appends_rows_with_the_default_if_exists(tmp_path):
    pytest.importorskip("sqlalchemy")
    database = tmp_path / "append.db"
    first = BaseData({"a": [1, 2]}, cache_dir=tmp_path)
    second = BaseData({"a": [3]}, cache_dir=tmp_path)

    first.save_to_sql("items", **_sqlite_arguments(database))
    second.save_to_sql("items", **_sqlite_arguments(database))

    assert _fetch_rows(database, "SELECT a FROM items ORDER BY a") == [(1,), (2,), (3,)]


def test_save_to_sql_replaces_rows_with_if_exists_replace(tmp_path):
    pytest.importorskip("sqlalchemy")
    database = tmp_path / "replace.db"
    frame = BaseData({"a": [1, 2], "b": ["x", "y"]}, cache_dir=tmp_path)

    frame.save_to_sql("items", **_sqlite_arguments(database))
    frame.save_to_sql("items", if_exists="replace", **_sqlite_arguments(database))

    assert _fetch_rows(database, "SELECT a, b FROM items ORDER BY a") == [
        (1, "x"),
        (2, "y"),
    ]


def test_save_to_sql_chunk_size_writes_every_row(tmp_path):
    pytest.importorskip("sqlalchemy")
    database = tmp_path / "chunked.db"
    frame = BaseData({"a": list(range(7))}, cache_dir=tmp_path)

    frame.save_to_sql("items", chunk_size=3, **_sqlite_arguments(database))

    assert _fetch_rows(database, "SELECT a FROM items ORDER BY a") == [
        (value,) for value in range(7)
    ]


def test_save_to_sql_columns_types_controls_sql_column_types(tmp_path):
    sqlalchemy = pytest.importorskip("sqlalchemy")
    database = tmp_path / "typed.db"
    frame = BaseData({"a": [1, 2], "b": ["x", "y"]}, cache_dir=tmp_path)

    frame.save_to_sql(
        "items",
        columns_types={"a": sqlalchemy.Integer, "b": sqlalchemy.String},
        **_sqlite_arguments(database),
    )

    schema = {
        row[1]: row[2]
        for row in _fetch_rows(database, "PRAGMA table_info(items)")
    }
    assert schema == {"a": "INTEGER", "b": "VARCHAR"}
    assert _fetch_rows(database, "SELECT a, b FROM items ORDER BY a") == [
        (1, "x"),
        (2, "y"),
    ]


def test_save_to_sql_index_true_persists_the_index_column(tmp_path):
    pytest.importorskip("sqlalchemy")
    database = tmp_path / "indexed.db"
    frame = BaseData(
        {"a": [1, 2]},
        index=pd.Index([10, 20], name="row_id"),
        cache_dir=tmp_path,
    )

    frame.save_to_sql("items", index=True, **_sqlite_arguments(database))
    frame.save_to_sql("plain", **_sqlite_arguments(database))

    assert [row[1] for row in _fetch_rows(database, "PRAGMA table_info(items)")] == [
        "row_id",
        "a",
    ]
    assert _fetch_rows(database, "SELECT row_id, a FROM items ORDER BY row_id") == [
        (10, 1),
        (20, 2),
    ]
    assert [row[1] for row in _fetch_rows(database, "PRAGMA table_info(plain)")] == ["a"]


def test_save_to_sql_normalizes_timezone_aware_datetimes(tmp_path):
    pytest.importorskip("sqlalchemy")
    database = tmp_path / "events.db"
    moments = pd.to_datetime(["2024-01-01 10:00:00", "2024-01-02 11:00:00"]).tz_localize("UTC")
    frame = BaseData({"a": [1, 2], "when": moments}, cache_dir=tmp_path)
    before = frame.copy(deep=True)

    frame.save_to_sql("events", **_sqlite_arguments(database))

    stored = [
        datetime.fromisoformat(row[0])
        for row in _fetch_rows(database, 'SELECT "when" FROM events ORDER BY a')
    ]
    assert stored == [datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 2, 11, 0)]
    assert all(value.tzinfo is None for value in stored)
    pd.testing.assert_frame_equal(frame, before)


def test_save_to_sql_returns_none_and_leaves_the_source_frame_unchanged(tmp_path):
    pytest.importorskip("sqlalchemy")
    database = tmp_path / "plain.db"
    frame = BaseData({"a": [1, 2]}, cache_dir=tmp_path)
    before = frame.copy(deep=True)

    returned = frame.save_to_sql("items", **_sqlite_arguments(database))

    assert returned is None
    pd.testing.assert_frame_equal(frame, before)


def test_save_to_sql_reports_missing_sqlalchemy_dependency(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "sqlalchemy", None)
    frame = BaseData({"a": [1]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="save_to_sql requires the optional 'SQLAlchemy'"):
        frame.save_to_sql("items", **_sqlite_arguments(tmp_path / "missing.db"))
