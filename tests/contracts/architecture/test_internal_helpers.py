import ast
import importlib
from pathlib import Path

import numpy as np
import pytest

import bynat._internal as internal

pytestmark = pytest.mark.unit


INTERNAL_DIR = Path(internal.__file__).resolve().parent


PACKAGE_ROOT = INTERNAL_DIR.parent


def _function_definitions(path: Path, names: set[str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules.append(node.module or "")
    return modules


def _relative_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level > 0
    ]


def test_internal_dedupe_key_normalizes_representative_unhashable_values():
    assert internal.dedupe_key([1, 2]) == "[1, 2]"
    assert internal.dedupe_key((1, 2)) == "[1, 2]"
    assert internal.dedupe_key({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
    assert internal.dedupe_key({2, 1}) == "[1, 2]"
    assert internal.dedupe_key(np.array([1, 2])) == "[1, 2]"
    assert internal.dedupe_key(5) == 5
    assert internal.dedupe_key("text") == "text"
    assert internal.dedupe_key({"a": 1, "b": 2}) == internal.dedupe_key({"b": 2, "a": 1})


def test_internal_dedupe_key_returns_hashable_keys_for_unhashable_values():
    keys = {
        internal.dedupe_key(value)
        for value in ([1, 2], {"a": 1}, {"b": 2}, {1, 2}, np.array([1, 2]))
    }

    assert keys == {"[1, 2]", '{"a": 1}', '{"b": 2}'}


def test_internal_dedupe_key_is_canonical_and_bound_by_consumers():
    keys_module = importlib.import_module("bynat._internal.keys")
    cleaning_writers = importlib.import_module("bynat.cleaning._writers")
    profiling_computations = importlib.import_module("bynat.profiling._internal.computations")

    assert internal.dedupe_key is keys_module.dedupe_key
    assert cleaning_writers._dedupe_key is internal.dedupe_key
    assert profiling_computations.dedupe_key is internal.dedupe_key
    assert internal.dedupe_key.__module__ == "bynat._internal.keys"


def test_internal_dedupe_key_has_no_duplicate_definitions():
    definitions: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        for name in _function_definitions(path, {"dedupe_key", "_dedupe_key"}):
            definitions.append(f"{path.relative_to(PACKAGE_ROOT).as_posix()}::{name}")

    assert definitions == ["_internal/keys.py::dedupe_key"]


def test_internal_cache_key_helpers_are_canonical_and_bound_by_consumers():
    engine = importlib.import_module("bynat.cleaning.enrich._engine")
    translate = importlib.import_module("bynat.cleaning.enrich._translate")

    assert internal.cache_value_key(1.0) == "1"
    assert internal.cache_has_value({"1": "x"}, 1) is True
    assert internal.cache_lookup_value({"1": "x"}, 1) == "x"
    assert engine.cache_value_key is internal.cache_value_key
    assert translate.cache_has_value is internal.cache_has_value
    assert translate.cache_lookup_value is internal.cache_lookup_value


def test_internal_dedupe_key_is_not_reexported_by_cleaning_internal():
    common = importlib.import_module("bynat.cleaning._internal")

    assert not hasattr(common, "dedupe_key")
    assert not hasattr(common, "_dedupe_key")
    assert "dedupe_key" not in common.__all__


def test_internal_modules_declare_explicit_all():
    keys_module = importlib.import_module("bynat._internal.keys")

    assert internal.__all__ == [
        "cache_has_value", "cache_lookup_value", "cache_value_key", "dedupe_key",
        "is_named_type_from_module",
    ]
    assert keys_module.__all__ == [
        "dedupe_key", "cache_value_key", "cache_has_value", "cache_lookup_value",
    ]


def test_internal_package_dependency_direction_is_stdlib_and_numpy_only():
    for path in sorted(INTERNAL_DIR.glob("*.py")):
        for module_name in _absolute_imports(path):
            assert module_name.split(".")[0] in {"json", "typing", "numpy"}, (
                path.name,
                module_name,
            )
        for module_name in _relative_imports(path):
            assert module_name in {"keys", "types"}, (path.name, module_name)
