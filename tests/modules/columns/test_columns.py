"""Column reshaping transformations: drop/rename/reorder/align, split_list_objects, melt_transform_pivot."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData, columns

# ---------------------------------------------------------------------------
# Columns: drop_CLASS_columns, rename_by_substring, reorder_columns, align_lat_lng
# ---------------------------------------------------------------------------


def test_drop_CLASS_columns_drops_only_matching_columns():
    frame = pd.DataFrame(
        {
            "metadata.__CLASS__": [1, 2],
            "object.__CLASS__id": [3, 4],
            "user_name": ["Ada", "Grace"],
            "value": [1.5, 2.5],
        },
        index=pd.Index([10, 20], name="row_id"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.drop_CLASS_columns()

    expected = pd.DataFrame(
        {"user_name": ["Ada", "Grace"], "value": [1.5, 2.5]},
        index=pd.Index([10, 20], name="row_id"),
    )
    assert type(result) is pd.DataFrame
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)

    result.loc[10, "value"] = 99.0
    assert frame.loc[10, "value"] == 1.5


def test_rename_by_substring_renames_every_occurrence_and_keeps_the_rest():
    frame = pd.DataFrame(
        {
            "user_display_name": ["Ada"],
            "post_display_name": ["p"],
            "display_display": ["d"],
            "created_at": ["2024-01-01"],
        },
        index=pd.Index([7], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.rename_by_substring("display", "name")

    expected = pd.DataFrame(
        {
            "user_name_name": ["Ada"],
            "post_name_name": ["p"],
            "name_name": ["d"],
            "created_at": ["2024-01-01"],
        },
        index=pd.Index([7], name="row"),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_rename_by_substring_without_matches_returns_an_independent_copy():
    frame = pd.DataFrame({"a": [1], "b": [2]})
    before = frame.copy(deep=True)

    result = frame.bynat.rename_by_substring("missing", "x")

    assert result is not frame
    pd.testing.assert_frame_equal(result, frame)
    pd.testing.assert_frame_equal(frame, before)

    result.loc[0, "a"] = 9
    assert frame.loc[0, "a"] == 1


def test_reorder_columns_moves_named_columns_to_the_front():
    frame = pd.DataFrame(
        {"C": [1], "A": [2], "D": [3], "B": [4]},
        index=pd.Index([5], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.reorder_columns("A", "B")

    expected = pd.DataFrame(
        {"A": [2], "B": [4], "C": [1], "D": [3]},
        index=pd.Index([5], name="row"),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)

    # Unknown names are ignored; the remaining names still move to the front.
    partial = frame.bynat.reorder_columns("B", "missing")
    assert list(partial.columns) == ["B", "C", "A", "D"]


def test_reorder_columns_with_no_valid_names_returns_an_independent_copy():
    frame = pd.DataFrame({"a": [1], "b": [2]})
    before = frame.copy(deep=True)

    result = frame.bynat.reorder_columns("missing", "also_missing")

    assert result is not frame
    pd.testing.assert_frame_equal(result, frame)
    pd.testing.assert_frame_equal(frame, before)


def test_align_lat_lng_moves_longitude_after_latitude():
    frame = pd.DataFrame(
        {"longitude": [31.0], "id": [1], "latitude": [30.0]},
        index=pd.Index([3], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.align_lat_lng()

    expected = pd.DataFrame(
        {"id": [1], "latitude": [30.0], "longitude": [31.0]},
        index=pd.Index([3], name="row"),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)

    # The match is exact and case-sensitive: lat/lng are left alone.
    lower = pd.DataFrame({"lng": [31.0], "id": [1], "lat": [30.0]})
    untouched = lower.bynat.align_lat_lng()
    assert list(untouched.columns) == ["lng", "id", "lat"]

    # A missing partner column is a lenient no-op.
    no_longitude = pd.DataFrame({"id": [1], "latitude": [30.0]})
    assert list(no_longitude.bynat.align_lat_lng().columns) == ["id", "latitude"]


# ---------------------------------------------------------------------------
# split_list_objects: documented variants
# ---------------------------------------------------------------------------


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
    # The contract pins the extracted values and schema, not whether pandas
    # stores the new string columns as object or str (version-dependent).
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


# ---------------------------------------------------------------------------
# melt_transform_pivot
# ---------------------------------------------------------------------------


def test_melt_transform_pivot_defaults_and_kwargs():
    frame = pd.DataFrame(
        {"id": [1, 2], "left": ["a", "b"], "right": ["c", "d"]},
        index=pd.Index([8, 9], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.melt_transform_pivot(
        id_vars="id",
        transform_func=lambda values, suffix: values.str.upper() + suffix,
        suffix="!",
    )

    # value_vars=None melts every non-id column; the pivot restores the schema.
    expected = pd.DataFrame({"id": [1, 2], "left": ["A!", "B!"], "right": ["C!", "D!"]})
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_melt_transform_pivot_custom_layout():
    frame = pd.DataFrame(
        {"id": [1, 1, 2], "left": ["a", "b", "c"], "right": ["d", "e", "f"]}
    )

    result = frame.bynat.melt_transform_pivot(
        id_vars="id",
        value_vars=["left", "right"],
        pivot_columns="id",
        pivot_index="variable_name",
    )

    expected = pd.DataFrame(
        {"variable_name": ["left", "right"], 1: ["a", "d"], 2: ["c", "f"]}
    )
    pd.testing.assert_frame_equal(result, expected)


def test_melt_transform_pivot_resets_the_index_and_preserves_the_subclass(tmp_path):
    frame = BaseData(
        {"id": [1, 2], "value": [10.0, 20.0]},
        index=pd.Index([5, 6], name="row"),
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.melt_transform_pivot(id_vars="id", value_vars=["value"])

    assert type(result) is BaseData
    pd.testing.assert_index_equal(result.index, pd.RangeIndex(2))
    assert result["id"].tolist() == [1, 2]
    assert result["value"].tolist() == [10.0, 20.0]
    pd.testing.assert_frame_equal(frame, before)


def test_melt_transform_pivot_derives_pivot_layout_defaults():
    frame = pd.DataFrame(
        {"id": [1, 1, 2], "left": ["a", "b", "c"], "right": ["d", "e", "f"]}
    )

    # pivot_columns alone: the index defaults to the remaining id_vars plus
    # the melted variable column.
    columns_first = frame.bynat.melt_transform_pivot(
        id_vars="id", value_vars=["left", "right"], pivot_columns="id"
    )
    expected_columns = pd.DataFrame(
        {"variable_name": ["left", "right"], 1: ["a", "d"], 2: ["c", "f"]}
    )
    pd.testing.assert_frame_equal(columns_first, expected_columns)

    # pivot_index alone: the columns default to the melted variable column.
    index_first = frame.bynat.melt_transform_pivot(
        id_vars="id", value_vars=["left", "right"], pivot_index="id"
    )
    expected_index = pd.DataFrame(
        {"id": [1, 2], "left": ["a", "c"], "right": ["d", "f"]}
    )
    pd.testing.assert_frame_equal(index_first, expected_index)


def test_melt_transform_pivot_supports_a_non_default_aggfunc():
    frame = pd.DataFrame({"id": [1, 1], "left": ["a", "b"]})

    result = frame.bynat.melt_transform_pivot(
        id_vars="id", value_vars=["left"], aggfunc="last"
    )

    expected = pd.DataFrame({"id": [1], "left": ["b"]})
    pd.testing.assert_frame_equal(result, expected)


# ---------------------------------------------------------------------------
# melt_transform_pivot -- documented argument validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        pytest.param(
            {"id_vars": None}, ValueError, "id_vars must contain at least one", id="id-vars-none"
        ),
        pytest.param(
            {"id_vars": []}, ValueError, "id_vars must contain at least one", id="id-vars-empty"
        ),
        pytest.param(
            {"id_vars": 5},
            TypeError,
            "id_vars must be a column name or an iterable",
            id="id-vars-non-iterable",
        ),
        pytest.param(
            {"id_vars": ["missing"]}, ValueError, "id_vars not found", id="id-vars-missing"
        ),
        pytest.param(
            {"id_vars": ["id", "id"]},
            ValueError,
            "id_vars contains duplicate",
            id="id-vars-duplicate",
        ),
        pytest.param(
            {"id_vars": "id", "value_vars": ["missing"]},
            ValueError,
            "value_vars not found",
            id="value-vars-missing",
        ),
        pytest.param(
            {"id_vars": "id", "value_vars": ["left", "left"]},
            ValueError,
            "value_vars contains duplicate",
            id="value-vars-duplicate",
        ),
        pytest.param(
            {"id_vars": "id", "value_vars": ["id", "left"]},
            ValueError,
            "value_vars cannot include id_vars",
            id="value-vars-overlap",
        ),
        pytest.param(
            {"id_vars": "id", "var_name": "  "},
            ValueError,
            "var_name must be a non-empty string",
            id="var-name-empty",
        ),
        pytest.param(
            {"id_vars": "id", "value_name": ""},
            ValueError,
            "value_name must be a non-empty string",
            id="value-name-empty",
        ),
        pytest.param(
            {"id_vars": "id", "var_name": "same", "value_name": "same"},
            ValueError,
            "must be different",
            id="var-name-equals-value-name",
        ),
        pytest.param(
            {"id_vars": "id", "value_name": "left"},
            ValueError,
            "cannot match an existing dataframe column",
            id="value-name-existing",
        ),
        pytest.param(
            {"id_vars": "id", "aggfunc": 5},
            TypeError,
            "aggfunc must be a string or callable",
            id="aggfunc-invalid",
        ),
        pytest.param(
            {"id_vars": "id", "transform_func": "not-callable"},
            TypeError,
            "transform_func must be callable",
            id="transform-func-non-callable",
        ),
        pytest.param(
            {"id_vars": "id", "transform_func": lambda values: [1, 2, 3]},
            ValueError,
            "same number of values",
            id="transform-func-length-mismatch",
        ),
        pytest.param(
            {"id_vars": "id", "transform_func": lambda values: 1 / 0},
            RuntimeError,
            "transform_func failed",
            id="transform-func-raises",
        ),
    ],
)
def test_melt_transform_pivot_rejects_invalid_arguments(kwargs, exception, message):
    frame = pd.DataFrame({"id": [1, 2], "left": ["a", "b"], "right": ["c", "d"]})

    with pytest.raises(exception, match=message):
        columns.melt_transform_pivot(frame, **kwargs)


# ---------------------------------------------------------------------------
# BaseData-level column transformations
# ---------------------------------------------------------------------------


def test_basedata_core_column_transformations_preserve_subclass_and_cache(tmp_path):
    frame = BaseData(
        {
            "user.name": ["Ada", "Grace"],
            "user_id": [1, 2],
            "value": [10, 20],
        },
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    renamed = frame.rename_all_DOTS()
    assert isinstance(renamed, BaseData)
    assert list(renamed.columns) == ["user_name", "user_id", "value"]
    assert renamed.cache_manager is not None
    assert list(frame.drop_by_substring("user").columns) == ["value"]
    pd.testing.assert_frame_equal(frame, original)

    frame.move_column("value", "user_id", position="before", inplace=True)
    assert list(frame.columns) == ["user.name", "value", "user_id"]


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
