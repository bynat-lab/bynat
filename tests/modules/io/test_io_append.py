"""JSON append mode contracts: creation, deduplication, and nested container handling."""

import json

import pandas as pd
import pytest

from bynat.cleaning import BaseData, io

pytestmark = pytest.mark.integration



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
