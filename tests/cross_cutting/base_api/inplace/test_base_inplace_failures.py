"""BaseData in-place calls that raise or hit a missing optional dependency."""

import sys

import pytest

from bynat.cleaning import BaseData

pytestmark = pytest.mark.integration


def _frame(tmp_path, data=None):
    return BaseData(
        data if data is not None else {"id": [1, 2], "latitude": [1.0, 2.0], "name": ["a", "b"]},
        cache_dir=tmp_path,
    )


def test_inplace_on_missing_optional_dependency_still_raises(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    frame = _frame(tmp_path)

    with pytest.raises(ImportError, match="deep-translator"):
        frame.translate_categorical_column("name", inplace=True)


def test_basedata_boundary_errors_and_inplace_return(tmp_path):
    frame = BaseData({"id": [1], "first": [2]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="position"):
        frame.move_column("id", "first", position="middle")
    with pytest.raises(ValueError, match="positive integer"):
        frame.translate_categorical_column("first", save_every=0)

    assert frame.drop_by_substring("missing", inplace=True) is None
    assert list(frame.columns) == ["id", "first"]
