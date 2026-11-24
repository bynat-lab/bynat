"""AST contract enforcing the constitutional dependency rules ARCH-022--ARCH-027."""

import ast
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(
    os.environ.get("BYNAT_VERIFY_SOURCE_ROOT", str(Path(__file__).resolve().parents[3]))
).resolve()
PACKAGE_ROOT = REPO_ROOT / "bynat"

# ARCH-022: exact target modules permitted for cross-package runtime imports. analytics permits none.
PERMITTED_CROSS_PACKAGE: dict[str, frozenset[str]] = {
    "bynat": frozenset({"bynat.cleaning", "bynat.caching", "bynat.analytics",
                        "bynat.profiling", "bynat._accessors", "bynat.cleaning.io"}),
    "_accessors": frozenset({"bynat.analytics",
                             "bynat.cleaning.columns", "bynat.cleaning.io", "bynat.cleaning.stats",
                             "bynat.cleaning.text", "bynat.cleaning._outputs",
                             "bynat.cleaning.enrich.currency", "bynat.cleaning.enrich.geocode",
                             "bynat.cleaning.enrich.nlp", "bynat.cleaning.enrich.translate",
                             "bynat.caching", "bynat.profiling", "bynat.profiling.profile"}),
    "cleaning": frozenset({"bynat.caching", "bynat.caching._keys", "bynat.profiling",
                           "bynat.profiling.profile", "bynat._internal"}),
    "profiling": frozenset({"bynat._internal"}),
    "analytics": frozenset(), "caching": frozenset(), "_internal": frozenset(),
}

PRIVATE_IMPORT_EXCEPTIONS: dict[tuple[str, str], frozenset[str]] = {
    ("bynat.cleaning.enrich.engine", "bynat.caching._keys"): frozenset({"cache_value_key"}),
    ("bynat.cleaning.enrich.translate", "bynat.caching._keys"): frozenset({"cache_has_value", "cache_lookup_value"}),
    ("bynat._accessors.dataframe", "bynat.cleaning._outputs"): frozenset({"is_basedata_type"}),
    ("bynat.cleaning.io", "bynat._internal"): frozenset({"dedupe_key"}),
    ("bynat.profiling.profile", "bynat._internal"): frozenset({"dedupe_key"}),
}


def _dotted(path: Path) -> str:
    parts = list(path.resolve().relative_to(REPO_ROOT).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1:] == ["__init__"] else parts)


def _module_file(base: Path) -> Path | None:
    if base.suffix == ".py" and base.exists():
        return base
    init = base / "__init__.py"
    module = Path(f"{base}.py")
    return init if init.exists() else module if module.exists() else None


def _runtime_imports(tree: ast.Module) -> list[tuple[str | None, list[str], int]]:
    imports: list[tuple[str | None, list[str], int]] = []
    pending = list(ast.iter_child_nodes(tree))
    while pending:
        node = pending.pop()
        test = getattr(node, "test", None)
        type_checking = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )
        if isinstance(node, ast.If) and type_checking:
            pending.extend(node.orelse)
            continue
        pending.extend(ast.iter_child_nodes(node))
        if isinstance(node, ast.Import):
            imports.extend((alias.name, [], 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.module, [alias.name for alias in node.names], node.level))
    return imports


def _resolve(source: Path, module: str | None, names: list[str], level: int) -> list[str]:
    if level:
        anchor = source.parent if level == 1 else source.parent.parents[level - 2]
        base = anchor.joinpath(*module.split(".")) if module else anchor
    else:
        assert module is not None
        base = REPO_ROOT.joinpath(*module.split("."))
    module_path = _module_file(base)
    if module_path is None:
        return []
    if not names:
        return [_dotted(module_path)]
    return [
        _dotted(candidate) if (candidate := _module_file(base / name)) is not None
        else _dotted(module_path)
        for name in names
    ]


def _owner(module: str) -> str:
    return "bynat" if module == "bynat" else module.split(".")[1]


def _module_trees() -> list[tuple[Path, str, ast.Module]]:
    return [
        (path, _dotted(path), ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(PACKAGE_ROOT.rglob("*.py"))
    ]


def _edges() -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for path, source, tree in _module_trees():
        for module, names, level in _runtime_imports(tree):
            for target in _resolve(path, module, names, level):
                if target.startswith("bynat") and target != source:
                    edges.add((source, target))
    return edges


def _private_imports() -> set[tuple[str, str, str]]:
    private: set[tuple[str, str, str]] = set()
    for path, source, tree in _module_trees():
        for module, names, level in _runtime_imports(tree):
            parts = module.split(".") if module else []
            if not any(part.startswith("_") for part in parts + names):
                continue
            symbols = names or ([parts[-1]] if parts else [])
            for target, symbol in zip(_resolve(path, module, names, level), symbols):
                if _owner(target) != _owner(source):
                    private.add((source, target, symbol))
    return private


def _find_cycle(edges: set[tuple[str, str]]) -> list[str]:
    adjacency: dict[str, set[str]] = {}
    for source, target in edges:
        adjacency.setdefault(source, set()).add(target)
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for neighbor in sorted(adjacency.get(node, set())):
            if state.get(neighbor) == 1:
                return stack[stack.index(neighbor) :] + [neighbor]
            if state.get(neighbor, 0) == 0:
                cycle = visit(neighbor)
                if cycle is not None:
                    return cycle
        stack.pop()
        state[node] = 2
        return None

    for node in sorted(adjacency):
        if state.get(node, 0) == 0 and (cycle := visit(node)) is not None:
            return cycle
    return []


def _row_wise_offenders() -> list[str]:
    offenders: list[str] = []
    for path, _, tree in _module_trees():
        relative = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in {"iterrows", "itertuples"}:
                offenders.append(f"{relative}:{node.lineno}:{node.func.attr}()")
            elif node.func.attr == "apply":
                values = [*node.args[1:2], *(k.value for k in node.keywords if k.arg == "axis")]
                if any(
                    isinstance(v, ast.Constant) and v.value == 1 and not isinstance(v.value, bool)
                    for v in values
                ):
                    offenders.append(f"{relative}:{node.lineno}:apply(axis=1)")
    return offenders


def test_dependency_edges_stay_within_permitted_boundaries():
    edges = _edges()
    violations = [
        f"{source} -> {target}"
        for source, target in sorted(edges)
        if _owner(source) != _owner(target)
        and target not in PERMITTED_CROSS_PACKAGE[_owner(source)]
    ]
    assert violations == []
    assert PERMITTED_CROSS_PACKAGE["analytics"] == frozenset() and all(
        ("bynat._accessors.dataframe", f"bynat.cleaning.enrich.{name}") in edges
        for name in ("currency", "geocode", "nlp", "translate")
    )


def test_private_module_imports_match_documented_allowances_exactly():
    expected = {
        (s, t, sym) for (s, t), syms in PRIVATE_IMPORT_EXCEPTIONS.items() for sym in syms
    } | {("bynat", "bynat._accessors", "_accessors")}  # root __init__ self-registration
    assert _private_imports() == expected


def test_runtime_import_graph_is_acyclic():
    edges = _edges()
    assert _find_cycle(edges) == []


def test_production_paths_do_not_use_row_wise_iteration():
    assert _row_wise_offenders() == []
