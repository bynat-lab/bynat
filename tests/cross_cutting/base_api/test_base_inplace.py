"""BaseData inplace mutation, silence, and accessor rejection contracts."""

import sys
import warnings

import pandas as pd
import pytest

from bynat.cleaning import BaseData, columns, text
from tests.shared.constants import PARITY_DATA

pytestmark = pytest.mark.integration


INPLACE_CASES = [
    pytest.param(
        lambda frame: frame.drop_CLASS_columns(),
        lambda frame: frame.drop_CLASS_columns(inplace=True),
        id="drop_CLASS_columns",
    ),
    pytest.param(
        lambda frame: frame.rename_by_substring("name", "n"),
        lambda frame: frame.rename_by_substring("name", "n", inplace=True),
        id="rename_by_substring",
    ),
    pytest.param(
        lambda frame: frame.reorder_columns("A", "B"),
        lambda frame: frame.reorder_columns("A", "B", inplace=True),
        id="reorder_columns",
    ),
    pytest.param(
        lambda frame: frame.move_column("value", "id", position="before"),
        lambda frame: frame.move_column("value", "id", position="before", inplace=True),
        id="move_column",
    ),
    pytest.param(
        lambda frame: frame.align_lat_lng(),
        lambda frame: frame.align_lat_lng(inplace=True),
        id="align_lat_lng",
    ),
    pytest.param(
        lambda frame: frame.melt_transform_pivot(id_vars="id", value_vars=["C", "A"]),
        lambda frame: frame.melt_transform_pivot(
            id_vars="id", value_vars=["C", "A"], inplace=True
        ),
        id="melt_transform_pivot",
    ),
    pytest.param(
        lambda frame: frame.split_list_objects("items", first=0),
        lambda frame: frame.split_list_objects("items", first=0, inplace=True),
        id="split_list_objects",
    ),
    pytest.param(
        lambda frame: frame.extract_keywords("description", colors=["blue", "red"]),
        lambda frame: frame.extract_keywords(
            "description", colors=["blue", "red"], inplace=True
        ),
        id="extract_keywords",
    ),
    pytest.param(
        lambda frame: frame.truncate_after_substring(regex=False, title="-"),
        lambda frame: frame.truncate_after_substring(
            regex=False, title="-", inplace=True
        ),
        id="truncate_after_substring",
    ),
]


@pytest.mark.parametrize(("copy_call", "inplace_call"), INPLACE_CASES)
def test_inplace_true_matches_the_copy_result_and_returns_none(
    tmp_path, copy_call, inplace_call
):
    frame = BaseData(PARITY_DATA, cache_dir=tmp_path)
    expected = copy_call(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = inplace_call(frame)

    assert returned is None
    pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(expected))


INPLACE_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="PD-01: variadic shared/accessor methods absorb `inplace` instead of "
    "rejecting it; see docs/temb/TEST-02-phase1-audit.md (S-4/ML-2)",
)


def _variadic_frame():
    return pd.DataFrame(
        {
            "id": [1, 2],
            "text": ["alpha-beta", "gamma"],
            "items": [["a", "b"], ["c"]],
            "left": ["x", "y"],
            "right": ["p", "q"],
        }
    )


@INPLACE_XFAIL
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda frame: frame.bynat.extract_keywords("text", found=["alpha"], inplace=True),
            id="extract_keywords",
        ),
        pytest.param(
            lambda frame: frame.bynat.truncate_after_substring(text="-", inplace=True),
            id="truncate_after_substring",
        ),
        pytest.param(
            lambda frame: frame.bynat.split_list_objects("items", first=0, inplace=True),
            id="split_list_objects",
        ),
        pytest.param(
            lambda frame: frame.bynat.melt_transform_pivot(
                id_vars="id", value_vars=["left", "right"], inplace=True
            ),
            id="melt_transform_pivot",
        ),
    ],
)
def test_accessor_rejects_inplace_for_variadic_methods(call):
    with pytest.raises(TypeError):
        call(_variadic_frame())


