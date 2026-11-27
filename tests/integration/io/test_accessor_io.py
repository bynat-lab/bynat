import json

import pandas as pd
import pytest

from bynat.cleaning import CsvFile, JsonFile
from bynat.cleaning.io import read_csv, read_json


def test_accessor_save_to_json(tmp_path):
    output = tmp_path / "out.json"

    pd.DataFrame({"name": ["Ada"]}).bynat.save_to_json(output)

    assert json.loads(output.read_text(encoding="utf-8")) == [{"name": "Ada"}]


def test_read_json_and_read_csv_return_plain_frames(tmp_path):
    json_path = tmp_path / "records.json"
    json_path.write_text(json.dumps({"items": [{"name": "Ada", "info": {"age": 37}}]}), encoding="utf-8")
    csv_path = tmp_path / "records.csv"
    csv_path.write_text("name;age\nGrace;28\n", encoding="utf-8")

    json_frame = read_json(json_path, key="items")
    csv_frame = read_csv(csv_path, sep=";")

    assert type(json_frame) is pd.DataFrame
    assert list(json_frame.columns) == ["name", "info.age"]
    assert list(json_frame.bynat.rename_all_DOTS().columns) == ["name", "info_age"]
    assert type(csv_frame) is pd.DataFrame
    assert csv_frame.to_dict("list") == {"name": ["Grace"], "age": [28]}


def test_read_helpers_raise_like_the_legacy_loaders(tmp_path):
    json_path = tmp_path / "list.json"
    json_path.write_text("[1, 2]", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        read_json(tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        read_csv(tmp_path / "missing.csv")
    with pytest.raises(TypeError, match="dictionary payload"):
        read_json(json_path, key="items")


def test_json_and_csv_constructors_read_local_files(tmp_path):
    json_path = tmp_path / "records.json"
    json_path.write_text(json.dumps({"items": [{"name": "Ada", "age": 37}]}), encoding="utf-8")
    csv_path = tmp_path / "records.csv"
    csv_path.write_text("name;age\nGrace;28\n", encoding="utf-8")

    json_frame = JsonFile(json_file_path=json_path, key="items", cache_dir=tmp_path / "json-cache")
    csv_frame = CsvFile(csv_file_path=csv_path, read_kwargs={"sep": ";"}, cache_dir=tmp_path / "csv-cache")

    assert list(json_frame.columns) == ["name", "age"]
    assert json_frame.iloc[0]["name"] == "Ada"
    assert list(csv_frame.columns) == ["name", "age"]
    assert csv_frame.iloc[0]["name"] == "Grace"
    assert isinstance(json_frame.view(), pd.DataFrame)
    assert type(json_frame.view()) is pd.DataFrame


def test_file_constructors_raise_for_missing_paths(tmp_path):
    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        JsonFile(json_file_path=tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        CsvFile(csv_file_path=tmp_path / "missing.csv")
