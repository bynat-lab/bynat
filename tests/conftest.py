"""Make repository-root support modules importable during the test session.

`tests/cross_cutting/contracts/test_doc_drift.py` imports `tools/sync_docs.py`,
and `tests/cross_cutting/equivalence/_bench_refs.py` imports
`benchmarks/reference_impls.py`; both are development tooling and are not part
of the installed `bynat` distribution. They are therefore only importable when
the repository root is on `sys.path`. Add it here so these modules collect
under every supported invocation (`python -m pytest`, the `pytest` console
script, and invocation from a working directory other than the repository
root) instead of silently dropping the doc-drift gate or the equivalence tests.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
