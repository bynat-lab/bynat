# Test-Suite Quality Improvement

Use this reference after a hierarchical test migration when improving decomposition, deduplication, coverage, discovery, CI, or execution cost.

## Baseline matrix

Capture these before editing and again after each implementation batch:

| Area | Evidence to collect |
|---|---|
| Structure | `find tests -type f`, root test modules, per-file `wc -l`, largest files |
| Collection | `python -m pytest --collect-only -q`, test functions/classes, parametrized cases, skips, xfails, deselections |
| Quality | `ruff check bynat tests benchmarks`, `python -m compileall -q bynat tests`, focused and full pytest results |
| Configuration | `pyproject.toml`, `pytest.ini`, `tox.ini`, `conftest.py`, registered markers |
| CI | every workflow's pytest, lint, typecheck, extras, slow, mutation, and network commands |
| Tooling | documentation drift, installed-wheel verifier, benchmark imports and execution |
| Coverage | production-file → owning test file → behavior/contract → gap or justification |
| Performance | collection and full-suite wall time, expensive fixture/setup timing, repeated preparation |

Run the project interpreter explicitly when the repository provides one; preserve the same interpreter and dependency state for before/after comparisons.

## Audit order

1. Read the complete testing standard and identify binding rules versus current-state facts and future targets.
2. Inspect production modules and test consumers together. Search symbols and imports before proposing helper extraction or file splits.
3. Classify each test file by primary responsibility, then list its distinct responsibilities, fixtures, helpers, constants, parameter data, optional-dependency behavior, and path/tool coupling.
4. Search for duplicate helpers, fixtures, assertion blocks, patch/install routines, temporary-resource setup, and test-module imports. Separate intentional repetition across public entry points from accidental duplication.
5. Build the coverage matrix. Treat package initializers and declarative metadata as explicit exclusions only when another test verifies their observable behavior; never infer coverage from neighboring modules.
6. Check discovery and CI paths, including nested manifest resolution, conftest scope, marker registration, optional extras, and installed-wheel copying rules.
7. Rank findings by correctness risk, discovery risk, maintainability, and measurable cost. Implement only confirmed defects or improvements with a clear owner and focused verification.

## Decomposition decision table

| Finding | Action |
|---|---|
| One file mixes independent ownership domains | Split by responsibility and preserve the original test inventory |
| One file is large but cohesive | Keep it together unless the constitutional size limit is exceeded |
| Similar setup is used within one module | Use a module-local helper or `conftest.py` |
| Same setup is used by distinct architectural domains | Promote only after verifying both consumers and the maintainability benefit |
| Same assertions validate different supported entry points | Keep both tests; share setup or a narrow assertion utility only |
| One test module imports another test module | Extract the reusable logic into production-independent test support code |
| A helper has one consumer | Keep it local; do not create generic shared infrastructure |
| A test is skipped or xfailed | Verify the condition, reason, marker policy, and expected count before changing it |

## Reusable verification recipes

### Inventory and root-file checks

```bash
find tests -type f -name '*.py' -not -path '*/__pycache__/*' -print | sort
find tests -maxdepth 1 -type f -name 'test_*.py' -print
wc -l tests/**/*.py
```

Use a small AST script when counts matter; distinguish test-function definitions from collected cases and count `pytest.param` cases separately.

### Discovery and marker checks

```bash
python -m pytest --collect-only -q
python -m pytest --collect-only -q -m network
python -m pytest -q -m 'not slow and not extras and not network and not mutation'
python -m pytest --markers
```

A marker selecting zero tests is not evidence that the marker may be removed. Confirm its registration/policy and preserve it.

### Optional-dependency cases inside one parametrized test

A single parametrized test often mixes core cases with cases that need an optional
extra. Do not mark the whole function `extras` (that needlessly gates the core cases)
and do not leave it unmarked (the optional case then runs where the extra is absent and
raises `ImportError`). Mark the individual parameter set and gate it in the body:

```python
EXTRAS_METHODS = {"categorize_by_reference"}


def _require_optional_dependency(name):
    if name in EXTRAS_METHODS:
        pytest.importorskip("ahocorasick")


TRANSFORMS = [
    pytest.param("extract_keywords", ("description",), {"colors": ["blue"]}, id="extract_keywords"),
    pytest.param(
        "categorize_by_reference",
        ("description",),
        {"target_col": "field", "reference": {"Colors": ["blue"]}},
        id="categorize_by_reference",
        marks=pytest.mark.extras,
    ),
]


@pytest.mark.parametrize(("name", "args", "kwargs"), TRANSFORMS)
def test_inplace(name, args, kwargs):
    _require_optional_dependency(name)
    ...
```

