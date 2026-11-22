"""
bynat: reusable pandas cleaning and enrichment utilities.

Importing `bynat` registers the `df.bynat` DataFrame accessor.
"""

from . import _accessors as _accessor_registration
from . import analytics, caching, cleaning, profiling
from .cleaning.io import read_csv, read_json

__all__ = [
    "cleaning",
    "caching",
    "analytics",
    "profiling",
    "read_csv",
    "read_json",
]
