"""TEST-02 Phase 3: transformation API contract coverage.

Pins documented transformation contracts that the existing suite did not
cover: positive paths for the column/text reshaping helpers, the
``split_list_objects`` variants, ``melt_transform_pivot`` layouts and
aggregation, the ``impute_by_language`` resolution hierarchy, strategy
normalization and non-null ``min_samples`` counting, reference-imputation
edge contracts, and class/accessor and inplace parity.

Input-validation contracts (rejected argument types and values, malformed
layout arguments, and the two unimplemented target contracts PD-01/PD-02)
are covered by ``tests/test_phase3_input_validation.py`` and are
deliberately not duplicated here.

Expected values are derived by hand from the documented behavior; comparisons
use ``pandas.testing`` helpers with default strictness.
"""

import sys
import types
import warnings

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData

OUTPUT_COLUMNS = [
    "hierarchy_level",
    "hierarchy_columns",
    "group_key",
    "target_column",
    "strategy",
    "statistic",
]


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
# truncate_after_substring
# ---------------------------------------------------------------------------


def test_truncate_after_substring_literal_delimiters():
    frame = pd.DataFrame(
        {
            "title": ["Software Engineer - Remote", "Data Analyst (Junior)", np.nan],
            "company": ["Tech Corp, LLC", "Data Inc.", "X"],
        },
        index=pd.Index([2, 4, 6], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.truncate_after_substring(
        regex=False, title=["-", "("], company=","
    )

    index = pd.Index([2, 4, 6], name="row")
    expected = pd.DataFrame(
        {
            # The helper casts targeted columns to object before splitting.
            "title": pd.Series(
                ["Software Engineer", "Data Analyst", np.nan], index=index, dtype=object
            ),
            "company": pd.Series(["Tech Corp", "Data Inc.", "X"], index=index, dtype=object),
        }
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)

    # A missing target column is skipped; a call with no targets is a copy.
    assert list(frame.bynat.truncate_after_substring(regex=False, missing="-").columns) == [
        "title",
        "company",
    ]
    no_targets = frame.bynat.truncate_after_substring()
    assert no_targets is not frame
    pd.testing.assert_frame_equal(no_targets, frame)


def test_truncate_after_substring_regex_delimiters():
    frame = pd.DataFrame(
        {
            "text": ["foo -- bar", "baz", np.nan],
            "title": ["Data Analyst (Junior)", "x", np.nan],
        }
    )
    before = frame.copy(deep=True)

    result = frame.bynat.truncate_after_substring(regex=True, text=r"--\s*", title=r"\(")

    index = pd.Index([0, 1, 2])
    expected = pd.DataFrame(
        {
            "text": pd.Series(["foo", "baz", np.nan], index=index, dtype=object),
            "title": pd.Series(["Data Analyst", "x", np.nan], index=index, dtype=object),
        }
    )
    pd.testing.assert_frame_equal(result, expected)
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
# impute_by_language
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_langdetect(monkeypatch):
    module = types.ModuleType("langdetect")

    class DetectorFactory:
        seed = None

    module.DetectorFactory = DetectorFactory
    module.LangDetectException = Exception
    module.detect = lambda text: "en"
    monkeypatch.setitem(sys.modules, "langdetect", module)
    return module


def test_impute_by_language_exact_detection_and_generated_fallback(fake_langdetect):
    fake_langdetect.detect = lambda text: "en" if text == "Pear (FR)" else "ar"
    frame = pd.DataFrame(
        {
            "slug": ["red-apple", "green-pear", "yellow-banana", "red-apple", "one-two"],
            "name": [None, "Pear (FR)", "موز", "Red Apple", "123"],
            "extra": [1, 2, 3, 4, 5],
        },
        index=pd.Index([3, 4, 5, 6, 7], name="row"),
    )
    before = frame.copy(deep=True)

    result = frame.bynat.impute_by_language("slug", "name", target_lang="en")

    # Pass 1 (exact, case- and hyphen-insensitive): "Red Apple" -> "Red Apple".
    # Pass 2 (detection): "Pear (FR)" is detected as English and kept.
    # Pass 3 (generation): the remaining references are title-cased.
    # Numeric text is never sent to the detector.
    expected = pd.DataFrame(
        {
            "slug": ["red-apple", "green-pear", "yellow-banana", "red-apple", "one-two"],
            "name": ["Red Apple", "Pear (FR)", "Yellow Banana", "Red Apple", "One Two"],
            "extra": [1, 2, 3, 4, 5],
        },
        index=pd.Index([3, 4, 5, 6, 7], name="row"),
    )
    pd.testing.assert_frame_equal(result, expected)
    assert result is not frame
    assert fake_langdetect.DetectorFactory.seed == 0
    pd.testing.assert_frame_equal(frame, before)

    # The seed makes repeated runs deterministic.
    again = frame.bynat.impute_by_language("slug", "name", target_lang="en")
    pd.testing.assert_frame_equal(again, result)


def test_impute_by_language_honors_target_lang(fake_langdetect):
    fake_langdetect.detect = lambda text: "en"
    frame = pd.DataFrame({"slug": ["green-pear"], "name": ["English Label"]})

    kept = frame.bynat.impute_by_language("slug", "name", target_lang="en")
    generated = frame.bynat.impute_by_language("slug", "name", target_lang="ar")

    assert kept["name"].tolist() == ["English Label"]
    assert generated["name"].tolist() == ["Green Pear"]


def test_impute_by_language_skips_missing_columns(fake_langdetect):
    frame = pd.DataFrame({"slug": ["a-b"], "name": [None], "other": [1]})
    before = frame.copy(deep=True)

    missing_target = frame.bynat.impute_by_language("slug", "missing")
    missing_reference = frame.bynat.impute_by_language("missing", "name")

    assert missing_target is not frame
    assert missing_reference is not frame
    pd.testing.assert_frame_equal(missing_target, frame)
    pd.testing.assert_frame_equal(missing_reference, frame)
    pd.testing.assert_frame_equal(frame, before)


def test_impute_by_language_inplace_matches_the_copy_result(tmp_path, fake_langdetect):
    fake_langdetect.detect = lambda text: "en"
    frame = BaseData({"slug": ["a-b"], "name": [None]}, cache_dir=tmp_path)
    expected = frame.impute_by_language("slug", "name")

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        returned = frame.impute_by_language("slug", "name", inplace=True)

    assert returned is None
    pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(expected))


# ---------------------------------------------------------------------------
# fill_missing: strategy normalization, boundaries, no-op input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("min_samples", "expected_last"),
    [pytest.param(2, 2.0, id="boundary_included"), pytest.param(3, np.nan, id="boundary_excluded")],
)
def test_fill_missing_min_samples_counts_only_non_null_observations(min_samples, expected_last):
    frame = pd.DataFrame({"g": ["a", "a", "a"], "v": [1.0, 3.0, None]})
    before = frame.copy(deep=True)

    result = frame.bynat.fill_missing("v", hierarchy_cols=["g"], min_samples=min_samples)

    expected = pd.Series([1.0, 3.0, expected_last], name="v", index=frame.index)
    pd.testing.assert_series_equal(result["v"], expected)
    pd.testing.assert_frame_equal(frame, before)


