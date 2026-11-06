import json
import sys
import types

import numpy as np
import pandas as pd
import pytest

from bynat.caching import CacheManager
from bynat.cleaning import BaseData, CsvFile, JsonFile


def test_public_cleaning_imports_use_the_bundled_cache_manager(tmp_path):
    frame = BaseData({"value": [1]}, cache_dir=tmp_path)

    assert isinstance(frame.cache_manager, CacheManager)
    assert BaseData.__module__ == "bynat.cleaning.base"
    legacy = __import__("bynat.cleaning.Cleaning", fromlist=["__all__"])
    assert legacy.BaseData is BaseData
    assert {"BaseData", "JsonFile", "CsvFile"}.issubset(set(legacy.__all__))


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


def test_basedata_text_list_reshape_and_imputation_helpers(tmp_path):
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

    keywords = frame.extract_keywords("description", colors=["blue", "red"])
    assert keywords["colors"].tolist() == ["Blue", "Red"]

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

    imputed = frame.fill_missing("score", hierarchy_cols="group")
    assert imputed["score"].tolist() == [1.0, 1.0]

    pd.testing.assert_frame_equal(frame, original)


def test_save_to_json_writes_local_output(tmp_path):
    output = tmp_path / "nested" / "records.json"
    BaseData({"name": ["Ada"]}, cache_dir=tmp_path).save_to_json(output)

    assert json.loads(output.read_text(encoding="utf-8")) == [{"name": "Ada"}]


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


def test_impute_by_language_missing_reference_returns_before_optional_import(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "langdetect", None)
    frame = BaseData({"category": ["pending"]}, cache_dir=tmp_path)

    result = frame.impute_by_language("missing")
    assert result is not frame
    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(frame))
    assert frame.impute_by_language("missing", inplace=True) is None


