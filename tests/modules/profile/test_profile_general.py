"""Tests for the data quality profiling API and report structures."""

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd
import pytest

import bynat
from bynat.cleaning import BaseData
from bynat.cleaning.profile import (
    ColumnProfile,
    DatasetProfile,
    ProfileReport,
    profile,
)

# Fine-grained `infer_dtype` labels that assert a single scalar type. A column
# holding both numbers and text must never be reported with one of these: the
# exact "mixed*" spelling pandas uses varies across versions, so the contract
# is asserted negatively instead of pinning a version-specific label.
_SINGLE_TYPE_INFERRED_LABELS: set[str] = {
    "integer",
    "floating",
    "decimal",
    "complex",
    "string",
    "unicode",
    "bytes",
    "boolean",
    "datetime64",
    "datetime",
    "date",
    "timestamp",
    "timedelta64",
    "timedelta",
    "time",
    "period",
    "interval",
    "categorical",
    "empty",
}


def test_public_entry_points():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    # Standalone from bynat.cleaning.profile
    rep1 = profile(df)
    assert isinstance(rep1, ProfileReport)

    # Standalone from top-level bynat
    rep2 = bynat.profile(df)
    assert isinstance(rep2, ProfileReport)

    # Accessor entry point
    rep3 = df.bynat.profile()
    assert isinstance(rep3, ProfileReport)

    # BaseData entry point
    base = BaseData(df)
    rep4 = base.profile()
    assert isinstance(rep4, ProfileReport)

    # All produce equivalent metrics
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

    # Run profile
    report = df.bynat.profile()

    assert report is not None
    # Verify input DataFrame is completely unchanged
    pd.testing.assert_frame_equal(df, original)
    assert list(df.columns) == list(original.columns)
    assert df.index.equals(original.index)


def test_report_structure_and_access_patterns():
    df = pd.DataFrame({"age": [20, 30, 40], "name": ["Alice", "Bob", "Charlie"]})
    report = df.bynat.profile()

    # Mapping contract
    assert isinstance(report, Mapping)
    assert "dataset" in report
    assert "columns" in report
    assert len(report) == 2
    assert list(report.keys()) == ["dataset", "columns"]

    # Attribute access
    assert isinstance(report.dataset, DatasetProfile)
    assert report.dataset.row_count == 3
    assert report.dataset.column_count == 2
    assert isinstance(report.columns["age"], ColumnProfile)
    assert report.columns["age"].count == 3

    # Dictionary access
    assert report["dataset"]["row_count"] == 3
    assert report["columns"]["age"]["missing_count"] == 0

    # Conversions
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

    # Readable repr
    repr_str = repr(report)
    assert "ProfileReport(" in repr_str
    assert "rows=3" in repr_str
    assert "columns=2" in repr_str


def test_output_type_parameter():
    df = pd.DataFrame({"x": [1, 2, 3]})

    # Default None -> ProfileReport
    rep_default = profile(df)
    assert isinstance(rep_default, ProfileReport)

    # Explicit ProfileReport
    rep_obj = profile(df, output_type=ProfileReport)
    assert isinstance(rep_obj, ProfileReport)

    # dict
    rep_dict = profile(df, output_type=dict)
    assert isinstance(rep_dict, dict)
    assert "dataset" in rep_dict and "columns" in rep_dict
    assert rep_dict["dataset"]["row_count"] == 3

    # pd.DataFrame
    rep_frame = profile(df, output_type=pd.DataFrame)
    assert isinstance(rep_frame, pd.DataFrame)
    assert len(rep_frame) == 1
    assert rep_frame.iloc[0]["column"] == "x"

    # BaseData subclass
    rep_basedata = profile(df, output_type=BaseData)
    assert isinstance(rep_basedata, BaseData)
    assert len(rep_basedata) == 1

    # Invalid output_type raises TypeError
    with pytest.raises(TypeError, match="Unsupported output_type"):
        profile(df, output_type=int)


def test_column_selection_and_errors():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})

    # Select specific columns as varargs
    rep = df.bynat.profile("a", "c")
    assert rep.dataset.column_count == 2
    assert list(rep.columns.keys()) == ["a", "c"]

    # Select specific columns as sequence
    rep2 = df.bynat.profile(["b"])
    assert rep2.dataset.column_count == 1
    assert list(rep2.columns.keys()) == ["b"]

    # Non-existent column raises KeyError
    with pytest.raises(KeyError, match="not found in DataFrame"):
        df.bynat.profile("non_existent")

    # Non-DataFrame raises TypeError
    with pytest.raises(TypeError, match="Expected a pandas DataFrame"):
        profile([1, 2, 3])  # type: ignore[arg-type]