`pytest.param(..., marks=...)` attaches the marker to that item only, so
`-m "not extras"` deselects just that case and `-m extras` selects just that case.
The in-body `importorskip` satisfies the marker policy's gating requirement and also
protects marker expressions that do not exclude `extras` (for example `-m unit`).

Before relying on this, confirm the job that runs `-m extras` actually installs the
extra and that the default job does not; the defect is usually a routing gap, not a
missing install.

### Simulating an absent optional dependency

Prove gating without a second environment by blocking the module with a throwaway
plugin instead of uninstalling anything from the user's environment:

```python
# scratch/block_dep.py
import sys

sys.modules["ahocorasick"] = None
```

```bash
PYTHONPATH=<scratch> python -m pytest tests/.../test_x.py -p block_dep -q
PYTHONPATH=<scratch> python -m pytest -p block_dep -q
```

`import of X halted; None in sys.modules` reproduces the `ImportError` path exactly.
Compare counts against the pre-change baseline: only the gated cases should move from
passed to deselected, and the run must stay green.

### Count reconciliation

Collection and execution totals differ by design; establish the identity before
quoting any number:

```
collected  = executed + deselected
executed   = passed + failed + skipped + xfailed (+ errors)
```

Derive the deselected set from the `addopts` marker expression in `pyproject.toml`
(currently excludes `slow`, `extras`, `network`, and `mutation`), not from memory; a
`-m <marker>` CLI flag overrides `addopts`, so `pytest -m extras` runs only that group.
Every excluded marker must have a documented runner (CI job, scheduled workflow, or a
named command in `docs/TESTING_STANDARDS.md`); a marker nothing runs is dead coverage.

A missing dev dependency fails **collection**, not execution: `--collect-only` reports
`N tests collected, 1 error` and the run aborts. Exclude that file with `--ignore` and
record the gap rather than installing into the user's environment.

For the full claimed-repair verification procedure, exclusion inventory, constitution
compliance matrix, mechanical anti-cheating scans, and stale-path sweep, use the
`reviewing-python-libraries` skill's `references/test-suite-integrity-audit.md` and its
`scripts/reconcile_pytest_counts.py`.

### Full verification

```bash
python -m pytest -q
python -m compileall -q bynat tests
ruff check bynat tests benchmarks
python tools/verify_installed_wheel.py
python benchmarks/bench_extract_keywords.py --sizes 2000
python benchmarks/bench_outliers.py --sizes 2000
```

Run optional/extras selections separately when dependencies are available, and record expected skips/xfails rather than collapsing them into pass counts.

## Common quality pitfalls

- The 200-line ceiling (`BYNAT-ARCH-4`) is a hard maximum, not an investigation trigger; a file over it is a defect unless it carries the recorded justification the rule requires. Splitting it must still follow functional boundaries, never line count alone.
- Do not centralize similar helpers without proving distinct-domain reuse; similarity alone creates a dumping ground and coupling.
- Do not remove a test because another entry point has the same assertions; public API coverage can be intentionally independent.
- Do not claim production coverage from a high line percentage; map each relevant module to behavior and failure-mode tests.
- Do not trust a passing full suite when collection changed; compare files, definitions, cases, skips, xfails, and deselections explicitly.
- Do not change CI selectors or marker semantics to make local runs look cleaner; verify the command used by CI and preserve the constitutional distinction between test-type filters, mutation, and network policies.
- Do not optimize fixture scope or cache test data across tests until isolation and order independence are demonstrated; shared mutable state can make a faster suite incorrect.
- Do not call historical path references defects automatically; distinguish active tooling/CI/docs from intentionally retained migration records before editing. But a dangling path inside a *test module's own docstring* is always a defect — it misdirects the next reader to a file that no longer exists. After any test move or rename, sweep docs, test module docstrings, and CI configuration for the old path.
- Do not parse module-level markers with a regex like `pytestmark = pytest.mark.<name>`; the list form `pytestmark = [pytest.mark.unit, pytest.mark.extras]` is common and a regex misses it, reporting every test in the file as having no primary marker. Parse the assignment value with `ast`.
- Do not report a `parametrize` call as missing per-case ids until every named constant is resolved. `@pytest.mark.parametrize("x", SOME_LIST)` and a module-level `PARAM = pytest.param(value, id="...")` referenced by name both satisfy an id rule that a raw AST read of the decorator reports as violated. Resolve `ast.Name` values — including names bound to `pytest.param(...)` — recursively before recording a finding, and re-measure the count after the fix; an unresolved scan overstates the violation list and sends the next session editing compliant cases.
- Verify a monkeypatch target against the production call site before trusting it; patching a method that merely wraps the call leaves the real path untouched and the suite green (see `testing-python-libraries`). An assertion-free test hides this completely.
- Do not report a performance improvement from different environments or dependency sets; keep interpreter, data size, and dependency conditions comparable.
- Scope linting to the directories you own; the repository's CI runs `ruff check bynat tests benchmarks`, and a bare `ruff check ./` also lints vendored agent-skill scripts under `.agents/` and reports failures in code outside the package.
- CI installs the latest pandas, so a green CI run does not by itself cover older supported pandas majors; verify version-sensitive DataFrame mutation and accessor behavior on the oldest supported version before claiming cross-version support.

