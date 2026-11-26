"""Internal helpers for the cleaning package. Not part of the public API."""

from .docs import shares_doc
from .frames import FrameT, like
from .hierarchy import (
    HIERARCHICAL_STATS_COLUMNS,
    hierarchical_outlier_masks,
    left_merge_aligned,
    normalize_hierarchy,
)
from .matching import (
    apply_removal_patterns,
    first_literal_matches,
    first_regex_matches,
)
from .optional import import_optional, try_import
from .outputs import (
    constructor_accepts_data,
    convert_default_output,
    convert_output,
    is_basedata_type,
    validate_output_type,
)
from .sql import build_engine_url
from .validation import require_positive_int

__all__ = [
    "HIERARCHICAL_STATS_COLUMNS",
    "FrameT",
    "apply_removal_patterns",
    "build_engine_url",
    "constructor_accepts_data",
    "convert_default_output",
    "convert_output",
    "first_literal_matches",
    "first_regex_matches",
    "hierarchical_outlier_masks",
    "import_optional",
    "is_basedata_type",
    "left_merge_aligned",
    "like",
    "normalize_hierarchy",
    "require_positive_int",
    "shares_doc",
    "try_import",
    "validate_output_type",
]
