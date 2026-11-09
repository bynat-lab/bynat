"""Data loader contracts for JSON and CSV: round trips, shapes, positional paths, and malformed inputs."""

import json

import pandas as pd
import pytest
from pandas.errors import EmptyDataError, ParserError

from bynat.cleaning import CsvFile, JsonFile, io


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
    assert "مكتمل" in raw

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
