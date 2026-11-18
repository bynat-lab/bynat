#!/usr/bin/env python3
"""Prove that the working tree differs from HEAD only in docstrings.

Usage:
    python scripts/verify_docs_only.py [repo-root]

For every tracked file that `git diff` reports as modified, parse the HEAD
revision and the working-tree revision, strip docstrings (the leading string
expression on Module/FunctionDef/AsyncFunctionDef/ClassDef) and attribute
docstrings (any other bare string expression), then compare `ast.dump`. A file
whose dumps match changed only in documentation; any other file is reported.

Exit code 0 when every modified Python file is documentation-only, 1 otherwise.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

_DOCSTRING_OWNERS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _strip(tree: ast.AST) -> ast.AST:
    """Return `tree` with docstrings and attribute docstrings removed."""
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_OWNERS):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        if _is_docstring(body[0]):
            body = body[1:] or [ast.Pass()]
        node.body = [statement for statement in body if not _is_docstring(statement)]
    return tree


def _modified_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _head_text(root: Path, relative: str) -> str:
    return subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    failures: list[str] = []
    checked = 0

    for relative in _modified_files(root):
        if not relative.endswith(".py"):
            continue
        checked += 1
        try:
            before = ast.dump(_strip(ast.parse(_head_text(root, relative))))
            after = ast.dump(_strip(ast.parse((root / relative).read_text(encoding="utf-8"))))
        except (SyntaxError, subprocess.CalledProcessError) as error:
            failures.append(f"{relative}: cannot compare ({error})")
            continue
        if before != after:
            failures.append(relative)

    for failure in failures:
        print(f"non-docstring change: {failure}")
    print(f"{checked} modified Python file(s) compared; {len(failures)} with non-docstring changes")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
