"""Tests for the bynat.profiling package boundary, exports, and private helper ownership."""

import ast
import importlib
from pathlib import Path

import numpy as np
import pytest

import bynat.profiling as profiling
from bynat.profiling import ColumnProfile, DatasetProfile, ProfileReport, profile

pytestmark = pytest.mark.unit


def _imported_module_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return names


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


def test_profiling_package_has_no_forbidden_imports():
    package_dir = Path(profiling.__file__).resolve().parent
    files = sorted(package_dir.glob("*.py"))
    assert {path.name for path in files} == {"__init__.py", "profile.py", "report.py"}

    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "is_basedata_type" not in source
        assert "_shared" not in source
        for module_name in _imported_module_names(path):
            assert not module_name.startswith(
                ("bynat.cleaning", "bynat.analytics", "bynat.caching", "bynat._accessors")
            ), (path.name, module_name)


def test_profiling_private_dedupe_key_normalizes_unhashable_values():
    from bynat.profiling.profile import _dedupe_key

    assert _dedupe_key([1, 2]) == "[1, 2]"
    assert _dedupe_key({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
    assert _dedupe_key({2, 1}) == "[1, 2]"
    assert _dedupe_key(np.array([1, 2])) == "[1, 2]"
    assert _dedupe_key(5) == 5


def test_profiling_private_dedupe_key_is_bound_to_canonical_internal_helper():
    import bynat._internal as internal

    profile_module = importlib.import_module("bynat.profiling.profile")

    assert profile_module._dedupe_key is internal.dedupe_key
    assert profile_module._dedupe_key.__module__ == "bynat._internal.values"
