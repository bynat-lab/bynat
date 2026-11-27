import pytest

from tests.contracts.architecture.dependency_helpers import (
    PERMITTED_CROSS_PACKAGE,
    PRIVATE_IMPORT_EXCEPTIONS,
    _edges,
    _find_cycle,
    _owner,
    _private_imports,
    _row_wise_offenders,
)

pytestmark = pytest.mark.unit


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
        for name in ("_currency", "_geocode", "_nlp", "_translate")
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
