from dataclasses import asdict

import numpy as np
import pandas as pd

from bynat.profiling import ColumnProfile, profile


def test_empty_dataframe_edge_cases():
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

    col_float = rep.columns["all_na_float"]
    assert col_float.count == 0
    assert col_float.missing_count == 3
    assert col_float.missing_proportion == 1.0
    assert col_float.distinct_count == 0
    assert not col_float.is_unique
    assert col_float.stats["mean"] is None
    assert col_float.stats["outliers_count"] is None
    assert col_float.stats["zeros_count"] == 0

    col_obj = rep.columns["all_none_obj"]
    assert col_obj.count == 0
    assert col_obj.missing_count == 3
    assert col_obj.missing_proportion == 1.0
    assert col_obj.distinct_count == 0
    assert col_obj.stats["top"] is None
    assert col_obj.stats["top_frequency"] is None


def test_single_row_statistics():
    df = pd.DataFrame({"single_num": [42.0]})
    rep = profile(df)
    stats = rep.columns["single_num"].stats

    assert stats["min"] == 42.0
    assert stats["max"] == 42.0
    assert stats["mean"] == 42.0
    assert stats["std"] is None
    assert stats["outliers_count"] is None


def test_duplicate_column_names_handling():
    df = pd.DataFrame([[1, 2], [3, 4]], columns=["a", "a"])
    rep = profile(df)

    assert rep.dataset.column_count == 2
    assert len(rep.column_list) == 2
    assert rep.column_list[0].name == "a"
    assert rep.column_list[1].name == "a"
    df_summary = rep.to_dataframe()
    assert len(df_summary) == 2
    assert df_summary["column"].tolist() == ["a", "a"]

    assert list(rep.columns.keys()) == ["a"]
    assert len(rep.columns) == 1
    assert isinstance(rep.columns["a"], ColumnProfile)
    assert rep.columns["a"].name == "a"
    assert rep.columns["a"].count == 2
    assert rep.columns["a"].dtype == "int64"
    assert rep.columns["a"].stats["min"] == 2
    assert rep.columns["a"].stats["max"] == 4

    rep_dict = rep.to_dict()
    assert list(rep_dict["columns"].keys()) == list(rep.columns.keys())
    assert rep_dict["columns"]["a"]["name"] == "a"
    assert rep_dict["columns"]["a"]["count"] == 2
    assert rep_dict["columns"]["a"]["stats"]["min"] == 2
    assert rep_dict["columns"]["a"]["stats"]["max"] == 4
    assert set(rep_dict["columns"]["a"].keys()) == set(asdict(rep.columns["a"]).keys())
