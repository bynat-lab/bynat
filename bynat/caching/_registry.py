"""Process-wide registry of shared cache managers."""

import threading
from os import PathLike
from typing import Any

__all__ = ['register_manager_type', 'resolve_cache_manager', 'shared_manager_for']

_shared_managers: dict[str, Any] = {}
_shared_managers_lock = threading.Lock()
_manager_type: type | None = None

# Bound by caching.manager at import time. Declared here but never imported
# from the public module, so the registry has no circular dependency.
CacheManager: Any


def register_manager_type(manager_type: type) -> None:
    """Record the public manager class used to build shared instances."""
    global _manager_type
    _manager_type = manager_type


def shared_manager_for(cache_dir: str | PathLike | None, manager_type: type) -> Any:
    """Build or return the process-wide manager for one cache directory."""
    probe = manager_type(cache_dir)

    with _shared_managers_lock:
        return _shared_managers.setdefault(probe.cache_dir_path, probe)


def resolve_cache_manager(cache: Any) -> Any:
    """Return an explicit manager as-is, or resolve a cache spec to a shared one."""
    if _manager_type is not None and isinstance(cache, _manager_type):
        return cache

    return shared_manager_for(cache, _manager_type)