## Remediation discipline

When an audit handoff authorizes fixes, keep the finding list authoritative and the tree honest:

- Re-validate every finding against the current test and implementation before editing; a finding is a hypothesis until the code is read.
- Do not modify cases that already comply. Adding ids, assertions, or structure to a compliant case is churn that obscures the real diff and can change what a failure report means.
- Consolidate helpers only where the duplication is genuine and behavior is preserved. A fake that records calls, injects failures, or varies a pipeline is a different test intent, not a duplicate; merging it changes what the test exercises.
- If a finding cannot be fixed safely because the governing specification is ambiguous, do not guess and do not silently skip it. Report the precise blocker, continue with the independent fixes, and leave the item open.
- When an established findings list is supplied, execute the fixes directly. Do not re-run the investigation, re-derive the findings, or produce another planning report; re-validate each finding against the current code and fix it.
- Re-run the focused tests for every changed area, then the full default suite, then the marker selections, lint, and documentation checks. Compare collected/passed/xfailed/skipped/deselected counts against the pre-remediation baseline: they must be identical unless a change was intentional and named.

## Functional hierarchy decisions

Apply this before creating, splitting, or moving any test directory. It restates `docs/TESTING_STANDARDS.md` `BYNAT-ARCH-12` as a procedure.

1. Name the broad responsibility the parent directory represents.
2. Name what each file in it actually covers.
3. Files covering independent aspects of that broad responsibility stay at the parent level.
4. If two or more files cover different aspects of one narrower responsibility, move them into a directory named for that responsibility.
5. Stop there. A directory for one file, or for a shared keyword, is wrong.

Forbidden: mirroring the production package layout; a directory per production module; one directory per test file; a subdirectory per independent concern; grouping by a shared filename word; combining unrelated tests to reduce directory count; splitting a large file mechanically without naming the responsibilities involved.

Worked example — `tests/cross_cutting/accessor/`, broad area "the `df.bynat` accessor":

```text
incorrect                                   correct
accessor/                                   accessor/
├── test_accessor.py                        ├── test_accessor.py
├── test_parity.py                          ├── test_parity.py
├── test_accessor_inplace.py                └── inplace/              # narrower: in-place execution
├── test_accessor_argument_binding.py           ├── test_mutation.py
└── test_accessor_variadic_capture.py           ├── test_argument_binding.py
                                                └── test_variadic_capture.py
```

`test_accessor.py` (registration, loaders, cache manager) and `test_parity.py` (class/accessor result parity) cover independent aspects, so they stay. The three in-place files cover one narrower responsibility, so they nest. The same reasoning keeps `tests/modules/columns/test_columns_inplace.py` and `tests/modules/stats/test_stats_inplace.py` flat: each covers a narrower responsibility with no sibling file, and a one-file directory is forbidden.

Ambiguous cases and how to resolve them: several `test_<area>_*.py` files at one level that all cover a single function or workflow are the suffix pattern the rule forbids, so group them in a directory named for that responsibility. A defect pin whose body exercises two different production areas is cross-cutting, so it belongs in `tests/cross_cutting/<topic>/` rather than in either owning module directory.
