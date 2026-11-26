"""Tests for the bynat.profiling core algorithm and report model behavior."""

import importlib
import json
from collections.abc import Mapping
from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest

from bynat.profiling import ColumnProfile, DatasetProfile, ProfileReport, profile

pytestmark = pytest.mark.unit


def _fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "num": [10.0, 20.0, 20.0, 30.0, 0.0],
            "cat": ["alpha", "beta", "alpha", None, "beta"],
            "flag": [True, False, True, True, None],
            "dt": pd.to_datetime(
                pd.Series(
                    ["2024-01-01", "2024-01-03", None, "2024-01-02", "2024-01-01"],
                    dtype="object",
                )
            ),
        }
    )


def test_profiling_core_dataset_metrics_and_immutability():
    df = _fixture_frame()
    original = df.copy(deep=True)

    report = profile(df)

    pd.testing.assert_frame_equal(df, original)
    assert report.dataset.row_count == 5
    assert report.dataset.column_count == 4
    assert report.dataset.total_cells == 20
    assert report.dataset.missing_count == 3
    assert report.dataset.missing_proportion == pytest.approx(0.15)
    assert report.dataset.duplicate_rows == 0
    assert report.dataset.duplicate_proportion == 0.0
    assert report.dataset.empty_column_count == 0
    assert sum(report.dataset.dtype_counts.values()) == 4


def test_profiling_core_numeric_column_statistics():
    report = profile(_fixture_frame())
    col = report.columns["num"]

    assert isinstance(col, ColumnProfile)
    assert col.kind == "numeric"
    assert col.count == 5
    assert col.missing_count == 0
    assert col.distinct_count == 4
    assert col.is_unique is False
    assert col.stats["min"] == 0.0
    assert col.stats["max"] == 30.0
    assert col.stats["mean"] == 16.0
    assert col.stats["median"] == 20.0
    assert col.stats["q25"] == 10.0
    assert col.stats["q75"] == 20.0
    assert col.stats["iqr"] == 10.0
    assert col.stats["std"] == pytest.approx(np.std([10.0, 20.0, 20.0, 30.0, 0.0], ddof=1))
    assert col.stats["zeros_count"] == 1
    assert col.stats["zeros_proportion"] == pytest.approx(0.2)
    assert col.stats["outliers_count"] == 0


def test_profiling_core_kind_specific_column_statistics():
    report = profile(_fixture_frame())

    cat = report.columns["cat"]
    assert cat.kind == "categorical"
    assert cat.count == 4
    assert cat.missing_count == 1
    assert cat.stats["top"] == "alpha"
    assert cat.stats["top_frequency"] == 2
    assert cat.stats["top_proportion"] == pytest.approx(0.5)
    assert cat.stats["min_length"] == 4
    assert cat.stats["max_length"] == 5
    assert cat.stats["mean_length"] == pytest.approx(4.5)

    flag = report.columns["flag"]
    assert flag.kind == "boolean"
    assert flag.stats["true_count"] == 3
    assert flag.stats["false_count"] == 1
    assert flag.stats["true_proportion"] == pytest.approx(0.75)

    dt = report.columns["dt"]
    assert dt.kind == "datetime"
    assert dt.stats["min"] == "2024-01-01T00:00:00"
    assert dt.stats["max"] == "2024-01-03T00:00:00"
    assert dt.stats["range_days"] == pytest.approx(2.0)


def test_profiling_core_output_type_dispatch():
    df = _fixture_frame()
    report = profile(df)

    assert isinstance(report, ProfileReport)
    assert isinstance(profile(df, output_type=ProfileReport), ProfileReport)
    assert profile(df, output_type=dict) == report.to_dict()
    pd.testing.assert_frame_equal(
        profile(df, output_type=pd.DataFrame), report.to_dataframe()
    )

    class _FrameSubclass(pd.DataFrame):
        pass

    with pytest.raises(TypeError, match="Unsupported output_type"):
        profile(df, output_type=_FrameSubclass)
    with pytest.raises(TypeError, match="Unsupported output_type"):
        profile(df, output_type=int)


def test_invalid_output_type_is_rejected_before_report_build(monkeypatch):
    module = importlib.import_module("bynat.profiling.profile")
    monkeypatch.setattr(module, "build_report", lambda *_: pytest.fail("report computed too early"))
    with pytest.raises(TypeError, match="Unsupported output_type"):
        module.profile(_fixture_frame(), output_type=int)


def test_profiling_core_column_selection_and_input_errors():
    df = _fixture_frame()

    subset = profile(df, "num", "cat")
    assert subset.dataset.column_count == 2
    assert list(subset.columns) == ["num", "cat"]

    as_list = profile(df, ["flag"])
    assert list(as_list.columns) == ["flag"]

    with pytest.raises(KeyError, match="not found in DataFrame"):
        profile(df, "missing_col")
    with pytest.raises(TypeError, match="Expected a pandas DataFrame"):
        profile([1, 2, 3])


def test_profiling_core_duplicate_rows_with_unhashable_cells():
    df = pd.DataFrame(
        {
            "tags": [["a", "b"], ["c"], ["a", "b"]],
            "meta": [{"k": 1}, {"k": 2}, {"k": 1}],
        }
    )

    report = profile(df)

    assert report.dataset.duplicate_rows == 1
    assert report.columns["tags"].distinct_count == 2
    assert report.columns["meta"].distinct_count == 2


def test_profiling_report_models_mapping_protocol_and_field_counts():
    report = profile(_fixture_frame())

    assert isinstance(report, Mapping)
    assert list(report) == ["dataset", "columns"]
    assert len(report) == 2
    assert report["dataset"]["row_count"] == 5
    assert report["columns"]["num"]["count"] == 5
    assert len(asdict(report.dataset)) == 10
    assert len(asdict(report.columns["num"])) == 11
    assert isinstance(report.dataset, DatasetProfile)

    with pytest.raises(KeyError):
        _ = report["unknown"]
    with pytest.raises(KeyError):
        _ = report.columns["num"]["unknown"]


def test_profiling_report_to_dataframe_flattens_stats():
    report = profile(_fixture_frame())
    summary = report.to_dataframe()

    assert isinstance(summary, pd.DataFrame)
    assert summary["column"].tolist() == ["num", "cat", "flag", "dt"]
    assert summary.loc[summary["column"] == "num", "stat_mean"].iloc[0] == 16.0
    assert summary.loc[summary["column"] == "cat", "stat_top"].iloc[0] == "alpha"
    assert {"stat_min", "stat_max", "stat_iqr"}.issubset(summary.columns)


def test_profiling_report_json_roundtrip_preserves_values():
    report = profile(_fixture_frame())
    raw = report.to_dict()

    parsed = json.loads(json.dumps(raw))

    assert parsed == raw
    assert parsed["dataset"]["row_count"] == 5
    assert parsed["columns"]["num"]["stats"]["mean"] == 16.0
    assert parsed["columns"]["cat"]["stats"]["top"] == "alpha"
