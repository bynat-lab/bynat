"""Helpers for optional dependencies that are imported only when used."""

import importlib
from types import ModuleType

__all__ = ["import_optional", "try_import"]


def import_optional(module_name: str, distribution: str, feature: str) -> ModuleType:
    """
    Import a feature dependency only when the feature is used.

    Args:
        module_name (str): Importable module to load.
        distribution (str): pip distribution name used in the error message.
        feature (str): Feature name used in the error message.

    Returns:
        ModuleType: The imported module.

    Raises:
        ImportError: If the module cannot be imported. The message names the
            missing optional distribution and the feature that needs it, and
            chains the original import error.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(
            f"{feature} requires the optional '{distribution}' dependency."
        ) from exc


def try_import(module_name: str) -> ModuleType | None:
    """
    Import an optional module, or return None when it is not installed.

    Args:
        module_name (str): Importable module to load.

    Returns:
        ModuleType | None: The imported module, or None when it cannot be
        imported.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None