def test_fill_missing_uppercase_strategy_matches_lowercase():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, None]})
    before = frame.copy(deep=True)

    upper = frame.bynat.fill_missing("v", strategy="MEDIAN", hierarchy_cols=["g"])
    lower = frame.bynat.fill_missing("v", strategy="median", hierarchy_cols=["g"])

    pd.testing.assert_frame_equal(upper, lower)
    assert upper["v"].tolist() == [1.0, 1.0]
    pd.testing.assert_frame_equal(frame, before)


def test_fill_missing_without_missing_values_returns_an_independent_copy():
    frame = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    before = frame.copy(deep=True)

    result = frame.bynat.fill_missing("v", hierarchy_cols=["g"])

    assert result is not frame
    pd.testing.assert_frame_equal(result, frame)
    pd.testing.assert_frame_equal(frame, before)


# ---------------------------------------------------------------------------
# fill_missing_from: edge contracts
# ---------------------------------------------------------------------------


def test_fill_missing_from_non_numeric_target_with_numeric_strategy_raises():
    train = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    target = pd.DataFrame({"g": ["a", "a"], "v": ["x", None]})

    with pytest.raises(TypeError, match="numeric dtype"):
        target.bynat.fill_missing_from(train, "v", strategy="median", hierarchy_cols=["g"])


def test_fill_missing_from_stats_reverse_map_match_cols():
    train = pd.DataFrame({"nation": ["EG", "EG", "US"], "wage": [10.0, 20.0, 30.0]})
    target = pd.DataFrame({"country": ["EG", "US"], "salary": [None, None]})
    before = target.copy(deep=True)

    result, stats_result = target.bynat.fill_missing_from(
        train,
        "salary",
        match_cols={"salary": "wage", "country": "nation"},
        hierarchy_cols=["country"],
        get_hierarchical_stats=True,
    )

    assert result["salary"].tolist() == [15.0, 30.0]
    assert list(stats_result.columns) == OUTPUT_COLUMNS
    # The schema is reverse-mapped to the target names, but the statistics
    # come from the reference column.
    assert stats_result["target_column"].tolist() == ["salary", "salary"]
    assert stats_result["hierarchy_columns"].tolist() == [("country",), ("country",)]
    assert stats_result["group_key"].tolist() == [("EG",), ("US",)]
    assert stats_result["strategy"].tolist() == ["median", "median"]
    assert stats_result["statistic"].tolist() == [15.0, 30.0]
    pd.testing.assert_frame_equal(target, before)


def test_fill_missing_from_inplace_with_stats_returns_stats_and_mutates(tmp_path):
    train = BaseData({"g": ["a", "a", "b"], "v": [10.0, 20.0, 30.0]}, cache_dir=tmp_path)
    frame = BaseData({"g": ["a", "b"], "v": [None, None]}, cache_dir=tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        stats_result = frame.fill_missing_from(
            train,
            "v",
            hierarchy_cols=["g"],
            get_hierarchical_stats=True,
            inplace=True,
        )

    assert type(stats_result) is BaseData
    assert list(stats_result.columns) == OUTPUT_COLUMNS
    assert frame["v"].tolist() == [15.0, 30.0]


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
