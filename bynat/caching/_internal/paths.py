"""Cache-directory and cache-key path helpers."""

import os
from os import PathLike

__all__ = [
    "legacy_json_path",
    "normalize_cache_dir",
    "validate_cache_key",
]


def normalize_cache_dir(cache_dir: str | PathLike) -> tuple[str, str]:
    """Validate and normalize an already-resolved cache directory.

    Relative paths are resolved from the current working directory. Absolute
    paths are used as provided. User home markers (`~`) and environment
    variables are expanded before the path is normalized. Nothing is created
    on disk.

    Args:
        cache_dir (str | os.PathLike): Directory to normalize.

    Returns:
        tuple[str, str]: The absolute path and the normalized path as given
        after expansion, in that order.

    Raises:
        TypeError: If `cache_dir` is not a string or path-like object.
        ValueError: If `cache_dir` is empty after normalization.
    """
    if not isinstance(cache_dir, (str, PathLike)):
        raise TypeError("cache_dir must be a string or path-like object")

    cache_dir = os.fspath(cache_dir)

    if not isinstance(cache_dir, str):
        raise TypeError("cache_dir must resolve to a string path")

    cache_dir = cache_dir.strip()

    if not cache_dir:
        raise ValueError("cache_dir cannot be empty")

    expanded_cache_dir = os.path.expandvars(os.path.expanduser(cache_dir))

    return os.path.abspath(expanded_cache_dir), os.path.normpath(expanded_cache_dir)


def validate_cache_key(key: str, key_name: str) -> str:
    """Validate a cache key before using it in file paths or dictionaries.

    Args:
        key (str): Cache key value to validate.
        key_name (str): Human-readable argument name for error messages.

    Returns:
        str: Normalized cache key.

    Raises:
        TypeError: If `key` is not a string.
        ValueError: If `key` is empty or contains path separators.
    """
    if not isinstance(key, str):
        raise TypeError(f"{key_name} must be a string")

    key = key.strip()

    if not key:
        raise ValueError(f"{key_name} cannot be empty")

    if os.path.basename(key) != key or os.path.sep in key or (os.path.altsep and os.path.altsep in key):
        raise ValueError(f"{key_name} cannot contain path separators")

    return key


def legacy_json_path(cache_dir_path: str, func_name: str) -> str:
    """Build the legacy JSON cache-file path for a specific function name.

    Args:
        cache_dir_path (str): Absolute path of the cache directory.
        func_name (str): The logical function identifier used as the cache
            filename prefix.

    Returns:
        str: Absolute path to the legacy `<func_name>_cache.json` file.

    Raises:
        TypeError: If `func_name` is not a string.
        ValueError: If `func_name` is empty or contains path separators.
    """
    func_name = validate_cache_key(func_name, "func_name")

    return os.path.join(cache_dir_path, f"{func_name}_cache.json")
