"""BaseData, JsonFile, and CsvFile constructor contracts and cache manager bundling."""

import json

import pandas as pd
import pytest

from bynat.caching import CacheManager
from bynat.cleaning import BaseData, CsvFile, JsonFile

pytestmark = pytest.mark.integration



def _frame(tmp_path, data=None):
    return BaseData(
        data if data is not None else {"id": [1, 2], "latitude": [1.0, 2.0], "name": ["a", "b"]},
        cache_dir=tmp_path,
    )


def test_melt_transform_pivot_result_keeps_the_cache_manager(tmp_path):
    frame = _frame(tmp_path, {"id": [1, 2], "left": ["a", "b"], "right": ["c", "d"]})
    original = frame.copy(deep=True)

    result = frame.melt_transform_pivot(id_vars="id", transform_func=lambda values: values.str.upper())

    assert isinstance(result, BaseData)
    assert result.cache_manager is frame.cache_manager
    pd.testing.assert_frame_equal(frame, original)


def test_public_cleaning_imports_use_the_bundled_cache_manager(tmp_path):
    frame = BaseData({"value": [1]}, cache_dir=tmp_path)

    assert isinstance(frame.cache_manager, CacheManager)
    assert BaseData.__module__ == "bynat.cleaning.base"
    legacy = __import__("bynat.cleaning.Cleaning", fromlist=["__all__"])
    assert legacy.BaseData is BaseData
    assert {"BaseData", "JsonFile", "CsvFile"}.issubset(set(legacy.__all__))


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
