"""Typing bridge for the ``df.bynat`` pandas accessor.

At runtime ``DataFrame`` is exactly ``pandas.DataFrame``: no wrapper,
subclass, registration, or extra dependency is introduced. Under
``TYPE_CHECKING`` it is declared as a subclass with a typed ``bynat``
property, so static checkers can see the generated accessor stub while
runtime behaviour stays identical to pandas.

Example:
    >>> from bynat.pandas_typing import DataFrame
    >>> frame = DataFrame({'value': [1, 2]})
    >>> frame.bynat.drop_by_substring('unused')
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from bynat._accessors.dataframe import BynatAccessor

__all__ = ['DataFrame']

if TYPE_CHECKING:

    class DataFrame(pd.DataFrame):
        """A ``pandas.DataFrame`` whose ``bynat`` accessor is statically typed.

        This class exists only for type checkers. At runtime ``DataFrame``
        is ``pandas.DataFrame`` itself, so construction and behaviour are
        unchanged.
        """

        @property
        def bynat(self) -> BynatAccessor:
            """The typed accessor bound to this frame.

            Returns:
                BynatAccessor: Accessor exposing bynat's cleaning and
                    enrichment methods.
            """
            ...

else:
    DataFrame = pd.DataFrame