def test_missing_values_and_proportions():
    df = pd.DataFrame(
        {
            "c1": [1, None, 3, None],      # 2 missing out of 4 (50%)
            "c2": ["a", "b", None, None],  # 2 missing out of 4 (50%)
            "c3": [10, 20, 30, 40],        # 0 missing out of 4 (0%)
        }
    )
    rep = df.bynat.profile()

    # Dataset missing metrics
    assert rep.dataset.row_count == 4
    assert rep.dataset.column_count == 3
    assert rep.dataset.total_cells == 12
    assert rep.dataset.missing_count == 4
    assert rep.dataset.missing_proportion == 4 / 12

    # Column missing metrics
    assert rep.columns["c1"].count == 2
    assert rep.columns["c1"].missing_count == 2
    assert rep.columns["c1"].missing_proportion == 0.5

    assert rep.columns["c3"].count == 4
    assert rep.columns["c3"].missing_count == 0
    assert rep.columns["c3"].missing_proportion == 0.0


def test_duplicate_rows_counting_semantics():
    # 5 rows total: row 0 and 2 are identical, row 1 and 3 are identical, row 4 is unique.
    # keep='first' semantics: 2 duplicate rows (row 2 and row 3).
    df = pd.DataFrame(
        {
            "id": [1, 2, 1, 2, 3],
            "val": ["x", "y", "x", "y", "z"],
        }
    )
    rep = df.bynat.profile()

    assert rep.dataset.row_count == 5
    assert rep.dataset.duplicate_rows == 2
    assert rep.dataset.duplicate_proportion == 2 / 5

    # Completely distinct rows -> 0 duplicates
    df_distinct = pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    rep_distinct = df_distinct.bynat.profile()
    assert rep_distinct.dataset.duplicate_rows == 0
    assert rep_distinct.dataset.duplicate_proportion == 0.0


def test_duplicate_rows_with_unhashable_cells():
    # Columns containing dicts and lists should not raise TypeError during duplicate detection
    df = pd.DataFrame(
        {
            "meta": [{"env": "prod"}, {"env": "dev"}, {"env": "prod"}],
            "tags": [["a", "b"], ["c"], ["a", "b"]],
        }
    )
    rep = df.bynat.profile()

    assert rep.dataset.row_count == 3
    assert rep.dataset.duplicate_rows == 1
    assert rep.dataset.duplicate_proportion == 1 / 3
    assert rep.columns["meta"].distinct_count == 2
    assert rep.columns["tags"].distinct_count == 2


def test_numeric_statistics():
    # Values: 10, 20, 20, 30, 0, 1000 (outlier)
    # count = 6, 0s = 1 (16.7%), distinct = 5
    data = [10.0, 20.0, 20.0, 30.0, 0.0, 1000.0]
    df = pd.DataFrame({"num": data})
    rep = df.bynat.profile()
    col = rep.columns["num"]

    assert col.kind == "numeric"
    assert col.count == 6
    assert col.missing_count == 0
    assert col.distinct_count == 5
    assert not col.is_unique

    stats = col.stats
    assert stats["min"] == 0.0
    assert stats["max"] == 1000.0
    assert stats["zeros_count"] == 1
    assert pytest.approx(stats["zeros_proportion"]) == 1 / 6

    # Independently derived from the fixed input, not by re-running the pandas
    # or NumPy aggregations the implementation itself uses. Sorted values are
    # [0, 10, 20, 20, 30, 1000] with n = 6:
    #   mean   = 1080 / 6 = 180.0
    #   median = (20 + 20) / 2 = 20.0
    #   q25    = 10 + 0.25 * (20 - 10) = 12.5   (linear interpolation)
    #   q75    = 20 + 0.75 * (30 - 20) = 27.5
    #   iqr    = q75 - q25 = 15.0
    #   sample variance = 807400 / 5 = 161480.0, so std = sqrt(161480.0)
    assert stats["mean"] == 180.0
    assert stats["median"] == 20.0
    assert stats["q25"] == 12.5
    assert stats["q75"] == 27.5
    assert stats["iqr"] == 15.0
    # std is irrational, so a tight relative tolerance is justified; it still
    # distinguishes the documented ddof=1 from ddof=0 (366.83...).
    assert stats["std"] == pytest.approx(math.sqrt(161480.0), rel=1e-12)

    # Tukey 1.5*IQR bounds are [12.5 - 22.5, 27.5 + 22.5] = [-10.0, 50.0];
    # only 1000.0 falls outside, so exactly one outlier is counted.
    assert stats["outliers_count"] == 1


