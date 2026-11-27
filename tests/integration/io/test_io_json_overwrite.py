import json

import pandas as pd
import pytest

from bynat.cleaning import BaseData, io


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


def test_save_to_json_requires_file_path(tmp_path):
    with pytest.raises(ValueError, match="file_path"):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_json("  ")
