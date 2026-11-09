"""Melt, transform, and pivot layout transformations and validation."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData, columns


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

    columns_first = frame.bynat.melt_transform_pivot(
        id_vars="id", value_vars=["left", "right"], pivot_columns="id"
    )
    expected_columns = pd.DataFrame(
        {"variable_name": ["left", "right"], 1: ["a", "d"], 2: ["c", "f"]}
    )
    pd.testing.assert_frame_equal(columns_first, expected_columns)

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
