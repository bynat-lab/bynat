"""Generic value and concurrency helpers for the enrichment engine."""

import threading
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd

__all__ = ["rate_limited_map", "unique_values", "translate_all"]


def unique_values(values: Iterable) -> list:
    """Return the unique non-null values in first-seen order."""
    series = values if isinstance(values, pd.Series) else pd.Series(list(values), dtype = object)
    return list(series.dropna().unique())


def rate_limited_map(
    func: Callable[[Any], Any],
    items: Sequence[Any],
    max_workers: int = 1,
    min_interval: float = 0.0,
) -> list:
    """
    Call `func` on every item and return results in input order, with an
    exception in place of each failed call.

    At most `max_workers` calls run at once, and call starts are spaced at
    least `min_interval` seconds apart across all workers.
    """
    lock = threading.Lock()
    next_start = time.monotonic()

    def call(item: Any) -> Any:
        nonlocal next_start

        if min_interval > 0:
            with lock:
                now = time.monotonic()
                wait = next_start - now
                next_start = max(now, next_start) + min_interval

            if wait > 0:
                time.sleep(wait)

        try:
            return func(item)
        except Exception as error:
            return error

    if max_workers <= 1 or len(items) <= 1:
        return [call(item) for item in items]

    with ThreadPoolExecutor(max_workers = min(max_workers, len(items))) as pool:
        return list(pool.map(call, items))


def translate_all(provider: Any, texts: Sequence[str], target_lang: str) -> list[Any]:
    """Translate texts with a provider's batch method or its rate-limited `translate`."""
    translate_batch = getattr(provider, "translate_batch", None)

    if callable(translate_batch):
        return list(translate_batch(list(texts), target_lang))

    return rate_limited_map(
        lambda text: provider.translate(text, target_lang),
        texts,
        max_workers = int(getattr(provider, "max_workers", 1) or 1),
        min_interval = float(getattr(provider, "min_interval", 0.0) or 0.0),
    )
