import warnings

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData
from tests.shared.constants import PARITY_DATA

pytestmark = pytest.mark.unit


def _truncate_frame(tmp_path):
    return BaseData(
        {
            "title": ["a.b-c", "x-y", np.nan],
            "note": ["a.b-c", "x.y.z", np.nan],
        },
        index=pd.Index([2, 4, 6], name="row"),
        cache_dir=tmp_path,
    )


EXTRAS_METHODS = {"categorize_by_reference"}


def _require_optional_dependency(name):
    if name in EXTRAS_METHODS:
        pytest.importorskip("ahocorasick")


TEXT_TRANSFORMS = [
    pytest.param("extract_keywords", ("description",), {"colors": ["blue", "red"]}, id="extract_keywords"),
    pytest.param("truncate_after_substring", (), {"regex": False, "title": "-"}, id="truncate_after_substring"),
    pytest.param(
        "categorize_by_reference",
        ("description",),
        {"target_col": "field", "reference": {"Colors": ["blue", "red"]}},
        id="categorize_by_reference",
        marks=pytest.mark.extras,
    ),
]


def _frame():
    return pd.DataFrame(PARITY_DATA)


def test_basedata_truncate_after_substring_inplace_true_mutates_same_object(tmp_path):
    frame = _truncate_frame(tmp_path)
    frame_id = id(frame)
    frame_type = type(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.truncate_after_substring(regex=False, title="-", inplace=True)

    assert returned is None
    assert id(frame) == frame_id
    assert type(frame) is frame_type
    assert frame["title"].tolist()[:2] == ["a.b", "x"]
    assert pd.isna(frame["title"].iloc[2])
    assert frame["note"].tolist()[:2] == ["a.b-c", "x.y.z"]


def test_basedata_truncate_after_substring_positional_inplace(tmp_path):
    frame = _truncate_frame(tmp_path)
    frame_id = id(frame)
    frame_type = type(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.truncate_after_substring(False, True, title="-")

    assert returned is None
    assert id(frame) == frame_id
    assert type(frame) is frame_type
    assert frame["title"].tolist()[:2] == ["a.b", "x"]
    assert pd.isna(frame["title"].iloc[2])
    assert frame["note"].tolist()[:2] == ["a.b-c", "x.y.z"]

    frame_copy = _truncate_frame(tmp_path)
    before = frame_copy.copy(deep=True)

    result = frame_copy.truncate_after_substring(False, False, title="-")

    assert result is not frame_copy
    assert type(result) is type(frame_copy)
    assert result["title"].tolist()[:2] == ["a.b", "x"]
    pd.testing.assert_frame_equal(frame_copy, before)


@pytest.mark.parametrize(("name", "args", "kwargs"), TEXT_TRANSFORMS)
def test_text_inplace_true_mutates_the_wrapped_frame_without_changing_its_identity(name, args, kwargs):
    _require_optional_dependency(name)
    frame = _frame()
    before = frame.copy(deep=True)
    original_id = id(frame)
    expected = getattr(_frame().bynat, name)(*args, **kwargs)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = getattr(frame.bynat, name)(*args, inplace=True, **kwargs)

    assert returned is None
    assert id(frame) == original_id
    assert not frame.equals(before)
    pd.testing.assert_frame_equal(frame, expected)


@pytest.mark.parametrize(("name", "args", "kwargs"), TEXT_TRANSFORMS)
def test_text_inplace_false_returns_a_new_frame_and_leaves_the_source_unchanged(name, args, kwargs):
    _require_optional_dependency(name)
    frame = _frame()
    before = frame.copy(deep=True)

    default_result = getattr(frame.bynat, name)(*args, **kwargs)
    explicit_result = getattr(frame.bynat, name)(*args, inplace=False, **kwargs)

    assert default_result is not frame
    assert explicit_result is not frame
    pd.testing.assert_frame_equal(frame, before)
    pd.testing.assert_frame_equal(default_result, explicit_result)
