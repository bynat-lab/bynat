"""Naming-only contract for prohibited generic internal-helper module/package names.

This is objective machine enforcement for the naming portion of ARCH-021 and ARCH-081 and
for the `_internal` naming convention in ARCH-094. It inspects only module and package
*names* under `bynat/`. It does not assess semantic helper placement, ownership, or
cohesion (ARCH-092/ARCH-093), which require human review under ARCH-101.
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(
    os.environ.get("BYNAT_VERIFY_SOURCE_ROOT", str(Path(__file__).resolve().parents[3]))
).resolve()
PACKAGE_ROOT = REPO_ROOT / "bynat"

PROHIBITED_GENERIC_NAMES = frozenset(
    {"shared", "_shared", "utils", "helpers", "common"}
)

# ARCH-095 grandfathers this existing cleaning-scoped owner module as a current-state
# exception. It is not a naming pattern for new helper collections.
GRANDFATHERED = {"cleaning/_common.py"}


def _production_paths() -> list[str]:
    """Every `.py` module and every directory under `bynat/`, relative to the package root."""
    paths = [
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    paths += [
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_dir() and path != PACKAGE_ROOT and "__pycache__" not in path.parts
    ]
    return sorted(paths)


def _generic_name_matches() -> list[str]:
    # Leading underscores are ignored so `_common`-style variants of a prohibited
    # generic name are caught too (`_shared` is already an explicit entry).
    return [
        path
        for path in _production_paths()
        if Path(path).stem.lstrip("_") in PROHIBITED_GENERIC_NAMES
    ]


def _offenders() -> list[str]:
    return [
        f"{'package' if not path.endswith('.py') else 'module'} {path}"
        for path in _generic_name_matches()
        if path not in GRANDFATHERED
    ]


def test_no_prohibited_generic_helper_module_or_package_names():
    assert _offenders() == []


def test_cleaning_common_is_the_single_grandfathered_exception():
    assert (PACKAGE_ROOT / "cleaning" / "_common.py").is_file()
    assert _generic_name_matches() == ["cleaning/_common.py"]