@INPLACE_XFAIL
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda frame: text.extract_keywords(frame, "text", found=["alpha"], inplace=True),
            id="extract_keywords",
        ),
        pytest.param(
            lambda frame: text.truncate_after_substring(frame, text="-", inplace=True),
            id="truncate_after_substring",
        ),
        pytest.param(
            lambda frame: columns.split_list_objects(frame, "items", first=0, inplace=True),
            id="split_list_objects",
        ),
        pytest.param(
            lambda frame: columns.melt_transform_pivot(
                frame, id_vars="id", value_vars=["left", "right"], inplace=True
            ),
            id="melt_transform_pivot",
        ),
    ],
)
def test_shared_functions_reject_inplace_for_variadic_methods(call):
    with pytest.raises(TypeError):
        call(_variadic_frame())


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda frame: frame.bynat.rename_all_DOTS(inplace=True), id="rename_all_DOTS"),
        pytest.param(lambda frame: frame.bynat.fill_missing("id", inplace=True), id="fill_missing"),
        pytest.param(
            lambda frame: frame.bynat.handle_outliers("id", hierarchy_cols=[], inplace=True),
            id="handle_outliers",
        ),
        pytest.param(
            lambda frame: frame.bynat.get_hierarchical_stats("id", hierarchy_cols=[], inplace=True),
            id="get_hierarchical_stats",
        ),
        pytest.param(lambda frame: frame.bynat.profile(inplace=True), id="profile"),
    ],
)
def test_accessor_rejects_inplace_for_non_variadic_methods(call):
    with pytest.raises(TypeError):
        call(pd.DataFrame({"id": [1, 2]}))


def test_inplace_is_accepted_by_the_class_api_and_rejected_by_the_accessor(tmp_path):
    data = {"g": ["a", "a"], "v": [1.0, None]}
    frame = BaseData(data, cache_dir=tmp_path)

    assert frame.fill_missing("v", hierarchy_cols="g", inplace=True) is None
    assert frame["v"].tolist() == [1.0, 1.0]

    with pytest.raises(TypeError):
        pd.DataFrame(data).bynat.fill_missing("v", hierarchy_cols="g", inplace=True)


def _frame(tmp_path, data=None):
    return BaseData(
        data if data is not None else {"id": [1, 2], "latitude": [1.0, 2.0], "name": ["a", "b"]},
        cache_dir=tmp_path,
    )


def test_inplace_true_still_mutates_and_returns_none(tmp_path):
    frame = _frame(tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert frame.drop_by_substring("name", inplace=True) is None

    assert list(frame.columns) == ["id", "latitude"]


@pytest.mark.parametrize(
    ("call", "returns_stats", "removes_outlier"),
    [
        pytest.param(
            lambda frame: frame.handle_outliers("v", hierarchy_cols=["g"], inplace=True),
            False,
            True,
            id="handle_outliers",
        ),
        pytest.param(
            lambda frame: frame.handle_outliers(
                "v", hierarchy_cols=["g"], inplace=True, get_hierarchical_stats=True
            ),
            True,
            True,
            id="handle_outliers_with_stats",
        ),
        pytest.param(
            lambda frame: frame.fill_missing("v", hierarchy_cols="g", inplace=True),
            False,
            False,
            id="fill_missing",
        ),
        pytest.param(
            lambda frame: frame.fill_missing_from(frame, "v", hierarchy_cols="g", inplace=True),
            False,
            False,
            id="fill_missing_from",
        ),
        pytest.param(
            lambda frame: frame.rename_all_DOTS(inplace=True),
            False,
            False,
            id="rename_all_DOTS",
        ),
    ],
)
def test_every_inplace_path_is_silent_and_preserves_behavior(
    tmp_path, call, returns_stats, removes_outlier
):
    frame = _frame(tmp_path, {"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]})
    before = frame.copy()

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        result = call(frame)

    assert isinstance(frame, BaseData)
    if returns_stats:
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
    else:
        assert result is None

    if removes_outlier:
        assert bool(frame["v"].isna().iloc[-1])
    else:
        pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(before))


def test_inplace_false_and_default_do_not_warn(tmp_path):
    frame = _frame(tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        res1 = frame.drop_by_substring("name")
        res2 = frame.drop_by_substring("name", inplace=False)

    assert isinstance(res1, BaseData)
    assert isinstance(res2, BaseData)
    assert "name" not in res1.columns
    assert "name" not in res2.columns


def test_split_list_objects_inplace_explode_reshapes_the_original(tmp_path):
    frame = _frame(tmp_path, {"id": [1, 2], "items": [["a", "b"], ["c"]]})
    expected = frame.split_list_objects("items", explode_rows=True, first=[0, 1])

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert frame.split_list_objects("items", explode_rows=True, inplace=True, first=[0, 1]) is None

    pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(expected))
    assert frame["first"].tolist() == ["a", "b", "c"]
    assert len(frame) == 3


def test_inplace_results_are_not_aliases(tmp_path):
    frame = _frame(tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        frame.rename_all_DOTS(inplace=True)

    result = frame.rename_all_DOTS()
    result.loc[0, "id"] = 99

    assert frame.loc[0, "id"] == 1


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