def test_categorical_and_text_statistics():
    df = pd.DataFrame(
        {
            "fruit": ["apple", "banana", "apple", "cherry", None],
        }
    )
    rep = df.bynat.profile()
    col = rep.columns["fruit"]

    assert col.kind == "categorical"
    assert col.count == 4
    assert col.missing_count == 1
    assert col.distinct_count == 3

    stats = col.stats
    assert stats["top"] == "apple"
    assert stats["top_frequency"] == 2
    assert stats["top_proportion"] == 0.5
    assert stats["min_length"] == 5  # "apple"
    assert stats["max_length"] == 6  # "banana", "cherry"
    assert stats["mean_length"] == (5 + 6 + 5 + 6) / 4


def test_boolean_statistics():
    df = pd.DataFrame({"flag": [True, False, True, True, None]})
    rep = df.bynat.profile()
    col = rep.columns["flag"]

    assert col.kind == "boolean"
    assert col.count == 4
    assert col.missing_count == 1
    assert col.distinct_count == 2

    stats = col.stats
    assert stats["true_count"] == 3
    assert stats["false_count"] == 1
    assert stats["true_proportion"] == 0.75


def test_datetime_statistics():
    dates = pd.to_datetime(["2024-01-01 10:00:00", "2024-01-05 10:00:00", None])
    df = pd.DataFrame({"timestamp": dates})
    rep = df.bynat.profile()
    col = rep.columns["timestamp"]

    assert col.kind == "datetime"
    assert col.count == 2
    assert col.missing_count == 1
    assert col.distinct_count == 2

    stats = col.stats
    # The contract formats min/max as ISO-8601 strings (`Timestamp.isoformat()`).
    # Assert the exact value rather than a date substring so a wrong day, a
    # wrong time, or a wrong format all fail.
    assert stats["min"] == "2024-01-01T10:00:00"
    assert stats["max"] == "2024-01-05T10:00:00"
    assert stats["range_days"] == pytest.approx(4.0)


def test_mixed_and_other_statistics():
    df = pd.DataFrame({"mixed": [1, "two", 3.0, "two"]})
    rep = df.bynat.profile()
    col = rep.columns["mixed"]

    # `inferred_type` is pandas' raw `infer_dtype` label, whose exact spelling
    # for mixed content is input- and version-dependent (this fixture yields
    # "mixed-integer", but other mixed inputs or pandas versions can return a
    # different "mixed*" label). The version-stable contract is the
    # kind/label consistency: a column holding both numbers and text is
    # classified as "other", so its label must not be one that maps to a
    # single scalar kind.
    assert col.kind == "other"
    assert isinstance(col.inferred_type, str)
    assert col.inferred_type not in _SINGLE_TYPE_INFERRED_LABELS
    assert col.count == 4
    assert col.distinct_count == 3

    stats = col.stats
    assert stats["top"] == "two"
    assert stats["top_frequency"] == 2
    assert stats["top_proportion"] == 0.5
    # String lengths are inapplicable for mixed types and represented as None
    assert "min_length" not in stats or stats["min_length"] is None


def test_nullable_dtypes():
    df = pd.DataFrame(
        {
            "int_null": pd.Series([10, 20, None], dtype="Int64"),
            "float_null": pd.Series([1.5, None, 4.5], dtype="Float64"),
            "bool_null": pd.Series([True, False, None], dtype="boolean"),
            "str_null": pd.Series(["hello", "world", None], dtype="string"),
        }
    )
    rep = df.bynat.profile()

    assert rep.columns["int_null"].count == 2
    assert rep.columns["int_null"].missing_count == 1
    assert rep.columns["int_null"].stats["mean"] == 15.0

    assert rep.columns["float_null"].count == 2
    assert rep.columns["float_null"].missing_count == 1
    assert rep.columns["float_null"].stats["mean"] == 3.0

    assert rep.columns["bool_null"].count == 2
    assert rep.columns["bool_null"].missing_count == 1
    assert rep.columns["bool_null"].stats["true_count"] == 1

    assert rep.columns["str_null"].count == 2
    assert rep.columns["str_null"].missing_count == 1
    assert rep.columns["str_null"].stats["top_frequency"] == 1

