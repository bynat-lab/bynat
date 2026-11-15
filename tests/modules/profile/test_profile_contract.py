"""Tests for the data quality profiling API and report structures."""

import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning.profile import profile
from tests.modules.profile.helpers import EXPECTED_STATS_KEYS_BY_KIND

pytestmark = pytest.mark.unit


EXPECTED_TOP_LEVEL_KEYS: set[str] = {"dataset", "columns"}

EXPECTED_DATASET_FIELDS: set[str] = {
    "row_count",
    "column_count",
    "total_cells",
    "missing_count",
    "missing_proportion",
    "duplicate_rows",
    "duplicate_proportion",
    "empty_column_count",
    "memory_bytes",
    "dtype_counts",
}

EXPECTED_COLUMN_FIELDS: set[str] = {
    "name",
    "dtype",
    "inferred_type",
    "kind",
    "count",
    "missing_count",
    "missing_proportion",
    "distinct_count",
    "distinct_proportion",
    "is_unique",
    "stats",
}


def test_contract_stability_key_sets():
    df = pd.DataFrame(
        {
            "num": [1.0, 2.0, 3.0, 4.0, 5.0],
            "cat": ["a", "b", "c", "d", "e"],
            "flag": [True, False, True, False, True],
            "dt": pd.date_range("2024-01-01", periods=5),
            "misc": [{"k": 1}, {"k": 2}, {"k": 1}, [1, 2], None],
        }
    )
    rep = profile(df)

    rep_dict = rep.to_dict()
    assert set(rep_dict.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert set(rep.keys()) == EXPECTED_TOP_LEVEL_KEYS

    assert set(asdict(rep.dataset).keys()) == EXPECTED_DATASET_FIELDS
    assert set(rep_dict["dataset"].keys()) == EXPECTED_DATASET_FIELDS

    for col_name, col_prof in rep.columns.items():
        assert set(asdict(col_prof).keys()) == EXPECTED_COLUMN_FIELDS
        assert set(rep_dict["columns"][col_name].keys()) == EXPECTED_COLUMN_FIELDS

    for col_name, expected_kind in [
        ("num", "numeric"),
        ("cat", "categorical"),
        ("flag", "boolean"),
        ("dt", "datetime"),
        ("misc", "other"),
    ]:
        col = rep.columns[col_name]
        assert col.kind == expected_kind
        assert set(col.stats.keys()) == EXPECTED_STATS_KEYS_BY_KIND[expected_kind]
        assert set(rep_dict["columns"][col_name]["stats"].keys()) == EXPECTED_STATS_KEYS_BY_KIND[expected_kind]

    empty_df = pd.DataFrame(
        {
            "num_empty": pd.Series([], dtype="float64"),
            "cat_empty": pd.Series([], dtype="category"),
            "flag_empty": pd.Series([], dtype="boolean"),
            "dt_empty": pd.Series([], dtype="datetime64[ns]"),
            "other_empty": pd.Series([], dtype="object"),
        }
    )
    empty_rep = profile(empty_df)
    for col_name, kind in [
        ("num_empty", "numeric"),
        ("cat_empty", "categorical"),
        ("flag_empty", "boolean"),
        ("dt_empty", "datetime"),
        ("other_empty", "other"),
    ]:
        col = empty_rep.columns[col_name]
        assert col.kind == kind
        assert set(col.stats.keys()) == EXPECTED_STATS_KEYS_BY_KIND[kind]


def test_contract_stability_value_types():
    df = pd.DataFrame(
        {
            "num": [10.0, 20.0, 0.0, 1000.0, 20.0, None],
            "cat": ["alpha", "beta", "alpha", None, "gamma", "delta"],
            "flag": [True, False, True, True, None, False],
            "dt": pd.to_datetime(["2024-01-01", "2024-01-05", "2024-01-03", None, "2024-01-02", "2024-01-04"]),
            "other": [pd.Timedelta(days=1), pd.Timedelta(days=2), pd.Timedelta(days=1), None, pd.Timedelta(days=3), pd.Timedelta(days=1)],
        }
    )
    rep = profile(df)

    ds = rep.dataset
    assert isinstance(ds.row_count, int)
    assert isinstance(ds.column_count, int)
    assert isinstance(ds.total_cells, int)
    assert isinstance(ds.missing_count, int)
    assert isinstance(ds.missing_proportion, float)
    assert isinstance(ds.duplicate_rows, int)
    assert isinstance(ds.duplicate_proportion, float)
    assert isinstance(ds.empty_column_count, int)
    assert isinstance(ds.memory_bytes, int)
    assert isinstance(ds.dtype_counts, dict)

    for col in rep.columns.values():
        assert isinstance(col.name, str)
        assert isinstance(col.dtype, str)
        assert isinstance(col.inferred_type, str)
        assert isinstance(col.kind, str)
        assert isinstance(col.count, int)
        assert isinstance(col.missing_count, int)
        assert isinstance(col.missing_proportion, float)
        assert isinstance(col.distinct_count, int)
        assert isinstance(col.distinct_proportion, float)
        assert isinstance(col.is_unique, bool)
        assert isinstance(col.stats, dict)

    num_stats = rep.columns["num"].stats
    assert isinstance(num_stats["zeros_count"], int)
    assert isinstance(num_stats["zeros_proportion"], float)
    assert isinstance(num_stats["outliers_count"], int)
    assert isinstance(num_stats["min"], (int, float))
    assert isinstance(num_stats["max"], (int, float))
    assert isinstance(num_stats["mean"], (int, float))

    cat_stats = rep.columns["cat"].stats
    assert isinstance(cat_stats["top"], str)
    assert isinstance(cat_stats["top_frequency"], int)
    assert isinstance(cat_stats["top_proportion"], float)
    assert isinstance(cat_stats["min_length"], int)
    assert isinstance(cat_stats["max_length"], int)
    assert isinstance(cat_stats["mean_length"], float)

    bool_stats = rep.columns["flag"].stats
    assert isinstance(bool_stats["true_count"], int)
    assert isinstance(bool_stats["false_count"], int)
    assert isinstance(bool_stats["true_proportion"], float)

    dt_stats = rep.columns["dt"].stats
    assert isinstance(dt_stats["min"], str)
    assert isinstance(dt_stats["max"], str)
    assert isinstance(dt_stats["range_days"], float)

    other_stats = rep.columns["other"].stats
    assert isinstance(other_stats["top"], str)
    assert isinstance(other_stats["top_frequency"], int)
    assert isinstance(other_stats["top_proportion"], float)


def test_contract_json_dumps_mixed_dataframe():
    df = pd.DataFrame(
        {
            "num_standard": [1.5, 2.5, np.nan, 4.5],
            "num_nullable_int": pd.Series([10, None, 30, 40], dtype="Int64"),
            "num_nullable_float": pd.Series([1.1, 2.2, None, 4.4], dtype="Float64"),
            "cat_str": ["apple", "banana", None, "apple"],
            "cat_categorical": pd.Series(pd.Categorical(["cat", "dog", None, "cat"])),
            "cat_nullable_str": pd.Series(["x", None, "z", "x"], dtype="string"),
            "bool_standard": [True, False, None, True],
            "bool_nullable": pd.Series([True, None, False, False], dtype="boolean"),
            "dt_naive": pd.to_datetime(["2024-01-01", "2024-01-02", None, "2024-01-04"]),
            "dt_tz": pd.Series(pd.date_range("2024-01-01", periods=4, tz="UTC")),
            "timedelta_col": [pd.Timedelta(days=1), pd.Timedelta(hours=2), None, pd.Timedelta(days=1)],
            "unhashable_list": [["a", "b"], ["c"], None, ["a", "b"]],
            "unhashable_dict": [{"a": 1}, {"b": 2}, None, {"a": 1}],
        }
    )

    report = profile(df)
    raw_dict = report.to_dict()

    dumped = json.dumps(raw_dict)
    assert isinstance(dumped, str)

    parsed = json.loads(dumped)
    assert set(parsed.keys()) == {"dataset", "columns"}
    assert parsed["dataset"]["row_count"] == 4
    assert parsed["dataset"]["column_count"] == 13
    assert "timedelta_col" in parsed["columns"]
    assert "unhashable_dict" in parsed["columns"]

