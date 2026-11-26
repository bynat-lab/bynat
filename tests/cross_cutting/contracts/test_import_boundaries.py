"""AST enforcement of bynat import-boundary rules 1-3 and private naming."""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "bynat"
SIBLINGS = frozenset({"profiling", "analytics", "caching", "cleaning"})
ACCESSOR = "_accessors"

# Rule 1: the exact public names exported by each sibling package __init__.py.
PUBLIC_NAMES = {
    "bynat.analytics": frozenset({"Analyzer"}),
    "bynat.caching": frozenset({
        "CacheManager", "CACHE_DIR_ENV_VAR", "DEFAULT_CACHE_DIR", "shared_cache_manager",
    }),
    "bynat.cleaning": frozenset({"BaseData", "CsvFile", "JsonFile"}),
    "bynat.profiling": frozenset({
        "profile", "ProfileReport", "DatasetProfile", "ColumnProfile",
    }),
}

# Rule 2: public modules the accessor may never import, even by a deep path.
ACCESSOR_FORBIDDEN = frozenset({
    "bynat.analytics", "bynat.analytics.analyzer",
    "bynat.caching", "bynat.caching.manager",
    "bynat.cleaning", "bynat.cleaning.base", "bynat.cleaning.io",
    "bynat.cleaning.enrich", "bynat.cleaning.enrich.providers",
    "bynat.profiling", "bynat.profiling.profile", "bynat.profiling.report",
})

# Rule 3: owner of every _internal package. "*" is open to all consumers.
INTERNAL_OWNERS = {
    "bynat._internal": "*",
    "bynat.analytics._internal": "analytics",
    "bynat.caching._internal": "caching",
    "bynat.cleaning._internal": "cleaning",
    "bynat.cleaning.enrich._internal": "cleaning",
    "bynat.profiling._internal": "profiling",
}


def _owner(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and module.startswith("bynat.") else "bynat"


def _imports(source: str, module: str, is_package: bool) -> list[tuple[str, list[str]]]:
    """All runtime imports, including those nested in functions and classes."""
    found: list[tuple[str, list[str]]] = []

    def walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):
                test = child.test
                if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                    continue
                if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
                    continue
            if isinstance(child, ast.Import):
                found.extend((alias.name, []) for alias in child.names)
            elif isinstance(child, ast.ImportFrom):
                if child.level:
                    base = module.split(".") if is_package else module.split(".")[:-1]
                    if child.level > 1:
                        base = base[: len(base) - (child.level - 1)]
                    target = ".".join([*base, *([child.module] if child.module else [])])
                else:
                    target = child.module or ""
                found.append((target, [alias.name for alias in child.names]))
            walk(child)

    walk(ast.parse(source))
    return found


def _internal_owner(path: str) -> str | None:
    matches = [key for key in INTERNAL_OWNERS if path == key or path.startswith(key + ".")]
    return INTERNAL_OWNERS[max(matches, key = len)] if matches else None


def check_rules(source: str, module: str, is_package: bool = False) -> list[str]:
    """Return every boundary violation in one module's source."""
    owner = _owner(module)
    problems: list[str] = []

    for target, names in _imports(source, module, is_package):
        if not target.startswith("bynat."):
            continue
        parts = target.split(".")

        # Rule 2: the accessor uses private cores only; never a public interface.
        if owner == ACCESSOR and len(parts) > 1 and parts[1] in SIBLINGS:
            public_module = any(forbidden == target or forbidden.startswith(target + ".")
                                for forbidden in ACCESSOR_FORBIDDEN)
            private = any(part.startswith("_") for part in parts[2:]) or (
                bool(names) and all(name.startswith("_") for name in names)
            )
            if public_module and not private:
                problems.append(f"R2: {module} imports public {target}")
            elif not private:
                problems.append(f"R2: {module} imports non-private {target} names={names}")

        # Rule 1: a subpackage reaches a sibling only through its public API.
        if owner in SIBLINGS and len(parts) > 1 and parts[1] in SIBLINGS and parts[1] != owner:
            sibling = f"bynat.{parts[1]}"
            if target == sibling:
                if not names or not set(names) <= PUBLIC_NAMES[sibling]:
                    problems.append(f"R1: {module} imports {target} names={names}")
            else:
                problems.append(f"R1: {module} imports deep {target}")

        # Rule 3: an _internal helper stays inside its owning package.
        for path in (target, *(f"{target}.{name}" for name in names)):
            internal_owner = _internal_owner(path)
            if internal_owner is not None and internal_owner != "*" and owner != internal_owner:
                problems.append(f"R3: {module} imports {path} owned by {internal_owner}")

    return sorted(set(problems))


def check_naming(root: Path) -> list[str]:
    """Rule: no private _<name>.py may mirror a public <name>.py in one directory."""
    problems = []
    for directory in sorted({root, *root.rglob("*")}):
        if not directory.is_dir():
            continue
        public = {p.stem for p in directory.glob("*.py")
                  if not p.stem.startswith("_") and p.stem != "__init__"}
        for path in directory.glob("_*.py"):
            if path.stem != "__init__" and path.stem[1:] in public:
                problems.append(f"{path.relative_to(root).as_posix()} mirrors {path.stem[1:]}.py")
    return problems


def test_all_production_modules_respect_the_boundaries():
    offenders = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        module = path.relative_to(PACKAGE_ROOT.parent).with_suffix("").as_posix().replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-len(".__init__")]
        offenders.extend(check_rules(path.read_text(encoding="utf-8"), module,
                                     is_package = path.name == "__init__.py"))
    assert offenders == []


def test_no_private_module_mirrors_a_public_module_name():
    assert check_naming(PACKAGE_ROOT) == []


def test_rule_1_fixture_is_rejected():
    bad = "from bynat.caching._internal import compute_cache_diff\n"
    assert any(problem.startswith("R1:") for problem in check_rules(bad, "bynat.analytics.probe"))


def test_rule_2_fixture_is_rejected():
    bad = "import bynat.analytics\nfrom bynat.caching import CacheManager\n"
    problems = check_rules(bad, "bynat._accessors.dataframe")
    assert sum(problem.startswith("R2:") for problem in problems) == 2


def test_rule_3_fixture_is_rejected():
    bad = "from bynat.caching._internal.keys import cache_value_key\n"
    assert any(problem.startswith("R3:") for problem in check_rules(bad, "bynat.analytics.probe"))


def test_naming_fixture_is_rejected(tmp_path):
    (tmp_path / "thing.py").write_text("")
    (tmp_path / "_thing.py").write_text("")
    assert check_naming(tmp_path) == ["_thing.py mirrors thing.py"]
