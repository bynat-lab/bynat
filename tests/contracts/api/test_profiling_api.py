import importlib

import pytest

import bynat.profiling as profiling
from bynat.profiling import ColumnProfile, DatasetProfile, ProfileReport, profile

pytestmark = pytest.mark.unit


def test_profiling_package_exports_exact_public_all():
    assert profiling.__all__ == ["profile", "ProfileReport", "DatasetProfile", "ColumnProfile"]
    assert profiling.profile is profile
    assert profiling.ProfileReport is ProfileReport
    assert profiling.DatasetProfile is DatasetProfile
    assert profiling.ColumnProfile is ColumnProfile
    assert profile.__module__ == "bynat.profiling.profile"
    assert ProfileReport.__module__ == "bynat.profiling.report"

    profile_module = importlib.import_module("bynat.profiling.profile")
    report_module = importlib.import_module("bynat.profiling.report")

    assert profile_module.__all__ == ["profile"]
    assert report_module.__all__ == ["ProfileReport", "DatasetProfile", "ColumnProfile"]
