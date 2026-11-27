import ast
import inspect
import textwrap

import pytest

from bynat.cleaning import _stats

pytestmark = pytest.mark.unit


def test_get_hierarchical_stats_has_no_nested_functions_or_apply_lambda():
    source = textwrap.dedent(inspect.getsource(_stats.get_hierarchical_stats))
    tree = ast.parse(source)

    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
        if node is not tree.body[0]
    )
    assert not any(isinstance(node, ast.Lambda) for node in ast.walk(tree))
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "apply"
        for node in ast.walk(tree)
    )
