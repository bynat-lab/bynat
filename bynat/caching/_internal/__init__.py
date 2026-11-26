"""Internal helpers for the caching package. Not part of the public API."""

from .diff import compute_cache_diff
from .paths import legacy_json_path, normalize_cache_dir, validate_cache_key
from .quarantine import quarantine_corrupt_cache_file

__all__ = [
    "compute_cache_diff",
    "legacy_json_path",
    "normalize_cache_dir",
    "quarantine_corrupt_cache_file",
    "validate_cache_key",
]
