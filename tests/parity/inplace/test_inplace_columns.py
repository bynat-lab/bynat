import warnings

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


DATA = {
    "user.name": ["Ada", "Grace"],
    "user_id": [1, 2],
    "value": [10.0, 20.0],
    "C": [1, 2],
    "A": [3, 4],
    "id": [1, 2],
    "items": [["a", "b"], ["c", "d"]],
    "longitude": [31.0, 32.0],
    "latitude": [30.0, 29.0],
    "__CLASS__marker": ["x", "y"],
}


COLUMN_TRANSFORMS = [
    pytest.param("drop_by_substring", ("user",), {}, id="drop_by_substring"),
    pytest.param("drop_CLASS_columns", (), {}, id="drop_CLASS_columns"),
    pytest.param(
        "rename_by_substring", (), {"old_substring": "name", "new_substring": "n"}, id="rename_by_substring"
    ),
    pytest.param("rename_all_DOTS", (), {}, id="rename_all_DOTS"),
    pytest.param("reorder_columns", ("value", "id"), {}, id="reorder_columns"),
    pytest.param(
        "melt_transform_pivot",
        (),
        {"id_vars": "id", "value_vars": ["C", "A"]},
        id="melt_transform_pivot",
    ),
    pytest.param(
        "move_column",
        (),
        {"col_to_move": "value", "col_target": "id", "position": "before"},
        id="move_column",
    ),
    pytest.param("align_lat_lng", (), {}, id="align_lat_lng"),
    pytest.param("split_list_objects", (), {"source_col": "items", "first": 0}, id="split_list_objects"),
]


def _frame():
    return pd.DataFrame(DATA)


@pytest.mark.parametrize(("name", "args", "kwargs"), COLUMN_TRANSFORMS)
def test_columns_inplace_true_mutates_the_wrapped_frame_without_changing_its_identity(name, args, kwargs):
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


@pytest.mark.parametrize(("name", "args", "kwargs"), COLUMN_TRANSFORMS)
def test_columns_inplace_false_returns_a_new_frame_and_leaves_the_source_unchanged(name, args, kwargs):
    frame = _frame()
    before = frame.copy(deep=True)

    default_result = getattr(frame.bynat, name)(*args, **kwargs)
    explicit_result = getattr(frame.bynat, name)(*args, inplace=False, **kwargs)

    assert default_result is not frame
    assert explicit_result is not frame
    pd.testing.assert_frame_equal(frame, before)
    pd.testing.assert_frame_equal(default_result, explicit_result)
