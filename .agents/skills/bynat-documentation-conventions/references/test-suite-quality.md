# Test-Suite Quality Improvement

Use this reference after a hierarchical test migration when improving decomposition, deduplication, coverage, discovery, CI, or execution cost.

## Baseline matrix

Capture these before editing and again after each implementation batch:

| Area | Evidence to collect |
|---|---|
| Structure | `find tests -type f`, root test modules, per-file `wc -l`, largest files |
| Collection | `python -m pytest --collect-only -q`, test functions/classes, parametrized cases, skips, xfails, deselections |
| Quality | `ruff check tests benchmarks tools`, `python -m compileall -q bynat tests`, focused and full pytest results |
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

### Full verification

```bash
python -m pytest -q
python -m compileall -q bynat tests
ruff check tests benchmarks tools
python tools/verify_installed_wheel.py
python benchmarks/bench_extract_keywords.py --sizes 2000
python benchmarks/bench_outliers.py --sizes 2000
```

Run optional/extras selections separately when dependencies are available, and record expected skips/xfails rather than collapsing them into pass counts.

## Common quality pitfalls

- Do not split at 200 lines mechanically; that threshold triggers investigation, while ownership and cohesion determine the actual split.
- Do not centralize similar helpers without proving distinct-domain reuse; similarity alone creates a dumping ground and coupling.
- Do not remove a test because another entry point has the same assertions; public API coverage can be intentionally independent.
- Do not claim production coverage from a high line percentage; map each relevant module to behavior and failure-mode tests.
- Do not trust a passing full suite when collection changed; compare files, definitions, cases, skips, xfails, and deselections explicitly.
- Do not change CI selectors or marker semantics to make local runs look cleaner; verify the command used by CI and preserve the constitutional distinction between test-type filters, mutation, and network policies.
- Do not optimize fixture scope or cache test data across tests until isolation and order independence are demonstrated; shared mutable state can make a faster suite incorrect.
- Do not call historical path references defects automatically; distinguish active tooling/CI/docs from intentionally retained migration records before editing.
- Do not report a performance improvement from different environments or dependency sets; keep interpreter, data size, and dependency conditions comparable.
