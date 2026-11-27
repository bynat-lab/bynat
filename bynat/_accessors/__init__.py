"""Private pandas accessor integration boundary.

Importing this package registers the ``df.bynat`` DataFrame accessor. It owns
registration and binding mechanics only; all transformations delegate to the
functional packages.
"""

from .dataframe import BynatAccessor

__all__ = ['BynatAccessor']
