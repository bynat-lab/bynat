"""Reconcile pytest collection and execution counts, and attribute deselections.

Run from the repository root with an interpreter that has pytest installed:

    python scripts/reconcile_pytest_counts.py --python <project-interpreter>
    python scripts/reconcile_pytest_counts.py --python <project-interpreter> \
        --ignore tests/cross_cutting/contracts/test_properties.py

Prints the identity check (collected = executed + deselected) and one row per
marker group so every deselected test can be attributed to a documented runner.
Exit code is non-zero when the identity does not balance or a run fails.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

SUMMARY = re.compile(
    r"(?P<passed>\d+) passed|(?P<failed>\d+) failed|(?P<skipped>\d+) skipped|"
    r"(?P<xfailed>\d+) xfailed|(?P<xpassed>\d+) xpassed|"
    r"(?P<errors>\d+) error|(?P<deselected>\d+) deselected"
)
COLLECTED = re.compile(r"(?P<collected>\d+)/(?P<total>\d+) tests collected")


def run(python: str, args: list[str]) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [python, "-m", "pytest", *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout + proc.stderr


def parse_summary(text: str) -> dict[str, int]:
    out = {}
    for match in SUMMARY.finditer(text):
        for key, value in match.groupdict().items():
            if value:
                out[key] = out.get(key, 0) + int(value)
    return out


def parse_collected(text: str) -> tuple[int, int] | None:
    match = COLLECTED.search(text)
    if not match:
        return None
    return int(match.group("collected")), int(match.group("total"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--ignore", action="append", default=[])
    ap.add_argument(
        "--markers",
        default="slow,extras,network,mutation",
        help="comma-separated marker groups excluded by addopts",
    )
    args = ap.parse_args()

    base = []
    for path in args.ignore:
        base += ["--ignore", path]

    print(f"interpreter: {args.python}")
    print(f"extra args : {' '.join(base) or '(none)'}")
    print()

    code, text = run(args.python, ["--collect-only", "-q", *base])
    collected = parse_collected(text)
    if collected is None:
        print("COLLECTION FAILED")
        print(text[-3000:])
        return 1
    n_collected, n_total = collected

    code, text = run(args.python, ["-q", "-ra", *base])
    if code not in (0, 1, 2, 5):
        print("EXECUTION FAILED")
        print(text[-3000:])
        return 1
    summ = parse_summary(text)
    executed = sum(
        summ.get(k, 0) for k in ("passed", "failed", "skipped", "xfailed", "xpassed", "errors")
    )
    deselected = summ.get("deselected", 0)

    print("TERM                COUNT")
    for key in ("passed", "failed", "skipped", "xfailed", "xpassed", "errors", "deselected"):
        if summ.get(key):
            print(f"{key:<18} {summ[key]}")
    print()
    print(f"collected (collect-only) : {n_collected}")
    print(f"total items known         : {n_total}")
    print(f"executed                 : {executed}")
    print(f"deselected               : {deselected}")
    ok = n_collected == executed + deselected
    print(f"identity collected = executed + deselected : {'OK' if ok else 'MISMATCH'}")
    if not ok:
        print("  -> a test module failed to collect, or addopts changed mid-run")

    print()
    print("MARKER GROUP        COLLECTED   PASSED   FAILED   SKIPPED   XFAILED")
    for marker in [m.strip() for m in args.markers.split(",") if m.strip()]:
        _, ctext = run(args.python, ["-m", marker, "--collect-only", "-q", *base])
        got = parse_collected(ctext)
        n = got[0] if got else 0
        _, rtext = run(args.python, ["-m", marker, "-q", *base])
        s = parse_summary(rtext)
        print(
            f"{marker:<18} {n:>9} {s.get('passed', 0):>8} {s.get('failed', 0):>8} "
            f"{s.get('skipped', 0):>9} {s.get('xfailed', 0):>8}"
        )

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
