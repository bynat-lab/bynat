"""Quarantine helper for corrupt legacy cache files."""

import os
import time
import uuid

__all__ = ["quarantine_corrupt_cache_file"]


def quarantine_corrupt_cache_file(file_path: str) -> str | None:
    """
    Move a corrupt cache file aside without overwriting a quarantine.

    A unique `.<name>.corrupt.<timestamp>.<uuid>` path is reserved with
    `os.open(..., O_CREAT | O_EXCL)` and the source is then moved onto it, so
    two processes cannot claim the same quarantine path. The source path is
    left untouched when the move fails.

    Args:
        file_path (str): Path of the corrupt cache file.

    Returns:
        str | None: The quarantine path, or None when no unique path could be
        reserved or the move failed (including when another process had
        already moved the source).
    """
    quarantine_path = None

    for _ in range(10):
        candidate = f"{file_path}.corrupt.{time.time_ns()}.{uuid.uuid4().hex}"
        try:
            descriptor = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            quarantine_path = candidate
            break
        except FileExistsError:
            continue

    if quarantine_path is None:
        return None

    try:
        os.replace(file_path, quarantine_path)
        return quarantine_path
    except FileNotFoundError:
        # Another process may have quarantined the source first.
        try:
            os.remove(quarantine_path)
        except OSError:
            pass
        return None
    except OSError:
        try:
            os.remove(quarantine_path)
        except OSError:
            pass
        return None
