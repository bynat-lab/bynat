import math

import pandas as pd
import pytest

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


def test_numeric_statistics():
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

    assert stats["mean"] == 180.0
    assert stats["median"] == 20.0
    assert stats["q25"] == 12.5
    assert stats["q75"] == 27.5
    assert stats["iqr"] == 15.0
    assert stats["std"] == pytest.approx(math.sqrt(161480.0), rel=1e-12)

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
    assert stats["min_length"] == 5
    assert stats["max_length"] == 6
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
    assert stats["min"] == "2024-01-01T10:00:00"
    assert stats["max"] == "2024-01-05T10:00:00"
    assert stats["range_days"] == pytest.approx(4.0)


def test_mixed_and_other_statistics():
    df = pd.DataFrame({"mixed": [1, "two", 3.0, "two"]})
    rep = df.bynat.profile()
    col = rep.columns["mixed"]

    assert col.kind == "other"
    assert isinstance(col.inferred_type, str)
    assert col.inferred_type not in _SINGLE_TYPE_INFERRED_LABELS
    assert col.count == 4
    assert col.distinct_count == 3

    stats = col.stats
    assert stats["top"] == "two"
    assert stats["top_frequency"] == 2
    assert stats["top_proportion"] == 0.5
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
