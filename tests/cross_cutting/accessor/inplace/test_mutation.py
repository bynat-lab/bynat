"""`df.bynat` in-place execution contract: identity, validation, and exclusions."""

import warnings

import pandas as pd
import pytest

from bynat.cleaning import BaseData

pytestmark = pytest.mark.integration


EXCLUDED_METHODS = [
    "get_hierarchical_stats", "profile", "save_to_json", "save_to_sql",
    "clear_cache_for_column", "with_cache",
]


def _sqlite_arguments(database):
    return {"database_type": "sqlite", "database_user": "", "database_password": "",
            "database_host": "", "database_port": "", "database_name": str(database)}


@pytest.mark.parametrize(
    "method_name",
    EXCLUDED_METHODS,
    ids=[
        "get_hierarchical_stats", "profile", "save_to_json",
        "save_to_sql", "clear_cache_for_column", "with_cache",
    ],
)
def test_accessor_methods_without_inplace_support_still_reject_the_keyword(tmp_path, method_name):
    frame = pd.DataFrame({"v": [1.0, None]})
    calls = {
        "get_hierarchical_stats": lambda: frame.bynat.get_hierarchical_stats("v", inplace=True),
        "profile": lambda: frame.bynat.profile(inplace=True),
        "save_to_json": lambda: frame.bynat.save_to_json(tmp_path / "out.json", inplace=True),
        "save_to_sql": lambda: frame.bynat.save_to_sql(
            "items", **_sqlite_arguments(tmp_path / "db.sqlite"), inplace=True),
        "clear_cache_for_column": lambda: frame.bynat.clear_cache_for_column(
            "translate_categorical_column", "status", inplace=True),
        "with_cache": lambda: frame.bynat.with_cache(tmp_path, inplace=True),
    }

    with pytest.raises(TypeError):
        calls[method_name]()


def test_accessor_inplace_true_validates_before_mutating():
    frame = pd.DataFrame({"id": [1, 2], "value": [3, 4]})
    before = frame.copy(deep=True)
    original_id = id(frame)

    with pytest.raises(ValueError, match="position"):
        frame.bynat.move_column("id", "value", position="middle", inplace=True)

    assert id(frame) == original_id
    pd.testing.assert_frame_equal(frame, before)


def test_accessor_inplace_false_keeps_the_source_unchanged_when_the_call_raises():
    frame = pd.DataFrame({"id": [1, 2], "value": [3, 4]})
    before = frame.copy(deep=True)

    with pytest.raises(ValueError, match="position"):
        frame.bynat.move_column("id", "value", position="middle")

    pd.testing.assert_frame_equal(frame, before)


def test_accessor_inplace_shape_changing_transformation_preserves_identity():
    frame = pd.DataFrame({"id": [1, 2], "items": [["a", "b"], ["c"]]})
    original_id = id(frame)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.bynat.split_list_objects("items", explode_rows=True, first=[0, 1], inplace=True)

    assert returned is None
    assert id(frame) == original_id
    assert len(frame) == 3


def test_accessor_inplace_repeated_calls_accumulate_on_the_same_object():
    frame = pd.DataFrame({"user.name": ["a"], "user_id": [1], "x": [2]})
    original_id = id(frame)

    assert frame.bynat.drop_by_substring("user", inplace=True) is None
    assert list(frame.columns) == ["x"]
    assert frame.bynat.drop_by_substring("user", inplace=True) is None
    assert list(frame.columns) == ["x"]
    assert id(frame) == original_id


def test_accessor_inplace_on_a_basedata_frame_preserves_its_cache_manager(tmp_path):
    frame = BaseData({"user.name": ["a"]}, cache_dir=tmp_path)
    manager = frame.cache_manager
    original_id = id(frame)

    returned = frame.bynat.rename_all_DOTS(inplace=True)

    assert returned is None
    assert id(frame) == original_id
    assert list(frame.columns) == ["user_name"]
    assert frame.cache_manager is manager


def test_inplace_is_accepted_by_the_class_api_and_the_accessor(tmp_path):
    data = {"g": ["a", "a"], "v": [1.0, None]}
    frame = BaseData(data, cache_dir=tmp_path)
    plain = pd.DataFrame(data)

    assert frame.fill_missing("v", hierarchy_cols="g", inplace=True) is None
    assert frame["v"].tolist() == [1.0, 1.0]

    identity = id(plain)
    assert plain.bynat.fill_missing("v", hierarchy_cols="g", inplace=True) is None
    assert id(plain) == identity
    assert plain["v"].tolist() == [1.0, 1.0]
