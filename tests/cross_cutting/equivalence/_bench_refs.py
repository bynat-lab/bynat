"""Shared support for the equivalence tests.

The 0.3.0 reference implementations live in ``benchmarks/reference_impls.py``
so that both the benchmarks and the equivalence tests consume one definition
and neither imports the other's test module. The benchmarks are development
tooling, not part of the installed ``bynat`` distribution, so the repository
root must be on ``sys.path`` for this import to resolve under every supported
pytest invocation (``python -m pytest``, the ``pytest`` console script, and a
working directory other than the repository root).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.reference_impls import (  # noqa: E402
    _legacy_convert_to_usd,
    _legacy_drop_outliers,
    _legacy_extract_keywords,
    _legacy_handle_outliers,
    _legacy_outlier_masks,
    _legacy_translate_categorical,
    _legacy_translate_conditional_column,
)

__all__ = [
    "_legacy_convert_to_usd",
    "_legacy_drop_outliers",
    "_legacy_extract_keywords",
    "_legacy_handle_outliers",
    "_legacy_outlier_masks",
    "_legacy_translate_categorical",
    "_legacy_translate_conditional_column",
]
