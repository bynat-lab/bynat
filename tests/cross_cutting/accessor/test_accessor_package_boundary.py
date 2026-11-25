"""Boundary contracts for the private `bynat._accessors` integration package.

These tests pin ownership (registration, binding, delegation), the forbidden
dependency direction (functional packages must not import `_accessors`), and
import-order safety (the boundary never imports the root package).
"""

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

import bynat
import bynat._accessors as accessors
from bynat._accessors import BynatAccessor
from bynat.cleaning import _columns, _stats, _text
from bynat.cleaning.enrich import _currency, _geocode, _nlp

pytestmark = pytest.mark.unit

PACKAGE_ROOT = Path(bynat.__file__).resolve().parent
ACCESSORS_DIR = PACKAGE_ROOT / "_accessors"
FUNCTIONAL_PACKAGES = ("cleaning", "profiling", "analytics", "caching")


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.append(node.module or "")
    return names


def _runtime_absolute_imports(path: Path) -> list[str]:
    """Absolute imports bound at module top level (TYPE_CHECKING blocks excluded)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.append(node.module or "")
    return names


def test_accessors_package_exports_the_accessor_class_from_its_owner():
    dataframe_module = importlib.import_module("bynat._accessors.dataframe")
    binding_module = importlib.import_module("bynat._accessors._binding")

    assert accessors.__all__ == ["BynatAccessor"]
    assert accessors.BynatAccessor is dataframe_module.BynatAccessor
    assert BynatAccessor.__module__ == "bynat._accessors.dataframe"
    assert binding_module.__all__ == []
    for factory in ("_method_signature", "_with_inplace", "_frame_method", "_cached_frame_method"):
        assert callable(getattr(binding_module, factory))


def test_binding_module_is_pure_wrapper_mechanics():
    binding_module = importlib.import_module("bynat._accessors._binding")

    for module_name in _runtime_absolute_imports(ACCESSORS_DIR / "_binding.py"):
        assert module_name.split(".")[0] in {"functools", "inspect", "typing", "collections"}, module_name

    assert not any(
        module_name.startswith("bynat")
        for module_name in _runtime_absolute_imports(ACCESSORS_DIR / "_binding.py")
    )
    assert binding_module._frame_method.__module__ == "bynat._accessors._binding"


def test_accessor_module_imports_only_allowed_boundaries():
    dataframe_module = importlib.import_module("bynat._accessors.dataframe")

    allowed = {"bynat", "os", "typing", "pandas"}
    for module_name in _runtime_absolute_imports(ACCESSORS_DIR / "dataframe.py"):
        assert module_name.split(".")[0] in allowed, module_name

    for module_name in _runtime_absolute_imports(ACCESSORS_DIR / "__init__.py"):
        assert module_name == "bynat._accessors.dataframe", module_name

    assert dataframe_module.BynatAccessor is BynatAccessor


def test_accessor_methods_delegate_to_functional_module_apis():
    from bynat.cleaning import io
    from bynat.cleaning.enrich import _translate

    expected = {
        "drop_by_substring": _columns.drop_by_substring,
        "drop_CLASS_columns": _columns.drop_CLASS_columns,
        "rename_by_substring": _columns.rename_by_substring,
        "rename_all_DOTS": _columns.rename_all_DOTS,
        "reorder_columns": _columns.reorder_columns,
        "melt_transform_pivot": _columns.melt_transform_pivot,
        "move_column": _columns.move_column,
        "align_lat_lng": _columns.align_lat_lng,
        "split_list_objects": _columns.split_list_objects,
        "extract_keywords": _text.extract_keywords,
        "truncate_after_substring": _text.truncate_after_substring,
        "categorize_by_reference": _text.categorize_by_reference,
        "handle_outliers": _stats.handle_outliers,
        "drop_outliers": _stats.drop_outliers,
        "fill_missing": _stats.fill_missing,
        "fill_missing_from": _stats.fill_missing_from,
        "get_hierarchical_stats": _stats.get_hierarchical_stats,
        "impute_by_language": _translate.impute_by_language,
        "translate_conditional_column": _translate.translate_conditional_column,
        "translate_categorical_column": _translate.translate_categorical_column,
        "fill_missing_coordinates": _geocode.fill_missing_coordinates,
        "convert_to_usd": _currency.convert_to_usd,
        "extract_entities_nlp": _nlp.extract_entities_nlp,
        "save_to_json": io.save_to_json,
        "save_to_sql": io.save_to_sql,
    }

    for name, implementation in expected.items():
        assert getattr(BynatAccessor, name).__wrapped__ is implementation, name


def test_accessor_profile_delegates_to_profiling_and_keeps_basedata_adaptation():
    dataframe_module = importlib.import_module("bynat._accessors.dataframe")
    profiling_profile = importlib.import_module("bynat.profiling.profile").profile
    from bynat.cleaning._outputs import is_basedata_type

    assert BynatAccessor.profile.__wrapped__ is dataframe_module.profile
    assert dataframe_module._profiling_profile is profiling_profile
    assert dataframe_module.is_basedata_type is is_basedata_type


def test_functional_packages_do_not_depend_on_the_accessor_boundary():
    offenders: list[str] = []
    for package in FUNCTIONAL_PACKAGES:
        package_dir = PACKAGE_ROOT / package
        for path in sorted(package_dir.rglob("*.py")):
            relative = path.relative_to(PACKAGE_ROOT.parent).as_posix()
            for module_name in _absolute_imports(path):
                if module_name.startswith("bynat._accessors"):
                    offenders.append(f"{relative}: {module_name}")
            source = path.read_text(encoding="utf-8")
            for forbidden in ("bynat._accessors", "bynat.cleaning.accessor", "cleaning.accessor"):
                if forbidden in source:
                    offenders.append(f"{relative}: {forbidden}")

    assert offenders == []


def test_accessor_boundary_does_not_import_the_root_package():
    for path in sorted(ACCESSORS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name != "bynat" for alias in node.names), (path.name, node.lineno)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module != "bynat", (path.name, node.lineno)


def test_old_accessor_module_is_gone():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bynat.cleaning.accessor")
    assert not (PACKAGE_ROOT / "cleaning" / "accessor.py").exists()
    assert not (PACKAGE_ROOT / "cleaning" / "accessor.pyi").exists()


def test_import_order_registers_the_accessor_without_circular_imports():
    root = PACKAGE_ROOT.parent
    script = (
        "import bynat.cleaning\n"
        "import bynat.profiling\n"
        "import bynat.caching\n"
        "import bynat.analytics\n"
        "import bynat\n"
        "import pandas as pd\n"
        "from bynat._accessors import BynatAccessor\n"
        "frame = pd.DataFrame({'user.name': ['Ada']})\n"
        "assert isinstance(frame.bynat, BynatAccessor)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(root),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
