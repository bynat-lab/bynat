"""Phase 3 file-I/O contract coverage (TEST-02).

Pins the documented contracts of the file-backed public surface that the
Phase 1/2 suite did not cover: ``read_json``/``read_csv`` round trips and
malformed or empty payloads, ``save_to_json`` orient/force_ascii/indent
variants, skip-on-unchanged and overwrite-on-change, append edge cases,
datetime serialization, unicode encoding, ``JsonFile``/``CsvFile``
positional-path constructors, relative paths, input non-mutation, and
filesystem failures.

Every test builds its own files under ``tmp_path`` and compares against
expected values written independently of the implementation.
"""

import json
import sys

import pandas as pd
import pytest
from pandas.errors import EmptyDataError, ParserError

from bynat.cleaning import BaseData, CsvFile, JsonFile, io

# ---------------------------------------------------------------------------
# Round trips
# ---------------------------------------------------------------------------


def test_read_json_round_trip_preserves_records_unicode_and_flattened_keys(tmp_path):
    frame = pd.DataFrame(
        {
            "name": ["مكتمل", "Ada"],
            "age": [37, 28],
            "info": [{"city": "Cairo"}, {"city": "Alex"}],
        }
    )
    path = tmp_path / "records.json"

    assert io.save_to_json(frame, path) is None

    raw = path.read_text(encoding="utf-8")
    assert "مكتمل" in raw  # default force_ascii=False keeps UTF-8 text

    loaded = io.read_json(path)
    assert list(loaded.columns) == ["name", "age", "info.city"]
    assert loaded["name"].tolist() == ["مكتمل", "Ada"]
    assert loaded["age"].tolist() == [37, 28]
    assert loaded["info.city"].tolist() == ["Cairo", "Alex"]


def test_read_csv_to_json_round_trip_preserves_unicode(tmp_path):
    csv_path = tmp_path / "people.csv"
    csv_path.write_text("name;city\nمكتمل;Cairo\n", encoding="utf-8")
    json_path = tmp_path / "people.json"

    frame = io.read_csv(csv_path, sep=";")
    io.save_to_json(frame, json_path)

    loaded = io.read_json(json_path)
    assert loaded["name"].tolist() == ["مكتمل"]
    assert loaded["city"].tolist() == ["Cairo"]


# ---------------------------------------------------------------------------
# save_to_json -- orient, force_ascii, indent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("orient", "expected"),
    [
        pytest.param(
            "split",
            {"columns": ["a", "b"], "index": [0, 1], "data": [[1, "x"], [2, "y"]]},
            id="split",
        ),
        pytest.param(
            "records",
            [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
            id="records",
        ),
        pytest.param(
            "index",
            {"0": {"a": 1, "b": "x"}, "1": {"a": 2, "b": "y"}},
            id="index",
        ),
        pytest.param(
            "columns",
            {"a": {"0": 1, "1": 2}, "b": {"0": "x", "1": "y"}},
            id="columns",
        ),
        pytest.param("values", [[1, "x"], [2, "y"]], id="values"),
    ],
)
def test_save_to_json_supports_documented_orients(tmp_path, orient, expected):
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = tmp_path / f"{orient}.json"

    io.save_to_json(frame, path, orient=orient)

    assert json.loads(path.read_text(encoding="utf-8")) == expected


def test_save_to_json_table_orient_writes_schema_and_rows(tmp_path):
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = tmp_path / "table.json"

    io.save_to_json(frame, path, orient="table")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"schema", "data"}
    assert payload["data"] == [
        {"index": 0, "a": 1, "b": "x"},
        {"index": 1, "a": 2, "b": "y"},
    ]
    fields = payload["schema"]["fields"]
    assert [field["name"] for field in fields] == ["index", "a", "b"]
    assert [field["type"] for field in fields] == ["integer", "integer", "string"]
    assert payload["schema"]["primaryKey"] == ["index"]
    assert "pandas_version" in payload["schema"]


def test_save_to_json_force_ascii_controls_non_ascii_escaping(tmp_path):
    frame = pd.DataFrame({"name": ["مكتمل"]})

    escaped_path = tmp_path / "escaped.json"
    io.save_to_json(frame, escaped_path, force_ascii=True)
    escaped = escaped_path.read_text(encoding="utf-8")
    assert "\\u0645\\u0643\\u062a\\u0645\\u0644" in escaped
    assert "مكتمل" not in escaped

    literal_path = tmp_path / "literal.json"
    io.save_to_json(frame, literal_path, force_ascii=False)
    literal = literal_path.read_text(encoding="utf-8")
    assert "مكتمل" in literal
    assert "\\u0645" not in literal


