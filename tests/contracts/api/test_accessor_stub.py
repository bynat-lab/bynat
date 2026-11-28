"""Contract tests for the generated accessor stub and the runtime alias."""

import ast
import difflib
import inspect
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import bynat._accessors.dataframe as dataframe_module
import bynat.pandas_typing
from bynat._accessors.dataframe import BynatAccessor
from bynat.pandas_typing import DataFrame

pytestmark = pytest.mark.integration

_NO_DEFAULT = object()

_PARAM_KINDS = {
    'posonly': inspect.Parameter.POSITIONAL_ONLY,
    'positional': inspect.Parameter.POSITIONAL_OR_KEYWORD,
    'vararg': inspect.Parameter.VAR_POSITIONAL,
    'kwonly': inspect.Parameter.KEYWORD_ONLY,
    'kwarg': inspect.Parameter.VAR_KEYWORD,
}


def _stub_class(path: Path) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding='utf-8').replace('\r\n', '\n'))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'BynatAccessor':
            return node
    raise AssertionError('BynatAccessor class not found in stub')


def _function_map(class_node: ast.ClassDef) -> dict[str, ast.FunctionDef]:
    functions: dict[str, ast.FunctionDef] = {}
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef):
            functions[item.name] = item
    return functions


def _stub_parameter_info(
    node: ast.FunctionDef,
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    names: list[str] = []
    kinds: dict[str, Any] = {}
    defaults: dict[str, Any] = {}

    posonly_names = {argument.arg for argument in node.args.posonlyargs}
    positional = node.args.posonlyargs + node.args.args
    positional_defaults = node.args.defaults
    offset = len(positional) - len(positional_defaults)
    for index, argument in enumerate(positional):
        names.append(argument.arg)
        kinds[argument.arg] = (
            _PARAM_KINDS['posonly']
            if argument.arg in posonly_names
            else _PARAM_KINDS['positional']
        )
        defaults[argument.arg] = (
            ast.literal_eval(positional_defaults[index - offset])
            if index >= offset
            else _NO_DEFAULT
        )

    if node.args.vararg is not None:
        names.append(node.args.vararg.arg)
        kinds[node.args.vararg.arg] = _PARAM_KINDS['vararg']
        defaults[node.args.vararg.arg] = _NO_DEFAULT

    for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        names.append(argument.arg)
        kinds[argument.arg] = _PARAM_KINDS['kwonly']
        defaults[argument.arg] = (
            ast.literal_eval(default) if default is not None else _NO_DEFAULT
        )

    if node.args.kwarg is not None:
        names.append(node.args.kwarg.arg)
        kinds[node.args.kwarg.arg] = _PARAM_KINDS['kwarg']
        defaults[node.args.kwarg.arg] = _NO_DEFAULT

    return names, kinds, defaults


def test_generated_stub_matches_runtime_signatures() -> None:
    stub_path = Path(dataframe_module.__file__).with_suffix('.pyi')
    stub_functions = _function_map(_stub_class(stub_path))

    runtime: dict[str, inspect.Signature] = {}
    for name, member in vars(BynatAccessor).items():
        if name.startswith('_') and name != '__init__':
            continue
        if isinstance(member, property):
            getter = member.fget
            assert getter is not None, f'{name} property has no getter'
            target = getter
        else:
            target = member
        runtime[name] = inspect.signature(target)

    missing = sorted(set(runtime) - set(stub_functions))
    extra = sorted(set(stub_functions) - set(runtime))
    assert not missing, f'public members missing from stub: {missing}'
    assert not extra, f'unexpected function members in stub: {extra}'

    mismatches: list[str] = []
    for name in sorted(runtime):
        signature = runtime[name]
        stub_names, stub_kinds, stub_defaults = _stub_parameter_info(stub_functions[name])
        runtime_names = list(signature.parameters)
        if runtime_names != stub_names:
            mismatches.append(
                f'{name}: parameter names differ: runtime={runtime_names} stub={stub_names}'
            )
            continue
        for parameter in signature.parameters.values():
            expected_kind = parameter.kind
            actual_kind = stub_kinds[parameter.name]
            if expected_kind != actual_kind:
                mismatches.append(
                    f'{name}.{parameter.name}: kind runtime={expected_kind!r} '
                    f'stub={actual_kind!r}'
                )
            expected_default = (
                parameter.default
                if parameter.default is not inspect.Parameter.empty
                else _NO_DEFAULT
            )
            actual_default = stub_defaults[parameter.name]
            if type(expected_default) is not type(actual_default) or expected_default != actual_default:
                mismatches.append(
                    f'{name}.{parameter.name}: default runtime={expected_default!r} '
                    f'stub={actual_default!r}'
                )

    assert not mismatches, 'stub/runtime signature drift:\n' + '\n'.join(mismatches)


def test_generated_stub_is_current() -> None:
    from tools.gen_accessor_stub import render_stub

    stub_path = Path(dataframe_module.__file__).with_suffix('.pyi')
    tracked = stub_path.read_text(encoding='utf-8').replace('\r\n', '\n')
    generated = render_stub(BynatAccessor)
    diff = ''.join(
        list(
            difflib.unified_diff(
                generated.splitlines(keepends=True),
                tracked.splitlines(keepends=True),
                fromfile='render_stub',
                tofile=str(stub_path),
            )
        )[:20]
    )
    assert tracked == generated, f'generated stub is out of date:\n{diff}'


def test_typing_alias_is_runtime_dataframe() -> None:
    assert DataFrame is pd.DataFrame
    assert 'DataFrame' in bynat.pandas_typing.__all__
