import pandas as pd
import pytest

from bynat.cleaning import BaseData

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
def test_columns_inplace_result_matches_the_class_api(name, args, kwargs):
    base = BaseData(DATA)
    plain = _frame()

    class_result = getattr(base, name)(*args, **kwargs)
    accessor_result = getattr(plain.bynat, name)(*args, **kwargs)

    pd.testing.assert_frame_equal(pd.DataFrame(class_result), accessor_result)
