"""Diff computation between a live function cache and its baseline snapshot."""

import json
from datetime import UTC, datetime

__all__ = ["compute_cache_diff"]


def compute_cache_diff(
    func_name: str,
    live_cache: dict,
    baseline: dict,
) -> tuple[list[tuple[str, str, str, str, str]], list[tuple[str, str, str]]]:
    """
    Diff a live function cache against its baseline snapshot.

    Entries that were newly added, or whose value differs from the baseline,
    become prepared rows with the value serialized by `json.dumps`. Every
    baseline `(bucket, key)` identity no longer present in the live cache,
    including the keys of an entirely removed bucket, becomes a removal
    identity. Non-dict buckets are skipped on both sides. All prepared rows
    share one `created_at` ISO timestamp (UTC).

    Args:
        func_name (str): Function identifier the rows belong to.
        live_cache (dict): Current in-memory `{bucket: {key: value}}` cache.
        baseline (dict): Snapshot of the cache as last loaded or saved.

    Returns:
        tuple: `(prepared_entries, removal_identities)` where
        `prepared_entries` is a list of
        `(func_name, bucket, key, value_json, created_at)` rows and
        `removal_identities` is a list of `(func_name, bucket, key)`.

    Raises:
        TypeError: If a changed value cannot be serialized to JSON.
        ValueError: If a changed value cannot be serialized to JSON (for
            example a circular reference).
    """
    prepared_entries: list[tuple[str, str, str, str, str]] = []
    removal_identities: list[tuple[str, str, str]] = []
    created_at = datetime.now(UTC).isoformat()

    for bucket, entries in live_cache.items():
        if not isinstance(entries, dict):
            continue

        baseline_bucket = baseline.get(bucket)

        if not isinstance(baseline_bucket, dict):
            baseline_bucket = {}

        for key, value in entries.items():
            if key in baseline_bucket and baseline_bucket[key] == value:
                continue

            prepared_entries.append(
                (
                    func_name,
                    bucket,
                    key,
                    json.dumps(value, ensure_ascii = False),
                    created_at,
                )
            )

    for bucket, baseline_entries in baseline.items():
        if not isinstance(baseline_entries, dict):
            continue

        live_bucket = live_cache.get(bucket)

        if isinstance(live_bucket, dict):
            removed_keys = [key for key in baseline_entries if key not in live_bucket]
        else:
            removed_keys = list(baseline_entries)

        for key in removed_keys:
            removal_identities.append((func_name, bucket, key))

    return prepared_entries, removal_identities
