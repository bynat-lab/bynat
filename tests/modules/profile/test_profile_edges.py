"""Tests for the data quality profiling API and report structures."""

import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning.profile import ColumnProfile, profile
from tests.modules.profile.test_profile_contract import EXPECTED_STATS_KEYS_BY_KIND


def test_empty_dataframe_edge_cases():
    # 1. 0 rows, 0 columns
    empty_df = pd.DataFrame()
    rep1 = profile(empty_df)
    assert rep1.dataset.row_count == 0
    assert rep1.dataset.column_count == 0
    assert rep1.dataset.total_cells == 0
    assert rep1.dataset.missing_count == 0
    assert rep1.dataset.missing_proportion == 0.0
    assert rep1.dataset.duplicate_rows == 0
    assert rep1.dataset.duplicate_proportion == 0.0
    assert rep1.dataset.empty_column_count == 0
    assert len(rep1.columns) == 0
    assert rep1.to_dataframe().empty

    # 2. 0 rows, with column schema (untyped columns default to object -> kind 'other')
    empty_with_cols = pd.DataFrame(columns=["num_col", "text_col"])
    rep2 = profile(empty_with_cols)
    assert rep2.dataset.row_count == 0
    assert rep2.dataset.column_count == 2
    assert rep2.dataset.empty_column_count == 2
    assert rep2.columns["num_col"].count == 0
    assert rep2.columns["num_col"].missing_count == 0
    assert rep2.columns["num_col"].missing_proportion == 0.0
    assert rep2.columns["num_col"].distinct_count == 0
    assert not rep2.columns["num_col"].is_unique
    assert rep2.columns["num_col"].kind == "other"
    assert rep2.columns["num_col"].stats == {
        "top": None,
        "top_frequency": None,
        "top_proportion": None,
    }
    assert rep2.columns["text_col"].kind == "other"
    assert rep2.columns["text_col"].stats == {
        "top": None,
        "top_frequency": None,
        "top_proportion": None,
    }

    # 3. 0 rows, with explicitly typed numeric column
    empty_typed = pd.DataFrame({"num": pd.Series([], dtype="float64")})
    rep3 = profile(empty_typed)
    assert rep3.dataset.row_count == 0
    assert rep3.columns["num"].kind == "numeric"
    assert rep3.columns["num"].stats["min"] is None
    assert rep3.columns["num"].stats["max"] is None
    assert rep3.columns["num"].stats["mean"] is None
    assert rep3.columns["num"].stats["zeros_count"] == 0
    assert rep3.columns["num"].stats["zeros_proportion"] == 0.0


def test_all_missing_column_edge_cases():
    df = pd.DataFrame(
        {
            "all_na_float": [np.nan, np.nan, np.nan],
            "all_none_obj": [None, None, None],
        }
    )
    rep = profile(df)

    assert rep.dataset.row_count == 3
    assert rep.dataset.empty_column_count == 2

    # Float col
    col_float = rep.columns["all_na_float"]
    assert col_float.count == 0
    assert col_float.missing_count == 3
    assert col_float.missing_proportion == 1.0
    assert col_float.distinct_count == 0
    assert not col_float.is_unique
    assert col_float.stats["mean"] is None
    assert col_float.stats["outliers_count"] is None
    assert col_float.stats["zeros_count"] == 0

    # Obj col
    col_obj = rep.columns["all_none_obj"]
    assert col_obj.count == 0
    assert col_obj.missing_count == 3
    assert col_obj.missing_proportion == 1.0
    assert col_obj.distinct_count == 0
    assert col_obj.stats["top"] is None
    assert col_obj.stats["top_frequency"] is None


def test_single_row_statistics():
    # Test numeric sample std when n=1 (should be None, not NaN or crash)
    df = pd.DataFrame({"single_num": [42.0]})
    rep = profile(df)
    stats = rep.columns["single_num"].stats

    assert stats["min"] == 42.0
    assert stats["max"] == 42.0
    assert stats["mean"] == 42.0
    assert stats["std"] is None  # n <= 1 sample std is undefined -> None
    assert stats["outliers_count"] is None  # n < 5 samples -> None


