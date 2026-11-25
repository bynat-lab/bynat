"""Argument validation helpers shared by the cleaning modules."""

from typing import Any

__all__ = ["require_positive_int"]


def require_positive_int(value: Any, arg_name: str) -> None:
    """
    Validate integer parameters that control sampling or cache checkpointing.

    Args:
        value (Any): Value to validate.
        arg_name (str): Parameter name used in the error message.

    Raises:
        ValueError: If `value` is not a positive integer. Booleans are
        rejected even though `bool` subclasses `int`.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"The '{arg_name}' parameter must be a positive integer")