def test_optional_integration_reports_missing_dependency_at_method_use(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    frame = BaseData({"category": ["pending"]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="deep-translator"):
        frame.translate_categorical_column("category")


def test_optional_categorization_reports_missing_dependency_at_method_use(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "ahocorasick", None)
    frame = BaseData({"description": ["python developer"]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="pyahocorasick"):
        frame.categorize_by_reference(
            "description",
            target_col="category",
            reference={"Software": ["python developer"]},
        )


def test_translate_conditional_safe_partition_does_not_import_deep_translator(monkeypatch, tmp_path):
    detect_calls = []

    class DetectorFactory:
        seed = None

    langdetect = types.ModuleType("langdetect")
    langdetect.DetectorFactory = DetectorFactory
    langdetect.detect = lambda text: detect_calls.append(text) or "en"

    class FailingGoogleTranslator:
        def __init__(self, *args, **kwargs):
            pytest.fail("deep-translator should not be required for a safe partition")

    deep_translator = types.ModuleType("deep_translator")
    deep_translator.GoogleTranslator = FailingGoogleTranslator
    monkeypatch.setitem(sys.modules, "langdetect", langdetect)
    monkeypatch.setitem(sys.modules, "deep_translator", deep_translator)

    frame = BaseData(
        {"partition": ["safe"], "description": ["already English"], "label": ["Existing Label"]},
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    result = frame.translate_conditional_column(
        partition_col="partition",
        detect_col="description",
        target_col="label",
        sample_size=1,
        number_of_samples=2,
        threshold=1.0,
        save_every=1,
    )

    assert type(result) is type(frame)
    pd.testing.assert_frame_equal(pd.DataFrame(result), pd.DataFrame(frame))
    assert DetectorFactory.seed == 0
    assert len(detect_calls) == 2
    pd.testing.assert_frame_equal(frame, original)


def test_translate_conditional_missing_langdetect_raises_documented_import_error(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "langdetect", None)
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    frame = BaseData(
        {"partition": ["group"], "description": ["text"], "label": ["value"]},
        cache_dir=tmp_path,
    )

    with pytest.raises(ImportError, match="langdetect"):
        frame.translate_conditional_column(
            partition_col="partition",
            detect_col="description",
            target_col="label",
            sample_size=1,
            number_of_samples=1,
        )



def test_save_to_json_append_keeps_existing_rows_with_list_columns(tmp_path):
    file_path = tmp_path / "out.json"

    BaseData({"a": [1, 2], "tags": [["x"], ["y"]]}, cache_dir=tmp_path).save_to_json(file_path)
    BaseData({"a": [2, 3], "tags": [["y"], ["z"]]}, cache_dir=tmp_path).save_to_json(
        file_path, append=True
    )

    saved = json.loads(file_path.read_text(encoding="utf-8"))

    assert saved == [
        {"a": 1, "tags": ["x"]},
        {"a": 2, "tags": ["y"]},
        {"a": 3, "tags": ["z"]},
    ]


@pytest.mark.parametrize(
    "index",
    [
        pd.Index(range(10, 16), name="row_id"),
        pd.MultiIndex.from_tuples([("k", i) for i in range(6)], names=["k", "i"]),
        pd.Index([0, 0, 1, 1, 2, 2]),
    ],
)
def test_hierarchy_methods_support_named_multi_and_duplicate_indexes(tmp_path, index):
    frame = BaseData(
        {"g": ["a"] * 6, "v": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]},
        index=index,
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    handled = frame.handle_outliers("v", hierarchy_cols=["g"])
    dropped = frame.drop_outliers("v", hierarchy_cols=["g"])

    assert handled["v"].isna().tolist() == [False] * 5 + [True]
    assert handled.index.equals(index)
    assert dropped["v"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert dropped.index.equals(index[:5])
    pd.testing.assert_frame_equal(frame, original)

    in_place = frame.copy()
    assert in_place.drop_outliers("v", hierarchy_cols=["g"], inplace=True) is None
    assert in_place.equals(dropped)

    modes = BaseData(
        {"g": ["a"] * 6, "c": ["x", "x", "y", None, "x", None]},
        index=index,
        cache_dir=tmp_path,
    ).fill_missing("c", strategy="mode", hierarchy_cols=["g"])

    assert modes["c"].tolist() == ["x", "x", "y", "x", "x", "x"]
    assert modes.index.equals(index)



def test_save_to_json_append_deduplicates_plain_columns_without_json_keys(tmp_path, monkeypatch):
    import bynat.cleaning.io as cleaning

    file_path = tmp_path / "out.json"
    BaseData({"a": [1, 2], "b": ["x", "y"]}, cache_dir=tmp_path).save_to_json(file_path)

    monkeypatch.setattr(cleaning, "_dedupe_key", lambda value: pytest.fail("fast path expected"))
    BaseData({"a": [2, 3], "b": ["y", "z"]}, cache_dir=tmp_path).save_to_json(file_path, append=True)

    assert json.loads(file_path.read_text(encoding="utf-8")) == [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
        {"a": 3, "b": "z"},
    ]


def test_fill_missing_rejects_unknown_strategy(tmp_path):
    frame = BaseData({"g": ["a", "a"], "v": [1.0, None]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid strategy 'sum'"):
        frame.fill_missing("v", strategy="sum", hierarchy_cols="g")


def test_save_to_json_append_refuses_to_overwrite_unreadable_file(tmp_path):
    file_path = tmp_path / "out.json"
    file_path.write_text('{"not": "records"', encoding="utf-8")

    with pytest.raises(ValueError, match="Cannot append"):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_json(file_path, append=True)

    assert file_path.read_text(encoding="utf-8") == '{"not": "records"'


def test_save_to_json_requires_file_path(tmp_path):
    with pytest.raises(ValueError, match="file_path"):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_json("  ")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"table_name": " "}, "table_name"),
        ({"if_exists": "merge"}, "if_exists"),
        ({"database_type": ""}, "database_type"),
        ({"database_name": ""}, "SQLite"),
        ({"database_type": "postgresql", "database_host": ""}, "are required"),
        ({"database_type": "mssql+pyodbc", "database_user": "u", "database_password": "p",
          "database_host": "h", "database_port": "1"}, "database_driver"),
    ],
)
def test_save_to_sql_rejects_invalid_arguments_before_connecting(monkeypatch, tmp_path, kwargs, message):
    monkeypatch.setitem(sys.modules, "sqlalchemy", None)
    arguments = {
        "table_name": "items",
        "database_type": "sqlite",
        "database_user": "",
        "database_password": "",
        "database_host": "",
        "database_port": "",
        "database_name": str(tmp_path / "out.db"),
        "if_exists": "append",
    }
    arguments.update(kwargs)

    with pytest.raises(ValueError, match=message):
        BaseData({"a": [1]}, cache_dir=tmp_path).save_to_sql(**arguments)


def test_fill_missing_min_samples_and_fallback_global_reproduction():
    from bynat.cleaning import stats

    # 1) A group with no observed values stays NaN by default, filled when fallback_global=True
    df1 = pd.DataFrame({
        "country": ["EG", "EG", "EG", "US", "US", "DE"],
        "salary":  [10.0, 14.0, np.nan, 70.0, 90.0, np.nan],
    })
    df1_before = df1.copy(deep=True)

    default_res = stats.fill_missing(df1, "salary", strategy="median", hierarchy_cols=["country"])
    assert pd.isna(default_res.loc[5, "salary"])
    assert default_res.loc[2, "salary"] == 12.0

    fallback_res = stats.fill_missing(
        df1, "salary", strategy="median", hierarchy_cols=["country"], fallback_global=True
    )
    assert fallback_res.loc[2, "salary"] == 12.0
    # Global median of observed [10, 14, 70, 90] is 42.0
    assert fallback_res.loc[5, "salary"] == 42.0

    # 2) A single-value group is trusted fully by default (min_samples=1), skipped when min_samples=2
    df2 = pd.DataFrame({
        "country": ["EG", "EG", "US", "US"],
        "salary":  [10.0, np.nan, 1000.0, np.nan],
    })
    df2_before = df2.copy(deep=True)
    res_min1 = stats.fill_missing(df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=1)
    assert res_min1.loc[1, "salary"] == 10.0
    assert res_min1.loc[3, "salary"] == 1000.0

    res_min2 = stats.fill_missing(df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=2)
    assert pd.isna(res_min2.loc[1, "salary"])
    assert pd.isna(res_min2.loc[3, "salary"])

    res_min2_fallback = stats.fill_missing(
        df2, "salary", strategy="median", hierarchy_cols=["country"], min_samples=2, fallback_global=True
    )
    # Global median of [10.0, 1000.0] is 505.0
    assert res_min2_fallback.loc[1, "salary"] == 505.0
    assert res_min2_fallback.loc[3, "salary"] == 505.0

    # 3) hierarchy_cols=None: nothing filled when fallback_global=False, plain imputation when fallback_global=True
    res_none_default = stats.fill_missing(df1, "salary", strategy="median")
    assert pd.isna(res_none_default.loc[2, "salary"])
    assert pd.isna(res_none_default.loc[5, "salary"])

    res_none_global = stats.fill_missing(df1, "salary", strategy="median", fallback_global=True)
    assert res_none_global.loc[2, "salary"] == 42.0
    assert res_none_global.loc[5, "salary"] == 42.0

    pd.testing.assert_frame_equal(df1, df1_before)
    pd.testing.assert_frame_equal(df2, df2_before)


def test_fill_missing_validates_min_samples(tmp_path):
    frame = BaseData({"g": ["a", "a"], "v": [1.0, None]}, cache_dir=tmp_path)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=0)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=-3)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples=True)

    with pytest.raises(ValueError, match="min_samples must be an integer greater than or equal to 1"):
        frame.fill_missing("v", hierarchy_cols="g", min_samples="2")  # type: ignore[arg-type]


