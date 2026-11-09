"""JSON serialization formatting, orients, schemas, overwrite, filesystem errors, and validation."""

import json
import sys

import pandas as pd
import pytest

from bynat.cleaning import BaseData, io


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
    frame = pd.DataFrame({"a": [1], "b": ["x"]})
    path = tmp_path / "table.json"

    io.save_to_json(frame, path, orient="table")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert list(payload.keys()) == ["schema", "data"]
    assert payload["data"] == [{"index": 0, "a": 1, "b": "x"}]
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
    pd.testing.assert_series_equal(frame.dtypes, dtypes_before)


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


def test_save_to_json_writes_local_output(tmp_path):
    output = tmp_path / "nested" / "records.json"
    BaseData({"name": ["Ada"]}, cache_dir=tmp_path).save_to_json(output)

    assert json.loads(output.read_text(encoding="utf-8")) == [{"name": "Ada"}]


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
