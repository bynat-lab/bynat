"""Structural column transformations: drop, rename, reorder, and coordinate alignment."""

import pandas as pd

from bynat.cleaning import BaseData


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

    lower = pd.DataFrame({"lng": [31.0], "id": [1], "lat": [30.0]})
    untouched = lower.bynat.align_lat_lng()
    assert list(untouched.columns) == ["lng", "id", "lat"]

    no_longitude = pd.DataFrame({"id": [1], "latitude": [30.0]})
    assert list(no_longitude.bynat.align_lat_lng().columns) == ["id", "latitude"]


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