def test_fill_missing_hierarchical_fallthrough_multi_level():
    df = pd.DataFrame({
        "country": ["EG", "EG", "EG", "EG", "US", "US"],
        "city":    ["Cairo", "Cairo", "Alex", "Alex", "NYC", "NYC"],
        "salary":  [100.0, np.nan, 20.0, 40.0, 500.0, np.nan],
    })
    original = df.copy(deep=True)

    res_no_global = df.bynat.fill_missing(
        "salary", strategy="median", hierarchy_cols=["country", "city"], min_samples=2
    )
    assert res_no_global.loc[1, "salary"] == 40.0
    assert pd.isna(res_no_global.loc[5, "salary"])

    res_global = df.bynat.fill_missing(
        "salary", strategy="median", hierarchy_cols=["country", "city"], min_samples=2, fallback_global=True
    )
    assert res_global.loc[1, "salary"] == 40.0
    assert res_global.loc[5, "salary"] == 70.0

    pd.testing.assert_frame_equal(df, original)


def test_fill_missing_all_strategies_with_fallbacks():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "num":   [10.0, np.nan, 50.0, np.nan],
        "cat":   ["x", None, "y", None],
    })
    original = df.copy(deep=True)

    res_mean = df.bynat.fill_missing(
        "num", strategy="mean", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res_mean["num"].tolist() == [10.0, 30.0, 50.0, 30.0]

    res_mode = df.bynat.fill_missing(
        "cat", strategy="mode", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res_mode["cat"].tolist() == ["x", "x", "y", "x"]

    res_mod = df.bynat.fill_missing(
        "cat", strategy="mod", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res_mod["cat"].tolist() == ["x", "x", "y", "x"]

    pd.testing.assert_frame_equal(df, original)


def test_fill_missing_all_nan_column():
    df = pd.DataFrame({
        "group": ["A", "A", "B", "B"],
        "val":   [np.nan, np.nan, np.nan, np.nan],
    })
    original = df.copy(deep=True)
    res = df.bynat.fill_missing(
        "val", strategy="median", hierarchy_cols=["group"], min_samples=2, fallback_global=True
    )
    assert res["val"].isna().all()
    pd.testing.assert_frame_equal(df, original)