@pytest.mark.parametrize(
    ("indent", "expected"),
    [
        pytest.param(0, '[{"a":1,"b":"x"},{"a":2,"b":"y"}]', id="indent-0"),
        pytest.param(
            2,
            '[\n  {\n    "a":1,\n    "b":"x"\n  },\n  {\n    "a":2,\n    "b":"y"\n  }\n]',
            id="indent-2",
        ),
        pytest.param(
            4,
            '[\n    {\n        "a":1,\n        "b":"x"\n    },\n    {\n        "a":2,\n        "b":"y"\n    }\n]',
            id="indent-4",
        ),
    ],
)
def test_save_to_json_indent_controls_disk_formatting(tmp_path, indent, expected):
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = tmp_path / "out.json"

    io.save_to_json(frame, path, indent=indent)

    assert path.read_text(encoding="utf-8") == expected


# ---------------------------------------------------------------------------
# save_to_json -- skip, overwrite, append
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "existing",
    [
        pytest.param('[{"a": 1, "b": "x"}]', id="compact"),
        pytest.param('[\n  {"b": "x", "a": 1}\n]', id="reordered-and-spaced"),
    ],
)
def test_save_to_json_skips_rewrite_when_payload_is_unchanged(tmp_path, existing):
    path = tmp_path / "out.json"
    path.write_text(existing, encoding="utf-8")
    before = path.read_bytes()

    assert io.save_to_json(pd.DataFrame({"a": [1], "b": ["x"]}), path) is None

    assert path.read_bytes() == before


def test_save_to_json_overwrites_when_payload_changed(tmp_path):
    path = tmp_path / "out.json"
    path.write_text('[{"a": 1}]', encoding="utf-8")

    io.save_to_json(pd.DataFrame({"a": [2]}), path)

    assert json.loads(path.read_text(encoding="utf-8")) == [{"a": 2}]


def test_save_to_json_overwrites_unreadable_existing_file(tmp_path):
    path = tmp_path / "out.json"
    path.write_text("{not json", encoding="utf-8")

    io.save_to_json(pd.DataFrame({"a": [1]}), path)

    assert json.loads(path.read_text(encoding="utf-8")) == [{"a": 1}]


@pytest.mark.parametrize(
    "existing",
    [pytest.param(None, id="missing-file"), pytest.param("[]", id="empty-array")],
)
def test_save_to_json_append_to_missing_or_empty_file_writes_rows(tmp_path, existing):
    path = tmp_path / "out.json"
    if existing is not None:
        path.write_text(existing, encoding="utf-8")

    io.save_to_json(pd.DataFrame({"a": [1, 2]}), path, append=True)

    assert json.loads(path.read_text(encoding="utf-8")) == [{"a": 1}, {"a": 2}]


def test_save_to_json_append_deduplicates_dict_cells_by_json_content(tmp_path):
    path = tmp_path / "out.json"
    io.save_to_json(pd.DataFrame({"a": [1], "meta": [{"x": 1, "y": 2}]}), path)

    io.save_to_json(
        pd.DataFrame({"a": [1, 2], "meta": [{"y": 2, "x": 1}, {"x": 1, "y": 3}]}),
        path,
        append=True,
    )

    assert json.loads(path.read_text(encoding="utf-8")) == [
        {"a": 1, "meta": {"x": 1, "y": 2}},
        {"a": 2, "meta": {"x": 1, "y": 3}},
    ]


# ---------------------------------------------------------------------------
# save_to_json -- datetime serialization, non-mutation, empty frames, paths
# ---------------------------------------------------------------------------


def test_save_to_json_formats_datetime_columns_as_documented(tmp_path):
    frame = pd.DataFrame(
        {
            "naive": pd.to_datetime(["2024-01-02 03:04:05"]),
            "aware": pd.to_datetime(["2024-01-02 03:04:05"], utc=True),
        }
    )
    path = tmp_path / "datetimes.json"

    io.save_to_json(frame, path)

    assert json.loads(path.read_text(encoding="utf-8")) == [
        {"naive": "2024-01-02 03:04:05", "aware": "2024-01-02 03:04:05"}
    ]


