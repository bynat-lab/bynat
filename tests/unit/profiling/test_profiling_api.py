from collections.abc import Mapping

import numpy as np
import pandas as pd
import pytest

from bynat.cleaning import BaseData
from bynat.profiling import (
    ColumnProfile,
    DatasetProfile,
    ProfileReport,
    profile,
)


def test_public_entry_points():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    rep1 = profile(df)
    assert isinstance(rep1, ProfileReport)

    rep2 = profile(df)
    assert isinstance(rep2, ProfileReport)

    rep3 = df.bynat.profile()
    assert isinstance(rep3, ProfileReport)

    base = BaseData(df)
    rep4 = base.profile()
    assert isinstance(rep4, ProfileReport)

    assert rep1.dataset.row_count == rep2.dataset.row_count == rep3.dataset.row_count == rep4.dataset.row_count == 3
    assert rep1.to_dict() == rep2.to_dict() == rep3.to_dict() == rep4.to_dict()


def test_profiling_does_not_modify_input():
    df = pd.DataFrame(
        {
            "num": [10.0, np.nan, 30.0],
            "text": ["hello", None, "world"],
            "flag": [True, False, None],
        }
    )
    original = df.copy(deep=True)

    report = df.bynat.profile()

    assert report is not None
    pd.testing.assert_frame_equal(df, original)
    assert list(df.columns) == list(original.columns)
    pd.testing.assert_index_equal(df.index, original.index)


def test_report_structure_and_access_patterns():
    df = pd.DataFrame({"age": [20, 30, 40], "name": ["Alice", "Bob", "Charlie"]})
    report = df.bynat.profile()

    assert isinstance(report, Mapping)
    assert "dataset" in report
    assert "columns" in report
    assert len(report) == 2
    assert list(report.keys()) == ["dataset", "columns"]

    assert isinstance(report.dataset, DatasetProfile)
    assert report.dataset.row_count == 3
    assert report.dataset.column_count == 2
    assert isinstance(report.columns["age"], ColumnProfile)
    assert report.columns["age"].count == 3

    assert report["dataset"]["row_count"] == 3
    assert report["columns"]["age"]["missing_count"] == 0

    d = report.to_dict()
    assert isinstance(d, dict)
    assert "dataset" in d and "columns" in d
    assert isinstance(d["dataset"], dict)
    assert isinstance(d["columns"]["age"], dict)

    summary_df = report.to_dataframe()
    assert isinstance(summary_df, pd.DataFrame)
    assert len(summary_df) == 2
    assert "column" in summary_df.columns
    assert "missing_proportion" in summary_df.columns
    assert set(summary_df["column"]) == {"age", "name"}

    repr_str = repr(report)
    assert "ProfileReport(" in repr_str
    assert "rows=3" in repr_str
    assert "columns=2" in repr_str


def test_output_type_parameter():
    df = pd.DataFrame({"x": [1, 2, 3]})

    rep_default = profile(df)
    assert isinstance(rep_default, ProfileReport)

    rep_obj = profile(df, output_type=ProfileReport)
    assert isinstance(rep_obj, ProfileReport)

    rep_dict = profile(df, output_type=dict)
    assert isinstance(rep_dict, dict)
    assert "dataset" in rep_dict and "columns" in rep_dict
    assert rep_dict["dataset"]["row_count"] == 3

    rep_frame = profile(df, output_type=pd.DataFrame)
    assert isinstance(rep_frame, pd.DataFrame)
    assert len(rep_frame) == 1
    assert rep_frame.iloc[0]["column"] == "x"

    rep_basedata = BaseData(df).profile(output_type=BaseData)
    assert isinstance(rep_basedata, BaseData)
    assert len(rep_basedata) == 1

    class _BaseDataSubclass(BaseData):
        pass

    rep_subclass = _BaseDataSubclass(df).profile(output_type=_BaseDataSubclass)
    assert isinstance(rep_subclass, _BaseDataSubclass)
    assert len(rep_subclass) == 1

    with pytest.raises(TypeError, match="Unsupported output_type"):
        profile(df, output_type=int)


def test_column_selection_and_errors():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})

    rep = df.bynat.profile("a", "c")
    assert rep.dataset.column_count == 2
    assert list(rep.columns.keys()) == ["a", "c"]

    rep2 = df.bynat.profile(["b"])
    assert rep2.dataset.column_count == 1
    assert list(rep2.columns.keys()) == ["b"]

    with pytest.raises(KeyError, match="not found in DataFrame"):
        df.bynat.profile("non_existent")

    with pytest.raises(TypeError, match="Expected a pandas DataFrame"):
        profile([1, 2, 3])
