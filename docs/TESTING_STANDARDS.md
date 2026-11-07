# bynat Testing Standards

This document is the testing policy for `bynat`. It defines what must be tested, how tests must be written, and which gates must pass before code ships. It elaborates the definition of done in `docs/ROADMAP.md` §6 and the principles in §2 of that document; it does not replace them. Every contributor, reviewer, and automated agent working on `bynat` is expected to follow it.

**Normative language.** `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` are used as defined in RFC 2119. Statements without one of these keywords are context, not requirements.

**Basis tags.**

- **[SB]** — source-backed practice. An authoritative source listed in §13 requires or recommends it.
- **[BP]** — bynat policy. A project decision that goes beyond external guidance.
- **[RP]** — recommended practice from community or project guidance. Adopt it unless a recorded reason says otherwise.

**Status of targets.** Coverage percentages, mutation scores, and phase completion in §7 and §12 are policy targets, not measurements of the current suite. The current suite has no coverage or mutation configuration, and nothing in this document claims otherwise. Targets become binding only when the corresponding phase in §12 is adopted.

## Contents

1. [Purpose and scope](#1-purpose-and-scope)
2. [Philosophy and principles](#2-philosophy-and-principles)
3. [Test types](#3-test-types)
4. [Anti-cheating rules](#4-anti-cheating-rules)
5. [DataFrame cases and pandas.testing assertion standards](#5-dataframe-cases-and-pandastesting-assertion-standards)
6. [Transformation-specific requirements](#6-transformation-specific-requirements)
7. [Coverage, mutation, and quality metrics](#7-coverage-mutation-and-quality-metrics)
8. [Architecture and organization](#8-architecture-and-organization)
9. [CI/CD gates](#9-cicd-gates)
10. [AI agent protocol](#10-ai-agent-protocol)
11. [Human review checklist](#11-human-review-checklist)
12. [Phased adoption roadmap](#12-phased-adoption-roadmap)
13. [References](#13-references)

---

## 1. Purpose and scope

### 1.1 Purpose

This standard exists so that `bynat` behavior is specified by executable tests, so that regressions are caught before release, and so that the quality of the suite itself can be reviewed. It is written against the code as it is: the public class API (`BaseData`, `JsonFile`, `CsvFile`), the `df.bynat` accessor, the shared cleaning functions, the SQLite `CacheManager`, and the optional integrations. [BP]

### 1.2 Scope

**In scope.** [BP]

- All code under `bynat/`.
- All tests under `tests/`, including fixtures, fakes, and helpers.
- Performance scripts under `benchmarks/`.
- CI workflows under `.github/workflows/`.
- Any test-only support code added to the repository.

**Out of scope.** [BP]

- Release engineering beyond the test gates in §9 (versioning, changelog formatting, publishing mechanics).
- Dependency-update policy.
- Security scanning and supply-chain tooling, except that tests MUST NOT introduce secrets or network access.
- Testing of third-party dependencies themselves.

### 1.3 Applies to

- Every pull request that adds or changes behavior, docs that describe behavior, or tests.
- Every scheduled run described in §9.
- Every AI agent or automated tool producing tests for this repository (see §10).

### 1.4 Relationship to other documents

- `docs/ROADMAP.md` §2 states the project principles; §6 states the definition of done. This document is the detailed policy behind those statements. If the two disagree, this document is the detailed policy and the roadmap item MUST be corrected before work proceeds. [BP]
- `README.md` documents behavior. A test that contradicts the README is wrong unless the README is updated in the same change. [BP]
- `CHANGELOG.md` records behavior changes. A test-only change does not need a changelog entry; a behavior change does. [BP]

---

## 2. Philosophy and principles

### 2.1 Principles

1. **Tests are executable specifications.** A test states one observable behavior of the public API. If the README documents it, a test pins it. [SB] (PyPA downstream packaging guidance; NumPy testing guidelines)
2. **One behavior per test.** A test fails for one reason and its name says what that reason is. [SB] (pyOpenSci; Scientific Python guide)
3. **Outside-in first.** Public interface tests come before integration tests, which come before unit tests. Each level has a distinct purpose. [RP] (Scientific Python guide)
4. **A test must be able to fail.** Deliberately break the code, or hard-code a failure, to confirm the test fails when it should. [SB] (Scientific Python guide)
5. **Every bug gets a regression test.** A fix is not complete until a test that fails without the fix and passes with it is merged. [SB] (NumPy testing guidelines)
6. **Determinism.** No unseeded randomness, no clock dependence, no network, no filesystem ordering, no locale dependence. Seed generators or use Hypothesis, which manages seeds, replays failures, and shrinks minimal examples. [SB] (NumPy; Hypothesis; PyPA)
7. **Coverage is a floor, not a proof.** Coverage measures execution, not assertions. A line can be covered by a test that asserts nothing. [SB] (pytest typing guide)
8. **Fail loudly on caller errors, stay lenient on data.** Invalid arguments raise; missing columns are skipped with a logged warning. Tests pin both halves of that contract. [BP] (ROADMAP principle 2)
9. **No row-wise iteration in data paths.** `apply(axis=1)`, `iterrows`, and `itertuples` are not allowed in `bynat/`. Tests enforce this where it is a performance invariant. [BP] (ROADMAP principle 1)
10. **Tests do not touch the network.** External services are replaced with fake modules or injected fake providers. [BP] (ROADMAP principle 5)
11. **Minimal footprint.** Tests use `numpy`, `pandas`, and `pytest` plus the optional extra under test. They do not add mandatory dependencies. [BP] (ROADMAP principle 4)
12. **Backward compatibility is explicit.** A test that pins current behavior is updated only together with a documented behavior change. [BP] (ROADMAP principle 3)

### 2.2 Test quality attributes

A good `bynat` test is: [BP]

- **Correct** — it passes on correct code and fails on incorrect code.
- **Independent** — it does not depend on execution order or on state left by another test.
- **Deterministic** — it produces the same result on every run and on every supported platform.
- **Readable** — a reviewer can tell what behavior is being pinned without reading the implementation.
- **Specific** — it asserts the values or errors that matter, not that "something happened".
- **Fast** — the default suite runs in minutes, not tens of minutes. Slow checks belong in scheduled jobs. [RP] (Scientific Python guide)

---

## 3. Test types

### 3.1 Overview

The table below describes the target testing architecture. It is not a claim that every listed directory, dependency, marker, or scheduled job exists today; current repository state is recorded in §9.1 and migration work is staged in §12. [BP]

| Type | Purpose | Required when | Location | Tooling | Gate |
| --- | --- | --- | --- | --- | --- |
| Unit | Pin one function's behavior in isolation | Every public function and every branch that can fail | `tests/modules/<module>/` | pytest | PR |
| Integration | Pin behavior across class, accessor, shared function, cache, and files | Every public method and every cross-module path | Owning module directory or `tests/cross_cutting/<topic>/` | pytest, tmp_path, fakes | PR |
| API/contract | Pin signatures, docstrings, stubs, schemas, return contracts | Every public API addition or change | `tests/cross_cutting/contracts/` and related cross-cutting topics | pytest, inspect | PR |
| Property-based | Pin invariants over generated inputs | Every transformation with data-shape invariants | Corresponding module directory or cross-cutting topic | Hypothesis | PR (fast profile), scheduled (extended) |
| Regression | Pin a specific fixed bug | Every bug fix | Next to the affected module | pytest | PR |
| Equivalence | Prove an optimized implementation matches a reference | Every performance optimization | `tests/cross_cutting/equivalence/` | pytest | PR |
| Performance | Measure and record speed at representative sizes | Every performance change | `benchmarks/` | scripts | PR (report in description) |
| Mutation | Find test gaps by killing generated mutants | Periodic diagnostic | scheduled | Cosmic Ray | Scheduled, advisory |
| Optional-dependency | Exercise real extras when installed | Every extra-backed method | Owning module directory, usually `tests/modules/enrichment/` | pytest.importorskip | Target extras matrix; current CI covers only `categorization` and `sql` |

### 3.2 Unit tests

**Purpose.** Pin the behavior of one function in `columns`, `text`, `stats`, `profile`, `io`, `enrich`, or `caching/manager.py`. [BP]

**Required.** Every public function MUST have unit tests for its happy path and for every documented failure mode. Every branch that can be reached from public input SHOULD be covered. [SB] (NumPy: every module should have a corresponding test file; Scientific Python: unit tests cover happy paths and supported usage)

**Isolation.** A unit test constructs its own input and calls the function directly. It does not depend on the class wrapper or the accessor. [BP]

**Data.** Small inline frames are preferred. A frame larger than a few hundred rows belongs in a property or performance test. [BP]

### 3.3 Integration tests

**Purpose.** Pin behavior that crosses module boundaries: `BaseData` → shared function → `CacheManager` → SQLite; accessor → shared function; `JsonFile` → `read_json` → pandas. [BP]

**Required.** Every public method MUST have at least one integration test that reaches it through its public entry point. [BP]

**Files and caches.** Use `tmp_path` for every file and cache directory. Never write to the repository, the user's home, or the default `Settings/Cache Data/Automated` directory. [SB] (PyPA: do not write to package directories during testing)

**Fakes.** External services are replaced with fake modules installed through `monkeypatch` or with injected providers. See §4 A-10. [BP]

### 3.4 API and contract tests

**Purpose.** Pin the public surface so that signatures, docstrings, stubs, and output schemas do not drift. [BP]

**Required coverage.** [BP]

- Every supported public class and function MUST be importable from its documented path. The contract inventory MUST distinguish top-level exports (`bynat`), cleaning exports (`bynat.cleaning`), caching exports (`bynat.caching`), and enrichment exports (`bynat.cleaning.enrich`). A documented path that does not resolve is an API/documentation defect to record and correct; it is not a test exception.
- `inspect.signature` matches the documented parameters, including keyword-only markers. For an unbound accessor method (`inspect.signature(BynatAccessor.method)`), `self` is the first parameter; for a bound accessor method (`inspect.signature(df.bynat.method)`), Python removes `self`. Neither form MUST expose the wrapped frame or internal `cache_manager` parameter.
- Docstrings on `BaseData` match the shared implementation docstrings.
- `bynat/cleaning/accessor.pyi` matches `accessor.py`.
- Output schemas match the documented columns and types (`get_hierarchical_stats`, `profile`, `fill_missing_from`).
- Return contracts match the documented behavior (new object by default; `inplace=True` returns `None` or the documented statistics result).
- The class API and the accessor produce equal results for the same input.

**Current guards.** `tests/test_doc_drift.py` and parts of `tests/test_accessor.py` and `tests/test_hierarchical_stats.py` pin the top-level `bynat` exports, the `bynat.cleaning` class API, and the accessor signatures and docstrings. No test yet pins the documented caching exports (`CacheManager`, `shared_cache_manager`, `CACHE_DIR_ENV_VAR`, `DEFAULT_CACHE_DIR`) or the enrichment default `NominatimGeocoder`; a contract test for those paths is recorded as a Phase 0 item. The caching module's public `resolve_cache_dir` helper is not a documented export and MAY be exercised by that test without entering the contract inventory. New public API MUST extend these guards. [BP]

The package-level `bynat.cleaning` namespace MUST expose only its established class API (`BaseData`, `CsvFile`, and `JsonFile`). Profiling functions and report classes MUST be imported from `bynat.cleaning.profile`, accessor APIs from `bynat.cleaning.accessor`, and loader helpers from `bynat.cleaning.io`. Tests MUST verify each documented path without expanding the package namespace merely for convenience. [BP]

### 3.5 Property-based tests

**Purpose.** Pin invariants that hold across many inputs: row count, index preservation, schema, no mutation, determinism, cache behavior, and statistical identities. [SB] (Hypothesis; SciPy proceedings: property tests found real bugs in NumPy and Astropy that example tests missed)

**Required.** Every transformation in §6 SHOULD have at least one property test stating its central invariant. [RP]

**Tooling.** Hypothesis with the `numpy` extra for array strategies. Tests live beside the module or cross-cutting responsibility they verify and carry the `property` marker. The marker is the test-type classification; it is not a mandatory directory. [BP]

**Target profiles.** Once Phase 1 is adopted, two profiles SHOULD be registered in `tests/conftest.py`: [BP]

| Profile | Use | Settings |
| --- | --- | --- |
| `fast` | Default PR run | `max_examples=25`, `derandomize=True`, `deadline=None` |
| `extended` | Scheduled run | `max_examples=200`, `derandomize=False`, `print_blob=True` |

**Determinism and isolation.** Property tests MUST NOT depend on global state, unmanaged randomness, or unreset filesystem/database state. Hypothesis treats a non-reproducing failure as fatal (`FlakyFailure`). Reset cache directories between examples or use `database=None` where appropriate. [SB] (Hypothesis flaky failures)

**Domain.** Use the most general strategy that still models valid input. Constrain size or variety only after observed slowdowns, and prefer `max_examples` or phases over weakening strategies. [SB] (Hypothesis domain and distribution)

**Deadline.** The default 200 ms deadline is too tight for DataFrame and I/O work. Set `deadline=None` for data-heavy properties rather than weakening assertions. [SB] (Hypothesis settings)

### 3.6 Regression tests

**Purpose.** Prevent a fixed bug from returning. [SB] (NumPy: write the test for every bug found)

**Required.** Every bug fix PR MUST include a test that fails on the pre-fix code and passes on the fixed code. The author SHOULD demonstrate the failure, for example by running the new test against the parent commit, and record that in the PR description. [SB] (Scientific Python: deliberately break the code to confirm the test fails)

**Naming.** `test_<area>_<bug>_regression`, or a name that states the incorrect behavior being prevented. [BP]

**Content.** A regression test asserts the documented behavior, not the bug's exact erroneous output. If the old output was observed and is now changed, the test asserts the new correct output and the CHANGELOG records the change. [BP]

### 3.7 Mutation testing

**Purpose.** Find test gaps that coverage cannot see: a mutant that survives means the suite executes the code but does not check its behavior. [SB] (Cosmic Ray theory)

**Status.** Mutation testing is a periodic diagnostic, not a PR gate. See §7.5 for tooling, scope, and targets. [BP]

### 3.8 Additional testing

**Equivalence tests.** Every optimized implementation MUST have an equivalence test against a reference implementation, kept in `tests/test_equivalence.py`. A clarity reference is written independently for readability, not speed, and MUST NOT share a production helper with the implementation under test: a shared helper can reproduce the defect the test exists to catch. A legacy reference preserves the pre-optimization implementation verbatim apart from the `self` → `df` rename and MAY share a production helper; when that helper could reproduce the defect, an independent clarity reference MUST also exist. [BP] (ROADMAP: performance changes must come with a benchmark and an equivalence test)

**Performance tests.** `benchmarks/` scripts compare the current implementation with the 0.3.0 algorithm and print a table. Numbers are recorded in the PR description, not in the code. A performance change without an equivalence test and a benchmark MUST NOT merge. [BP] (ROADMAP definition of done)

**Optional-dependency tests.** Tests that need an extra use `pytest.importorskip("<module>")` and are exercised in the extras CI job. They MUST NOT fail when the extra is absent. [SB] (PyPA: make optional-dependency tests optional)

**Characterization tests.** When behavior is undocumented and must be pinned before it can be changed, a characterization test records the current output and says so in a comment. It is a stopping point, not a destination: the behavior MUST be documented or corrected later. [BP]

---

## 4. Anti-cheating rules

These rules exist because a test that cannot fail is worse than no test: it creates false confidence and blocks real signal. Each rule gives a rejected pattern and a required pattern. [BP]

### A-1 A test MUST be able to fail

Every test function MUST contain at least one assertion or assertion helper (`assert`, `pytest.raises`, `pytest.warns`, `pytest.deprecated_call`, `pd.testing.assert_*`, `np.testing.assert_*`, or `warnings.catch_warnings()` with `simplefilter("error", ...)` escalating the warnings under test). A test that only calls the code under test is rejected.

**Weak (rejected).** The current shape of `tests/test_enrichment.py::test_translate_conditional_column_accepts_a_generator`:

```python
def test_accepts_a_generator(tmp_path, monkeypatch):
    _install_langdetect(monkeypatch, lambda text: "en")
    frame = pd.DataFrame({"p": ["a"] * 5, "d": list("vwxyz"), "t": ["x"] * 5})
    frame.bynat.with_cache(tmp_path).translate_conditional_column(
        "p", "d", "t", sample_size=2, random_state=np.random.default_rng(3)
    )
```

This is an abridged weak example; it passes whether or not the method works.

**Strong (required).**

```python
def test_accepts_a_generator(tmp_path, monkeypatch):
    _install_langdetect(monkeypatch, lambda text: "ar")
    translator = DictTranslator({value: value.upper() for value in "vwxyz"})
    frame = pd.DataFrame({"p": ["a"] * 5, "d": list("vwxyz"), "t": list("vwxyz")})

    result = frame.bynat.with_cache(tmp_path).translate_conditional_column(
        "p", "d", "t", sample_size=2, random_state=np.random.default_rng(3),
        provider=translator,
    )

    assert result["t"].tolist() == list("VWXYZ")
    assert len(translator.calls) == 5
```

### A-2 Never replace the unit under test

Monkeypatching the function under test, or a helper it calls directly, to return the expected value is rejected. Fake the boundary, not the behavior.

**Weak (rejected).**

```python
def test_fill_missing_returns_expected(monkeypatch):
    monkeypatch.setattr(stats, "fill_missing", lambda *args, **kwargs: expected)
    assert stats.fill_missing(df, "salary") is expected
```

**Strong (required).** Call the real function. Replace only the optional dependency or the external service:

```python
def test_translate_uses_provider(tmp_path):
    translator = DictTranslator({"مكتمل": "Completed"})
    result = pd.DataFrame({"status": ["مكتمل"]}).bynat.with_cache(tmp_path).translate_categorical_column(
        "status", provider=translator
    )
    assert result["status"].tolist() == ["Completed"]
```

### A-3 Assert the contract, not the implementation

Tests assert observable inputs and outputs. Private state, internal call counts, and source structure are not contracts unless the contract is about them.

**Weak (rejected).**

```python
assert manager._baselines["translate"] == {"status": {"pending": "Pending"}}
assert groupby_calls == 4
```

**Strong (required).**

```python
assert result["status"].tolist() == ["Pending"]
```

**Narrow exceptions.** [BP]

- `tests/test_caching.py` MAY assert cache internals because the cache is the unit under test.
- Provider call counts MAY be asserted where call count is the documented contract, for example "one download per currency" or "translate each unique value once".
- AST/source guard tests MAY enforce project principles such as "no row-wise iteration", with a comment naming the principle. `tests/test_hierarchical_stats.py::test_get_hierarchical_stats_has_no_nested_functions_or_apply_lambda` is the model. Such a test does not replace behavior tests.

### A-4 No blanket exception swallowing

`except Exception: pass`, bare `except:`, and `except Exception:` with no assertion are rejected. Catch the specific exception and assert what matters.

**Weak (rejected).**

```python
try:
    result = frame.fill_missing("salary")
except Exception:
    pass
```

**Strong (required).**

```python
with pytest.raises(ValueError, match="Invalid strategy"):
    frame.fill_missing("salary", strategy="sum")
```

### A-5 Skips and xfails need a reason

A skip without a reason, or an `xfail` without a linked issue, is rejected. `xfail` MUST be strict so that an unexpected pass fails the suite. [SB] (pytest skipping: `strict=True` makes XPASS fail)

**Weak (rejected).**

```python
@pytest.mark.skip
def test_something():
    ...

@pytest.mark.xfail
def test_known_bug():
    ...
```

**Strong (required).**

```python
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only fixture; see issue #123")
def test_posix_path():
    ...

@pytest.mark.xfail(strict=True, reason="pandas 2 merge mishandles NaN group keys; see issue #45")
def test_legacy_comparison():
    ...
```

Optional dependencies use `pytest.importorskip("<module>")`, not `skipif(importlib.util.find_spec(...))`. [SB] (pytest skipping; PyPA)

### A-6 Do not hide warnings

`@pytest.mark.filterwarnings("ignore")` on a test, or `warnings.simplefilter("ignore")` around a call whose warnings are the subject, is rejected. Assert warnings with `pytest.warns` or prove their absence by escalating to an error. [SB] (pytest warnings; PyPA: assert warnings with `pytest.warns()`, not `pytest.raises()`)

**Weak (rejected).**

```python
@pytest.mark.filterwarnings("ignore")
def test_deprecation():
    frame.drop_by_substring("name", inplace=True)
```

**Strong (required).**

```python
def test_inplace_does_not_warn(tmp_path):
    frame = BaseData({"name": ["a"]}, cache_dir=tmp_path)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert frame.drop_by_substring("name", inplace=True) is None
```

`tests/test_inplace_deprecation.py` is the model for warning contracts.

### A-7 Determinism

Unseeded randomness, clock reads, and hash-order iteration in assertions are rejected. Seed every generator or pass a seeded `numpy` generator. [SB] (NumPy: seed random data for determinism; Hypothesis: unmanaged randomness causes flakiness)

**Weak (rejected).**

```python
values = np.random.lognormal(10, 1, size=100)
```

**Strong (required).**

```python
rng = np.random.default_rng(0)
values = rng.lognormal(10, 1, size=100)
```

Where order is not contractual, sort before comparing. Where order is contractual, assert it explicitly.

### A-8 Independence

Tests MUST NOT share mutable state. Module-level frames that a test mutates, cache directories shared between tests, and manual `sys.modules` edits without `monkeypatch` are rejected. [SB] (pytest fixtures; Hypothesis flaky failures)

**Weak (rejected).**

```python
FRAME = pd.DataFrame({"g": ["a", "b"], "v": [1.0, None]})

def test_fill_a():
    FRAME.fill_missing("v", hierarchy_cols="g", inplace=True)
```

**Strong (required).**

```python
def test_fill_a(tmp_path):
    frame = BaseData({"g": ["a", "b"], "v": [1.0, None]}, cache_dir=tmp_path)
    result = frame.fill_missing("v", hierarchy_cols="g")
    assert pd.isna(result["v"].iloc[1])
```

Parametrized values are passed as-is: mutable parameter values mutated by one test are shared with later calls. Use fresh values per parameter or immutable values. [SB] (pytest parametrize)

### A-9 No version overfit

Exact floating-point literals from a specific pandas or NumPy version, exact dtype strings where the contract is "numeric", and exact log messages in behavior tests are rejected. [SB] (PyPA: avoid exact floating-point results and platform details)

**Weak (rejected).**

```python
assert result["salary"].tolist() == [0.30000000000000004]
assert result.dtypes["salary"] == "int64"
```

**Strong (required).**

```python
np.testing.assert_allclose(result["salary"].to_numpy(), [0.3], rtol=1e-7, atol=0)
assert pd.api.types.is_numeric_dtype(result["salary"])
```

Warning-contract tests MAY match log text, but SHOULD match a substring or regex rather than the full message list. [BP]

### A-10 No network, secrets, or user files

Tests MUST NOT call external services, read credentials, or write outside `tmp_path`. Real providers are replaced with fakes or injected providers. [SB] (PyPA: make the suite work offline; ROADMAP principle 5)

**Weak (rejected).**

```python
def test_translate_real():
    result = frame.bynat.translate_categorical_column("status")
```

**Strong (required).**

```python
def test_translate_with_fake_provider(tmp_path):
    translator = DictTranslator({"مكتمل": "Completed"})
    result = frame.bynat.with_cache(tmp_path).translate_categorical_column(
        "status", provider=translator
    )
    assert translator.calls == [("مكتمل", "en")]
```

`tests/test_integrations.py` and `tests/test_enrichment.py` are the models.

### A-11 No test-only hooks in production code

Adding a `_test_mode` flag, a debug branch, or a special case to production code so a test can pass is rejected. Use the existing injection points: `provider=`, `cache_manager=`, `with_cache(...)`, and monkeypatching the optional dependency module. [BP]

### A-12 Do not weaken existing tests

Deleting assertions, broadening `assert_frame_equal` flags, adding `check_dtype=False`, or adding exclusions to make a change pass is rejected. When behavior changes intentionally, update the contract test in the same PR and record the change in `CHANGELOG.md`. [BP]

**Weak (rejected).**

```python
pd.testing.assert_frame_equal(result, expected, check_dtype=False, check_index_type=False)
```

**Strong (required).** Use the defaults. Relax one flag at a time, with a comment explaining why the difference is correct.

---

## 5. DataFrame cases and pandas.testing assertion standards

`pandas.testing` and `numpy.testing` are the only normative comparison helpers for frame, series, index, and array results. `DataFrame.equals` MAY be used as a secondary sanity check, but MUST NOT be the only assertion. [BP]

### 5.1 Required DataFrame cases

Every public transformation covered by this document MUST cover the cases that apply. "Applicable" means the case can reach the code path; a case that the API rejects before touching data (for example, a duplicate column name in `fill_missing_from`) is covered by the validation test instead. [BP]

| Case | What can go wrong | bynat examples | Required check |
| --- | --- | --- | --- |
| Empty frame (0 rows) | groupby/quantile on empty input; index operations | `fill_missing`, `get_hierarchical_stats`, `profile` | Returns an empty result with the documented schema; no exception |
| Frame with 0 columns | Column selection; `valid_cols` | `fill_missing`, `profile` | No exception; warning where documented |
| All-null target column | median/mean/mode of no observations | `fill_missing` | Stays all-NaN unless a global statistic exists; `fill_missing_from` is covered by FF-22 |
| All-null group | Group with no observations | `fill_missing` | Falls through; stays NaN by default |
| Single row | Degenerate quantiles; `min_samples` | `handle_outliers` | No outlier flagged unless the bounds allow it |
| Single unique group | Hierarchy relaxation is a no-op | `handle_outliers` | Same result as a one-level hierarchy |
| Duplicate rows | Dedupe semantics; `keep='first'` | `profile`, `save_to_json(append=True)` | Documented counts and survivors |
| Duplicate index labels | Label-based drop removes both twins | `drop_outliers` | Rows dropped by position; twins safe |
| Named index | Index name lost in merge or reset | `fill_missing_from`, `handle_outliers` | `assert_index_equal` |
| MultiIndex | Levels lost in merge or reset | `fill_missing_from` | Index preserved exactly |
| NaN hierarchy keys | `groupby` drops NaN by default | All hierarchy methods | Null keys remain valid groups (`dropna=False`) |
| Categorical hierarchy | Unobserved categories change grouping | `handle_outliers` | `observed=True` semantics |
| Mixed dtypes | Numeric strategy on an object column | `fill_missing_from` | `TypeError` where documented |
| Nullable dtypes (`Int64`, `Float64`, `string`, `boolean`) | `pd.NA` propagation and numeric-strategy validation | `profile`, `fill_missing` | Match the documented pandas result: numeric nullable dtypes preserve valid fills; non-numeric targets with numeric strategies raise when applicable |
| `datetime` / `datetimetz` | Serialization; timezone handling | `save_to_json`, `save_to_sql` | Documented formatting and tz normalization |
| Unhashable cells (list, dict, set) | `duplicated()` raises `TypeError` | `profile`, `save_to_json` | Compared by value |
| Non-string column names | Rename/reorder assumptions | `reorder_columns` | Names preserved; methods requiring string operations MUST reject unsupported labels explicitly |
| Duplicate column names | Ambiguous selection | `fill_missing_from` | `ValueError` |
| Unicode text | Encoding; case folding | `extract_keywords`, `translate_*` | Values preserved exactly |
| Large frame (≥10k rows) | Performance; chunking | benchmarks | Equivalence plus a timing report |

### 5.2 Assertion helpers

| Helper | Use for | Default strictness | Policy |
| --- | --- | --- | --- |
| `pd.testing.assert_frame_equal` | Frame results | dtype, index type, column order, frequency | Use defaults. Relax one flag at a time with a comment. [SB] (pandas testing) |
| `pd.testing.assert_series_equal` | A single column | dtype, index | Same |
| `pd.testing.assert_index_equal` | Index preservation | Exact type and values | Same |
| `numpy.testing.assert_allclose` | Numeric arrays | `rtol=1e-7`, `atol=0`, `equal_nan=True` | Set `rtol`/`atol` explicitly. Use `strict=True` when dtype or shape matters. [SB] (NumPy testing guidelines) |
| `numpy.testing.assert_array_equal` | Exact arrays | Exact | Use for integers and categories |
| `pytest.approx` | Scalar floats | `rel=1e-6` | Prefer the NumPy helper for arrays. [SB] (pytest assert) |
| `assert result is not frame` | Mutation contract | Identity | Required for frame-to-frame transformations |
| `type(result) is type(frame)` | Subclass contract | Exact input subclass | Require preserved subclass identity; use `isinstance(result, BaseData)` only when the contract permits any supported subclass |
| `DataFrame.equals` | Quick sanity | dtype-sensitive, index-name-insensitive | Never the only assertion |

**Why `.equals()` is not enough.** `DataFrame.equals` ignores the index name, so it can hide index drift. `pd.testing.assert_frame_equal` checks index type and name by default. Prefer the pandas helper. [BP]

**Comparing a `BaseData` result.** Assert that the result preserves the input subclass, then compare values:

```python
assert type(result) is type(frame)
pd.testing.assert_frame_equal(pd.DataFrame(result), expected)
```

**Errors.** Use `pytest.raises` with `match=` targeting the intended message. Use `excinfo.type is X` when the exact type matters; `pytest.raises` matches subclasses. [SB] (pytest assert)

**Warnings.** Use `pytest.warns(DeprecationWarning, match=...)` or `warnings.catch_warnings()` with `simplefilter("error", ...)`. Do not use `pytest.raises` for warnings. [SB] (PyPA; pytest warnings)

---

## 6. Transformation-specific requirements

### 6.1 Shared requirements

The requirements in this subsection apply to public frame-to-frame transformations: column, text, statistics, enrichment, and frame-returning I/O methods reached through `BaseData` or the accessor. They do not apply unchanged to report-producing `profile`/`get_hierarchical_stats`, loaders (`read_json`, `read_csv`), or writers (`save_to_json`, `save_to_sql`); those operations require their own return, schema, persistence, and non-mutation assertions. [BP]

- **S-1 Input immutability.** `before = df.copy(deep=True)`; call the method; `pd.testing.assert_frame_equal(df, before)`.
- **S-2 New object.** `assert result is not df`. Early exits return an independent copy, not the original object. [SB] (ROADMAP API-02)
- **S-3 Index preservation.** `pd.testing.assert_index_equal(result.index, df.index)`, except for methods documented to reset or reconstruct the index, including `split_list_objects(explode_rows=True)` and `melt_transform_pivot`.
- **S-4 Return contract.** For the class-based API, the default returns a new frame; `inplace=True` returns `None` (or the documented statistics result); `get_hierarchical_stats=True` returns `(result, stats)`; `inplace=True` with statistics returns the statistics directly. The target contract for shared functions and accessor methods is to reject `inplace` rather than silently accept it. The current variadic methods `melt_transform_pivot`, `truncate_after_substring`, `extract_keywords`, and `split_list_objects` require an explicit Phase 0 validation decision because their `**kwargs` paths currently absorb or mis-handle that name. [SB] (ROADMAP API-02, D-03) [BP]
- **S-5 Class and accessor agreement.** The class method and the accessor produce equal values for the same input. [BP]
- **S-6 No unexpected warnings.** At minimum, valid input MUST NOT raise `DeprecationWarning`; test with `warnings.simplefilter("error", DeprecationWarning)`. Other warnings are reviewed case by case. [BP]
- **S-7 Lenient no-op inputs.** For methods whose public contract documents lenient handling, an empty frame, a missing optional column, or a frame with nothing to change returns an independent copy. Methods with required inputs, such as `melt_transform_pivot` with a missing `id_vars` or `value_vars`, MUST raise their documented validation error instead. A warning is required only where the public contract documents one. [BP]

Rows in the following tables that mention `inplace=True` apply only to `BaseData`, `JsonFile`, and `CsvFile`; the shared functions and pandas accessor have no `inplace` parameter. [BP]

### 6.2 `fill_missing`

| ID | Required case | Expected behavior | Assertion |
| --- | --- | --- | --- |
| FM-1 | Strategies `median`, `mean`, `mode`, and the alias `mod` | Correct fill per strategy | Exact values |
| FM-2 | Uppercase strategy name | Normalized (`str(strategy).lower()`) | Same result as lowercase |
| FM-3 | Unknown strategy | `ValueError` naming the strategy | `pytest.raises(ValueError, match="Invalid strategy")` |
| FM-4 | `min_samples` default 1 | A single observation supplies the statistic | Exact fill |
| FM-5 | `min_samples` boundary N and N−1 | N fills; N−1 falls through | Exact fill and NaN |
| FM-6 | `min_samples` invalid: `True`, `0`, `-1`, `"2"` | `ValueError` | `pytest.raises` |
| FM-7 | `hierarchy_cols=None`, `fallback_global=False` | Nothing filled | All NaN preserved |
| FM-8 | `hierarchy_cols=None`, `fallback_global=True` | Column-wide fill from the original frame | Exact fill |
| FM-9 | `hierarchy_cols` as a string | Treated as a one-item list | Same result as the list form |
| FM-10 | Missing hierarchy columns | Ignored; remaining valid columns used | Result equals the valid-column run |
| FM-11 | No valid target columns remain | Warning and unchanged copy | `caplog` plus `assert_frame_equal` |
| FM-11a | Some target columns missing, others valid | Missing ones skipped silently; valid ones filled | Exact fills and unchanged missing columns |
| FM-12 | No missing values | Unchanged copy, no fill | `assert_frame_equal` |
| FM-13 | All-NaN column | Stays all-NaN by default; `fallback_global=True` may fill it when a statistic exists | `isna().all()` or exact fallback values |
| FM-14 | All-NaN group | Falls through to coarser levels | NaN by default |
| FM-15 | Multi-level hierarchy | Most specific level first, then coarser | Exact fills per level |
| FM-16 | Coarser-level statistics | Computed from the original frame, not from already-filled values | Hand-computed expected values |
| FM-17 | `fallback_global=True` after exhaustion | Remaining NaN filled with the column-wide statistic | Exact fill |
| FM-18 | Mode tie-breaking | Deterministic | Repeated runs equal |
| FM-19 | Null hierarchy keys | Valid groups | Exact fills |
| FM-20 | `get_hierarchical_stats=True` | Returns `(result, stats)`; stats from the original data | Type, schema, and values |
| FM-21 | `inplace=True` with statistics | Returns stats only; mutates the original | Type and mutation |
| FM-22 | Index preservation: named, duplicate, MultiIndex | Index unchanged | `assert_index_equal` |
| FM-23 | Non-numeric target with at least one non-null value and numeric `median`/`mean` strategy | pandas `TypeError` on a hierarchy path or `fallback_global=True`; an all-NaN non-numeric target does not raise | `pytest.raises(TypeError)` plus an all-NaN control |
| FM-24 | Input immutability | Original unchanged | S-1 |

### 6.3 `fill_missing_from`

| ID | Required case | Expected behavior | Assertion |
| --- | --- | --- | --- |
| FF-1 | Column-wide imputation with `hierarchy_cols=None` and `fallback_global=True` | Exact fill from the reference statistic | Exact values |
| FF-2 | **Statistical leakage** | Target values never influence statistics | Hand-computed expected values from the reference only, with extreme target values that would change the statistic if leaked |
| FF-3 | **Reference immutability** | Reference unchanged | `assert_frame_equal(dataset, dataset_copy)` |
| FF-4 | Target index, row order, un-imputed values | Preserved | `assert_index_equal` and exact values |
| FF-5 | `match_cols` for targets and hierarchy | Mapping applied to both | Exact fills |
| FF-6 | `match_cols` invalid: non-dict, non-string keys/values, empty strings, missing columns | `TypeError` or `ValueError` | `pytest.raises` |
| FF-7 | `targets` keyword alternative | Same result as positional targets | Exact fills |
| FF-8 | Duplicate targets | Deduplicated | Same result as unique targets |
| FF-9 | Multi-level hierarchy fallback | Full → drop last → … → global | Exact fills per level |
| FF-10 | `min_samples` boundary | N fills; N−1 falls through | Exact fill and NaN |
| FF-11 | **Unseen group** in the target | Falls through to coarser levels, then `fallback_global` or NaN | Exact fill or NaN |
| FF-12 | Reference group with insufficient samples | Does not supply a statistic | Falls through |
| FF-13 | No valid target columns remain in the target frame | Skipped with warning | Warning plus unchanged copy |
| FF-13a | Some target columns missing, others valid | Missing ones skipped silently; valid ones imputed | Exact fills and unchanged missing columns |
| FF-14 | Missing reference column for a valid target | `ValueError` | `pytest.raises` |
| FF-15 | Missing hierarchy column in target or reference | `ValueError` | `pytest.raises` |
| FF-16 | Target and hierarchy overlap | `ValueError` | `pytest.raises` |
| FF-17 | Duplicate columns in target or reference | `ValueError` | `pytest.raises` |
| FF-18 | `dataset` `None`, non-DataFrame, or empty | `ValueError`/`TypeError` | `pytest.raises` |
| FF-19 | Non-numeric reference column, or non-numeric target column with at least one non-null value, with a numeric (`median`/`mean`) strategy | `TypeError`; an all-NaN target column is exempt | `pytest.raises(TypeError)` plus the all-NaN control |
| FF-20 | Empty target frame | Empty result, schema preserved | `empty` and columns |
| FF-21 | No missing values | Unchanged copy | `assert_frame_equal` |
| FF-22 | All-missing target | Filled where a matching reference group has at least `min_samples` non-null observations, or globally when `fallback_global=True`; otherwise remains NaN | Exact fills and NaN cases |
| FF-23 | Numeric all-null reference column with a numeric strategy | Stays NaN; a non-numeric all-null reference column with `median`/`mean` raises `TypeError`, while `mode` remains a separate supported case | `isna().all()` plus the numeric-strategy error control |
| FF-24 | `get_hierarchical_stats=True` | Stats from the reference; `match_cols` reverse-mapped | Schema and values |
| FF-25 | `inplace=True` | Mutates and returns `None` (or stats) | Identity and mutation |
| FF-26 | BaseData and accessor agreement | Equal values | `assert_frame_equal` |
| FF-27 | Index preservation: named, duplicate, MultiIndex | Index unchanged | `assert_index_equal` |

### 6.4 `handle_outliers`

| ID | Required case | Expected behavior | Assertion |
| --- | --- | --- | --- |
| HO-1 | `min_samples` default 5 | Groups below 5 are not evaluated | Exact mask |
| HO-2 | Full hierarchy first, then relax | Most specific level first | Exact fills |
| HO-3 | Replaced values excluded from later quartiles | A value that is an outlier only because an earlier outlier is still present is not flagged at a coarser level | Hand-computed mask |
| HO-4 | Groups below `min_samples` | Not evaluated; fall through | Exact mask |
| HO-5 | Outliers replaced with NaN | Row count and index preserved | `assert_frame_equal` on index |
| HO-6 | Missing target columns | Skipped | Unchanged copy |
| HO-7 | No hierarchy columns (`None` or empty) | Warning and unchanged copy; a named hierarchy column missing from the frame raises `KeyError` | `caplog` plus `assert_frame_equal`, or `pytest.raises(KeyError)` |
| HO-8 | Multiple target columns | Each evaluated independently | Union of masks |
| HO-9 | `get_hierarchical_stats=True` | Stats from the original data before replacement | Schema and values |
| HO-10 | Null hierarchy keys | Valid groups | Exact mask |
| HO-11 | Categorical hierarchy | `observed=True` semantics | Exact mask |
| HO-12 | Equivalence with a brute-force reference | Identical masks on randomized frames | `assert_frame_equal` |
| HO-13 | No merge in the IQR path | Performance invariant | Guard test (monkeypatch `DataFrame.merge` to fail) |
| HO-14 | Duplicate index labels | Index preserved | `assert_index_equal` |
| HO-15 | Input immutability | Original unchanged | S-1 |

### 6.5 `drop_outliers`

| ID | Required case | Expected behavior | Assertion |
| --- | --- | --- | --- |
| DO-1 | Same grouping and IQR rules as `handle_outliers` | Same rules, but `handle_outliers` excludes replaced values from later quartiles while `drop_outliers` keeps the original values during its scan | Compare each method to its independently derived expected mask; compare directly only for single-level hierarchies |
| DO-2 | Rows dropped by position | Duplicate index labels do not remove twins | Exact surviving index |
| DO-3 | Union across targets | A row is dropped if any target flags it | Exact survivors |
| DO-4 | Index preservation | Surviving index equals the input index subset | `assert_index_equal` |
| DO-5 | All rows dropped | Empty frame with the same columns | `empty` and columns |
| DO-6 | No hierarchy columns (`None` or empty) | Warning and unchanged copy; a named hierarchy column missing from the frame raises `KeyError` | `caplog` plus `assert_frame_equal`, or `pytest.raises(KeyError)` |
| DO-7 | `get_hierarchical_stats=True` | Stats from the original data before the drop | Schema and values |
| DO-8 | Input immutability | Original unchanged | S-1 |

### 6.6 Hierarchical fallbacks (cross-cutting)

- **HF-1** The full hierarchy is evaluated first; the last grouping column is removed at each level. [BP]
- **HF-2** `min_samples` counts non-null observations in the group. [BP]
- **HF-3** A group that is absent or has too few observations falls through to the next coarser level. It never raises for data reasons. [BP]
- **HF-4** `fallback_global=True` applies only after the hierarchy is exhausted. [BP]
- **HF-5** Filled values do not affect coarser-level statistics: `fill_missing` computes from the original frame, and `fill_missing_from` from the reference. Outlier handling is different: `handle_outliers` excludes values it replaces before later levels, while `drop_outliers` keeps the original values during its scan. [BP]
- **HF-6** Null hierarchy values remain valid grouping keys at every level. [BP]

### 6.7 `min_samples`

- **MS-1** Defaults: `fill_missing` and `fill_missing_from` default to 1; `handle_outliers` and `drop_outliers` default to 5. [BP]
- **MS-2** Boundary: a group with exactly `min_samples` observations supplies a statistic; `min_samples − 1` does not. [BP]
- **MS-3** For `fill_missing` and `fill_missing_from`, invalid values (`True`, `0`, negative numbers, floats, and strings) raise `ValueError`. [BP]
- **MS-3a** `handle_outliers` and `drop_outliers` MUST define and test the same invalid-input contract before their validation gate is adopted. The current implementation does not consistently validate `min_samples`; this is a Phase 0 implementation/test gap, not permission to write weak or implementation-dependent tests. [BP]
- **MS-4** Only non-null observations count toward the threshold. [BP]

### 6.8 Unseen groups

- **UG-1** `fill_missing_from`: a group present in the target but absent from the reference. [BP]
- **UG-2** `fill_missing`: a group with no observed target values. [BP]
- **UG-3** Outlier methods: a group below `min_samples`. [BP]
- **UG-4** Behavior: fall through to a coarser level; then to `fallback_global` when enabled; otherwise leave NaN. Never raise because of data. [BP]

### 6.9 Missing keys

The asymmetry below is documented behavior and MUST be pinned by tests. The table covers `fill_missing`, `fill_missing_from`, and `get_hierarchical_stats`; outlier methods have separate missing-hierarchy behavior in HO-7 and DO-6. [BP]

| Situation | `fill_missing` | `fill_missing_from` | `get_hierarchical_stats` |
| --- | --- | --- | --- |
| No valid target columns remain | Warning; unchanged copy | Warning; unchanged copy | Warning; empty result |
| Some target columns missing, others valid | Missing skipped silently | Missing skipped silently | Missing skipped silently |
| Target column missing from the reference | Not applicable | `ValueError` | Not applicable |
| Hierarchy column missing from the frame | Ignored | `ValueError` | Ignored |
| Hierarchy column missing from the reference | Not applicable | `ValueError` | Not applicable |
| `match_cols` references a missing column | Not applicable | `ValueError` | Not applicable |

### 6.10 Mutation and leakage

- **ML-1** Every frame-to-frame transformation returns a new object; the input is unchanged. Report, loader, writer, and cache operations have their own return and persistence contracts. [BP]
- **ML-2** On the class-based API, `inplace=True` mutates the original and returns `None` (or the documented statistics result). The target contract requires shared functions and the accessor to reject `inplace`; current variadic methods that absorb the name are a Phase 0 gap. Results of later operations are not aliased to the mutated object. [BP]
- **ML-3** The accessor never mutates the frame it wraps. [BP]
- **ML-4** Cache isolation: different cache directories do not share values; the same directory reuses values. Cache keys are normalized (`1`, `1.0`, and `"1"` collide by design); tests pin the documented normalization rather than assuming uniqueness. [BP]
- **ML-5** `fill_missing_from` leaks nothing from the target into the statistics and never modifies the reference. [BP]
- **ML-6** Enrichment cache semantics are tested per provider: exceptions are never cached; translation does not cache falsy results; geocoding and currency may cache not-found results as `None`; NLP uses its required multi-bucket cache identity and caches valid empty-list outcomes; successful results are cached. [BP]
- **ML-7** `clear_cache_for_column` deletes only the named bucket and preserves unrelated buckets and functions. [BP]

---

## 7. Coverage, mutation, and quality metrics

### 7.1 What is measured

| Metric | Tool | What it tells you | What it does not tell you |
| --- | --- | --- | --- |
| Statement coverage | coverage.py | Which lines executed | Whether the lines were checked |
| Branch coverage | coverage.py | Which conditional destinations executed | Whether both outcomes were asserted |
| Mutation score | Cosmic Ray | Which behavior changes the suite detects | That the surviving code is correct |
| Property invariants | Hypothesis | Which invariants hold over generated inputs | That the invariants are complete |
| Assertion density | custom count | Whether tests assert enough | Whether the assertions are correct |

### 7.2 Tools and configuration

**Coverage.** coverage.py with pytest-cov. The target configuration belongs in `pyproject.toml`: [BP]

```toml
[tool.coverage.run]
branch = true
source = ["bynat"]
dynamic_context = "test_function"

[tool.coverage.report]
precision = 1
exclude_also = [
    "if TYPE_CHECKING:",
    "pragma: no cover",
]
```

Command: `python -m pytest --cov=bynat --cov-branch --cov-report=term-missing --cov-report=xml`. [SB] (coverage.py config; pytest-cov config)

**Branch coverage on Python 3.13.** coverage.py's `sysmon` core does not support branch coverage on Python 3.12/3.13 and does not support dynamic contexts. The CI matrix includes 3.13, so coverage MUST run on the default `ctrace` core there, or on 3.11 only. [SB] (coverage.py config caveat)

**Mutation.** Cosmic Ray, configured with a session database and `pytest -x` so one failing test kills a mutant. [SB] (Cosmic Ray concepts)

**Property tests.** The target Hypothesis profiles are registered in `tests/conftest.py` after Phase 1; the current repository does not yet contain that file. [BP]

### 7.3 Targets (policy)

Targets are floors, not quality proofs. They are adopted phase by phase in §12; until a phase is adopted, the current value is the floor. [BP]

| Phase | Statement coverage | Branch coverage | Core module statement | Mutation score | Gate |
| --- | --- | --- | --- | --- | --- |
| Phase 1 | Baseline (no decrease) | Baseline | Baseline | Not measured | No gate |
| Phase 2 | ≥ 80% | ≥ 75% | ≥ 90% | Advisory | Coverage gate at baseline |
| Phase 3 | ≥ 85% | ≥ 80% | ≥ 95% | ≥ 70% killed | Coverage gate at target |
| Phase 4 | ≥ 90% | ≥ 85% | ≥ 98% | ≥ 80% killed | Coverage gate at target; mutation advisory |

Core modules: `bynat/cleaning/stats.py`, `bynat/caching/manager.py`, `bynat/cleaning/enrich/engine.py`. [BP]

**Justification.**

- **Why not 100%.** coverage.py measures execution, not assertions; pytest's own typing guide gives a 100%-coverage example that misses a real bug. Defensive branches, optional-dependency paths, and impossible states cannot all be covered without writing tests for states that cannot occur. [SB] (pytest typing guide; coverage.py)
- **Why branch coverage.** Statement coverage hides untested conditional paths. Branch coverage catches them. Intentional partial branches are marked with `# pragma: no branch`. [SB] (coverage.py branch coverage)
- **Why higher targets for core modules.** `stats.py`, `manager.py`, and `engine.py` carry the data-safety and caching logic where a silent defect is most expensive. [BP]
- **Why mutation is advisory at first.** Mutation is expensive: Cosmic Ray's own example extrapolates a 10-second suite with 1000 mutants to about 2.7 hours. Equivalent mutants distort the score, and tool behavior differs materially, so scores are not comparable across tools. A bounded, occasional run gives signal without blocking merges. [SB] (Cosmic Ray tutorial; SLR cost reduction; ACM tool comparison)
- **Why a ratchet.** A threshold that jumps to a target the suite has not reached blocks all work. The threshold rises only after the corresponding tests exist. [BP]

### 7.4 Exclusions

Coverage exclusions are allowed only for code that cannot be executed by design. [SB] (coverage.py excluding)

**Allowed.**

- `if TYPE_CHECKING:` blocks.
- `pragma: no cover` on a defensive branch that guards an impossible state, with a comment saying why it is impossible.
- `pragma: no branch` on an intentional partial branch, with a comment.

**Rejected.**

- Broad patterns such as `raise`, `...`, or `pass`, which over-exclude real gaps. [SB] (coverage.py excluding: patterns only need to match part of a line)
- Excluding a module because it is hard to test. The correct response is a test or a recorded, reviewed decision.
- `exclude_lines` in place of `exclude_also`: `exclude_also` preserves the defaults, `exclude_lines` replaces them. [SB] (coverage.py excluding)

Every exclusion MUST be reviewed in the PR that adds it. [BP]

### 7.5 Mutation testing

**Current status.** The policy below is the target, not the current repository state: cosmic-ray and mutmut are not declared in the `dev` extra, no Cosmic Ray session config exists, and no CI job runs either tool. The tooling and configuration are added in Phase 3. [BP]

**Tool.** Cosmic Ray is the primary tool: it is pure Python and uses restartable SQLite sessions. Run it on Ubuntu or Windows where the selected version supports the repository's environment. [SB] (Cosmic Ray concepts)

**Windows and mutmut.** mutmut requires fork support and must run inside WSL on Windows. It is a secondary tool, used on Ubuntu or under WSL, never as a Windows-only requirement. [SB] (mutmut documentation)

**Scope.** Start with `bynat/cleaning/stats.py`, `bynat/cleaning/enrich/engine.py`, and `bynat/caching/manager.py`. Expand only after the first triage. [BP]

**Workflow.** [SB] (Cosmic Ray tutorial)

1. The baseline suite MUST pass on unmutated code.
2. Commit before `exec`; mutations are applied on disk and a failed undo can leave mutated code behind.
3. `cosmic-ray init <config.toml> <session.sqlite>`; `cosmic-ray exec <config.toml> <session.sqlite>`; `cr-report <session.sqlite>`.
4. Triage every survivor as one of: missing test, equivalent mutant, or accepted risk. Record the decision.

**Score.** `MS = K / (M − E)`, where `K` is killed mutants, `M` total mutants, and `E` equivalent mutants. Report killed, survived, equivalent, and incompetent mutants separately. Never compare scores across tools. [SB] (SLR cost reduction; ACM tool comparison)

**Timing.** Weekly or before a release, on Ubuntu or Windows. Results are uploaded as an artifact and are advisory. [BP]

### 7.6 Property-test invariants

At minimum, property tests SHOULD state these invariants for every transformation that applies: [BP]

- The row count changes only where documented (`drop_outliers`, `split_list_objects(explode_rows=True)`, and `melt_transform_pivot`).
- The index is preserved except where documented (`split_list_objects(explode_rows=True)` and `melt_transform_pivot`).
- The input frame is unchanged.
- The output schema matches the documented columns and types.
- Repeated calls with the same seed produce the same result.
- A transformation followed by its inverse (where one exists) restores the original values.

---

## 8. Architecture and organization

### 8.1 Layout

The current layout is a flat root `tests/` directory with 15 test files and `tests/conftest.py`; it does not yet contain the target hierarchical structure, shared test infrastructure, or marker configuration. The following is the authoritative target hierarchical layout after the phased additions in §12 and the migration plan in §8.9; paths that do not yet exist MUST NOT be described as current state. [BP]

| Path | Purpose |
| --- | --- |
| `tests/conftest.py` | Root suite-wide configuration and genuinely suite-wide fixtures; marker registration and Hypothesis profiles are future Phase 1 additions |
| `tests/modules/<module>/` | Module-owned unit and component-level integration tests (e.g. `caching`, `columns`, `text`, `stats`, `profile`, `io`, `enrichment`) |
| `tests/cross_cutting/<topic>/` | Topic-oriented cross-cutting tests: class contracts, parity, doc drift, equivalence, multi-step workflows, invariant properties |
| `tests/shared/` | Illustrative home for genuinely reusable infrastructure when distinct-domain reuse is verified; no current shared file is prescribed |
| `benchmarks/` | Performance benchmark scripts with equivalence checks against reference implementations |

**Splitting rule.** When a test file exceeds roughly 800 lines or the suite exceeds roughly 2000 collected tests, new tests go into topic-named files rather than appending to the largest file. The rule applies to every test file, current and new, across both `tests/modules/` and `tests/cross_cutting/`. Two current files exceed it: `tests/test_caching.py` (1,774 lines) and `tests/test_profile.py` (857 lines). They are recorded as target-state violations in §8.9, not exceptions: new tests MUST NOT be appended to them, and the §8.9 migration plan brings each below the threshold. [BP]

### 8.2 Naming

- Test functions: `test_<module>_<behavior>_<condition>`. The name states the behavior and the condition, not the implementation. [BP]
- New test functions MUST NOT have docstrings. Use a comment when the intent is not obvious. This keeps verbose output readable. [SB] (NumPy testing guidelines)
- Existing docstrings are grandfathered; do not mass-remove them. [BP]
- Parametrize IDs MUST be readable: use `pytest.param(value, id="...")` instead of relying on pandas object representations. [SB] (pyOpenSci)

### 8.3 Fixtures

- Fixtures are function-scoped unless there is a measured reason for a wider scope. [BP]
- One state-changing action per fixture, bundled with its own teardown, so a failure cannot leave state behind. [SB] (pytest fixtures)
- Yield fixtures are the preferred teardown mechanism. [SB] (pytest fixtures)
- `tmp_path` is the only filesystem location tests write to. [BP]
- No fixture mutates a module-level object. [BP]

**Conftest scoping.** [BP]
- Root `tests/conftest.py` is reserved for suite-wide configuration and fixtures genuinely applicable to the whole suite. The current file contains only the `sys.path` shim; marker registration, Hypothesis profiles, and any global safety fixture are future additions only when separately justified and adopted.
- Module-local `conftest.py` files (e.g. `tests/modules/caching/conftest.py` or `tests/modules/enrichment/conftest.py`) are permitted only where justified by module-scoped fixtures (such as isolated database handles or mock provider lifecycles). Modules that require no special fixtures MUST NOT introduce a local `conftest.py`.
- Fixtures used by only one test file MUST remain file-local.

### 8.4 Parametrization

- Use `@pytest.mark.parametrize` instead of sharing mutable fixtures across cases. [SB] (Scientific Python pytest guide)
- Parameter values are passed as-is; mutable values mutated by a test are shared with later calls. Use fresh values or immutable values. [SB] (pytest parametrize)
- Empty parameter sets are controlled explicitly; for bynat, an unexpectedly empty parameter set is a test-design defect and MUST be reviewed rather than silently accepted. [BP] (pytest parametrize)

### 8.5 Markers

After Phase 1, all markers MUST be registered in `pyproject.toml`. Unknown markers are errors under strict configuration. Until then, marker registration is a target-state requirement, not a claim about the current repository. [SB] (pytest good practices)

| Marker | Meaning | Default run |
| --- | --- | --- |
| `unit` | Tests one function in isolation | Yes |
| `integration` | Cross-module behavior | Yes |
| `property` | Hypothesis property test | Yes (fast profile) |
| `slow` | Takes more than a few seconds | No, when the target `addopts` excludes it (`-m "not slow"`) |
| `extras` | Needs an optional extra | Only in extras CI, when the target job selects it explicitly |
| `mutation` | Mutation-testing support | No, when the target `addopts` excludes it (`-m "not mutation"`) |
| `network` | Reserved quarantine label for externally supplied probes; no supported bynat test may access live services | Never |

**Marker execution paths.** [BP]

- The default run excludes `slow`, `extras`, `network`, and `mutation` through the target `addopts` expression.
- Slow tests MAY be run explicitly with `python -m pytest -m slow` in a local or scheduled job.
- Extras tests MUST be run explicitly with `python -m pytest -m extras` after the required optional extra is installed, as described in §9.2.
- `python -m pytest -m mutation` runs tests marked as mutation support tests only; it does **not** invoke Cosmic Ray, mutmut, or another mutation engine. Actual mutation testing follows the independent §7.5 workflow.
- Network-marked tests are not part of the supported CI architecture. bynat tests MUST use fakes or injected providers instead; a network marker MUST NOT be used to justify live service access in CI.

**Orthogonality to directory hierarchy.** [BP] Markers remain the suite's independent responsibility-classification axis (`unit`, `integration`, `property`, `slow`, `extras`, `mutation`, `network`). A test under `tests/modules/` or `tests/cross_cutting/` is selected by what kind of check it performs and which gate runs it, not by which directory it resides in. The hierarchical directory structure organizes ownership and code cohesion, while markers control execution profiles.

### 8.6 pytest configuration

Target configuration in `pyproject.toml`: [BP]

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -m 'not slow and not extras and not network and not mutation'"
```

- Do not enable a global `filterwarnings = ["error"]`. Downstream packagers may need to disable `-Werror`, and newer dependency versions cause false positives. Assert warnings per test with `pytest.warns()`. [SB] (PyPA downstream packaging)
- Resolve the flat-layout import ambiguity: either move the package to `src/bynat` or set `--import-mode=importlib`. Tests SHOULD exercise the installed package, not the checkout. [SB] (pytest good practices; Scientific Python guide)
- Enable strict markers and strict config only with a pinned pytest version. [SB] (pytest good practices)

**Discovery across nested directories.** [BP] The target Phase 1 configuration adds `testpaths = ["tests"]`; the current `pyproject.toml` has no pytest configuration. With that target configuration, pytest discovers `test_*.py` recursively under `tests/modules/` and `tests/cross_cutting/`. Files under `tests/shared/` (`fakes.py`, `factories.py`, `constants.py`) do not use the `test_` prefix and are not collected as tests.

### 8.7 Type checking

Tests SHOULD be annotated and added to the mypy scope incrementally. Fixture and test parameters are annotated like normal function parameters. [SB] (pytest typing)

### 8.8 Test data

- Build small frames inline. [BP]
- Use `tmp_path` for JSON, CSV, and SQLite files. [BP]
- Do not read application data files from the repository outside `tests/` except through the public API under test. Packaging and typing-contract tests MAY inspect declared artifacts such as `bynat/py.typed` and `bynat/cleaning/accessor.pyi`, and documentation synchronization tests MAY load `tools/sync_docs.py`. [BP]
- Do not use the default cache directory. [BP]

### 8.9 TEST-ARCH-01 hierarchical test-suite architecture

**Authority and status.** This section is the authoritative TEST-ARCH-01 analysis and defines binding policy for the test suite layout. It replaces the previous flat-root hybrid model with a single consistent, repository-specific hierarchical architecture and migration plan. §1.4 makes this document the detailed policy behind `docs/ROADMAP.md` §2 and §6, and this document controls on conflict. The normative apparatus of §1 (RFC 2119 keywords and the [SB]/[BP]/[RP] basis tags) applies to every statement below. Where this section and §8.1–§8.8 overlap, this section is the more specific rule and controls; where it is silent, §8.1–§8.8 control. [BP]

**Current state (verified).** The repository at the reviewed revision contains 15 `tests/test_*.py` modules plus `tests/conftest.py`, 319 test function definitions, 528 collected test cases, 8,454 lines across the 15 test modules, and 8,471 lines across `tests/*.py` including `conftest.py`. `tests/conftest.py` is a 17-line `sys.path` shim with no fixtures, markers, or Hypothesis profiles. `tests/modules/`, `tests/cross_cutting/`, and `tests/shared/` do not exist. `pyproject.toml` declares no `[tool.pytest.ini_options]`, no `[tool.coverage.*]`, and no Hypothesis dependency. Four files are named after a process phase (`tests/test_phase3_file_io.py`, `tests/test_phase3_input_validation.py`, `tests/test_phase3_optional_integrations.py`, `tests/test_phase3_transformations.py`), one after a process artifact (`tests/test_inplace_deprecation.py`), and one is a cross-component grab-bag (`tests/test_cleaning.py`). Two files exceed the §8.1 800-line threshold: `tests/test_caching.py` at 1,774 lines and `tests/test_profile.py` at 857 lines. [BP]

**Target state.** Everything in §8.9.1–§8.9.9 is target state, not a description of current repository files. This section establishes the authoritative hierarchical architecture and migration plan. The migration that produces it is documented in §8.9.8 and is **not authorized** (§8.9.9). §12's phases remain the adoption gates for tooling and CI; this section approves the organizational model. [BP]

#### 8.9.1 Alternatives evaluated

Seven architectural models were evaluated against the observed suite, the §8 policy, and the constitution's mandatory structural rules. Each model is repository-specific, evaluated against the actual codebase (`bynat/caching/`, `bynat/cleaning/`, accessor, and integrations). The mandatory rules are the constitution's hard constraints: the 800-line splitting rule (§8.1), suite-wide configuration at root `tests/conftest.py` (§8.9.6), and the prohibition on network access and test-only production hooks (§4). Markers are the suite's existing responsibility-selection mechanism (§8.5). "Files moved" and "tests moved" are quantified from the current 15-module, 319-test-function, 528-case suite. [BP]

| Model | Shape | Dedicated cross-cutting ownership? | Verdict |
| --- | --- | --- | --- |
| F. Flat (status quo) | The current 15 topic-named files, including grab-bags and phase-named files | No | Rejected |
| A. Module flat | One flat file per production module directly under `tests/` | No | Rejected |
| B. Test-type nested | Nested `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/property/` | Yes (by directory) | Rejected |
| C. Layered | Nested by dependency depth: functions → classes → accessor → cache → storage | Partial | Rejected |
| D. Domain-only | Nested by business domain: `tests/cleaning/`, `tests/caching/`, `tests/enrichment/` | Partial | Rejected |
| E. Flat hybrid | Flat topic files for modules + flat cross-cutting files directly under `tests/` | Yes | Rejected |
| H. Hierarchical responsibility | Hierarchical: `tests/modules/<module>/`, `tests/cross_cutting/<topic>/`, `tests/shared/` | Yes (structural) | **Selected** |

**Comparison against neutral long-term criteria.** [BP]

| Criterion | F flat | A module | B type | C layered | D domain | E hybrid | H hierarchical |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ownership clarity: where does a test for `stats.py` or `accessor` parity go? | Poor | Good for modules; poor for cross-cutting | Poor: features split across type dirs | Medium | Medium | Good | **Excellent**: clear module vs cross-cutting home |
| Separation / cohesion | Poor | High in modules; cross-cutting scattered | Poor: splits single feature into 3+ dirs | Medium | Medium | Medium: 25+ files in root | **High**: isolated module subtrees & dedicated topics |
| Coupling | High | Medium | Medium | Medium | Medium | Medium | **Low**: clear boundaries, reusable infrastructure in `shared/` |
| Discoverability | Medium | High | High | Medium | Medium | Medium | **High**: intuitive filesystem mirror of package responsibilities |
| Scalability past 800-line / 2,000-test thresholds | Poor | Medium | Medium | Medium | Medium | Medium | **High**: natural subdivision within module directories |
| Change locality: a cross-cutting change touches how many directories? | Many | Medium | Many | Many | Many | Few | **Optimal**: localized to specific topic under `cross_cutting/` |
| Shared infrastructure / test independence | Poor | Poor | Medium | Medium | Medium | Medium (`tests/helpers.py`) | **High**: scoped `tests/shared/` + local `conftest.py` |
| Tooling / CI coupling | Medium | Medium | Medium | Medium | Medium | Low | **Low**: recursive discovery via `testpaths = ["tests"]` |
| Maintenance cost / consistency | High | Medium | Medium | Medium | Medium | Medium | **Low**: self-contained modules, clear boundary rules |
| Mandatory-rule compliance (<800 lines, root conftest) | No (violations) | Yes | Yes | Yes | Yes | Yes | **Planned yes**: each target must pass the migration-time <800-line check |
| Files moved / tests moved | 0 / 0 | 15 / 319 | 15 / 319 | 15 / 319 | 15 / 319 | 11 / 287 | 15 / 319 |

**Why F is rejected.** The status quo Flat model scores worst across all maintainability dimensions: cross-cutting contracts lack a defined home, cross-component grab-bags mix unrelated dependencies, and two files (`test_caching.py` at 1,774 lines, `test_profile.py` at 857 lines) violate the mandatory 800-line limit. [BP]

**Why A is rejected.** A pure module flat model leaves cross-cutting contracts homeless. API-02 (`BaseData` new-object vs `inplace`), class/accessor parity, and multi-component input validation would either be duplicated or scattered across module files without clear ownership. [BP]

**Why B is rejected.** Organizing by test type (`unit/`, `integration/`) fractures feature cohesion: testing a single function like `fill_missing` requires jumping across multiple directories. Furthermore, markers (`unit`, `integration`, `property`) already provide test-type selection without directory fragmentation. [BP]

**Why C is rejected.** Layered architectures based on dependency depth become brittle and convoluted when applied to pandas-based libraries, where accessor methods, wrapper classes, and functional implementations are tightly interrelated. [BP]

**Why D is rejected.** Domain-only grouping (`tests/cleaning/`, `tests/caching/`) conflates internal module unit tests with multi-component contracts (such as documentation synchronization and accessor parity), leaving cross-cutting concerns poorly separated. [BP]

**Why E is rejected.** The flat hybrid model places 25+ test files directly in the root `tests/` directory. As the suite expands toward 2,000 tests, a flat root directory becomes unmanageable, obscures module cohesion, and lacks cleanly scoped infrastructure. [BP]

**Why H is selected.** The Hierarchical Responsibility Architecture (Model H) establishes a clean separation of concerns: module-owned tests are grouped under `tests/modules/<module>/`, cross-cutting contracts and workflows have dedicated homes under `tests/cross_cutting/<topic>/`, genuinely reusable infrastructure has a reserved home in `tests/shared/` when evidence justifies it, and markers provide an orthogonal axis of responsibility selection. It satisfies every mandatory limit, scales smoothly, and minimizes long-term maintenance costs. [BP]

#### 8.9.2 Selected architecture and ownership

The target suite is structured hierarchically into three distinct functional tiers under `tests/`: [BP]

1. `tests/modules/<module>/`: Owns unit and component-level integration tests for a specific production module. Submodules or responsibility splits within a large module live together in this directory, accompanied by a module-local `conftest.py` only if justified.
2. `tests/cross_cutting/<topic>/`: Owns tests that span multiple components or verify system-wide contracts. Topics include base API contracts (`base_api`), accessor parity (`accessor`), documentation synchronization (`contracts`), performance equivalence against reference implementations (`equivalence`), multi-step workflows (`workflows`), and system-wide invariants (`invariants`).
3. `tests/shared/`: Owns only genuinely reusable infrastructure whose consumers span distinct architectural domains. Domain-local fakes, factories, and helpers remain in their module or topic subtree.

**Ownership rules.** [BP]
- Module-specific behavior and contracts belong to the relevant module directory; a production package may have several focused test files within that directory. The directory is the ownership boundary, not an exactly-one-test-file rule.
- When a module's test volume exceeds 800 lines (e.g. caching, profile, stats), the module tests are split into responsibility-focused files within that module's directory.
- Each cross-cutting contract maps to exactly one topic directory under `tests/cross_cutting/`, and each test has one primary owner.
- A test that verifies a genuinely cross-module contract or workflow belongs to `tests/cross_cutting/` and is referenced by the relevant module coverage matrices.
- A helper, fake, or fixture used by two or more files across different domains belongs in `tests/shared/`. Domain-specific helpers remain within their owning module directory.

**Production-module → owner table.** [BP]

| Production module | Owning target directory | Owning test file(s) |
| --- | --- | --- |
| `bynat/caching/manager.py` | `tests/modules/caching/` | `test_persistence.py`, `test_migration.py`, `test_concurrency.py`, `conftest.py` |
| `bynat/cleaning/columns.py` | `tests/modules/columns/` | `test_columns.py` |
| `bynat/cleaning/text.py` | `tests/modules/text/` | `test_text.py` |
| `bynat/cleaning/stats.py` | `tests/modules/stats/` | `test_fill_missing.py`, `test_hierarchical_stats.py`, `test_hierarchical_stats_mode.py`, `test_hierarchical_stats_flags.py` |
| `bynat/cleaning/profile.py` | `tests/modules/profile/` | `test_profile_general.py`, `test_profile_edges.py`, `test_profile_contract.py` |
| `bynat/cleaning/io.py` | `tests/modules/io/` | `test_io.py` |
| `bynat/cleaning/enrich/` (all submodules) | `tests/modules/enrichment/` | `test_translate.py`, `test_geocode.py`, `test_currency.py`, `test_nlp.py`, `test_optional.py`, `conftest.py` |

**Cross-cutting contract → owner table.** [BP]

| Cross-cutting contract | Owning target directory | Owning test file(s) |
| --- | --- | --- |
| Base API & API-02 (`inplace` / copy contract) | `tests/cross_cutting/base_api/` | `test_base.py` |
| Accessor registration & class/accessor parity | `tests/cross_cutting/accessor/` | `test_accessor.py`, `test_parity.py` |
| Documentation & typing drift (`py.typed`, `.pyi`) | `tests/cross_cutting/contracts/` | `test_doc_drift.py` |
| Reference equivalence (PERF invariants, benchmark imports) | `tests/cross_cutting/equivalence/` | `test_equivalence.py` |
| Multi-dataset reference workflows (`fill_missing_from`) | `tests/cross_cutting/workflows/` | `test_fill_missing_from.py` |
| System-wide invariant & property-based tests (Hypothesis) | `tests/cross_cutting/invariants/` | Future `test_invariants.py` only if system-wide invariants are added |

**Input-validation ownership policy.** [BP] Input-validation tests belong to the component whose public API is validated: component-specific validation belongs to the module owning that component (e.g. `stats` validation in `tests/modules/stats/`, loader validation in `tests/modules/io/`). Cross-cutting validation rules that span components — such as the `min_samples` contract (§6.7), the `inplace` rejection contract (§6.1 S-4, §6.10 ML-2), and class/accessor parity of validation errors (§6.1 S-5) — belong to `tests/cross_cutting/base_api/` and `tests/cross_cutting/accessor/`.

#### 8.9.3 Target tree and size budgets

**Planning-estimate formula.** [BP] For a target file created by a split or move, the planning estimate is `Σ(item line ranges) + 1 separator per resulting test + H`, where item line ranges are computed from current file ASTs, separators represent single blank lines between test functions, and `H` is the deduplicated import and fixture header. These are approximate planning estimates, not verified post-migration line counts. For an unchanged kept file, the estimate is its current line count.

**Target tree and per-target size arithmetic.** [BP]

| Target path | Source items | Arithmetic (body + separators + header) | Estimate | Limit |
| --- | --- | --- | ---: | ---: |
| `tests/conftest.py` | Root suite shim | 17 current lines | 17 | 800 |
| `tests/modules/caching/helpers.py` | Caching-only `_seed_cache_entries`, `_rows` | 40 + 0 + 5 | 45 | 800 |
| `tests/modules/caching/conftest.py` | Caching local fixtures | 30 + 4 + 6 | 40 | 800 |
| `tests/modules/caching/test_persistence.py` | `test_caching.py` (30 items) | 715 + 30 + 5 | 750 | 800 |
| `tests/modules/caching/test_migration.py` | `test_caching.py` (21 items) | 592 + 21 + 6 | 619 | 800 |
| `tests/modules/caching/test_concurrency.py` | `test_caching.py` (11 items) | 290 + 5 + 6 | 301 | 800 |
| `tests/modules/columns/test_columns.py` | `cleaning` (2), `transformations` (16), `validation` (1) | 436 + 19 + 5 | 460 | 800 |
| `tests/modules/text/test_text.py` | `cleaning` (2), `transformations` (2) | 99 + 4 + 6 | 109 | 800 |
| `tests/modules/stats/test_fill_missing.py` | `cleaning` (8), `transformations` (3), `validation` (14) | 316 + 23 + 6 | 345 | 800 |
| `tests/modules/stats/test_hierarchical_stats.py` | `hierarchical_stats` (19), `validation` (6) | 428 + 25 + 8 | 461 | 800 |
| `tests/modules/stats/test_hierarchical_stats_mode.py` | `hierarchical_stats` (5 items) | 117 + 5 + 4 | 126 | 800 |
| `tests/modules/stats/test_hierarchical_stats_flags.py` | `hierarchical_stats` (5 items) | 123 + 5 + 3 | 131 | 800 |
| `tests/modules/profile/test_profile_general.py` | `test_profile.py` (15 items) | 358 + 14 + 13 | 385 | 800 |
| `tests/modules/profile/test_profile_edges.py` | `test_profile.py` (8 items) | 193 + 8 + 12 | 213 | 800 |
| `tests/modules/profile/test_profile_contract.py` | `test_profile.py` (6 items) | 190 + 3 + 11 | 204 | 800 |
| `tests/modules/io/test_io.py` | `cleaning` (6), `validation` (2), `file_io` (24) | 391 + 32 + 8 | 431 | 800 |
| `tests/modules/enrichment/conftest.py` | Enrichment local fixtures | 22 + 3 + 5 | 30 | 800 |
| `tests/modules/enrichment/test_translate.py` | `cleaning` (4), `trans` (5), `val` (2), `int` (1), `enrich` (20) | 549 + 28 + 22 | 599 | 800 |
| `tests/modules/enrichment/test_geocode.py` | `validation` (1), `integrations` (3), `enrichment` (4) | 181 + 5 + 6 | 192 | 800 |
| `tests/modules/enrichment/test_currency.py` | `integrations` (2), `enrichment` (6) | 192 + 5 + 15 | 212 | 800 |
| `tests/modules/enrichment/test_nlp.py` | `test_integrations.py` (18 items) | 314 + 15 + 8 | 337 | 800 |
| `tests/modules/enrichment/test_optional.py` | `integrations` (3), `optional_integrations` (15) | 266 + 16 + 6 | 288 | 800 |
| `tests/cross_cutting/base_api/test_base.py` | `cleaning` (4), `trans` (2), `val` (6), `deprecation` (11) | 365 + 18 + 10 | 393 | 800 |
| `tests/cross_cutting/accessor/test_accessor.py` | `test_accessor.py` (12 items) | unchanged | 200 | 800 |
| `tests/cross_cutting/accessor/test_parity.py` | `test_phase3_transformations.py` (2 items) | 52 + 1 + 1 | 54 | 800 |
| `tests/cross_cutting/contracts/test_doc_drift.py` | `test_doc_drift.py` (4 items) | unchanged | 86 | 800 |
| `tests/cross_cutting/equivalence/test_equivalence.py` | `test_equivalence.py` (19 items) | unchanged | 400 | 800 |
| `tests/cross_cutting/workflows/test_fill_missing_from.py` | `fill_missing_from` (9), `trans` (3), `val` (4) | 393 + 84 + 9 | 486 | 800 |
| `tests/cross_cutting/invariants/test_invariants.py` | Future system-wide Hypothesis property tests only | — | Not estimated until justified | 800 |

**Planned compliance.** Every listed target is intended to remain strictly below the 800-line threshold; the largest planning estimate is `test_persistence.py` at 750 lines. Migration MUST recompute actual line counts from the resulting files and stop for a responsibility-based split if any file reaches or exceeds 800 lines. The estimates are planning evidence, not a claim that the target files already exist or that their final counts have been verified. [BP]

#### 8.9.4 Responsibility and boundary rules

- **Module ownership.** Files under `tests/modules/<module>/` are owned by the primary responsibility and contract they verify. They MAY exercise dependencies from other modules when those dependencies support the module-specific behavior. They MUST NOT own a genuinely cross-module contract or multi-step workflow whose primary responsibility belongs under `tests/cross_cutting/<topic>/`. [BP]
- **Cross-cutting ownership.** Tests that assert parity between different APIs (such as `BaseData` vs `df.bynat`), documentation drift, or end-to-end workflows MUST reside in `tests/cross_cutting/<topic>/`. [BP]
- **Orthogonality of markers.** Directory structure defines ownership; markers define execution gates (§8.5). `unit`, `integration`, `property`, `slow`, `extras`, `mutation`, and `network` markers apply equally across module and cross-cutting tests. [BP]
- **Property tests.** Hypothesis property tests for module invariants reside within the respective module directory (e.g. `tests/modules/stats/test_invariants_property.py`). Cross-component or system-wide invariants reside under an appropriate cross-cutting topic such as `tests/cross_cutting/invariants/`; `property` is a marker, not a mandatory directory. All property tests MUST be marked with `@pytest.mark.property`. [BP]
- **No grab-bags.** No test file may be named after a process phase (`test_phase3_*`), work item, or generic concept (`test_cleaning.py`). Every file name states the specific behavior or component under test. [BP]

#### 8.9.5 Fixture, helper, data, naming, marker, and discovery rules

**Fixtures and conftest scoping.** [BP]
- Root `tests/conftest.py` is reserved for genuinely suite-wide configuration and fixtures. The current file contains only the `sys.path` shim. Marker declarations, Hypothesis settings, and global safety fixtures are optional future additions, not permanent requirements, and require separate evidence and adoption.
- Module-local `conftest.py` is permitted only where justified by module-scoped fixtures (e.g. `tests/modules/caching/conftest.py` for SQLite database handles and seeder fixtures; `tests/modules/enrichment/conftest.py` for mock provider lifecycles). Modules without shared fixtures MUST NOT create a local `conftest.py`.
- Single-file fixtures remain file-local.

**Shared infrastructure.** [BP]
- Genuinely reusable infrastructure is placed in `tests/shared/` only when there are two or more consumers across distinct architectural domains and centralization improves maintainability. The current suite provides no verified shared-infrastructure consumer that requires a new `tests/shared/` file; the directory remains reserved for a future evidence-based extraction.
- Caching-only helpers (`_seed_cache_entries`, `_rows`) remain in `tests/modules/caching/helpers.py`; enrichment provider fakes and installers remain in the enrichment subtree; `PARITY_DATA`, `OUTPUT_COLUMNS`, and `EXPECTED_STATS_KEYS_BY_KIND` remain local unless a future migration audit verifies distinct-domain consumers.
- Domain-specific helpers (such as `_Location`, `_install_geopy`, `_install_fake_spacy`) remain local to their owning module directory.

**Naming and discovery.** [BP]
- Test files MUST be named `test_<topic>.py`.
- Any future shared infrastructure file in `tests/shared/` MUST NOT start with `test_`, ensuring pytest never attempts to collect it as a test module.
- The future Phase 1 configuration in `pyproject.toml` adds `testpaths = ["tests"]`. Pytest then discovers test files recursively across all nested module and cross-cutting directories without manual path enumeration; the current configuration has no pytest section.

#### 8.9.6 Verified structural constraints versus temporary implementation dependencies

**Structural constraints (permanent architecture invariants).** [BP]
1. Root `tests/conftest.py` MUST remain at the `tests/` root. It preserves the existing suite-wide `sys.path` shim; additional suite-wide configuration or fixtures require separate evidence and adoption.
2. The 800-line per-file limit is an absolute constraint across all target directories.
3. The prohibition on network access, test-only production hooks, and modifying production code to satisfy tests is absolute (§4, §10).
4. Test-type markers (`unit`, `integration`, `property`, `extras`, `slow`) remain the execution filter mechanism in CI, independent of directory location.

**Temporary implementation dependencies (resolved during migration).** [BP]
1. `tools/verify_installed_wheel.py`: Currently hardcodes `PHASE3_TESTS` pointing at the four `test_phase3_*.py` files. When these files are dissolved, `PHASE3_TESTS` MUST be updated to reference representative target verification files (e.g., `tests/modules/io/test_io.py`, `tests/modules/enrichment/test_optional.py`, `tests/modules/columns/test_columns.py`, and `tests/cross_cutting/accessor/test_parity.py`).
2. `benchmarks/_common.py`: Adds `ROOT / "tests"` to `sys.path`, and the benchmark scripts import reference implementations from `test_equivalence.py`. The preferred future solution is to create `benchmarks/reference_impls.py`, extract those reference implementations there, and have both equivalence tests and benchmarks import that module. Updating benchmark imports and the equivalence-test imports is a separate migration dependency; adding a nested test directory to `sys.path` is not the preferred permanent architecture.
3. `tests/test_doc_drift.py`: Computes `ROOT` as the repository root with `Path(__file__).resolve().parent.parent`. When moved to `tests/cross_cutting/contracts/test_doc_drift.py`, `ROOT` MUST remain the repository root, which requires `.parents[3]`; the test-suite root is then `ROOT / "tests"`.
4. Strict xfail reason references: The 20 strict-xfail cases (8 in `tests/cross_cutting/base_api/test_base.py`, 12 in `tests/modules/stats/test_fill_missing.py`) point to `docs/temb/TEST-02-phase1-audit.md` via reason strings. That tracked file MUST NOT be moved.
5. Pandas-2 skips: The 17 version-conditional skips in `test_equivalence.py` are preserved in place.

#### 8.9.7 Complete mapping of current test and support files

**Item definition.** An item is a test function, module-level helper function, class, or constant defined in a current test module. Fixtures and parametrization IDs are internal to items. All 15 current test modules, 319 test functions, and supporting items are mapped completely below. [BP]

**File-level migration mapping.** Legend: **K** = keep in place, **S** = split, **M** = merge into another file, **A** = absorb/dissolve, **C** = create, **U** = update in same change. [BP]

| Current path | Action | Target path(s) | Reason |
| --- | --- | --- | --- |
| `tests/conftest.py` | **K** | `tests/conftest.py` | Root suite-wide configuration and `sys.path` shim |
| `tests/test_accessor.py` | **K** | `tests/cross_cutting/accessor/test_accessor.py` | Accessor contracts and signatures |
| `tests/test_caching.py` | **S** | `tests/modules/caching/test_persistence.py`, `test_migration.py`, `test_concurrency.py`, `conftest.py` | 1,774 lines exceeds 800-line limit; split by responsibility |
| `tests/test_cleaning.py` | **S** | `tests/modules/columns/test_columns.py`, `text/test_text.py`, `stats/test_fill_missing.py`, `io/test_io.py`, `enrichment/test_translate.py`, `cross_cutting/base_api/test_base.py` | 471-line cross-component grab-bag dissolved by component |
| `tests/test_doc_drift.py` | **M** | `tests/cross_cutting/contracts/test_doc_drift.py` | API and documentation drift contract gate |
| `tests/test_enrichment.py` | **S** | `tests/modules/enrichment/test_translate.py`, `test_geocode.py`, `test_currency.py` | Split by enrichment submodule to avoid 800-line violation |
| `tests/test_equivalence.py` | **M** | `tests/cross_cutting/equivalence/test_equivalence.py` | Reference implementations and optimization parity |
| `tests/test_fill_missing_from.py` | **M** | `tests/cross_cutting/workflows/test_fill_missing_from.py` | Multi-dataset reference imputation workflow |
| `tests/test_hierarchical_stats.py` | **S** | `tests/modules/stats/test_hierarchical_stats.py`, `test_hierarchical_stats_mode.py`, `test_hierarchical_stats_flags.py` | 710 lines; split by strategy and flags to prevent threshold breach |
| `tests/test_inplace_deprecation.py` | **M** | `tests/cross_cutting/base_api/test_base.py` | API-02 mutability contracts; process-named file dissolved |
| `tests/test_integrations.py` | **S** | `tests/modules/enrichment/test_nlp.py`, `test_geocode.py`, `test_currency.py`, `test_optional.py` | Dissolved by target integration submodule |
| `tests/test_phase3_file_io.py` | **M** | `tests/modules/io/test_io.py` | File I/O contracts; process-named file dissolved |
| `tests/test_phase3_input_validation.py` | **A** | `tests/modules/stats/`, `columns/`, `io/`, `enrichment/`, `cross_cutting/base_api/`, `workflows/` | Input validation dissolved by component validated |
| `tests/test_phase3_optional_integrations.py` | **M** | `tests/modules/enrichment/test_optional.py` | Real optional dependency tests; process name dissolved |
| `tests/test_phase3_transformations.py` | **A** | `tests/modules/columns/`, `text/`, `stats/`, `enrichment/`, `cross_cutting/accessor/test_parity.py`, `base_api/` | Transformations dissolved by component and parity owner |
| `tests/test_profile.py` | **S** | `tests/modules/profile/test_profile_general.py`, `test_profile_edges.py`, `test_profile_contract.py` | 857 lines exceeds 800-line limit; split by responsibility |
| — | **C** | `tests/modules/caching/helpers.py` | Caching-local helpers reused by multiple caching target files; no shared-domain extraction is currently justified |

**Support-item migration mapping.** [BP]

| Support path | Action | Target update | Reason |
| --- | --- | --- | --- |
| `tools/sync_docs.py` | **K** | Unchanged | Imported by `test_doc_drift.py` |
| `tools/verify_installed_wheel.py` | **U** | Update `PHASE3_TESTS` manifest | Target paths replace dissolved `test_phase3_*` files |
| `benchmarks/_common.py` | **U** | Prefer no test-directory path addition; consume the future benchmark reference module | Removes benchmark dependence on importing a test module |
| `benchmarks/bench_extract_keywords.py` | **U** | Import the future benchmark reference module | Keeps benchmark/reference code outside `tests/` |
| `benchmarks/bench_outliers.py` | **U** | Import the future benchmark reference module | Keeps benchmark/reference code outside `tests/` |
| — | **C** | `benchmarks/reference_impls.py` | Future home for benchmark reference implementations shared by benchmarks and equivalence tests |
| `.github/workflows/test.yml` | **K** | Unchanged | Runs `pytest -q` which discovers all nested tests recursively |
| `.github/workflows/publish.yml` | **K** | Unchanged | Packaging workflow; no test path coupling |
| `pyproject.toml` | **U** | Add target `[tool.pytest.ini_options]` during the separately adopted Phase 1 | Enables recursive discovery and marker configuration; current file has no pytest section |
| `docs/temb/TEST-02-phase1-audit.md` | **K** | Unchanged | Referenced by 20 strict-xfail cases; do not move |
| `docs/ROADMAP.md` | **K** | Unchanged | Aligned with hierarchical architecture |

**Test-level routing details.** Every test and helper is routed to exactly one target. Tests marked `#part` represent the single multi-concept test split into three focused tests. Shared infrastructure is extracted only where distinct-domain consumers are evidenced; same-domain helpers remain in their module or topic subtree. [BP]

- **Shared/local support items:**
  - `OUTPUT_COLUMNS` (`tests/test_hierarchical_stats.py:10`, duplicate in `test_phase3_transformations.py:29`) remains local to the responsible target files unless migration evidence demonstrates a distinct-domain shared consumer; duplicate definitions alone do not justify `tests/shared/` centralization.
  - `_seed_cache_entries` (`tests/test_caching.py:1146`) and `_rows` (`tests/test_caching.py:1500`) -> `tests/modules/caching/helpers.py`, because both are reused only within caching responsibilities.
  - `_install`, provider fakes, `EXPECTED_STATS_KEYS_BY_KIND`, and `PARITY_DATA` remain local to their owning enrichment, profile, or accessor-parity targets unless migration evidence demonstrates distinct-domain reuse.

- **`tests/test_caching.py` (64 items):**
  - `test_persistence.py` (30 items): `test_cache_round_trip_via_sqlite`, `test_save_persists_added_changed_and_removed_entries`, `test_save_persists_entirely_removed_buckets`, `test_save_handles_deletion_only_transaction`, `test_failed_removal_transaction_rolls_back_and_retries`, `test_save_advances_baseline_after_removal`, `test_cache_rejects_empty_and_path_like_keys`, `test_corrupt_cache_is_quarantined_and_replaced_with_empty_dict`, `test_save_unserializable_value_reports_error_without_raising`, `test_cache_directory_is_created_on_save_not_construction`, `test_failed_db_save_keeps_baseline_and_rows_intact_for_retry`, `test_save_transaction_rolls_back_on_commit_failure`, `test_save_serialization_failure_keeps_prior_checkpoint_readable`, `test_cache_dir_defaults_to_environment_variable_then_legacy_path`, `test_rebuild_function_cache_from_sqlite`, `test_rebuild_function_cache_from_sqlite_is_empty_without_rows`, `test_load_function_cache_migrates_legacy_json_through_public_path`, `test_load_function_cache_missing_function_returns_empty_and_builds_backend`, `test_load_function_cache_reads_sqlite_authoritatively`, `test_load_function_cache_memoizes_and_preserves_mutations`, `test_get_column_cache_returns_existing_bucket_identity`, `test_get_column_cache_creates_missing_bucket`, `test_get_column_cache_preserves_explicit_none_value`, `test_get_column_cache_missing_function_creates_empty_bucket`, `test_load_function_cache_records_baseline_matching_loaded_state`, `test_baseline_is_deep_copy_and_survives_nested_mutation`, `test_separate_functions_have_separate_baselines`, `test_save_detects_nested_mutation_and_writes_only_changed_entries`, `test_save_advances_baseline_after_success`, `test_save_conflict_update_last_writer_wins_and_disjoint_merge`.
  - `test_migration.py` (21 items): `test_delete_column_cache_persists_existing_bucket_removal`, `test_delete_column_cache_leaves_unrelated_buckets_intact`, `test_delete_column_cache_leaves_unrelated_function_intact`, `test_delete_column_cache_missing_bucket_is_a_no_op`, `test_delete_column_cache_failed_transaction_is_retryable`, `test_sqlite_initialization_is_lazy_until_explicitly_requested`, `test_sqlite_schema_has_required_tables_columns_keys_and_index`, `test_sqlite_connection_configures_timeout_wal_and_full_synchronous`, `test_sqlite_connection_closes_when_pragma_configuration_fails`, `test_sqlite_initialization_rolls_back_and_closes_on_failure`, `test_sqlite_initialization_rolls_back_real_ddl_on_later_schema_failure`, `test_sqlite_initialization_rolls_back_and_closes_when_commit_fails`, `test_repeated_sqlite_initialization_is_safe`, `test_legacy_migration_imports_supported_values_and_maps_filename`, `test_legacy_migration_is_idempotent_and_existing_rows_win`, `test_missing_legacy_source_does_not_create_database_or_marker`, `test_legacy_migration_quarantines_corrupt_source_without_marker`, `test_legacy_migration_preserves_unsupported_source_for_retry`, `test_legacy_migration_rolls_back_and_can_retry_after_partial_insert_failure`, `test_legacy_migration_rolls_back_and_can_retry_after_marker_insert_failure`, `test_legacy_migration_rolls_back_and_can_retry_after_commit_failure`.
  - `test_concurrency.py` (11 items): `test_legacy_migration_is_safe_for_concurrent_sources`, `_concurrent_save_worker`, `test_save_function_cache_is_safe_for_concurrent_disjoint_saves`, `_first_writer_worker`, `_second_writer_worker`, `test_save_function_cache_last_committed_writer_wins_same_key_across_processes`, `test_delete_column_cache_stale_manager_preserves_concurrent_additions`, `_add_key_after_baseline_worker`, `_load_baseline_then_delete_worker`, `test_delete_column_cache_across_processes_preserves_concurrent_addition`, `_run_legacy_migration`.
  - `tests/modules/caching/helpers.py` (2 items): `_seed_cache_entries`, `_rows`.

- **`tests/test_cleaning.py` (24 items):**
  - `tests/cross_cutting/base_api/test_base.py` (4 items): `test_public_cleaning_imports_use_the_bundled_cache_manager`, `test_basedata_boundary_errors_and_inplace_return`, `test_json_and_csv_constructors_read_local_files`, `test_file_constructors_raise_for_missing_paths`.
  - `tests/modules/columns/test_columns.py` (2 items): `test_basedata_core_column_transformations_preserve_subclass_and_cache`, `test_basedata_text_list_reshape_and_imputation_helpers#split_list_objects`.
  - `tests/modules/text/test_text.py` (2 items): `test_translate_conditional_safe_partition_does_not_import_deep_translator`, `test_basedata_text_list_reshape_and_imputation_helpers#extract_keywords`.
  - `tests/modules/stats/test_fill_missing.py` (8 items): `test_hierarchy_methods_support_named_multi_and_duplicate_indexes`, `test_fill_missing_rejects_unknown_strategy`, `test_fill_missing_min_samples_and_fallback_global_reproduction`, `test_fill_missing_validates_min_samples`, `test_fill_missing_hierarchical_fallthrough_multi_level`, `test_fill_missing_all_strategies_with_fallbacks`, `test_fill_missing_all_nan_column`, `test_basedata_text_list_reshape_and_imputation_helpers#fill_missing`.
  - `tests/modules/io/test_io.py` (6 items): `test_save_to_json_writes_local_output`, `test_save_to_json_append_keeps_existing_rows_with_list_columns`, `test_save_to_json_append_deduplicates_plain_columns_without_json_keys`, `test_save_to_json_append_refuses_to_overwrite_unreadable_file`, `test_save_to_json_requires_file_path`, `test_save_to_sql_rejects_invalid_arguments_before_connecting`.
  - `tests/modules/enrichment/test_translate.py` (4 items): `test_impute_by_language_missing_reference_returns_before_optional_import`, `test_translate_conditional_missing_langdetect_raises_documented_import_error`, `test_optional_integration_reports_missing_dependency_at_method_use`, `test_optional_categorization_reports_missing_dependency_at_method_use`.

- **`tests/test_profile.py` (30 items):**
  - `test_profile_general.py` (15 items): `test_public_entry_points`, `test_profiling_does_not_modify_input`, `test_report_structure_and_access_patterns`, `test_output_type_parameter`, `test_column_selection_and_errors`, `test_missing_values_and_proportions`, `test_duplicate_rows_counting_semantics`, `test_duplicate_rows_with_unhashable_cells`, `test_numeric_statistics`, `test_categorical_and_text_statistics`, `test_boolean_statistics`, `test_datetime_statistics`, `test_mixed_and_other_statistics`, `test_nullable_dtypes`, `_SINGLE_TYPE_INFERRED_LABELS`.
  - `test_profile_edges.py` (8 items): `test_empty_dataframe_edge_cases`, `test_all_missing_column_edge_cases`, `test_single_row_statistics`, `test_duplicate_column_names_handling`, `test_clean_scalar_bool_before_int`, `test_timedelta_columns_and_clean_scalar`, `test_categorical_pd_categorical`, `test_tz_aware_datetime`.
  - `test_profile_contract.py` (6 items): `test_contract_stability_key_sets`, `test_contract_stability_value_types`, `test_contract_json_dumps_mixed_dataframe`, `EXPECTED_TOP_LEVEL_KEYS`, `EXPECTED_DATASET_FIELDS`, `EXPECTED_COLUMN_FIELDS`.
  - Profile-local constant (1 item): `EXPECTED_STATS_KEYS_BY_KIND` remains with the profile contract tests.

- **`tests/test_hierarchical_stats.py` (30 items):**
  - `test_hierarchical_stats.py` (19 items): `test_get_hierarchical_stats_returns_median_levels_and_preserves_source`, `test_get_hierarchical_stats_supports_mean_multiple_targets_and_string_hierarchy`, `test_get_hierarchical_stats_handles_null_values_and_empty_groups`, `test_get_hierarchical_stats_returns_fixed_empty_schema_for_invalid_inputs`, `test_get_hierarchical_stats_does_not_change_fill_missing_behavior`, `test_get_hierarchical_stats_supports_explicit_dataframe_and_dict_outputs`, `test_get_hierarchical_stats_supports_explicit_basedata_family_outputs`, `test_get_hierarchical_stats_preserves_custom_basedata_subclass_by_default`, `test_get_hierarchical_stats_rejects_invalid_output_type_before_aggregation`, `test_get_hierarchical_stats_returns_requested_type_for_empty_results`, `test_get_hierarchical_stats_has_no_nested_functions_or_apply_lambda`, `test_get_hierarchical_stats_deduplicates_hierarchy_columns_without_adding_levels`, `test_get_hierarchical_stats_rejects_target_hierarchy_overlap_before_aggregation`, `test_get_hierarchical_stats_supports_ordered_multiple_strategies`, `test_get_hierarchical_stats_rejects_non_string_strategy_values_before_aggregation`, `test_get_hierarchical_stats_default_fallback_requires_data_signature`, `test_get_hierarchical_stats_propagates_internal_constructor_errors`, `test_get_hierarchical_stats_all_output_types_keep_multi_strategy_schema`, `test_get_hierarchical_stats_falls_back_to_dataframe_for_incompatible_default_subclass`.
  - `test_hierarchical_stats_mode.py` (5 items): `test_get_hierarchical_stats_mode_matches_tie_breaking_and_normalizes_mod`, `test_get_hierarchical_stats_mode_returns_all_targets_at_every_hierarchy_level`, `test_get_hierarchical_stats_mode_allows_hierarchy_column_named_count`, `test_get_hierarchical_stats_mode_has_no_melt_and_keeps_null_groups`, `test_get_hierarchical_stats_mode_empty_valid_values_returns_empty_rows`.
  - `test_hierarchical_stats_flags.py` (5 items): `test_hierarchy_methods_keep_existing_return_contract_when_stats_disabled`, `test_hierarchy_methods_skip_stats_calculation_when_disabled`, `test_hierarchy_methods_return_stats_for_copy_and_inplace_modes`, `test_hierarchy_stats_are_extracted_before_drop_outliers`, `test_hierarchy_stats_are_extracted_before_progressive_fill`.
  - Stats-local constant (1 item): `OUTPUT_COLUMNS` remains with the statistics targets unless a future migration audit demonstrates distinct-domain reuse.

- **`tests/test_phase3_transformations.py` (35 items):**
  - `tests/cross_cutting/workflows/test_fill_missing_from.py` (3 items): `test_fill_missing_from_non_numeric_target_with_numeric_strategy_raises`, `test_fill_missing_from_stats_reverse_map_match_cols`, `test_fill_missing_from_inplace_with_stats_returns_stats_and_mutates`.
  - `tests/cross_cutting/accessor/test_parity.py` (2 items): `test_accessor_and_basedata_produce_equal_results`, `PARITY_CASES`.
  - `tests/cross_cutting/base_api/test_base.py` (2 items): `test_inplace_true_matches_the_copy_result_and_returns_none`, `INPLACE_CASES`.
  - `tests/modules/columns/test_columns.py` (16 items): `test_drop_CLASS_columns_drops_only_matching_columns`, `test_rename_by_substring_renames_every_occurrence_and_keeps_the_rest`, `test_rename_by_substring_without_matches_returns_an_independent_copy`, `test_reorder_columns_moves_named_columns_to_the_front`, `test_reorder_columns_with_no_valid_names_returns_an_independent_copy`, `test_align_lat_lng_moves_longitude_after_latitude`, `test_split_list_objects_remove_source_col_drops_the_original_column`, `test_split_list_objects_joined_extraction_ignores_missing_elements`, `test_split_list_objects_parallel_explode_resets_the_index`, `test_split_list_objects_cartesian_explode_builds_the_cross_product`, `test_split_list_objects_all_index_copies_the_source_list`, `test_melt_transform_pivot_defaults_and_kwargs`, `test_melt_transform_pivot_custom_layout`, `test_melt_transform_pivot_resets_the_index_and_preserves_the_subclass`, `test_melt_transform_pivot_derives_pivot_layout_defaults`, `test_melt_transform_pivot_supports_a_non_default_aggfunc`.
  - `tests/modules/text/test_text.py` (2 items): `test_truncate_after_substring_literal_delimiters`, `test_truncate_after_substring_regex_delimiters`.
  - `tests/modules/stats/test_fill_missing.py` (3 items): `test_fill_missing_min_samples_counts_only_non_null_observations`, `test_fill_missing_uppercase_strategy_matches_lowercase`, `test_fill_missing_without_missing_values_returns_an_independent_copy`.
  - `tests/modules/enrichment/test_translate.py` (5 items): `test_impute_by_language_exact_detection_and_generated_fallback`, `test_impute_by_language_honors_target_lang`, `test_impute_by_language_skips_missing_columns`, `test_impute_by_language_inplace_matches_the_copy_result`, `fake_langdetect`.
  - Local support items: `OUTPUT_COLUMNS` remains with the statistics targets; `PARITY_DATA` remains with `tests/cross_cutting/accessor/test_parity.py`.

- **`tests/test_phase3_input_validation.py` (36 items):**
  - `tests/modules/stats/test_hierarchical_stats.py` (6 items): `test_get_hierarchical_stats_non_numeric_target_raises_typeerror`, `test_get_hierarchical_stats_non_numeric_target_mode_is_allowed`, `test_get_hierarchical_stats_skips_missing_targets`, `test_get_hierarchical_stats_rejects_non_iterable_strategy`, `test_get_hierarchical_stats_rejects_empty_strategy_iterable`, `test_get_hierarchical_stats_rejects_unknown_strategy`.
  - `tests/cross_cutting/workflows/test_fill_missing_from.py` (4 items): `test_fill_missing_from_non_numeric_all_nan_target_is_exempt`, `test_fill_missing_from_skips_missing_targets_and_fills_valid_ones`, `test_fill_missing_from_duplicate_targets_are_deduplicated`, `test_fill_missing_from_rejects_empty_match_cols_strings`.
  - `tests/cross_cutting/base_api/test_base.py` (6 items): `test_accessor_rejects_inplace_for_variadic_methods`, `test_shared_functions_reject_inplace_for_variadic_methods`, `test_accessor_rejects_inplace_for_non_variadic_methods`, `test_inplace_is_accepted_by_the_class_api_and_rejected_by_the_accessor`, `_variadic_frame`, `INPLACE_XFAIL` (8 strict xfail cases).
  - `tests/modules/columns/test_columns.py` (1 item): `test_melt_transform_pivot_rejects_invalid_arguments`.
  - `tests/modules/stats/test_fill_missing.py` (14 items): `test_handle_outliers_rejects_invalid_min_samples`, `test_drop_outliers_rejects_invalid_min_samples`, `test_fill_missing_and_fill_missing_from_reject_invalid_min_samples`, `test_handle_outliers_min_samples_boundary`, `test_min_samples_counts_only_non_null_observations`, `test_outlier_methods_warn_and_return_an_unchanged_copy_without_hierarchy`, `test_outlier_methods_raise_keyerror_for_a_missing_named_hierarchy`, `test_fill_missing_non_numeric_target_with_hierarchy_raises_typeerror`, `test_fill_missing_non_numeric_target_with_fallback_global_raises_typeerror`, `test_fill_missing_non_numeric_target_without_hierarchy_is_unchanged`, `test_fill_missing_non_numeric_all_nan_target_does_not_raise`, `test_fill_missing_skips_missing_targets_and_fills_valid_ones`, `MIN_SAMPLES_XFAIL` (12 strict xfail cases), `INVALID_MIN_SAMPLES`.
  - `tests/modules/io/test_io.py` (2 items): `test_read_json_missing_key_raises_keyerror`, `test_read_json_key_on_non_dict_payload_raises_typeerror`.
  - `tests/modules/enrichment/test_translate.py` (2 items): `test_translate_conditional_column_rejects_out_of_range_threshold`, `test_translate_conditional_column_rejects_non_positive_integer_parameters`.
  - `tests/modules/enrichment/test_geocode.py` (1 item): `test_fill_missing_coordinates_rejects_non_positive_integer_save_every`.

- **`tests/test_integrations.py` (28 items):**
  - `tests/modules/enrichment/test_translate.py` (1 item): `test_translate_categorical_column_translates_each_unique_value_once`.
  - `tests/modules/enrichment/test_geocode.py` (3 items): `test_fill_missing_coordinates_shortens_queries_and_caches_misses`, `_Location`, `_install_geopy`.
  - `tests/modules/enrichment/test_currency.py` (2 items): `test_convert_to_usd_looks_back_and_caches_missing_years`, `_install_currency`.
  - `tests/modules/enrichment/test_nlp.py` (18 items): `test_extract_entities_nlp_default_disable_reaches_both_pipe_calls`, `test_extract_entities_nlp_skips_unused_pipes_and_reuses_cache`, `test_extract_entities_nlp_custom_disable_reaches_both_pipe_calls`, `test_extract_entities_nlp_normalizes_single_string_and_none`, `test_extract_entities_nlp_rejects_required_disable_before_spacy_load`, `test_extract_entities_nlp_reports_all_required_disabled_components`, `test_extract_entities_nlp_warns_for_unknown_disable_and_continues`, `test_extract_entities_nlp_different_disable_configs_do_not_reuse_cache`, `test_extract_entities_nlp_different_models_do_not_reuse_cache`, `test_extract_entities_nlp_equivalent_disable_configs_reuse_cache`, `test_extract_entities_nlp_noisy_terms_filters_matched_terms`, `test_extract_entities_nlp_signature_exposes_noisy_terms_only`, `test_extract_entities_nlp_rejects_the_noisey_terms_spelling`, `test_free_enrichment_extract_entities_nlp_rejects_noisey_terms_spelling`, `test_extract_entities_nlp_raises_for_bad_configuration`, `_install_fake_spacy`, `_install_matching_spacy`, `_run_fake_nlp`.
  - `tests/modules/enrichment/test_optional.py` (3 items): `test_categorize_by_reference_with_real_pyahocorasick`, `test_save_to_sql_with_real_sqlalchemy_and_sqlite`, `test_save_to_sql_propagates_database_errors`.
  - Enrichment-local helper (1 item): `_install` remains local to the enrichment targets; it is not promoted to shared infrastructure because both current consumers are within the same domain.

- **`tests/test_enrichment.py` (31 items):**
  - `tests/modules/enrichment/test_translate.py` (20 items): `test_default_providers_satisfy_the_protocols`, `test_documented_enrich_exports_include_the_default_providers`, `test_translate_categorical_column_constructs_the_default_google_translator`, `test_translate_categorical_column_accepts_a_plain_provider`, `test_translate_skips_and_does_not_cache_empty_translations`, `test_translate_batch_is_used_in_save_every_chunks`, `test_default_google_provider_uses_one_translator_per_thread`, `test_translate_conditional_column_sampling_is_reproducible`, `test_translate_conditional_column_translates_only_foreign_partitions`, `test_translate_conditional_column_accepts_a_generator`, `test_rate_limited_map_runs_calls_concurrently`, `test_rate_limited_map_spaces_call_starts`, `test_rate_limited_map_returns_exceptions_in_place`, `test_cached_map_checkpoints_skips_and_retries_failures`, `test_cached_map_multi_bucket_requires_every_bucket`, `test_cached_map_batch_failure_leaves_the_chunk_uncached`, `test_cached_map_rejects_batches_with_the_wrong_length`, `DictTranslator`, `BatchTranslator`, `_install_langdetect`.
  - `tests/modules/enrichment/test_geocode.py` (4 items): `test_fill_missing_coordinates_constructs_the_default_nominatim_geocoder`, `test_fill_missing_coordinates_accepts_a_plain_provider`, `test_geocoding_errors_are_not_cached`, `DictGeocoder`.
  - `tests/modules/enrichment/test_currency.py` (6 items): `test_convert_to_usd_constructs_the_default_yfinance_rate_source`, `test_convert_to_usd_downloads_once_per_currency`, `test_convert_to_usd_does_not_cache_provider_failures`, `test_yfinance_rate_source_computes_yearly_means_from_one_download`, `FakeRates`, `_install_currency_lookup`.
  - Enrichment-local helper (1 item): `_install` remains local to the enrichment targets; it is not promoted to shared infrastructure because both current consumers are within the same domain.

- **Files kept or moved whole (7 files):**
  - `tests/test_accessor.py` -> `tests/cross_cutting/accessor/test_accessor.py` (12 items: 11 tests + `_Translator`, unchanged)
  - `tests/test_fill_missing_from.py` -> `tests/cross_cutting/workflows/test_fill_missing_from.py` (9 tests, unchanged base)
  - `tests/test_doc_drift.py` -> `tests/cross_cutting/contracts/test_doc_drift.py` (4 items: 3 tests + `ROOT`, unchanged)
  - `tests/test_equivalence.py` -> `tests/cross_cutting/equivalence/test_equivalence.py` (19 items: 9 tests, 8 helpers, 2 constants, unchanged)
  - `tests/test_phase3_file_io.py` -> `tests/modules/io/test_io.py` (24 tests, all moved)
  - `tests/test_phase3_optional_integrations.py` -> `tests/modules/enrichment/test_optional.py` (15 items: 13 tests + `_sqlite_arguments`, `_fetch_rows`, all moved)
  - `tests/test_inplace_deprecation.py` -> `tests/cross_cutting/base_api/test_base.py` (11 items: 9 tests + `_frame`, `EARLY_EXITS`, all moved)

**Collection and definition-count reconciliation.** [BP] The current suite collects 528 test cases and defines 319 test functions. The split of `test_basedata_text_list_reshape_and_imputation_helpers` (in `tests/test_cleaning.py`) produces 3 focused single-assertion test functions (one for `split_list_objects` in `columns`, one for `extract_keywords` in `text`, and one for `fill_missing` in `stats`), increasing the collected test count by +2 and the function-definition count by +2. The expected post-migration suite therefore collects exactly 530 cases and defines 321 test functions, assuming no other parametrization or test-function changes. All 528 original cases, scenarios, parametrized combinations, and assertions are preserved in full.

#### 8.9.8 Phased migration plan with verification gates

**Planning authority and non-execution.** This plan is future planning only and MUST NOT be executed without supervisor approval. No test file was moved or renamed in this task. Each migration step below represents an independent, reviewable change with strict verification gates. [BP]

1. **Step 1: Create shared infrastructure and module scaffolding.**
   - Do not create a `tests/shared/` file unless the migration audit verifies a distinct-domain reusable consumer.
   - Create `tests/modules/caching/helpers.py` for caching-only `_seed_cache_entries` and `_rows`; keep domain-specific fakes, `OUTPUT_COLUMNS`, `PARITY_DATA`, and `EXPECTED_STATS_KEYS_BY_KIND` local.
   - Create module directories under `tests/modules/` and `tests/cross_cutting/`.
   - *Verification gate:* Full suite green; collected count 528; `ruff check tests` clean.

2. **Step 2: Split `tests/test_caching.py` into `tests/modules/caching/`.**
   - Move persistence tests to `tests/modules/caching/test_persistence.py` (30 items).
   - Move migration and schema tests to `tests/modules/caching/test_migration.py` (21 items).
   - Move concurrency tests to `tests/modules/caching/test_concurrency.py` (11 items).
   - Create `tests/modules/caching/conftest.py` for isolated cache directory fixtures.
   - Remove original `tests/test_caching.py`.
   - *Verification gate:* Full suite green; collected count 528; `ruff check tests` clean; actual caching files < 800 lines.

3. **Step 3: Split `tests/test_profile.py` into `tests/modules/profile/`.**
   - Move general statistics and reports to `tests/modules/profile/test_profile_general.py` (15 items).
   - Move edge cases to `tests/modules/profile/test_profile_edges.py` (8 items).
   - Move contract stability tests to `tests/modules/profile/test_profile_contract.py` (6 items).
   - Remove original `tests/test_profile.py`.
   - *Verification gate:* Full suite green; collected count 528; `ruff check tests` clean; actual profile files < 800 lines.

4. **Step 4: Split hierarchical stats and migrate stats module.**
   - Split `tests/test_hierarchical_stats.py` into `test_hierarchical_stats.py`, `test_hierarchical_stats_mode.py`, and `test_hierarchical_stats_flags.py` under `tests/modules/stats/`.
   - Relocate `tests/test_fill_missing_from.py` to `tests/cross_cutting/workflows/test_fill_missing_from.py`.
   - *Verification gate:* Full suite green; collected count 528; `ruff check tests` clean; actual stats files < 800 lines.

5. **Step 5: Split enrichment and integrations into `tests/modules/enrichment/`.**
   - Split `tests/test_enrichment.py` and `tests/test_integrations.py` into `test_translate.py`, `test_geocode.py`, `test_currency.py`, `test_nlp.py`, and `test_optional.py`.
   - Create `tests/modules/enrichment/conftest.py` for mock provider fixtures.
   - Remove original `test_enrichment.py` and `test_integrations.py`.
   - *Verification gate:* Full suite green; extras job green; collected count 528; `ruff check tests` clean; actual enrichment files < 800 lines.

6. **Step 6: Dissolve `tests/test_phase3_file_io.py` into `tests/modules/io/`.**
   - Move all 24 tests from `tests/test_phase3_file_io.py` to `tests/modules/io/test_io.py`.
   - Remove `tests/test_phase3_file_io.py`.
   - *Verification gate:* Full suite green; collected count 528; `ruff check tests` clean; `test_io.py` < 800 lines.

7. **Step 7: Dissolve `tests/test_phase3_transformations.py` and `test_phase3_input_validation.py`.**
   - Route items to `tests/modules/columns/test_columns.py`, `tests/modules/text/test_text.py`, `tests/modules/stats/test_fill_missing.py`, `tests/cross_cutting/accessor/test_parity.py`, `tests/cross_cutting/base_api/test_base.py`, and `tests/cross_cutting/workflows/test_fill_missing_from.py`.
   - Preserve all 20 strict-xfail cases citing `docs/temb/TEST-02-phase1-audit.md` (8 in `tests/cross_cutting/base_api/test_base.py`, 12 in `tests/modules/stats/test_fill_missing.py`).
   - Update `PHASE3_TESTS` manifest in `tools/verify_installed_wheel.py` in the same change.
   - Remove `test_phase3_transformations.py` and `test_phase3_input_validation.py`.
   - *Verification gate:* Full suite green; wheel verifier passes; collected count 528; `ruff check tests` clean.

8. **Step 8: Split `tests/test_cleaning.py` and merge `tests/test_inplace_deprecation.py`.**
   - Merge `test_inplace_deprecation.py` into `tests/cross_cutting/base_api/test_base.py`.
   - Split `test_cleaning.py` into its component targets. Multi-concept test `test_basedata_text_list_reshape_and_imputation_helpers` is partitioned into 3 tests (+2 collected items).
   - Remove `test_cleaning.py` and `test_inplace_deprecation.py`.
   - *Verification gate:* Full suite green; collected count reaches exactly 530 (528 + 2 from split); 321 test functions defined (319 original definitions plus 2 from the split); 990 `assert` statements preserved; 100 `pytest.param` cases preserved; `ruff check tests` clean; actual target files < 800 lines.

9. **Step 9: Relocate contracts, accessor, and equivalence to `tests/cross_cutting/`.**
   - Move `tests/test_accessor.py` to `tests/cross_cutting/accessor/test_accessor.py`.
   - Move `tests/test_doc_drift.py` to `tests/cross_cutting/contracts/test_doc_drift.py` and update root path resolution.
   - Move `tests/test_equivalence.py` to `tests/cross_cutting/equivalence/test_equivalence.py`.
   - Create `benchmarks/reference_impls.py`, extract the benchmark reference implementations into it, and update both benchmark scripts and equivalence tests to import it.
   - *Verification gate:* Full suite green; `pytest tests/cross_cutting/contracts/test_doc_drift.py` green; benchmark import works without importing a test module; collected count 530.

10. **Step 10: Suite-wide audit and verification.**
    - Re-run full test suite across all environments, run `tools/verify_installed_wheel.py`, and verify benchmark execution.
    - Verify line counts across all test files (`wc -l tests/modules/*/*.py tests/cross_cutting/*/*.py tests/shared/*.py`) confirming 100% compliance with the 800-line limit.
    - Confirm 20 strict-xfail cases and 17 pandas-2 skips are intact.
    - *Verification gate:* 530 collected cases; 0 warnings/errors; wheel verification green; benchmarks green; clean git diff; no stale test-path or test-module imports.

**Preservation invariants.** [BP] The migration plan preserves every test function, helper, class, and constant; all 990 `assert` statements; all 100 `pytest.param` cases; and all 20 strict `xfail` cases with `strict=True`. Redundancy cleanup MUST NOT be used to eliminate tests or assertions.

#### 8.9.9 Non-authorization of migration

The migration described in §8.9.8 is future design and planning only and is **not authorized**. It MUST NOT be performed until explicitly approved by the supervisor. Until authorization is granted, all 15 test files remain in their current flat layout directly under `tests/`, and the hierarchical architecture approved here serves as the authoritative design model for all new work. No test file was created, moved, renamed, or deleted by this documentation update, and no production code, configuration, CI workflow, or dependency was modified. [BP]


---

## 9. CI/CD gates

### 9.1 Current state (verified)

`.github/workflows/test.yml` defines four jobs: [BP]

| Job | Runner | Steps |
| --- | --- | --- |
| `lint` | ubuntu-latest, Python 3.11 | `ruff check bynat tests benchmarks` |
| `typecheck` | ubuntu-latest, Python 3.11 | install package, mypy, pandas-stubs; `python -m mypy` |
| `test` | ubuntu-latest and windows-latest, Python 3.11 and 3.13 | install package, pytest, build; `python -m build`; `python -m compileall -q bynat`; `python -m pytest -q` |
| `test-extras` | ubuntu-latest, Python 3.11 | install `".[categorization,sql]"`; `python -m pytest -q -rs` |

`.github/workflows/publish.yml` builds and publishes to PyPI manually. [BP]

### 9.2 Required gates (target)

A PR MUST pass every required gate before merge. [BP]

| Gate | Trigger | Command | Required | Notes |
| --- | --- | --- | --- | --- |
| Lint | push, PR | `ruff check bynat tests benchmarks` | Yes | Existing |
| Type check | push, PR | `python -m mypy` | Yes | Existing |
| Unit and integration | push, PR | `python -m pytest -q` on Ubuntu and Windows × 3.11, 3.13 | Yes | Existing; no undocumented skips |
| Coverage | push, PR | `python -m pytest --cov=bynat --cov-branch --cov-report=term-missing --cov-report=xml` | Yes, from Phase 2 | Ubuntu 3.11; `fail_under` from §7.3 |
| Build and install | push, PR | `python -m build`; install the wheel in a clean virtualenv; run the suite against it | Yes, from Phase 3 | Catches missing files and dependency gaps |
| Extras matrix | push, PR | One job per extra, or a matrix; `pytest -m "extras"` after optional-dependency tests carry the `extras` marker | Yes, from Phase 2 | Each extra is exercised at least once |
| Property (extended) | scheduled | `python -m pytest -m property --hypothesis-profile=extended` | Yes, from Phase 2 | Scheduled, not a PR gate |
| Mutation | scheduled | Cosmic Ray on the §7.5 scope | Advisory, from Phase 3 | Weekly or pre-release |
| Compile | push, PR | `python -m compileall -q bynat tests` | Yes | Existing (package only); extend to tests |
| Doc drift | push, PR | `python -m pytest tests/cross_cutting/contracts/test_doc_drift.py` after the hierarchical migration | Yes | Existing contract test; current pre-migration path is `tests/test_doc_drift.py` |

### 9.3 Windows and mutation tooling

- mutmut requires a POSIX-like environment because it uses fork. On Windows it MUST run under WSL, or the mutation job MUST use Ubuntu. Never make a Windows mutation run a merge requirement. [SB] (mutmut documentation) [BP]
- Cosmic Ray is pure Python and runs on `windows-latest`. Prefer it for cross-platform mutation runs. [SB] (Cosmic Ray) [BP]
- Tests MUST NOT assume POSIX paths, POSIX line endings, or POSIX-only modules. Use `pathlib` and `tmp_path`. [SB] (PyPA: avoid platform details) [BP]
- Cache and file tests MUST pass on Windows with the same assertions as on Ubuntu. [BP]

### 9.4 Branch protection

Once Phase 2 is adopted, the repository administrator SHOULD require the lint, type check, all four test matrix legs, and the adopted coverage gate before merge. Before Phase 2, only the currently configured gates can be required. [BP]

### 9.5 Release gate

A release MUST NOT be published unless all required gates are green on the release commit. From Phase 3, the package MUST also have been installed from the built wheel in a clean environment. Publishing to TestPyPI before PyPI is recommended. [SB] (PyPA packaging tutorial)

---

## 10. AI agent protocol

This section is binding on any AI agent or automated tool that writes, modifies, or runs tests in this repository. [BP]

### 10.1 Before writing tests

1. Read this document and `docs/ROADMAP.md` §2 and §6. [BP]
2. Read the behavior in `README.md` and the docstrings of the function under test. [BP]
3. Read the existing tests for that function before adding or changing anything. [BP]
4. Identify the public entry point: class method, accessor, or shared function. Test through it. [BP]

### 10.2 While writing tests

5. Follow §4 and §5. Every test MUST be able to fail. [BP]
6. Use the existing injection points (`provider=`, `cache_manager=`, `with_cache(...)`) and fake modules. Never call real services. [BP]
7. Keep tests deterministic and independent. [BP]
8. One behavior per test. Do not combine unrelated assertions to save time. [BP]
9. Do not add test-only hooks to production code. [BP]
10. Do not modify production code, configuration, or existing tests to make a test pass. If a test fails, the code or the test is wrong; report which and why. [BP]

### 10.3 Before reporting done

11. Run the tests you changed and the full suite. Record the exact commands and their real output. Never paste invented results. [BP]
12. If you claim a coverage or mutation number, run the tool and paste its output. [BP]
13. If you changed behavior, confirm the CHANGELOG and README are accurate; if they are not, report it instead of silently editing them. [BP]
14. Report the files changed, the commands run, the results, and any remaining risk. [BP]

### 10.4 Prohibited shortcuts

15. Do not add `skip`, `xfail`, `filterwarnings("ignore")`, or coverage exclusions to make a run green. If a skip or xfail is genuinely needed, give a reason and link an issue. [BP]
16. Do not weaken or delete an existing assertion. If the assertion is wrong, say so and propose the correction. [BP]
17. Do not assert current behavior as correct merely because it is current. If the behavior looks like a bug, flag it. [BP]
18. Do not commit unless explicitly asked. [BP]

---

## 11. Human review checklist

A reviewer of a test PR MUST confirm the following. [BP]

- [ ] Every new or changed behavior has a test that fails without the change.
- [ ] Every test can fail; no test only calls the code.
- [ ] Tests assert observable behavior, not private state or internal call counts, unless §4 A-3 allows it.
- [ ] No network, secrets, credentials, or user files are used.
- [ ] Tests are deterministic: seeded randomness, no clock or locale dependence.
- [ ] Tests are independent: no shared mutable state, no order dependence.
- [ ] `pd.testing` / `np.testing` helpers are used with explicit tolerances and default strictness.
- [ ] The DataFrame cases in §5.1 that apply are covered.
- [ ] The transformation requirements in §6 that apply are covered.
- [ ] Errors are asserted with `pytest.raises(..., match=...)`; warnings with `pytest.warns(...)` or an error filter.
- [ ] No blanket skips, xfails, warning filters, or coverage exclusions.
- [ ] Existing tests were not weakened, deleted, or broadened.
- [ ] New public API extends the contract tests (`test_doc_drift.py`, `test_accessor.py`) and each applicable requirement ID from §5/§6 is referenced in the test name, comment, or a maintained coverage matrix.
- [ ] Property tests state meaningful invariants and are not over-constrained.
- [ ] Coverage did not decrease; new lines are covered or exclusions are justified. (Applicable from Phase 2.)
- [ ] Mutation survivors, if a run exists, are triaged. (Applicable from Phase 3.)
- [ ] CHANGELOG and README are updated when behavior changed.
- [ ] CI is green on all required gates and matrix legs.

---

## 12. Phased adoption roadmap

The phases are ordered by value and cost. A phase is adopted when its "Done when" list is met; until then, its targets are not binding. [BP]

### Phase 0 — Stop the bleeding

- Apply §4 to all new tests.
- Fix the tests that cannot fail: `tests/test_enrichment.py::test_translate_conditional_column_accepts_a_generator` currently has no assertion. (`tests/test_inplace_deprecation.py::test_inplace_false_and_default_do_not_warn` uses the §4 A-1 warning-escalation helper and can fail.)
- Add a contract test that imports and asserts the documented caching exports (`CacheManager`, `shared_cache_manager`, `CACHE_DIR_ENV_VAR`, `DEFAULT_CACHE_DIR`) and the enrichment default `NominatimGeocoder`, without expanding the `bynat.cleaning` namespace.
- Remove the unused `tmp_path` fixtures (14 test functions) or use them.
- Add the missing transformation cases from §6, prioritizing `fill_missing_from` leakage, unseen groups, and `min_samples` boundaries.
- Resolve the validation contracts identified by MS-3a and S-4/ML-2 for outlier `min_samples` values and variadic methods that absorb `inplace`.
- Add the missing DataFrame cases from §5.1.

**Done when.** No test function lacks an assertion; every applicable requirement ID in §5/§6 is mapped to a named test, comment, or maintained coverage matrix; the documented caching and enrichment export paths are pinned by a contract test; no unused fixture remains. [BP]

### Phase 1 — Make the suite measurable

- Add `[tool.pytest.ini_options]` with `testpaths`, `addopts`, and registered markers.
- Add `tests/conftest.py` with shared fixtures, marker registration, and Hypothesis profiles.
- Add coverage measurement with pytest-cov; record the baseline. No gate yet.
- Resolve the import-mode ambiguity (`--import-mode=importlib` or `src/` layout).

**Done when.** `pytest --cov` runs locally and in CI; the baseline is recorded in the PR that adds it. [BP]

### Phase 2 — Gates and properties

- Enable the coverage gate at the Phase 1 baseline, then at the Phase 2 target in §7.3.
- Add property tests for the §7.6 invariants.
- Complete the extras matrix so every extra is exercised.
- Add equivalence tests for any optimization that lacks one.
- Run the extended Hypothesis profile on a schedule.

**Done when.** The coverage gate is green; at least one property test exists per transformation in §6; every extra has CI coverage. [BP]

### Phase 3 — Artifacts and mutation

- Add the build-and-install job: build a wheel, install it in a clean virtualenv, run the suite against it.
- Declare Cosmic Ray (and optionally mutmut) in the `dev` extra and add the Cosmic Ray session config.
- Add the scheduled Cosmic Ray run on the §7.5 scope; upload the report.
- Triage the first survivor set.

**Done when.** The wheel job is green; Cosmic Ray is declared and configured; a mutation report exists and its survivors are triaged. [BP]

### Phase 4 — Raise the bar

- Raise coverage targets to Phase 3, then Phase 4.
- Add the mutation target as an advisory gate.
- Add the test suite to the mypy scope.
- Re-run the DataFrame and transformation matrices against the full public API.

**Done when.** Targets have held for two consecutive releases. [BP]

---

## 13. References

Stable URLs, grouped by topic. Every [SB] and [RP] tag in this document points here.

### pytest

- [pytest — Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) — official docs.
- [pytest — How to parametrize fixtures and test functions](https://docs.pytest.org/en/stable/how-to/parametrize.html) — official docs.
- [pytest — How to write and report assertions in tests](https://docs.pytest.org/en/stable/how-to/assert.html) — official docs.
- [pytest — How to capture warnings](https://docs.pytest.org/en/stable/how-to/capture-warnings.html) — official docs.
- [pytest — How to use skip and xfail](https://docs.pytest.org/en/stable/how-to/skipping.html) — official docs.
- [pytest — How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) — official docs.
- [pytest — Typing in pytest](https://docs.pytest.org/en/stable/explanation/types.html) — official docs.

### Hypothesis

- [Hypothesis — Configuring test settings](https://hypothesis.readthedocs.io/en/latest/tutorial/settings.html) — official docs.
- [Hypothesis — Settings reference](https://hypothesis.readthedocs.io/en/latest/settings.html) — official docs.
- [Hypothesis — Flaky failures](https://hypothesis.readthedocs.io/en/latest/tutorial/flaky.html) — official docs.
- [Hypothesis — Replaying failed tests](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html) — official docs.
- [Hypothesis — Domain and distribution](https://hypothesis.readthedocs.io/en/latest/explanation/domain.html) — official docs.
- [Hypothesis — Stateful tests](https://hypothesis.readthedocs.io/en/latest/stateful.html) — official docs.
- [Hypothesis — First-party extensions](https://hypothesis.readthedocs.io/en/latest/extras.html) — official docs.

### Coverage

- [coverage.py — Branch coverage measurement](https://coverage.readthedocs.io/en/latest/branch.html) — official docs.
- [coverage.py — Measurement contexts](https://coverage.readthedocs.io/en/latest/contexts.html) — official docs.
- [coverage.py — Messages and warnings](https://coverage.readthedocs.io/en/latest/messages.html#warning-no-sysmon) — official explanation of the sysmon limitation.
- [coverage.py — Excluding code from coverage.py](https://coverage.readthedocs.io/en/latest/excluding.html) — official docs.
- [coverage.py — Configuration reference](https://coverage.readthedocs.io/en/latest/config.html) — official docs.
- [pytest-cov — Configuration](https://pytest-cov.readthedocs.io/en/latest/config.html) — official docs.
- [pytest-cov — Reporting](https://pytest-cov.readthedocs.io/en/latest/reporting.html) — official docs.

### Mutation testing

- [Cosmic Ray — Theory](https://cosmic-ray.readthedocs.io/en/latest/theory.html) — tool docs.
- [Cosmic Ray — Concepts](https://cosmic-ray.readthedocs.io/en/latest/concepts.html) — tool docs.
- [Cosmic Ray — Tutorial: The basics](https://cosmic-ray.readthedocs.io/en/latest/tutorials/intro/index.html) — tool docs.
- [mutmut — Python mutation tester documentation](https://mutmut.readthedocs.io/en/latest/) — tool docs.

- [Mutation testing in the wild: findings from GitHub](https://link.springer.com/article/10.1007/s10664-022-10177-8) — peer-reviewed paper.
- [A Systematic Literature Review of Techniques and Metrics to Reduce the Cost of Mutation Testing](https://www.albany.edu/faculty/offutt/research/papers/SLR-CostReductionMutation.pdf) — peer-reviewed paper.
- [Static and Dynamic Comparison of Mutation Testing Tools for Python](https://dl.acm.org/doi/10.1145/3701625.3701659) — peer-reviewed paper.

### Packaging guidance

- [PyPA — Supporting downstream packaging](https://packaging.python.org/en/latest/discussions/downstream-packaging/) — official guidance.
- [PyPA — Packaging Python Projects tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/) — official guidance.
- [PyPA packaging — Development: Getting started](https://packaging.pypa.io/en/stable/development/getting-started.html) — official project guidance.

### Scientific Python and NumPy

- [NumPy — Testing guidelines](https://numpy.org/doc/stable/reference/testing.html) — project guidance.
- [NumPy — numpy.testing.assert_allclose](https://numpy.org/doc/stable/reference/generated/numpy.testing.assert_allclose.html) — official docs.
- [pandas — Testing](https://pandas.pydata.org/docs/reference/testing.html) — official testing helpers.
- [Scientific Python Development Guide — Testing recommendations](https://learn.scientific-python.org/development/principles/testing/) — community guidance.
- [Scientific Python Development Guide — Testing with pytest](https://learn.scientific-python.org/development/guides/pytest/) — community guidance.
- [pyOpenSci — Write tests for your Python package](https://www.pyopensci.org/python-package-guide/tests/write-tests.html) — community guidance.
- [SciPy — Running SciPy tests locally](https://docs.scipy.org/doc/scipy/dev/contributor/devpy_test.html) — project guidance.
- [Falsify your Software: validating scientific code with Hypothesis](https://proceedings.scipy.org/articles/Majora-342d178e-016.pdf) — peer-reviewed proceedings.

### Repository documents

- [`README.md`](../README.md) — behavior documentation.
- [`docs/ROADMAP.md`](ROADMAP.md) — principles, decisions, definition of done.
- [`CHANGELOG.md`](../CHANGELOG.md) — behavior changes.
