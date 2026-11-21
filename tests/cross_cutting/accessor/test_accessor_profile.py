"""Accessor profiling delegation: bynat.profiling ownership, adaptation, and parity."""

import pandas as pd
import pytest

from bynat.cleaning import BaseData
from bynat.profiling import ProfileReport
from bynat.profiling import profile as profiling_profile

pytestmark = pytest.mark.integration


def test_accessor_profile_returns_profiling_report_without_mutating_input():
    frame = pd.DataFrame({
        "age": [25, 30, None, 40, 30],
        "city": ["Cairo", "Alex", "Cairo", "Giza", "Alex"],
    })
    original = frame.copy(deep=True)

    report = frame.bynat.profile()

    assert type(report) is ProfileReport
    assert report.dataset.row_count == 5
    assert report.dataset.missing_count == 1
    assert report.columns["age"].stats["median"] == 30.0
    pd.testing.assert_frame_equal(frame, original)


def test_accessor_profile_output_type_dispatch_matches_profiling():
    frame = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "a"]})
    expected = profiling_profile(frame)

    assert frame.bynat.profile().to_dict() == expected.to_dict()
    assert frame.bynat.profile(output_type=ProfileReport).to_dict() == expected.to_dict()
    assert frame.bynat.profile(output_type=dict) == expected.to_dict()
    pd.testing.assert_frame_equal(
        frame.bynat.profile(output_type=pd.DataFrame), expected.to_dataframe()
    )

    with pytest.raises(TypeError, match="Unsupported output_type"):
        frame.bynat.profile(output_type=int)


def test_accessor_profile_adapts_basedata_output_type_to_the_requested_subclass(tmp_path):
    frame = pd.DataFrame({"x": [1, 2, 3]})
    expected = profiling_profile(frame, output_type=pd.DataFrame)

    class _Subclass(BaseData):
        pass

    for output_type in (BaseData, _Subclass):
        result = frame.bynat.profile(output_type=output_type)
        assert type(result) is output_type
        pd.testing.assert_frame_equal(pd.DataFrame(result), expected)


def test_accessor_profile_matches_basedata_and_profiling_results(tmp_path):
    frame = pd.DataFrame({"g": ["a", "a", "b"], "v": [1.0, 2.0, 3.0]})
    legacy = BaseData(frame, cache_dir=tmp_path)

    assert frame.bynat.profile().to_dict() == legacy.profile().to_dict()
    pd.testing.assert_frame_equal(
        frame.bynat.profile(output_type=pd.DataFrame),
        legacy.profile(output_type=pd.DataFrame),
    )


def test_accessor_profile_column_selection_and_missing_column_error():
    frame = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})

    subset = frame.bynat.profile("a", "c")
    assert subset.dataset.column_count == 2
    assert list(subset.columns) == ["a", "c"]
    assert list(frame.bynat.profile(["b"]).columns) == ["b"]

    with pytest.raises(KeyError, match="not found in DataFrame"):
        frame.bynat.profile("missing")
