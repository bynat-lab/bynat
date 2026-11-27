"""Type-introspection helpers shared across bynat packages."""

from typing import Any

__all__ = ['is_named_type_from_module']


def is_named_type_from_module(value: Any, class_name: str, module_name: str) -> bool:
    """Check whether a value is a class named `class_name` from `module_name`.

    The class MRO is inspected so subclasses are recognised without importing
    the owning module from a lower-level helper. No module name is hard-coded
    here: each caller supplies the class and module it cares about.

    Args:
        value (Any): Candidate value.
        class_name (str): Expected class name.
        module_name (str): Module that defines the expected class.

    Returns:
        bool: True only when `value` is a class whose MRO contains a class
        named `class_name` defined in `module_name`.
    """
    if not isinstance(value, type):
        return False

    return any(
        getattr(base_cls, "__name__", None) == class_name
        and getattr(base_cls, "__module__", "") == module_name
        for base_cls in value.__mro__
    )
