"""Accessor argument binding: signature parity and positional `inplace`."""

import inspect

import pandas as pd
import pytest

from bynat.cleaning import BaseData
from bynat.cleaning.accessor import BynatAccessor
from tests.modules.enrichment.helpers import DictTranslator, install_langdetect

pytestmark = pytest.mark.integration


INPLACE_METHODS = [
    "align_lat_lng", "categorize_by_reference", "convert_to_usd", "drop_CLASS_columns",
    "drop_by_substring", "drop_outliers", "extract_entities_nlp", "extract_keywords",
    "fill_missing", "fill_missing_coordinates", "fill_missing_from", "handle_outliers",
    "impute_by_language", "melt_transform_pivot", "move_column", "rename_all_DOTS",
    "rename_by_substring", "reorder_columns", "split_list_objects",
    "translate_categorical_column", "translate_conditional_column", "truncate_after_substring",
]

BASE_COLUMNS = [
    "user.name", "user_id", "C", "A", "id", "longitude", "latitude", "title",
    "status", "part", "detect", "target",
]
DROPPED_USER_COLUMNS = [column for column in BASE_COLUMNS if "user" not in column]
RENAMED_COLUMNS = ["user_name" if column == "user.name" else column for column in BASE_COLUMNS]
ALIGNED_COLUMNS = [
    "latitude" if column == "longitude" else "longitude" if column == "latitude" else column
    for column in BASE_COLUMNS
]

POSITIONAL_CASES = [
    pytest.param("truncate_after_substring", (False, True), {"title": "-"}, BASE_COLUMNS, id="truncate_after_substring"),
    pytest.param("drop_by_substring", ("user", True), {}, DROPPED_USER_COLUMNS, id="drop_by_substring"),
    pytest.param("rename_all_DOTS", ("_", True), {}, RENAMED_COLUMNS, id="rename_all_DOTS"),
    pytest.param("align_lat_lng", (True,), {}, ALIGNED_COLUMNS, id="align_lat_lng"),
    pytest.param(
        "melt_transform_pivot",
        ("id", ["C", "A"], None, "first", "variable_name", "variable_value", None, None, True),
        {},
        ["id", "A", "C"],
        id="melt_transform_pivot",
    ),
    pytest.param(
        "translate_categorical_column",
        ("status", "en", 1000, True),
        {"provider": DictTranslator({"a": "A"})},
        BASE_COLUMNS,
        id="translate_categorical_column",
    ),
    pytest.param(
        "translate_conditional_column",
        ("part", "detect", "target", "en", 10, 3, 0.5, 1000, True),
        {"provider": DictTranslator({"a": "A"})},
        BASE_COLUMNS,
        id="translate_conditional_column",
    ),
]

KEYWORD_ONLY_FLAG_CALLS = {
    "reorder_columns": lambda frame: frame.bynat.reorder_columns("value", "g", True),
    "handle_outliers": lambda frame: frame.bynat.handle_outliers("value", True, hierarchy_cols=["g"]),
}


def _positional_index(signature, name):
    parameters = list(signature.parameters.values())
    return sum(
        1
        for parameter in parameters[: list(signature.parameters).index(name)]
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )


def _positional_frame():
    return pd.DataFrame({
        "user.name": ["Ada", "Grace"], "user_id": [1, 2], "C": [1, 2], "A": [3, 4], "id": [1, 2],
        "longitude": [31.0, 32.0], "latitude": [30.0, 29.0], "title": ["alpha-beta", "gamma"],
        "status": ["a", "a"], "part": ["p", "p"], "detect": ["a", "a"], "target": [None, "a"],
    })


@pytest.mark.parametrize(
    "name",
    INPLACE_METHODS,
    ids=[
        "align_lat_lng", "categorize_by_reference", "convert_to_usd", "drop_CLASS_columns",
        "drop_by_substring", "drop_outliers", "extract_entities_nlp", "extract_keywords",
        "fill_missing", "fill_missing_coordinates", "fill_missing_from", "handle_outliers",
        "impute_by_language", "melt_transform_pivot", "move_column", "rename_all_DOTS",
        "rename_by_substring", "reorder_columns", "split_list_objects",
        "translate_categorical_column", "translate_conditional_column", "truncate_after_substring",
    ],
)
def test_accessor_inplace_parameter_matches_the_class_api_calling_convention(name):
    accessor = inspect.signature(getattr(BynatAccessor, name))
    klass = inspect.signature(getattr(BaseData, name))
    assert accessor.parameters["inplace"].kind is klass.parameters["inplace"].kind
    if accessor.parameters["inplace"].kind is not inspect.Parameter.KEYWORD_ONLY:
        assert _positional_index(accessor, "inplace") == _positional_index(klass, "inplace")


@pytest.mark.parametrize(("name", "args", "kwargs", "expected_columns"), POSITIONAL_CASES)
def test_accessor_inplace_positional_binding_matches_the_class_api(name, args, kwargs, expected_columns, monkeypatch):
    if name == "translate_conditional_column":
        install_langdetect(monkeypatch, lambda text: "ar")
    frame = _positional_frame()
    original_id = id(frame)

    expected = getattr(_positional_frame().bynat, name)(*args[:-1], **kwargs)
    returned = getattr(frame.bynat, name)(*args, **kwargs)

    assert returned is None
    assert id(frame) == original_id
    assert list(frame.columns) == expected_columns
    pd.testing.assert_frame_equal(frame, expected)


@pytest.mark.parametrize("name", KEYWORD_ONLY_FLAG_CALLS, ids=["reorder_columns", "handle_outliers"])
def test_accessor_inplace_keyword_only_methods_reject_a_positional_flag(name):
    frame = pd.DataFrame({"value": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0], "g": ["a"] * 6})
    before = frame.copy(deep=True)

    parameter = inspect.signature(getattr(BynatAccessor, name)).parameters["inplace"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY

    result = KEYWORD_ONLY_FLAG_CALLS[name](frame)

    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


SURPLUS_POSITIONAL_CASES = [
    pytest.param("drop_by_substring", ("user", True, "extra"), id="drop_by_substring"),
    pytest.param("rename_all_DOTS", ("_", True, "extra"), id="rename_all_DOTS"),
    pytest.param("move_column", ("title", "id", "before", True, "extra"), id="move_column"),
    pytest.param(
        "melt_transform_pivot",
        ("id", ["C", "A"], None, "first", "variable_name", "variable_value", None, None, True, "extra"),
        id="melt_transform_pivot",
    ),
]


@pytest.mark.parametrize(("name", "args"), SURPLUS_POSITIONAL_CASES)
def test_accessor_positional_binding_rejects_surplus_arguments_like_the_class_api(name, args, tmp_path):
    plain = _positional_frame()
    legacy = BaseData(_positional_frame(), cache_dir=tmp_path)
    plain_before = plain.copy(deep=True)
    legacy_before = pd.DataFrame(legacy).copy(deep=True)

    with pytest.raises(TypeError):
        getattr(plain.bynat, name)(*args)
    with pytest.raises(TypeError):
        getattr(legacy, name)(*args)

    pd.testing.assert_frame_equal(plain, plain_before)
    pd.testing.assert_frame_equal(pd.DataFrame(legacy), legacy_before)