def test_save_to_json_does_not_mutate_the_source_frame(tmp_path):
    frame = pd.DataFrame(
        {
            "when": pd.to_datetime(["2024-01-02 03:04:05"]),
            "name": ["Ada"],
            "tags": [["a"]],
        }
    )
    before = frame.copy(deep=True)
    dtypes_before = frame.dtypes.copy()
    path = tmp_path / "out.json"

    assert io.save_to_json(frame, path) is None
    assert io.save_to_json(frame, path, append=True) is None

    pd.testing.assert_frame_equal(frame, before)
    assert frame.dtypes.equals(dtypes_before)


def test_save_to_json_empty_frame_round_trip(tmp_path):
    path = tmp_path / "empty.json"

    io.save_to_json(pd.DataFrame({"a": []}), path)

    assert json.loads(path.read_text(encoding="utf-8")) == []
    assert io.read_json(path).shape == (0, 0)


def test_save_to_json_writes_relative_paths_to_the_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    io.save_to_json(pd.DataFrame({"a": [1]}), "output.json")

    output = tmp_path / "output.json"
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8")) == [{"a": 1}]
    assert io.read_json("output.json").to_dict("list") == {"a": [1]}


# ---------------------------------------------------------------------------
# save_to_json -- filesystem failures
# ---------------------------------------------------------------------------


def test_save_to_json_raises_for_directory_targets(tmp_path):
    target = tmp_path / "target.json"
    target.mkdir()

    with pytest.raises(OSError):
        io.save_to_json(pd.DataFrame({"a": [1]}), target)

    assert target.is_dir()


def test_save_to_json_raises_when_parent_is_a_file(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")

    with pytest.raises(OSError):
        io.save_to_json(pd.DataFrame({"a": [1]}), blocker / "out.json")

    assert blocker.read_text(encoding="utf-8") == "not a directory"


# ---------------------------------------------------------------------------
# Loaders -- malformed, empty, and invalid paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param("", id="empty-file"),
        pytest.param("{not json", id="truncated-object"),
        pytest.param('[{"a": 1},', id="truncated-array"),
    ],
)
def test_read_json_rejects_malformed_json(tmp_path, payload):
    path = tmp_path / "malformed.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        io.read_json(path)


def test_read_csv_rejects_empty_and_malformed_files(tmp_path):
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("", encoding="utf-8")
    with pytest.raises(EmptyDataError):
        io.read_csv(empty_path)

    malformed_path = tmp_path / "malformed.csv"
    malformed_path.write_text('a,b\n"1,2\n', encoding="utf-8")
    with pytest.raises(ParserError):
        io.read_csv(malformed_path)


def test_read_helpers_reject_directory_paths(tmp_path):
    json_dir = tmp_path / "records.json"
    json_dir.mkdir()
    csv_dir = tmp_path / "records.csv"
    csv_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        io.read_json(json_dir)
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        io.read_csv(csv_dir)


def test_read_json_accepts_dict_payload_without_key(tmp_path):
    path = tmp_path / "scalars.json"
    path.write_text('{"a": 1, "b": "x"}', encoding="utf-8")

    frame = io.read_json(path)

    assert frame.to_dict("list") == {"a": [1], "b": ["x"]}


