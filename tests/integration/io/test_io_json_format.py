import json

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


def test_save_to_json_empty_frame_round_trip(tmp_path):
    path = tmp_path / "empty.json"

    io.save_to_json(pd.DataFrame({"a": []}), path)

    assert json.loads(path.read_text(encoding="utf-8")) == []
    assert io.read_json(path).shape == (0, 0)


def test_save_to_json_writes_local_output(tmp_path):
    output = tmp_path / "nested" / "records.json"
    BaseData({"name": ["Ada"]}, cache_dir=tmp_path).save_to_json(output)

    assert json.loads(output.read_text(encoding="utf-8")) == [{"name": "Ada"}]
