"""Docstring-sharing decorator used by the `BaseData` facade."""

from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["shares_doc"]

F = TypeVar('F', bound=Callable[..., Any])


def shares_doc(func: Callable[..., Any]) -> Callable[[F], F]:
    """
    Reuse a shared implementation's docstring on a `BaseData` method.

    The decorator assigns the implementation's cleaned docstring to the
    method's `__doc__` at import time. `tools/sync_docs.py` writes the same
    text as a literal docstring in `base.py` so editors and type checkers can
    see it without running the decorator, and `tests/cross_cutting/contracts/
    test_doc_drift.py` fails when the two drift apart.

    Args:
        func (Callable): Shared implementation whose docstring is copied.

    Returns:
        Callable: Decorator that assigns the docstring and returns the method
        unchanged.
    """
    def decorate(method: F) -> F:
        """Assign the shared docstring to `method` and return it unchanged."""
        method.__doc__ = (func.__doc__ or "").rstrip()

        return method

    return decorate