def test_duplicate_column_names_handling():
    # DataFrame with duplicate column names: columns=['a', 'a']
    df = pd.DataFrame([[1, 2], [3, 4]], columns=["a", "a"])
    rep = profile(df)

    assert rep.dataset.column_count == 2
    assert len(rep.column_list) == 2
    assert rep.column_list[0].name == "a"
    assert rep.column_list[1].name == "a"
    df_summary = rep.to_dataframe()
    assert len(df_summary) == 2
    assert df_summary["column"].tolist() == ["a", "a"]

    # README "Working with a report" documents that `report.columns` holds one
    # entry per name when a DataFrame has repeated column names, while
    # `column_list` preserves every column by position. The ProfileReport
    # docstring documents that the mapping keeps the last occurrence. Pin that
    # documented mapping explicitly (PD-03): the name must not disappear from
    # the mapping, the entry must describe the last column, and `to_dict()`
    # must mirror the same mapping instead of losing it silently.
    assert list(rep.columns.keys()) == ["a"]
    assert len(rep.columns) == 1
    assert isinstance(rep.columns["a"], ColumnProfile)
    assert rep.columns["a"].name == "a"
    assert rep.columns["a"].count == 2
    assert rep.columns["a"].dtype == "int64"
    assert rep.columns["a"].stats["min"] == 2  # last occurrence values are [2, 4]
    assert rep.columns["a"].stats["max"] == 4

    rep_dict = rep.to_dict()
    assert list(rep_dict["columns"].keys()) == list(rep.columns.keys())
    assert rep_dict["columns"]["a"]["name"] == "a"
    assert rep_dict["columns"]["a"]["count"] == 2
    assert rep_dict["columns"]["a"]["stats"]["min"] == 2
    assert rep_dict["columns"]["a"]["stats"]["max"] == 4
    assert set(rep_dict["columns"]["a"].keys()) == set(asdict(rep.columns["a"]).keys())


def test_clean_scalar_bool_before_int():
    # Object column with booleans and strings must preserve bool type for top value
    df = pd.DataFrame({"obj": [True, "x", True]})
    rep = profile(df)
    col = rep.columns["obj"]
    assert col.kind == "other"
    assert col.stats["top"] is True
    assert type(col.stats["top"]) is bool
    assert col.stats["top_frequency"] == 2

    # Direct check of _clean_scalar
    from bynat.cleaning.profile import _clean_scalar

    assert _clean_scalar(True) is True
    assert type(_clean_scalar(True)) is bool
    assert _clean_scalar(False) is False
    assert type(_clean_scalar(False)) is bool
    assert _clean_scalar(np.bool_(True)) is True
    assert type(_clean_scalar(np.bool_(True))) is bool
    assert _clean_scalar(1) == 1
    assert type(_clean_scalar(1)) is int


def test_timedelta_columns_and_clean_scalar():
    # Timedelta columns are kind 'other' and serializable in to_dict()
    td_series = pd.Series([pd.Timedelta(days=1), pd.Timedelta(days=2), pd.Timedelta(days=1)])
    df = pd.DataFrame({"td": td_series})
    rep = profile(df)
    col = rep.columns["td"]
    assert col.kind == "other"
    assert col.stats["top"] == "P1DT0H0M0S"
    assert col.stats["top_frequency"] == 2
    assert col.stats["top_proportion"] == pytest.approx(2 / 3)

    # Ensure json.dumps succeeds on to_dict()
    dumped = json.dumps(rep.to_dict())
    assert "P1DT0H0M0S" in dumped

    # Direct check of _clean_scalar with pd.Timedelta, np.timedelta64, datetime.timedelta
    import datetime

    from bynat.cleaning.profile import _clean_scalar

    assert _clean_scalar(pd.Timedelta(days=1)) == "P1DT0H0M0S"
    assert _clean_scalar(np.timedelta64(10, "s")) == "P0DT0H0M10S"
    assert _clean_scalar(datetime.timedelta(days=2)) == "P2DT0H0M0S"


def test_categorical_pd_categorical():
    # pd.Categorical column should have kind 'categorical'
    cat_series = pd.Series(pd.Categorical(["apple", "banana", "apple", None]))
    df = pd.DataFrame({"cat": cat_series})
    rep = profile(df)
    col = rep.columns["cat"]
    assert col.kind == "categorical"
    assert set(col.stats.keys()) == EXPECTED_STATS_KEYS_BY_KIND["categorical"]
    assert col.stats["top"] == "apple"
    assert col.stats["top_frequency"] == 2
    assert col.stats["top_proportion"] == pytest.approx(2 / 3)


def test_tz_aware_datetime():
    # Tz-aware datetime column should have kind 'datetime'
    tz_series = pd.Series(pd.date_range("2024-01-01", periods=3, tz="UTC"))
    df = pd.DataFrame({"dt_tz": tz_series})
    rep = profile(df)
    col = rep.columns["dt_tz"]
    assert col.kind == "datetime"
    assert set(col.stats.keys()) == EXPECTED_STATS_KEYS_BY_KIND["datetime"]
    assert col.stats["min"] == "2024-01-01T00:00:00+00:00"
    assert col.stats["max"] == "2024-01-03T00:00:00+00:00"
    assert col.stats["range_days"] == pytest.approx(2.0)

