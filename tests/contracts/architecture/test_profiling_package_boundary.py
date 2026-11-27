import ast
from pathlib import Path

import pytest

import bynat.profiling as profiling

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


def test_profiling_package_has_no_forbidden_imports():
    package_dir = Path(profiling.__file__).resolve().parent
    files = sorted(package_dir.glob("*.py"))
    assert {path.name for path in files} == {
        "__init__.py", "_builders.py", "profile.py", "report.py"
    }

    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "is_basedata_type" not in source
        assert "_shared" not in source
        for module_name in _imported_module_names(path):
            assert not module_name.startswith(
                ("bynat.cleaning", "bynat.analytics", "bynat.caching", "bynat._accessors")
            ), (path.name, module_name)