def test_read_json_empty_array_payload(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")

    frame = io.read_json(path)

    assert frame.shape == (0, 0)
    assert frame.columns.tolist() == []


def test_read_csv_header_only_file_returns_empty_frame(tmp_path):
    path = tmp_path / "header.csv"
    path.write_text("a,b\n", encoding="utf-8")

    frame = io.read_csv(path)

    assert frame.shape == (0, 2)
    assert frame.columns.tolist() == ["a", "b"]


# ---------------------------------------------------------------------------
# JsonFile / CsvFile -- positional-path constructors
# ---------------------------------------------------------------------------


def test_file_constructors_accept_positional_paths(tmp_path):
    json_path = tmp_path / "records.json"
    json_path.write_text('{"items": [{"a": 1, "b": "x"}]}', encoding="utf-8")
    csv_path = tmp_path / "records.csv"
    csv_path.write_text("a;b\n1;2\n", encoding="utf-8")

    json_frame = JsonFile(json_path, key="items", cache_dir=tmp_path / "json-cache")
    csv_frame = CsvFile(csv_path, read_kwargs={"sep": ";"}, cache_dir=tmp_path / "csv-cache")

    assert isinstance(json_frame, JsonFile)
    assert json_frame[["a", "b"]].to_dict("list") == {"a": [1], "b": ["x"]}
    assert isinstance(csv_frame, CsvFile)
    assert csv_frame[["a", "b"]].to_dict("list") == {"a": [1], "b": [2]}


# ---------------------------------------------------------------------------
# read_json -- documented loader validation
# ---------------------------------------------------------------------------


def test_read_json_missing_key_raises_keyerror(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps({"items": [{"a": 1}]}), encoding="utf-8")

    with pytest.raises(KeyError, match="missing"):
        io.read_json(path, key="missing")


def test_read_json_key_on_non_dict_payload_raises_typeerror(tmp_path):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([{"a": 1}]), encoding="utf-8")

    with pytest.raises(TypeError, match="dictionary payload"):
        io.read_json(path, key="items")


# ---------------------------------------------------------------------------
# BaseData save_to_json / save_to_sql contracts
# ---------------------------------------------------------------------------


def test_save_to_json_writes_local_output(tmp_path):
    output = tmp_path / "nested" / "records.json"
    BaseData({"name": ["Ada"]}, cache_dir=tmp_path).save_to_json(output)

    assert json.loads(output.read_text(encoding="utf-8")) == [{"name": "Ada"}]


def test_save_to_json_append_keeps_existing_rows_with_list_columns(tmp_path):
    file_path = tmp_path / "out.json"

    BaseData({"a": [1, 2], "tags": [["x"], ["y"]]}, cache_dir=tmp_path).save_to_json(file_path)
    BaseData({"a": [2, 3], "tags": [["y"], ["z"]]}, cache_dir=tmp_path).save_to_json(
        file_path, append=True
    )

    saved = json.loads(file_path.read_text(encoding="utf-8"))

    assert saved == [
        {"a": 1, "tags": ["x"]},
        {"a": 2, "tags": ["y"]},
        {"a": 3, "tags": ["z"]},
    ]


def test_save_to_json_append_deduplicates_plain_columns_without_json_keys(tmp_path, monkeypatch):
    import bynat.cleaning.io as cleaning

    file_path = tmp_path / "out.json"
    BaseData({"a": [1, 2], "b": ["x", "y"]}, cache_dir=tmp_path).save_to_json(file_path)

    monkeypatch.setattr(cleaning, "_dedupe_key", lambda value: pytest.fail("fast path expected"))
    BaseData({"a": [2, 3], "b": ["y", "z"]}, cache_dir=tmp_path).save_to_json(file_path, append=True)

    assert json.loads(file_path.read_text(encoding="utf-8")) == [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
        {"a": 3, "b": "z"},
    ]


def test_save_to_json_append_refuses_to_overwrite_unreadable_file(tmp_path):
    file_path = tmp_path / "out.json"
    file_path.write_text('{"not": "records"', encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot append"):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_json(file_path, append=True)

    assert file_path.read_text(encoding="utf-8") == '{"not": "records"'


def test_save_to_json_requires_file_path(tmp_path):
    with pytest.raises(ValueError, match="file_path"):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_json("  ")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"table_name": " "}, "table_name"),
        ({"if_exists": "merge"}, "if_exists"),
        ({"database_type": ""}, "database_type"),
        ({"database_name": ""}, "SQLite"),
        ({"database_type": "postgresql", "database_host": ""}, "are required"),
        ({"database_type": "mssql+pyodbc", "database_user": "u", "database_password": "p",
          "database_host": "h", "database_port": "1"}, "database_driver"),
    ],
)
def test_save_to_sql_rejects_invalid_arguments_before_connecting(monkeypatch, tmp_path, kwargs, message):
    monkeypatch.setitem(sys.modules, "sqlalchemy", None)
    arguments = {
        "table_name": "items",
        "database_type": "sqlite",
        "database_user": "",
        "database_password": "",
        "database_host": "",
        "database_port": "",
        "database_name": str(tmp_path / "out.db"),
        "if_exists": "append",
    }
    arguments.update(kwargs)

    with pytest.raises(ValueError, match=message):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_sql(**arguments)
