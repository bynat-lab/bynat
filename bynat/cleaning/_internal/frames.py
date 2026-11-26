"""DataFrame subtype helpers shared by the cleaning modules."""

from typing import Any, TypeVar, cast

import pandas as pd

__all__ = ["FrameT", "like"]

FrameT = TypeVar("FrameT", bound = pd.DataFrame)


def like(df: FrameT, data: pd.DataFrame) -> FrameT:
    """
    Return `data` as `df`'s frame type, carrying `df`'s metadata.

    A plain `pandas.DataFrame` is returned unchanged; any other frame type is
    rebuilt through its `_constructor` and finalized with `df`, so pandas
    metadata propagates.

    Args:
        df (FrameT): Frame supplying the target type and metadata.
        data (pd.DataFrame): Data to wrap.

    Returns:
        FrameT: `data` typed as `df`.
    """
    if type(df) is pd.DataFrame:
        return cast(FrameT, data)

    # pandas-stubs types `_constructor` as an attribute, not a callable.
    constructor: Any = df._constructor
    return cast(FrameT, constructor(data).__finalize__(df))
