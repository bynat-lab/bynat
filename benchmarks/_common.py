"""Shared helpers for the benchmark scripts."""

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The repository root makes the checkout's ``bynat`` package importable when
# the benchmarks run from a source tree. The ``tests/`` tree is deliberately
# not added: the shared 0.3.0 references live in ``benchmarks/reference_impls.py``
# and the benchmarks must not depend on the test suite.
sys.path[:0] = [str(ROOT)]


def best_of(func, repeat=3):
    """Return the result of `func()` and its fastest wall time in seconds."""
    best = float("inf")
    result = None

    for _ in range(repeat):
        start = time.perf_counter()
        result = func()
        best = min(best, time.perf_counter() - start)

    return result, best


def print_table(rows):
    """Print rows of `(label, legacy_seconds | None, current_seconds)`."""
    print(f"{'case':<28}{'0.3.0 (s)':>12}{'current (s)':>14}{'speed-up':>10}")

    for label, legacy, current in rows:
        legacy_text = f"{legacy:12.3f}" if legacy is not None else f"{'skipped':>12}"
        ratio = f"{legacy / current:9.1f}x" if legacy is not None else f"{'':>10}"
        print(f"{label:<28}{legacy_text}{current:14.3f}{ratio}")
