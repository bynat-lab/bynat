"""Text transformations: in-place identity, copy semantics, and class parity."""

import warnings

import pandas as pd
import pytest

from bynat.cleaning import BaseData
from tests.shared.constants import PARITY_DATA

pytestmark = pytest.mark.unit


TEXT_TRANSFORMS = [
    pytest.param("extract_keywords", ("description",), {"colors": ["blue", "red"]}, id="extract_keywords"),
    pytest.param("truncate_after_substring", (), {"regex": False, "title": "-"}, id="truncate_after_substring"),
    pytest.param(
        "categorize_by_reference",
        ("description",),
        {"target_col": "field", "reference": {"Colors": ["blue", "red"]}},
        id="categorize_by_reference",
    ),
]


def _frame():
    return pd.DataFrame(PARITY_DATA)


@pytest.mark.parametrize(("name", "args", "kwargs"), TEXT_TRANSFORMS)
def test_text_inplace_true_mutates_the_wrapped_frame_without_changing_its_identity(name, args, kwargs):
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
    frame = _frame()
    before = frame.copy(deep=True)

    default_result = getattr(frame.bynat, name)(*args, **kwargs)
    explicit_result = getattr(frame.bynat, name)(*args, inplace=False, **kwargs)

    assert default_result is not frame
    assert explicit_result is not frame
    pd.testing.assert_frame_equal(frame, before)
    pd.testing.assert_frame_equal(default_result, explicit_result)


@pytest.mark.parametrize(("name", "args", "kwargs"), TEXT_TRANSFORMS)
def test_text_inplace_result_matches_the_class_api(name, args, kwargs):
    base = BaseData(PARITY_DATA)
    plain = _frame()

    class_result = getattr(base, name)(*args, **kwargs)
    accessor_result = getattr(plain.bynat, name)(*args, **kwargs)

    pd.testing.assert_frame_equal(pd.DataFrame(class_result), accessor_result)
