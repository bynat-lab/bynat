"""List splitting and exploding transformations on structured columns."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData


def test_split_list_objects_remove_source_col_drops_the_original_column():
    frame = pd.DataFrame(
        {"id": [1, 2], "items": [["a", "b", "c"], ["x", "y"]]},
        index=pd.Index([4, 5], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.split_list_objects(
        "items", remove_source_col=True, first=0, pair=[0, 1]
    )

    index = pd.Index([4, 5], name="row")
    expected = pd.DataFrame(
        {
            "id": pd.Series([1, 2], index=index),
            "first": pd.Series(["a", "x"], index=index),
            "pair": pd.Series(["a, b", "x, y"], index=index),
        }
    )
    pd.testing.assert_frame_equal(result, expected, check_dtype=False)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_split_list_objects_joined_extraction_ignores_missing_elements():
    frame = pd.DataFrame({"items": [["a", None, "c"], [None, None, None], ["x"]]})
    before = frame.copy(deep=True)

    joined = frame.bynat.split_list_objects("items", joined=[0, 1, 2])
    assert joined["joined"].tolist() == ["a, c", "", "x"]

    single = frame.bynat.split_list_objects("items", first=0)
    assert single["first"].tolist() == ["a", None, "x"]

    out_of_range = frame.bynat.split_list_objects("items", first=5)
    assert out_of_range["first"].isna().tolist() == [True, True, True]

    pd.testing.assert_frame_equal(frame, before)


def test_split_list_objects_parallel_explode_resets_the_index():
    frame = pd.DataFrame({"id": [1, 2], "items": [["a", "b", "c"], ["x", "y", "z"]]})
    before = frame.copy(deep=True)

    result = frame.bynat.split_list_objects(
        "items", explode_rows=True, first=[0, 1], second=[1, 2]
    )

    expected = pd.DataFrame(
        {
            "id": [1, 1, 2, 2],
            "items": [
                ["a", "b", "c"],
                ["a", "b", "c"],
                ["x", "y", "z"],
                ["x", "y", "z"],
            ],
            "first": ["a", "b", "x", "y"],
            "second": ["b", "c", "y", "z"],
        },
        index=pd.RangeIndex(4),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_split_list_objects_cartesian_explode_builds_the_cross_product():
    frame = pd.DataFrame({"id": [1], "items": [["a", "b", "c"]]})
    before = frame.copy(deep=True)

    result = frame.bynat.split_list_objects(
        "items", explode_rows=True, cartesian_explode=True, first=[0, 1], second=[1, 2]
    )

    expected = pd.DataFrame(
        {
            "id": [1, 1, 1, 1],
            "items": [["a", "b", "c"]] * 4,
            "first": ["a", "a", "b", "b"],
            "second": ["b", "c", "b", "c"],
        },
        index=pd.RangeIndex(4),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("index", [None, "all"], ids=["none", "all"])
def test_split_list_objects_all_index_copies_the_source_list(index):
    frame = pd.DataFrame({"id": [1], "items": [["a", "b"]]})
    before = frame.copy(deep=True)

    result = frame.bynat.split_list_objects("items", everything=index)

    assert result["everything"].tolist() == [["a", "b"]]
    assert "everything" in result.columns
    pd.testing.assert_frame_equal(frame, before)


def test_basedata_split_list_objects_and_melt_transform_pivot_helpers(tmp_path):
    frame = BaseData(
        {
            "id": [1, 2],
            "description": ["Blue shoes", "red shirt"],
            "items": [["A", "B"], ["C", "D"]],
            "group": ["x", "x"],
            "score": [1, None],
            "left": ["a", "b"],
            "right": ["c", "d"],
        },
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    split = frame.split_list_objects("items", first=0, pair=[0, 1])
    assert split["first"].tolist() == ["A", "C"]
    assert split["pair"].tolist() == ["A, B", "C, D"]

    reshaped = frame.melt_transform_pivot(
        id_vars="id", value_vars=["left", "right"], transform_func=lambda values: values.str.upper()
    )
    assert reshaped[["left", "right"]].to_dict("list") == {
        "left": ["A", "B"],
        "right": ["C", "D"],
    }

    pd.testing.assert_frame_equal(frame, original)
