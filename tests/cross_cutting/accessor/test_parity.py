"""Class/accessor parity (S-5): BaseData and the bynat accessor produce equal results."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData

# ---------------------------------------------------------------------------
# Class/accessor parity (S-5) and inplace parity (S-4/ML-2)
# ---------------------------------------------------------------------------


PARITY_DATA = {
    "user.name": ["Ada", "Grace"],
    "user_id": [1, 2],
    "value": [10.0, 20.0],
    "C": [1, 2],
    "A": [3, 4],
    "D": [5, 6],
    "B": [7, 8],
    "longitude": [31.0, 32.0],
    "latitude": [30.0, 29.0],
    "id": [1, 2],
    "items": [["a", "b"], ["c", "d"]],
    "description": ["Blue shoes", "red shirt"],
    "title": ["Software Engineer - Remote", "Data Analyst"],
    "g": ["x", "x"],
    "score": [1.0, None],
}


# Each case takes the entry point object and the underlying data so that
# ``fill_missing_from`` can use the frame as its own reference on both paths.


PARITY_CASES = [
    pytest.param(lambda obj, data: obj.drop_by_substring("user"), id="drop_by_substring"),
    pytest.param(lambda obj, data: obj.drop_CLASS_columns(), id="drop_CLASS_columns"),
    pytest.param(lambda obj, data: obj.rename_by_substring("name", "n"), id="rename_by_substring"),
    pytest.param(lambda obj, data: obj.rename_all_DOTS(), id="rename_all_DOTS"),
    pytest.param(lambda obj, data: obj.reorder_columns("A", "B"), id="reorder_columns"),
    pytest.param(
        lambda obj, data: obj.move_column("value", "id", position="before"), id="move_column"
    ),
    pytest.param(lambda obj, data: obj.align_lat_lng(), id="align_lat_lng"),
    pytest.param(
        lambda obj, data: obj.melt_transform_pivot(id_vars="id", value_vars=["C", "A"]),
        id="melt_transform_pivot",
    ),
    pytest.param(
        lambda obj, data: obj.split_list_objects("items", first=0), id="split_list_objects"
    ),
    pytest.param(
        lambda obj, data: obj.extract_keywords("description", colors=["blue", "red"]),
        id="extract_keywords",
    ),
    pytest.param(
        lambda obj, data: obj.truncate_after_substring(regex=False, title="-"),
        id="truncate_after_substring",
    ),
    pytest.param(
        lambda obj, data: obj.fill_missing("score", hierarchy_cols="g"), id="fill_missing"
    ),
    pytest.param(
        lambda obj, data: obj.fill_missing_from(data, "score", hierarchy_cols="g"),
        id="fill_missing_from",
    ),
    pytest.param(
        lambda obj, data: obj.handle_outliers("value", hierarchy_cols=["g"], min_samples=2),
        id="handle_outliers",
    ),
    pytest.param(
        lambda obj, data: obj.drop_outliers("value", hierarchy_cols=["g"], min_samples=2),
        id="drop_outliers",
    ),
]


@pytest.mark.parametrize("transform", PARITY_CASES)
def test_accessor_and_basedata_produce_equal_results(tmp_path, transform):
    base = BaseData(PARITY_DATA, cache_dir=tmp_path)
    plain = pd.DataFrame(PARITY_DATA)

    base_result = transform(base, base)
    accessor_result = transform(plain.bynat, plain)

    assert isinstance(base_result, BaseData)
    assert type(accessor_result) is pd.DataFrame
    pd.testing.assert_frame_equal(pd.DataFrame(base_result), accessor_result)
