"""BaseData API contracts: inplace parity, mutability, and ``inplace`` rejection."""

import json
import sys
import warnings

import pandas as pd
import pytest

from bynat.caching import CacheManager
from bynat.cleaning import BaseData, CsvFile, JsonFile, columns, text

# Local copy of the parity dataset; kept file-local so no test imports another
# test module.

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


# ---------------------------------------------------------------------------
# PD-01 -- `inplace` rejection on shared functions and the accessor
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# API-02 -- `inplace=True` deprecation and early-exit copies
# ---------------------------------------------------------------------------


def _frame(tmp_path, data=None):
    return BaseData(
        data if data is not None else {"id": [1, 2], "latitude": [1.0, 2.0], "name": ["a", "b"]},
        cache_dir=tmp_path,
    )


# Calls that take an early-exit path because nothing needs changing.
EARLY_EXITS = {
    "drop_by_substring": lambda frame: frame.drop_by_substring("missing"),
    "drop_CLASS_columns": lambda frame: frame.drop_CLASS_columns(),
    "rename_by_substring": lambda frame: frame.rename_by_substring("missing", "x"),
    "rename_all_DOTS": lambda frame: frame.rename_all_DOTS(),
    "reorder_columns": lambda frame: frame.reorder_columns("missing"),
    "move_column": lambda frame: frame.move_column("missing", "id"),
    "align_lat_lng": lambda frame: frame.align_lat_lng(),
    "extract_keywords": lambda frame: frame.extract_keywords("missing", found=["a"]),
    "split_list_objects": lambda frame: frame.split_list_objects("missing"),
    "impute_by_language": lambda frame: frame.impute_by_language("missing"),
    "translate_conditional_column": lambda frame: frame.translate_conditional_column("missing", "id", "name"),
    "translate_categorical_column": lambda frame: frame.translate_categorical_column("missing"),
    "truncate_after_substring": lambda frame: frame.truncate_after_substring(),
    "fill_missing_coordinates": lambda frame: frame.fill_missing_coordinates(lat_col="missing", long_col="lng"),
    "convert_to_usd": lambda frame: frame.convert_to_usd("id", country_col="missing", year_col="year"),
    "handle_outliers": lambda frame: frame.handle_outliers("id", hierarchy_cols=[]),
    "drop_outliers": lambda frame: frame.drop_outliers("id", hierarchy_cols=[]),
    "fill_missing": lambda frame: frame.fill_missing("missing"),
    "fill_missing_from": lambda frame: frame.fill_missing_from(frame, "missing"),
    "categorize_by_reference": lambda frame: frame.categorize_by_reference("missing", target_col="c", reference={}),
    "extract_entities_nlp": lambda frame: frame.extract_entities_nlp(
        "missing", lexicon_source={"skills": ["python"]}, skills="skills"
    ),
}


@pytest.mark.parametrize("method_name", sorted(EARLY_EXITS))
def test_early_exits_return_an_independent_copy(tmp_path, method_name):
    frame = _frame(tmp_path)
    original = frame.copy()

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        result = EARLY_EXITS[method_name](frame)

    assert result is not frame
    assert isinstance(result, BaseData)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(original))

    result["id"] = [10, 20]
    assert frame["id"].tolist() == [1, 2]


def test_early_exit_with_stats_returns_a_copy(tmp_path):
    frame = _frame(tmp_path, {"g": ["a"] * 3, "v": [1.0, 2.0, 3.0]})

    result, stats = frame.handle_outliers("v", hierarchy_cols=[], get_hierarchical_stats=True)

    assert result is not frame
    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(frame))
    assert stats.empty


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
        frame.drop_by_substring("name")
        frame.drop_by_substring("name", inplace=False)


def test_split_list_objects_inplace_explode_reshapes_the_original(tmp_path):
    frame = _frame(tmp_path, {"id": [1, 2], "items": [["a", "b"], ["c"]]})
    expected = frame.split_list_objects("items", explode_rows=True, first=[0, 1])

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert frame.split_list_objects("items", explode_rows=True, inplace=True, first=[0, 1]) is None

    pd.testing.assert_frame_equal(pd.DataFrame(frame), pd.DataFrame(expected))
    assert frame["first"].tolist() == ["a", "b", "c"]
    assert len(frame) == 3


def test_melt_transform_pivot_result_keeps_the_cache_manager(tmp_path):
    frame = _frame(tmp_path, {"id": [1, 2], "left": ["a", "b"], "right": ["c", "d"]})
    original = frame.copy(deep=True)

    result = frame.melt_transform_pivot(id_vars="id", transform_func=lambda values: values.str.upper())

    assert isinstance(result, BaseData)
    assert result.cache_manager is frame.cache_manager
    pd.testing.assert_frame_equal(frame, original)


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


# ---------------------------------------------------------------------------
# Cleaning constructors and documented boundary errors
# ---------------------------------------------------------------------------


def test_public_cleaning_imports_use_the_bundled_cache_manager(tmp_path):
    frame = BaseData({"value": [1]}, cache_dir=tmp_path)

    assert isinstance(frame.cache_manager, CacheManager)
    assert BaseData.__module__ == "bynat.cleaning.base"
    legacy = __import__("bynat.cleaning.Cleaning", fromlist=["__all__"])
    assert legacy.BaseData is BaseData
    assert {"BaseData", "JsonFile", "CsvFile"}.issubset(set(legacy.__all__))


def test_basedata_boundary_errors_and_inplace_return(tmp_path):
    frame = BaseData({"id": [1], "first": [2]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="position"):
        frame.move_column("id", "first", position="middle")
    with pytest.raises(ValueError, match="positive integer"):
        frame.translate_categorical_column("first", save_every=0)

    assert frame.drop_by_substring("missing", inplace=True) is None
    assert list(frame.columns) == ["id", "first"]


def test_json_and_csv_constructors_read_local_files(tmp_path):
    json_path = tmp_path / "records.json"
    json_path.write_text(json.dumps({"items": [{"name": "Ada", "age": 37}]}), encoding="utf-8")
    csv_path = tmp_path / "records.csv"
    csv_path.write_text("name;age\nGrace;28\n", encoding="utf-8")

    json_frame = JsonFile(json_file_path=json_path, key="items", cache_dir=tmp_path / "json-cache")
    csv_frame = CsvFile(csv_file_path=csv_path, read_kwargs={"sep": ";"}, cache_dir=tmp_path / "csv-cache")

    assert list(json_frame.columns) == ["name", "age"]
    assert json_frame.iloc[0]["name"] == "Ada"
    assert list(csv_frame.columns) == ["name", "age"]
    assert csv_frame.iloc[0]["name"] == "Grace"
    assert isinstance(json_frame.view(), pd.DataFrame)
    assert type(json_frame.view()) is pd.DataFrame


def test_file_constructors_raise_for_missing_paths(tmp_path):
    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        JsonFile(json_file_path=tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        CsvFile(csv_file_path=tmp_path / "missing.csv")
