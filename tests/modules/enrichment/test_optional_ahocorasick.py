import sys

import pandas as pd
import pytest

from bynat.cleaning import BaseData


def test_categorize_by_reference_prefers_the_longest_matching_keyword(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Data Analyst", "Data", "Data Analyst Assistant"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Data": ["data"], "Software": ["data analyst"]},
    )

    assert result["family"].tolist() == ["Software", "Data", "Software"]
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_respects_word_boundaries_and_case(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Reactor", "database", "SENIOR REACT DEVELOPER", "Chef"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Software": ["react", "python developer"]},
        default_category="Uncategorized",
    )

    assert result["family"].tolist() == [
        "Uncategorized",
        "Uncategorized",
        "Software",
        "Uncategorized",
    ]
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_combines_multiple_source_columns(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {
            "title": ["Data", "Senior", "Chef"],
            "description": ["Analyst", "React Developer", "Nowhere"],
        },
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        "description",
        target_col="family",
        reference={"Data": ["data analyst"], "Software": ["react developer"]},
    )

    assert result["family"].tolist() == ["Data", "Software", "Other"]
    assert result is not frame
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_overwrites_an_existing_target_column(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Data Analyst", "Chef"], "family": ["old", "old"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Data": ["data analyst"]},
    )

    assert result["family"].tolist() == ["Data", "Other"]
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_ignores_blank_keywords(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["data analyst", "python developer", "chef"]},
        cache_dir=tmp_path,
    )
    before = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Data": ["data", "", None, "   "], "Software": ["python developer"]},
    )

    assert result["family"].tolist() == ["Data", "Software", "Other"]
    pd.testing.assert_frame_equal(frame, before)


def test_categorize_by_reference_with_real_pyahocorasick(tmp_path):
    pytest.importorskip("ahocorasick")
    frame = BaseData(
        {"title": ["Senior Python Developer", "Data Analyst", "Chef", None]},
        cache_dir=tmp_path,
    )
    original = frame.copy(deep=True)

    result = frame.categorize_by_reference(
        "title",
        target_col="family",
        reference={"Engineering": ["python developer", "developer"], "Data": ["data analyst"]},
    )

    assert result["family"].tolist() == ["Engineering", "Data", "Other", "Other"]
    pd.testing.assert_frame_equal(frame, original)


def test_optional_categorization_reports_missing_dependency_at_method_use(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "ahocorasick", None)
    frame = BaseData({"description": ["python developer"]}, cache_dir=tmp_path)

    with pytest.raises(ImportError, match="pyahocorasick"):
        frame.categorize_by_reference(
            "description",
            target_col="category",
            reference={"Software": ["python developer"]},
        )
