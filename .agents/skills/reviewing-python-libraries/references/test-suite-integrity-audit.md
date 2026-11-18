# Test-Suite Integrity and Claimed-Repair Verification

Use when the task is to verify repairs a previous report claimed, or to audit an
existing test suite for integrity: collection completeness, exclusions, compliance
with a governing testing standard, and anti-cheating. Read-only unless the user
asks for fixes.

## 0. Execution ownership

Execute this work personally. Do not delegate repository inspection, test
execution, or evidence collection: the report's authority is that the auditor ran
the commands. Implementation work may be delegated, but the verification that
closes it may not. Confirm the delegation scope before spawning anything.

## 1. Verify claimed repairs against the tree, never against the report

- Read the actual file and re-run the probe. A prior report is not evidence.
- A patch that "could not find the old text" does not mean the edit is missing:
  read the current file first. The intended state is often already present, and
  blindly re-applying is how a heading gets rewritten twice.
- Confirm the repaired artifact and its *dependent* artifacts agree: runtime
  signature, generated stub, docstring-sync check, and the tests that assert
  parity. A repair that lands in one file and not its dependents is the common
  half-finished shape.
- Re-run the suite **after** the last repair and date the result mentally; counts
  produced before a repair do not describe the current tree.

## 2. Reconcile the pytest counts before quoting any of them

Collection totals and execution totals differ by design. Establish the identity
first, then explain every term:

```
collected  = executed + deselected
executed   = passed + failed + skipped + xfailed (+ errors)
```

Derive the deselected set from the *configured* marker expression, not from
memory — read `addopts` in `pyproject.toml` and enumerate each excluded marker:

```bash
python -m pytest --collect-only -q                       # collected + deselected
for m in slow extras network mutation; do
  python -m pytest -m "$m" --collect-only -q | tail -1
  python -m pytest -m "$m" -q | tail -1                 # who actually runs it
done
```

`scripts/reconcile_pytest_counts.py` produces this table from the same inputs.

Rules the arithmetic exposes:

- Every marker group excluded by `addopts` must have a documented runner (a CI
  job, a scheduled workflow, or a named command in the testing standard). A
  marker nothing runs is silently dead coverage.
- A `-m <marker>` CLI flag **overrides** `addopts`' `-m`, so `pytest -m extras`
  runs *only* that group — verify that is the intent before calling it "the full
  extras suite".
- A missing dev dependency fails **collection**, not execution: `--collect-only`
  reports `N tests collected, 1 error`, and the run aborts. Exclude that file with
  `--ignore` and record the gap; do not install into the user's environment.
- Cross-environment count differences must be explained term by term. A skip that
  appears on one framework version and not another is usually a `skipif` on the
  major version — read the condition and confirm it against the actual run.

## 3. Exclusion audit

Inventory every `skip`, `skipif`, `pytest.skip`, `xfail`, `importorskip`, and
`filterwarnings`. For each: location, exact condition, documented reason, and
whether a supported environment can run it.

- `xfail` without `strict=True`, or without a tracked-issue reason, is a hole.
  A strict `xfail` that starts passing must turn the suite red — that is the
  mechanism working, not a failure to suppress.
- A `skipif` keyed on a framework major version is legitimate but must be
  re-checked: confirm the reason still describes a real upstream defect rather
  than a bug that was fixed and a condition nobody revisited.
- `pytest.mark.filterwarnings("ignore")` hides deprecations; the acceptable
  pattern is `warnings.catch_warnings()` + `simplefilter("error", ...)`.
- `importorskip` inside a test is normally paired with an `extras`-style marker
  so the default run does not pay for it.

## 4. Constitution compliance matrix

When a governing testing standard exists, it is authoritative — do not substitute
your own idea of good practice. Build a requirement-by-requirement matrix:
rule id, what it demands, the files that must satisfy it, the concrete evidence,
and `Compliant / Violated / Unverified`.

Two parsing traps that produce false "violation" or false "compliant" rows:

- **Module-level `pytestmark` may be a list.** `pytestmark = [pytest.mark.unit,
  pytest.mark.extras]` is common; a regex looking for
  `pytestmark = pytest.mark.<name>` misses it and reports every test in the file
  as having no primary marker. Parse the assignment's value with `ast`.
- **File-size rules often carry an explicit backlog clause.** Read the rule and
  any sibling backlog rule together. A file over the ceiling that the standard
  explicitly lists as a tracked backlog is compliant *as written*; a backlog is
  not a general licence, so record which trigger ("next substantive
  modification") has or has not fired.

## 5. Mechanical anti-cheating scans

Run these as AST/grep passes over `tests/`; each is cheap and each finds a
different class of false green.

| Scan | What it catches |
|---|---|
| test functions with no `assert` / `raises` / `warns` / comparison helper | tests that pass by not raising, never by checking |
| `parametrize` calls with no per-case `id` | unreadable failure reports; often a standard violation — resolve named constants first, or compliant calls get reported |
| `except Exception` / bare `except` in test code | swallowed failures — but check whether it is a multiprocessing worker reporting to the parent before calling it a violation |
| `.equals()` as the only assertion | ignores index names and dtypes |
| `test_*.py` importing another `test_*.py` | shared helpers must live in `helpers.py` / `conftest.py` / `tests/shared/` |
| module-level mutable state, unseeded RNG, wall-clock reads | non-determinism |
| duplicate fakes/helpers defined inside test files | a module `helpers.py` exists for exactly this |

For every candidate finding, read the surrounding code before reporting. A
`monkeypatch` on a private method is often legitimate failure injection at a
boundary, and an `except Exception` in a child process is often the only way to
surface the error to the parent.

## 6. Stale path references

A move or rename leaves prose behind. Sweep docs, test module docstrings, and
CI configuration for repository paths and resolve each one:

```bash
# every repo-relative .py path mentioned in docs/ and tests/, checked for existence
```

A dangling path inside a *test module's docstring* is still a defect — it
misdirects the next reader to a file that no longer exists.

## 7. Reporting

Distinguish four states and never merge them: **verified** (you ran it and read
the output), **confirmed defect** (code evidence plus a reproduction),
**unresolved discrepancy** (two numbers that do not reconcile, with both raw
outputs), and **unverified** (an environment you could not run). A green suite
is not a pass; a documented gap is not a solved problem.