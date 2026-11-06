"""Make repository-root support modules importable during the test session.

`tests/test_doc_drift.py` imports `tools/sync_docs.py`, which is development
tooling and is not part of the installed `bynat` distribution. It is therefore
only importable when the repository root is on `sys.path`. Add it here so the
module collects under every supported invocation (`python -m pytest`, the
`pytest` console script, and invocation from a working directory other than
the repository root) instead of silently dropping the doc-drift gate.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
