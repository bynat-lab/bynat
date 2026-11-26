"""Output-type validation and conversion helpers for tabular operations."""

import inspect
from typing import Any

import pandas as pd

__all__ = [
    "constructor_accepts_data",
    "convert_default_output",
    "convert_output",
    "is_basedata_type",
    "validate_output_type",
]


def is_basedata_type(output_type: Any) -> bool:
    """
    Check whether a type is BaseData or a BaseData subclass without importing it.

    Inspects the class MRO to identify BaseData ancestry without creating a
    dependency from lower-level cleaning modules to the facade layer.

    Args:
        output_type (Any): Candidate type.

    Returns:
        bool: True only when `output_type` is a class whose MRO contains a
        class named `BaseData` defined in `bynat.cleaning.base`.
    """
    if not isinstance(output_type, type):
        return False

    return any(
        getattr(base_cls, "__name__", None) == "BaseData"
        and getattr(base_cls, "__module__", "") == "bynat.cleaning.base"
        for base_cls in output_type.__mro__
    )


def validate_output_type(output_type: Any) -> None:
    """
    Validate the generic tabular output types supported by this package.

    Args:
        output_type (Any): Candidate output type.

    Raises:
        TypeError: If `output_type` is not None, `dict`, `pandas.DataFrame`,
            or a BaseData-family class.
    """
    if output_type is None or output_type is dict or output_type is pd.DataFrame:
        return

    if is_basedata_type(output_type):
        return

    raise TypeError(
        "output_type must be None, pandas.DataFrame, dict, or a "
        "BaseData subclass."
    )


def convert_output(data: pd.DataFrame, output_type: Any) -> Any:
    """
    Convert a dataframe to a supported output type without schema coupling.

    Args:
        data (pd.DataFrame): Frame to convert.
        output_type (Any): `None` or `pandas.DataFrame` returns `data`
            unchanged, `dict` returns `{column: values_list}`, and anything
            else is called as `output_type(data=data)`.

    Returns:
        Any: The converted value.
    """
    if output_type is None or output_type is pd.DataFrame:
        return data

    if output_type is dict:
        return {column: data[column].tolist() for column in data.columns}

    return output_type(data = data)


def constructor_accepts_data(output_type: Any) -> bool:
    """
    Return whether a constructor signature can bind the keyword ``data``.

    Args:
        output_type (Any): Candidate constructor.

    Returns:
        bool: True when `inspect.signature(output_type).bind(data=...)` runs
        without `TypeError` or `ValueError`.
    """
    try:
        inspect.signature(output_type).bind(data = pd.DataFrame())
    except (TypeError, ValueError):
        return False
    return True


def convert_default_output(data: pd.DataFrame, output_type: Any) -> Any:
    """
    Use a custom default constructor only when its signature accepts data.

    `pandas.DataFrame` and any constructor that cannot bind `data=` are
    returned as the plain frame; otherwise the frame is converted through
    `convert_output`.

    Args:
        data (pd.DataFrame): Frame to convert.
        output_type (Any): Candidate default output type.

    Returns:
        Any: `data` or its converted form.
    """
    if output_type is pd.DataFrame or not constructor_accepts_data(output_type):
        return data
    return convert_output(data, output_type)
