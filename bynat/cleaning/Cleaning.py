"""Compatibility shim: `bynat.cleaning.Cleaning` is now `bynat.cleaning.base`."""

import sys

from bynat.cleaning import base as _base
from bynat.cleaning.base import *  # noqa: F403

# Alias the module so attribute access and monkeypatching reach the real code.
sys.modules[__name__] = _base
