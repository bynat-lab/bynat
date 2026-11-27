"""Make repository-root support modules importable during the test session.

`tests/cross_cutting/equivalence/_bench_refs.py` imports
`benchmarks/reference_impls.py`, which is development tooling and is not part
of the installed `bynat` distribution. It is therefore only importable when
the repository root is on `sys.path`. Add it here so the module collects under
every supported invocation (`python -m pytest`, the `pytest` console script,
and invocation from a working directory other than the repository root).
"""

import os
import sys
from pathlib import Path

import pytest

import bynat  # noqa: F401  # importing bynat registers the DataFrame accessor

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRIMARY_MARKERS = {"unit", "integration", "property"}


def pytest_collection_modifyitems(items):
    """Derive the primary marker from the test-type directory and enforce exactly one."""
    for item in items:
        parts = item.path.relative_to(ROOT).parts
        if parts and parts[0] == "tests":
            parts = parts[1:]
        derived = {
            "unit": "unit",
            "integration": "integration",
            "properties": "property",
        }.get(parts[0] if parts else "")
        if derived:
            item.add_marker(getattr(pytest.mark, derived))
        present = {m.name for m in item.iter_markers() if m.name in PRIMARY_MARKERS}
        assert len(present) == 1, f"{item.nodeid} has primary markers {sorted(present)}"

try:
    from hypothesis import settings

    settings.register_profile("default", max_examples=25, deadline=None, derandomize=True)
    settings.register_profile("fast", max_examples=25, deadline=None, derandomize=True)
    settings.register_profile("extended", max_examples=200, deadline=None, derandomize=False, print_blob=True)
    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
except ImportError:
    pass

