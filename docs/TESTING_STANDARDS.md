# bynat Testing Standards and Constitution

This document is the authoritative testing constitution for the `bynat` project. It establishes an enforceable, hierarchical standard defining how tests must be designed, organized, implemented, verified, and integrated into Continuous Integration (CI). Every contributor, reviewer, and automated agent working on `bynat` is bound by this constitution.

**Normative language.** The keywords `MUST`, `MUST NOT`, `REQUIRED`, `SHALL`, `SHALL NOT`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and `OPTIONAL` in this document are to be interpreted as described in RFC 2119. Statements without an RFC 2119 keyword represent explanatory context or architectural rationale, not independent requirements.

**Basis tags.**
- **[SB]** — Source-backed practice derived from authoritative software testing standards, Python Packaging Authority (PyPA) guidelines, or official upstream library documentation (pytest, Hypothesis, coverage.py, Cosmic Ray, NumPy, pandas).
- **[BP]** — bynat policy established by project architectural decisions.
- **[RP]** — Recommended engineering practice from scientific Python community guidelines.

---

## 1. Preamble, Purpose, Scope, and Precedence

### 1.1 Purpose

This testing constitution establishes executable, automated specifications for all library behaviors, prevents functional and performance regressions prior to release, and provides an objective standard against which test suite quality can be audited. All tests must be written against production behavior as defined: the public class API, accessor extensions, standalone utility and transformation functions, SQLite caching infrastructure, and optional service integrations. [BP]

### 1.2 Scope

**In scope.** [BP]
- All production code under the primary package directory (`bynat/`).
- All automated tests, fixtures, test doubles, and shared helpers under the test directory (`tests/`).
- Performance benchmark suites and reference implementations under `benchmarks/`.
- CI automation workflows under `.github/workflows/`.
- Developer tooling supporting testing and packaging verification under `tools/`.

**Out of scope.** [BP]
- Release distribution logistics beyond CI test gates (PyPI token management, changelog publishing).
- Upstream third-party package dependency release cycles.
- Security vulnerability scanning of external infrastructure, except that tests MUST NOT leak credentials, execute unauthenticated network requests, or write outside sandboxed directories.
- Testing internal behaviors of third-party dependencies themselves.

### 1.3 Applies to

- Every pull request introducing, modifying, or refactoring production code, public documentation, or tests.
- Every automated CI matrix execution, scheduled quality job, and release validation run.
- Every human contributor, code reviewer, and autonomous AI engineering agent modifying this repository.

### 1.4 Precedence and Relationship to Other Documents

- **Constitutional Precedence.** This document represents the binding, authoritative testing policy. If a project roadmap document (`docs/ROADMAP.md`), issue description, or planning draft conflicts with this document, this constitution controls. Discrepancies in secondary documents MUST be corrected to align with this constitution before corresponding code merges. [BP]
- **Documentation Parity.** Public documentation (`README.md`) documents user-facing behavior. A test that contradicts documented behavior indicates a defect in either the test or the documentation; both MUST be reconciled in the same pull request. [BP]
- **Changelog Integrity.** Behavioral changes, deprecations, and breaking modifications require corresponding entries in `CHANGELOG.md`. Test-only organizational refactors that preserve observable behavior do not require changelog entries. [BP]

---

## 2. Authority Level 1 — General Testing Principles and Rules

The rules in this section represent universal, repository-independent software testing standards. They MUST be written without references to specific project filenames, directory paths, or package names.

### 2.1 General Testing Philosophy

- **GEN-PHIL-1: Tests are Executable Specifications.** Automated tests MUST serve as the authoritative, executable specification of observable software contracts. Any behavior promised by user-facing documentation MUST be pinned by automated tests. [SB]
- **GEN-PHIL-2: Single Observable Behavior per Test.** Each test function MUST verify exactly one observable behavior, boundary condition, or invariant. A test MUST fail for exactly one logical reason, and its identifier MUST clearly state that reason. [SB]
- **GEN-PHIL-3: Outside-In Testing Hierarchy.** Test suites SHOULD prioritize public interface contracts before internal integration pathways, and component integrations before isolated unit logic. Tests MUST verify observable outcomes rather than private implementation mechanics. [RP]
- **GEN-PHIL-4: Falsifiability Requirement.** Every test MUST be demonstrably capable of failing. A test that passes unconditionally regardless of underlying logic is invalid and MUST be rejected. [SB]
- **GEN-PHIL-5: Mandatory Regression Testing.** Every defect fix MUST be accompanied by an automated regression test that fails on the unfixed baseline and passes upon applying the fix. [SB]
- **GEN-PHIL-6: Determinism and Environment Invariance.** Tests MUST be deterministic. They MUST NOT depend on unseeded pseudorandomness, wall-clock time, system timezone, filesystem iteration order, or ambient network access. Given identical inputs, tests MUST produce identical results across all supported execution environments. [SB]
- **GEN-PHIL-7: Coverage as an Execution Floor, Not Quality Proof.** Code coverage metrics quantify statement and branch execution; they do not quantify assertion validity or behavioral correctness. High coverage is a necessary prerequisite, never proof of comprehensive testing. [SB]
- **GEN-PHIL-8: Explicit Backward Compatibility Verification.** Tests pinning established public contracts MUST NOT be modified or relaxed without an explicit, documented, and approved behavioral change. [BP]
- **GEN-PHIL-9: Core Test Quality Attributes.** Every test MUST satisfy seven fundamental quality attributes:
  1. *Correct*: Passes on correct code and fails on incorrect code.
  2. *Independent*: Executes in any order without dependencies on preceding or succeeding tests.
  3. *Deterministic*: Generates identical results on every run across all platforms.
  4. *Readable*: Clearly conveys the contract being verified without requiring inspection of implementation code.
  5. *Specific*: Asserts precise values, types, or exceptions rather than vague state changes.
  6. *Fast*: Executes efficiently to maintain interactive developer velocity.
  7. *Maintainable*: Uses clear abstractions and avoids fragile coupling to internal implementation details. [BP]

### 2.2 Universal Test Types

- **GEN-TYPE-1: Unit Tests.** Unit tests verify a single function, method, or class in strict isolation. External collaborators, persistent storage, and environment resources MUST be replaced with in-memory doubles or stubbed boundaries. Inputs SHOULD be minimal and constructed directly within the test. [SB]
- **GEN-TYPE-2: Integration Tests.** Integration tests verify interactions across two or more internal subsystems, persistent databases, filesystem boundaries, or third-party adapters. All persistent state MUST be isolated to sandboxed temporary workspaces and torn down completely upon completion. [SB]
- **GEN-TYPE-3: API and Contract Tests.** Contract tests verify that public entry points, callable signatures, type annotations, stub files, docstring synchronizations, and output schemas conform to published specifications. Contract tests MUST assert structural stability and schema invariants. [BP]
- **GEN-TYPE-4: Property-Based Tests.** Property-based tests verify algebraic, relational, or structural invariants across large sets of generated inputs. Generators MUST cover valid domains, edge cases, and boundary values. Property-based tests MUST execute with deterministic seed management and automated shrinking. [SB]
- **GEN-TYPE-5: Regression Tests.** Regression tests reproduce a specific, previously identified defect. They MUST assert the documented correct behavior rather than merely pinning the historical buggy output. [SB]
- **GEN-TYPE-6: Mutation Testing.** Mutation testing evaluates test suite effectiveness by injecting syntactic faults into source code and verifying that existing tests detect and kill the mutants. Surviving mutants indicate deficiencies in assertion density or test coverage. [SB]
- **GEN-TYPE-7: Equivalence Tests.** When an algorithm is refactored for performance optimization, equivalence tests MUST prove that the optimized implementation produces identical outputs to a verified reference implementation across representative data variations. [BP]
- **GEN-TYPE-8: Characterization Tests.** When legacy or undocumented behavior must be preserved during refactoring, characterization tests record existing operational behavior. Such tests MUST be clearly identified and subsequently refined into normative contract tests. [BP]

### 2.3 Universal Anti-Cheating Rules (A-1 through A-12)

These rules prevent false confidence created by invalid, misleading, or ineffective tests.

#### A-1: A Test MUST Be Able to Fail
Every test function MUST execute at least one explicit assertion or assertion helper (e.g. `assert`, framework-provided error assertion contexts, or warning capture filters). A test that merely executes production code without asserting observable results is rejected. [BP]

- *Rejected Pattern:* Invoking a function without asserting its return value, side effects, or error conditions.
- *Required Pattern:* Explicitly asserting output structure, return values, mutated state, or raised exceptions.

#### A-2: Never Replace the Unit Under Test
Tests MUST NOT monkeypatch, stub, or mock the primary function, method, or class undergoing verification. Test doubles MUST be applied only at external service boundaries, network interfaces, or third-party adapters. [BP]

- *Rejected Pattern:* Mocking the function under test to return an expected constant.
- *Required Pattern:* Invoking the real production code while stubbing only external, slow, or non-deterministic boundary dependencies.

#### A-3: Assert the Contract, Not the Implementation
Tests MUST assert observable public behaviors, outputs, and contracts. Tests MUST NOT assert private internal object states, private attributes, or call counts of internal private functions unless such properties are an explicit part of the public specification. [BP]

- *Rejected Pattern:* Asserting that an internal helper was invoked a specific number of times during a standard public call.
- *Required Pattern:* Asserting that the public method returned the correct transformed data and schema.

#### A-4: No Blanket Exception Swallowing
Tests MUST NOT use broad exception catching (`except Exception:` or bare `except:`) to suppress unexpected errors. Tests verifying error conditions MUST use explicit exception assertion constructs targeting the exact expected exception type and matching error message patterns. [BP]

- *Rejected Pattern:* Wrapping an invocation in `try...except Exception: pass`.
- *Required Pattern:* Using explicit exception inspection contexts verifying exception type and message regex.

#### A-5: Skips and Xfails Need a Specific Justification and Strict Enforcement
Unconditional test skips and unexplained expected failures (`xfail`) are prohibited. Every skip MUST define an explicit condition and documented reason. Every `xfail` MUST reference an active issue tracker identifier and MUST be configured strictly (`strict=True`) so that unexpected passes fail the test run. [SB]

- *Rejected Pattern:* Adding `@pytest.mark.skip` or `@pytest.mark.xfail` without parameters, justification, or strict enforcement.
- *Required Pattern:* Adding `@pytest.mark.skipif(condition, reason="...")` or `@pytest.mark.xfail(strict=True, reason="Defect description; see issue #123")`.

#### A-6: Do Not Hide Warnings
Tests MUST NOT suppress warnings globally or use blanket warning ignore directives to conceal deprecation warnings or runtime flaws. Tests asserting warning-free behavior MUST escalate warnings to errors within their execution context; tests asserting warning contracts MUST explicitly capture and assert them. [SB]

- *Rejected Pattern:* Marking tests with `@pytest.mark.filterwarnings("ignore")`.
- *Required Pattern:* Using warning capture contexts or escalating warnings to errors via local filtering.

#### A-7: Determinism
Tests MUST NOT use unseeded random number generators, wall-clock timestamps, system locale dependencies, or unstable dictionary/set iteration orders in assertions. All random generators MUST be explicitly seeded. Collections with non-contractual ordering MUST be sorted before comparison. [SB]

- *Rejected Pattern:* Generating randomized inputs using unseeded global random calls.
- *Required Pattern:* Passing an explicit, seeded pseudorandom generator instance.

#### A-8: Independence and Isolation
Tests MUST NOT share mutable state across test boundaries. Module-level mutable variables, persistent disk files shared between cases, and unreset environment variables are prohibited. [SB]

- *Rejected Pattern:* Mutating a shared module-level dataset in one test and reading it in another.
- *Required Pattern:* Constructing fresh test inputs per test or using isolated, scoped fixtures with automatic teardown.

#### A-9: No Version Overfit
Tests MUST NOT assert brittle, implementation-dependent representations such as exact floating-point string representations, compiler-specific formatting, or exact upstream log strings. Floating-point comparisons MUST use tolerance-based assertions. Dtype checks MUST verify category semantics rather than platform-specific byte widths. [SB]

- *Rejected Pattern:* Asserting exact equality against a platform-dependent float representation.
- *Required Pattern:* Comparing numeric arrays using explicit relative and absolute tolerances (`assert_allclose`).

#### A-10: No Network Calls, Secrets, or Persistent User Environment Access
Standard test suites MUST NOT execute live network calls, access remote cloud services, read ambient user credentials, or modify files outside sandboxed temporary directories. All external network interactions MUST be replaced with offline test doubles. [SB]

- *Rejected Pattern:* Making HTTP requests to live endpoints during test execution.
- *Required Pattern:* Using offline mock adapters, in-memory fake servers, or injected test providers.

#### A-11: No Test-Only Hooks in Production Code
Production code MUST NOT include test-only flags, debug modes, or conditional logic that alters production behavior solely to facilitate test execution. Verification MUST rely on standard dependency injection points, public constructor arguments, or documented extension mechanisms. [BP]

- *Rejected Pattern:* Adding `if _test_mode:` checks to production source code.
- *Required Pattern:* Injecting custom providers or test doubles via documented constructor or method parameters.

#### A-12: Do Not Weaken Existing Tests
Contributors and agents MUST NOT delete existing assertions, loosen assertion tolerances, ignore dtypes, or broaden comparison flags simply to make failing tests pass. If production behavior changes intentionally, corresponding test updates MUST be justified and documented in the pull request. [BP]

- *Rejected Pattern:* Setting assertion comparison flags to ignore types or mismatches when a test fails.
- *Required Pattern:* Diagnosing and addressing the root cause in production logic or updating the contract test with explicit documentation.

### 2.4 General Test Design and Organization

- **GEN-DESIGN-1: Assertion Quality and Granularity.** Assertions MUST verify specific, meaningful properties of test outputs. Comparisons MUST verify data contents, shapes, labels, and types. [SB]
- **GEN-DESIGN-2: Tabular and Collection Comparison Standards.** When comparing structured data collections (e.g. tabular datasets, series, or structured arrays), tests MUST use dedicated framework comparison utilities rather than primitive boolean equality checks. Dedicated comparison utilities report granular diffs across labels, shapes, and values. [SB]
- **GEN-DESIGN-3: Error and Boundary Condition Testing.** Test suites MUST verify that invalid inputs, out-of-range parameters, and missing required arguments fail loudly with documented exception types and informative error messages. Valid but boundary inputs (e.g. empty collections, single-item collections) MUST be handled gracefully according to specification. [BP]
- **GEN-DESIGN-4: Immutability and Side-Effect Verification.** When a function specifies that input arguments remain unmodified, tests MUST assert that input objects remain strictly identical before and after invocation. [BP]
- **GEN-DESIGN-5: Fixture Lifecycle and Scope Isolation.** Test fixtures MUST use function-level scoping by default. Broader scopes (module, session) are permitted only for immutable, expensive-to-construct read-only resources. Fixtures that create temporary resources MUST bundle their own teardown logic using yield mechanisms. [SB]
- **GEN-DESIGN-6: Parametrization Clarity.** Parametrized tests MUST supply human-readable identifiers (`id="..."`) for each parameter set to ensure failure reports pinpoint the exact failing case. Parametrized inputs MUST be immutable or freshly instantiated per test iteration. [SB]
- **GEN-DESIGN-7: Optional Dependency and Environment Gating.** Tests requiring optional third-party packages MUST use standard framework skipping utilities to skip gracefully when dependencies are absent. [SB]
- **GEN-DESIGN-8: Discovery and Collection Integrity.** Test files and functions MUST follow consistent naming conventions to ensure recursive discovery engines collect all tests without requiring manual path enumeration. Test suites MUST pass collection without errors or warnings under strict discovery configurations. [SB]

---

## 3. Authority Level 2 — `bynat`-Specific Rules

This section contains mandatory, enforceable requirements specific to the `bynat` repository. Every rule possesses an explicit identifier and defines binding policy.

### 3.1 Test-Suite Architecture and Ownership (BYNAT-ARCH)

- **BYNAT-ARCH-1: Type-First Suite Layout.** The `tests/` directory MUST conform to the following type-first layout:
  1. `tests/conftest.py`: Root configuration, environment hooks, marker derivation, and suite-wide fixtures.
  2. `tests/unit/<responsibility>/`: Isolated unit tests grouped by functional responsibility, not as a mirror of the source layout.
  3. `tests/integration/<responsibility>/`: Cross-component, persistence, file I/O, and optional-dependency integration tests grouped by responsibility.
  4. `tests/contracts/{api,architecture,helpers}/`: Public API, architecture-boundary, and helper-contract tests.
  5. `tests/parity/{class_accessor,inplace}/`: Class-vs-accessor and in-place behavior parity tests.
  6. `tests/properties/`: Hypothesis property-based invariant tests.
  7. `tests/equivalence/`: Reference-equivalence tests, including `_bench_refs.py` re-exports.
  8. `tests/regression/tracked_defects/`: Regression tests pinning tracked defects.
  9. `tests/shared/`: Genuinely reusable test infrastructure shared across distinct domains. [BP]
- **BYNAT-ARCH-2: Type-Directory Ownership Rules.** Each test file under `tests/unit/<responsibility>/` or `tests/integration/<responsibility>/` MUST verify behavior of a single functional responsibility; unit tests isolate a function, method, or class, while integration tests exercise cross-component, persistence, file I/O, or optional-dependency boundaries. A test MAY exercise supporting internal dependencies only when directly supporting that primary responsibility. Type-directory tests MUST NOT own contracts belonging in `tests/contracts/`, `tests/parity/`, or `tests/regression/`. [BP]
- **BYNAT-ARCH-3: Specialized Type Ownership Rules.** Tests that verify public API or architecture boundaries MUST reside in `tests/contracts/<kind>/`; tests that assert parity between different APIs (e.g. `BaseData` vs `df.bynat`) or in-place behavior MUST reside in `tests/parity/<kind>/`; property-based invariants MUST reside in `tests/properties/`; reference-equivalence tests MUST reside in `tests/equivalence/`; and previously identified defects MUST reside in `tests/regression/tracked_defects/`. [BP]
- **BYNAT-ARCH-4: Size Ceiling and Responsibility Ownership.** A test file MUST NOT exceed **200 lines of code**. Test files MUST be split by functional responsibility and architectural ownership, never by line count alone: a file under `tests/unit/<responsibility>/` or `tests/integration/<responsibility>/` owns one functional responsibility, and a file under `tests/contracts/<kind>/`, `tests/parity/<kind>/`, or `tests/regression/tracked_defects/` owns one cross-component contract. A file that groups several responsibilities because they share a feature (for example, one `inplace` file spanning columns, text, statistics, and enrichment) MUST NOT be created; the shared contract belongs in `tests/parity/inplace/` and responsibility-specific coverage belongs in the owning unit or integration directory. Exceeding the ceiling requires a justification recorded in the file that names the single responsibility which cannot be split without breaking ownership or fixture reuse. "These tests all concern the same feature" is not sufficient justification, and a file that is oversized only because it was never split is a defect, not an exception. [BP]
- **BYNAT-ARCH-4a: Size-Ceiling Adoption Backlog.** Test files that currently exceed the `BYNAT-ARCH-4` ceiling are a tracked backlog (kept in the issue tracker, not in this document), not sanctioned exceptions: each MUST be split by functional responsibility the next time it is substantively modified, and any file still over the ceiling after that MUST carry the recorded justification `BYNAT-ARCH-4` requires. [BP]
- **BYNAT-ARCH-5: Conftest Scoping and `tests/shared/` Admission Gate.**
  - Root `tests/conftest.py` is reserved exclusively for suite-wide configuration and universal fixtures.
  - Type-local `conftest.py` files (e.g. `tests/integration/conftest.py`, `tests/integration/enrichment/conftest.py`) are permitted only when justified by type-scoped fixtures (e.g. SQLite handles, provider fakes).
  - Helper code, constants, or fixtures MAY be admitted to `tests/shared/` ONLY when verified to have two or more consumers across distinct architectural domains. Domain-local helpers MUST remain within their responsibility directory in `helpers.py` (e.g. `tests/integration/caching_persistence/helpers.py`, `tests/integration/enrichment/helpers.py`, `tests/unit/profiling/helpers.py`). [BP]
- **BYNAT-ARCH-6: Prohibition of Cross-Test Module Imports.** A test file (`test_*.py`) MUST NOT import from another test file (`test_*.py`). Shared helper functions, classes, and constants MUST be defined in dedicated helper modules (`helpers.py`, `conftest.py`, or `tests/shared/`). [BP]
- **BYNAT-ARCH-7: Naming Standards.** Test files MUST follow the pattern `test_<topic>.py`. Test functions MUST follow the pattern `test_<module>_<behavior>_<condition>`. New test functions MUST NOT include docstrings; intent MUST be communicated via the function name or concise inline comments. [SB]
- **BYNAT-ARCH-8: Benchmark Reference Isolation.** Pre-optimization reference implementations MUST reside in `benchmarks/reference_impls.py` and be re-exported for testing through `tests/equivalence/_bench_refs.py`. Benchmark scripts under `benchmarks/` MUST NOT import from `tests/`, and test modules MUST NOT import benchmark execution scripts. [BP]
- **BYNAT-ARCH-9: Test Data Management.** All test files, databases, and serialization outputs MUST be written to `tmp_path`. Tests MUST NOT read application data from the repository checkout except for declared static packaging artifacts (`bynat/py.typed`). [BP]
- **BYNAT-ARCH-10: Prohibition of Row-Wise Iteration in Data Paths.** Production transformation and cleaning paths MUST NOT use row-wise iteration (`apply(axis=1)`, `iterrows()`, `itertuples()`). Where row-wise iteration is an architectural concern, tests MUST enforce vectorized execution via AST inspection or execution guards. [BP]
- **BYNAT-ARCH-11: Functionality-Oriented Subdirectory Grouping.** When multiple test files cover the same function, type, or closely related functionality within a module or topic directory, they MUST be grouped inside a dedicated subdirectory named after the functionality being tested (e.g. `caching_persistence/`, `caching_concurrency/`, and `caching_migration/` under `tests/integration/`, `hierarchical_stats/` and `imputation/` under `tests/unit/`, and `class_accessor/` and `inplace/` under `tests/parity/`). Directory names MUST reflect the target functionality, and single test files that already cover a distinct responsibility MUST remain directly in their parent directory without introducing unnecessary nesting. [BP]
- **BYNAT-ARCH-12: Test Hierarchy Follows Functional Relationships.** The `tests/` tree is organized by the responsibilities the tests cover and by how closely those responsibilities are related. It is NOT a mirror of the production source layout, and a production package or module boundary is not by itself a reason to create a test directory.
  1. A parent directory represents a broad functional area. Test files directly inside it MUST cover different, relatively independent aspects of that area, and they remain at that level. A subdirectory MUST NOT be created for a single file, nor for a single independent aspect.
  2. A nested directory represents a narrower responsibility inside the broader area. It MUST be created only when two or more test files cover different aspects of that same narrower responsibility, and its name MUST name that responsibility.
  3. A filename suffix MUST NOT be used as a substitute for a directory level. When several files accumulate at one level as `test_<area>_a.py`, `test_<area>_b.py`, and so on because they all cover the same narrower responsibility, they MUST be grouped in a directory named for that responsibility instead.
  4. Grouping MUST be justified by a genuine functional relationship between the tests. Files MUST NOT be grouped merely because they share a feature name or a keyword, and unrelated files MUST NOT be combined only to reduce the number of directories.
  5. A file whose responsibility genuinely spans more than one area MUST be placed in the appropriate specialized type directory (`tests/contracts/`, `tests/parity/`, `tests/equivalence/`, or `tests/regression/`). A file that belongs to one area MUST stay under that area's directory.
  6. Splitting or moving files MUST preserve logical grouping, test ownership, fixtures, and existing coverage, and MUST respect the size ceiling in `BYNAT-ARCH-4`.
  7. Where the correct grouping is ambiguous, the files stay at the parent level unless a concrete narrower responsibility can be named, and the resolution MUST be recorded with the directory.
  [BP]

### 3.2 Required DataFrame Cases and Assertion Standards (DF and BYNAT-ASSERT)

#### Required DataFrame Edge Cases (DF-1 through DF-20)
Every public transformation and cleaning method MUST be tested against applicable DataFrame edge cases from the table below:

| Case ID | Dimension / Edge Case | Failure Mode Prevented | bynat Application Scope | Required Behavioral Verification |
|---|---|---|---|---|
| **DF-1** | Empty frame (0 rows) | Groupby/quantile crashes on empty data | `fill_missing`, `get_hierarchical_stats`, `profile` | Returns empty result with documented schema; no exception raised |
| **DF-2** | Frame with 0 columns | Column selection crashes; empty index | `fill_missing`, `profile` | Graceful handling; logs warning or returns empty copy |
| **DF-3** | All-null target column | Median/mean/mode of zero observations | `fill_missing`, `fill_missing_from` | Stays all-NaN unless fallback statistic exists |
| **DF-4** | All-null grouping key | Group dropped during groupby operations | `fill_missing`, `handle_outliers` | Null keys treated as valid grouping partition (`dropna=False`) |
| **DF-5** | Single-row DataFrame | Degenerate quantiles; division by zero | `handle_outliers`, `drop_outliers`, `profile` | Correct evaluation without IndexError; boundary samples handled |
| **DF-6** | Single unique group | Degenerate hierarchy traversal | `fill_missing`, `handle_outliers` | Hierarchy relaxation evaluates single level without error |
| **DF-7** | Duplicate row contents | Deduplication logic; indexing errors | `profile`, `save_to_json(append=True)` | Correct duplicate counts and preservation semantics |
| **DF-8** | Duplicate index labels | Label-based indexing drops both rows | `drop_outliers`, `handle_outliers` | Rows dropped strictly by integer position, preserving twin rows |
| **DF-9** | Named custom index | Index name lost during merge/reset | `fill_missing_from`, `handle_outliers` | Output index name strictly matches input index name |
| **DF-10**| MultiIndex on rows | Hierarchical index levels corrupted | `fill_missing_from`, `fill_missing` | Complete MultiIndex level structure and names preserved |
| **DF-11**| NaN values in hierarchy keys | Groupby silently drops NaN groups | All hierarchical transformation methods | NaN group keys retained and matched consistently |
| **DF-12**| Categorical hierarchy keys | Unobserved categories corrupt counts | `handle_outliers`, `get_hierarchical_stats` | Respects `observed=True` grouping semantics |
| **DF-13**| Mixed data types in column | Numeric operations on object columns | `fill_missing_from`, `profile` | Raises documented `TypeError` or handles per contract |
| **DF-14**| Nullable dtypes (`Int64`, `Float64`, `boolean`) | `pd.NA` propagation and scalar coercion | `profile`, `fill_missing` | Preserves nullable dtype semantics and valid fills |
| **DF-15**| `datetime64` and `datetimetz` | Serialization drift; timezone loss | `save_to_json`, `save_to_sql`, `profile` | Preserves ISO formatting, UTC offsets, and tz awareness |
| **DF-16**| Unhashable cell values (lists, dicts) | `DataFrame.duplicated()` raises `TypeError` | `profile`, `save_to_json` | Compares unhashable contents by value without crashing |
| **DF-17**| Non-string column labels (ints, tuples) | String operations crash on non-string names | `reorder_columns`, `columns` ops | Labels preserved; unsupported operations raise clear error |
| **DF-18**| Duplicate column names in frame | Ambiguous column selection | `fill_missing_from`, `profile` | Raises `ValueError` prior to processing |
| **DF-19**| Unicode text & multi-byte characters | Encoding errors; string truncation | `extract_keywords`, `translate_*`, `text` | Full Unicode fidelity preserved across transformations |
| **DF-20**| Large DataFrame ($\ge 10,000$ rows) | Memory spikes; quadratic slowdowns | `benchmarks/`, `test_equivalence_*` | Vectorized execution without memory leaks; benchmark verified |

#### Assertion Standards (BYNAT-ASSERT-1 through BYNAT-ASSERT-5)
- **BYNAT-ASSERT-1: Mandatory `pandas.testing` Assertions.** `pd.testing.assert_frame_equal`, `assert_series_equal`, and `assert_index_equal` MUST be used for all DataFrame, Series, and Index comparisons. `DataFrame.equals()` MUST NOT be used as the sole assertion because it ignores index names and dtype subtleties. Comparisons MUST use default strictness (asserting dtypes, index types, and column order); relaxing flags (e.g. `check_dtype=False`) requires an inline comment justifying the difference. [BP]
- **BYNAT-ASSERT-2: `BaseData` Subclass Identity Preservation.** Transformations executed on `BaseData` or its subclasses (`CsvFile`, `JsonFile`) MUST return an instance preserving the exact input subclass (`assert type(result) is type(frame)`). [BP]
- **BYNAT-ASSERT-3: Warning Contract Verification.** Warnings MUST be asserted explicitly using `pytest.warns(ExpectedWarning, match="...")` or by escalating warnings to errors within `warnings.catch_warnings()` using `simplefilter("error", ...)`. [SB]
- **BYNAT-ASSERT-4: Caching Internals Assertion Exception.** As an exception to Rule A-3, tests residing strictly under `tests/integration/caching_persistence/`, `tests/integration/caching_concurrency/`, or `tests/integration/caching_migration/` MAY inspect SQLite tables and private cache metadata because the caching subsystem is the primary unit under test. [BP]
- **BYNAT-ASSERT-5: AST / Source Guard Testing for Architectural Principles.** Tests MAY use AST inspection to enforce architectural invariants (e.g. verifying that `get_hierarchical_stats` contains no nested function definitions or `apply(axis=1)` calls). Such tests MUST complement, never replace, functional behavioral tests. [BP]

### 3.3 Transformation-Specific Requirements

#### 3.3.1 Shared Transformation Requirements (S-1 through S-7)
The following requirements apply to all public frame-to-frame transformations across `BaseData`, the `df.bynat` accessor, and shared transformation functions:

- **S-1: Input Immutability.** Unless the caller explicitly requests in-place execution, the input DataFrame MUST NOT be modified. `before = df.copy(deep=True)`; execute the transformation with the default arguments (or `inplace=False`); `pd.testing.assert_frame_equal(df, before)`. [BP]
- **S-2: New Object Return.** By default, transformations MUST return a new object instance (`assert result is not df`). Early exits on no-op data MUST return an independent copy, never the original reference. [SB]
- **S-3: Index Preservation.** Output index MUST match input index (`pd.testing.assert_index_equal(result.index, df.index)`), except for operations documented to reshape or explode the index (`split_list_objects(explode_rows=True)`, `melt_transform_pivot`). [BP]
- **S-4: Return Contract & Inplace Handling.** On class-based APIs (`BaseData`) and on the `df.bynat` accessor, default calls return a new frame, while `inplace=True` mutates the original object in place and returns `None` (or statistics). Standalone functions do not accept `inplace`. Methods that do not transform the frame (`get_hierarchical_stats`, `profile`, `save_to_json`, `save_to_sql`, `clear_cache_for_column`, `with_cache`) do not accept it either. [BP]
- **S-5: Class and Accessor Parity.** The `BaseData` class method and the `df.bynat` accessor method MUST produce identical values when called with identical arguments on identical data. [BP]
- **S-6: No Unexpected Deprecation Warnings.** Valid method invocations MUST NOT emit unexpected `DeprecationWarning` or `FutureWarning` notices. [BP]
- **S-7: Lenient Handling of Empty/No-Op Inputs.** Lenient methods called with empty frames or missing optional columns MUST return an independent copy without error. Methods with required arguments MUST raise documented validation errors. [BP]

#### 3.3.2 `fill_missing` Requirements (FM-1 through FM-24)

| ID | Required Case | Expected Behavior | Required Assertion |
|---|---|---|---|
| **FM-1** | Strategies `median`, `mean`, `mode`, `mod` | Correct statistical fill per strategy | Exact expected values verified |
| **FM-2** | Uppercase strategy string | Normalized via `str(strategy).lower()` | Matches lowercase execution |
| **FM-3** | Unknown strategy name | Raises `ValueError` naming invalid strategy | `pytest.raises(ValueError, match="Invalid strategy")` |
| **FM-4** | `min_samples` default (1) | Single observation supplies valid statistic | Exact expected fill |
| **FM-5** | `min_samples` boundary ($N$ vs $N-1$) | $N$ fills; $N-1$ falls through | Exact filled value and NaN fallthrough |
| **FM-6** | Invalid `min_samples` (`True`, `0`, `-1`, `"2"`) | Raises `ValueError` | `pytest.raises(ValueError)` |
| **FM-7** | `hierarchy_cols=None`, `fallback_global=False` | No imputation performed | All NaN values preserved |
| **FM-8** | `hierarchy_cols=None`, `fallback_global=True` | Column-wide statistic fills missing values | Exact column-wide fill |
| **FM-9** | `hierarchy_cols` supplied as string | Automatically converted to single-item list | Matches list-based execution |
| **FM-10**| Missing hierarchy columns in frame | Missing columns ignored; valid ones used | Result matches valid-column execution |
| **FM-11**| No valid target columns remain | Logs warning; returns unchanged copy | Warning captured; `assert_frame_equal` |
| **FM-11a**| Some target columns missing, others valid | Missing columns skipped; valid ones filled | Valid columns filled; missing unchanged |
| **FM-12**| Input frame has no missing values | Returns independent copy without modification | `assert_frame_equal` on result and input |
| **FM-13**| All-NaN column | Remains NaN by default; fills if global fallback | `isna().all()` or exact global fill |
| **FM-14**| All-NaN group | Falls through to coarser hierarchy levels | NaN by default |
| **FM-15**| Multi-level hierarchy | Evaluates from finest to coarsest level | Exact values filled per level |
| **FM-16**| Coarser-level statistics calculation | Computed from original frame, not partially filled | Verified against independent pre-fill stats |
| **FM-17**| `fallback_global=True` on exhausted hierarchy | Remaining NaNs filled with global statistic | Exact global fill |
| **FM-18**| Mode tie-breaking | Deterministic tie-breaking | Repeated runs yield identical values |
| **FM-19**| Null values in hierarchy grouping keys | Treated as valid grouping partition | Exact fills computed for null group |
| **FM-20**| `get_hierarchical_stats=True` | Returns `(result, stats)` tuple | Tuple types, DataFrame schema, stats values |
| **FM-21**| `inplace=True` with `get_hierarchical_stats=True` | Mutates original; returns stats DataFrame | Returns stats; source mutated in place |
| **FM-22**| Index preservation | Named, duplicate, and MultiIndex preserved | `pd.testing.assert_index_equal` |
| **FM-23**| Non-numeric target with numeric strategy | Raises `TypeError` if target has non-null values | `pytest.raises(TypeError)`; all-null exempt |
| **FM-24**| Input immutability | Original DataFrame unmodified | Conforms to Rule S-1 |

#### 3.3.3 `fill_missing_from` Requirements (FF-1 through FF-27)

| ID | Required Case | Expected Behavior | Required Assertion |
|---|---|---|---|
| **FF-1** | Column-wide imputation (`hierarchy_cols=None`, `fallback_global=True`) | Fills missing target from reference column | Exact values match reference statistic |
| **FF-2** | **Statistical Isolation (Zero Leakage)** | Target frame values NEVER influence statistics | Reference statistics verified unchanged |
| **FF-3** | **Reference Immutability** | Reference dataset MUST NOT be modified | `assert_frame_equal` on reference before/after |
| **FF-4** | Target index and row order preservation | Target index and un-imputed values preserved | `assert_index_equal` and exact values |
| **FF-5** | `match_cols` mapping | Dict mapping applied to targets and hierarchy | Exact fills using mapped columns |
| **FF-6** | Invalid `match_cols` (non-dict, non-string, missing) | Raises `TypeError` or `ValueError` | `pytest.raises` targeting invalid argument |
| **FF-7** | `targets` keyword parameter | Accepts keyword alternative to positional target | Exact fills match positional execution |
| **FF-8** | Duplicate column names in `targets` | Automatically deduplicated | Matches unique target execution |
| **FF-9** | Multi-level hierarchy fallback | Traverses finest to coarsest, then global | Exact fills per hierarchy stage |
| **FF-10**| `min_samples` boundary | $N$ fills; $N-1$ falls through | Exact fills and NaN preservation |
| **FF-11**| **Unseen group in target frame** | Falls through hierarchy, then global or NaN | Exact fill or NaN preserved |
| **FF-12**| Reference group with $< \text{min\_samples}$ | Does not supply statistic; falls through | Falls through to next level |
| **FF-13**| No valid target columns remain in target frame | Logs warning; returns unchanged copy | Warning logged; `assert_frame_equal` |
| **FF-13a**| Some target columns missing, others valid | Missing targets skipped; valid ones filled | Valid targets filled; missing unchanged |
| **FF-14**| Missing reference column for valid target | Raises `ValueError` | `pytest.raises(ValueError)` |
| **FF-15**| Missing hierarchy column in target or reference | Raises `ValueError` | `pytest.raises(ValueError)` |
| **FF-16**| Target and hierarchy column overlap | Raises `ValueError` | `pytest.raises(ValueError)` |
| **FF-17**| Duplicate column names in target or reference | Raises `ValueError` | `pytest.raises(ValueError)` |
| **FF-18**| `dataset` is `None`, non-DataFrame, or empty | Raises `ValueError` or `TypeError` | `pytest.raises` targeting invalid dataset |
| **FF-19**| Non-numeric column with numeric strategy | Raises `TypeError` (unless target is all-NaN) | `pytest.raises(TypeError)` |
| **FF-20**| Empty target DataFrame (0 rows) | Returns empty DataFrame with preserved schema | `result.empty` and matching columns |
| **FF-21**| Target DataFrame has no missing values | Returns independent copy without modification | `assert_frame_equal` |
| **FF-22**| Target column completely missing (all-NaN) | Imputed from matching reference groups | Exact fills matching reference groups |
| **FF-23**| All-null reference column with numeric strategy | Cannot compute statistic; stays NaN | Target values remain NaN |
| **FF-24**| `get_hierarchical_stats=True` | Returns stats computed from reference data | Stats schema and reverse-mapped names |
| **FF-25**| `inplace=True` execution | Mutates target in place; returns `None`/stats | Target mutated; return value verified |
| **FF-26**| BaseData and Accessor agreement | Equal results between class API and accessor | `assert_frame_equal` |
| **FF-27**| Index preservation | Named, duplicate, and MultiIndex preserved | `pd.testing.assert_index_equal` |

#### 3.3.4 `handle_outliers` Requirements (HO-1 through HO-15)

| ID | Required Case | Expected Behavior | Required Assertion |
|---|---|---|---|
| **HO-1** | `min_samples` default (5) | Groups with $<5$ observations not evaluated | Outlier mask excludes small groups |
| **HO-2** | Full hierarchy first, then relaxation | Most specific level evaluated before relaxing | Exact outlier mask per hierarchy level |
| **HO-3** | Replaced outliers excluded from coarser quartiles | Replaced values do not distort coarser bounds | Hand-calculated expected outlier mask |
| **HO-4** | Groups below `min_samples` threshold | Unchecked; fall through to coarser levels | Values remain unflagged |
| **HO-5** | Outliers replaced with NaN | Flagged outliers become NaN; others preserved | Values replaced; index preserved |
| **HO-6** | Missing target columns | Missing columns skipped | Unchanged copy returned |
| **HO-7** | Missing hierarchy columns (`None` vs missing) | `None`/empty warns; missing named col raises `KeyError` | Warning logged or `pytest.raises(KeyError)` |
| **HO-8** | Multiple target columns | Each target evaluated independently | Union of target outlier masks |
| **HO-9** | `get_hierarchical_stats=True` | Statistics extracted before outlier replacement | Stats schema and pre-replacement values |
| **HO-10**| Null values in hierarchy keys | Valid grouping keys (`dropna=False`) | Outliers identified within null groups |
| **HO-11**| Categorical hierarchy keys | Respects `observed=True` semantics | Outlier mask verified |
| **HO-12**| Reference equivalence | Output matches brute-force reference | `assert_frame_equal` against reference |
| **HO-13**| No merge in IQR calculation path | Performance invariant: no `DataFrame.merge` | Monkeypatch `DataFrame.merge` to fail |
| **HO-14**| Duplicate index labels | Handled safely by integer position | `assert_index_equal` |
| **HO-15**| Input immutability | Source DataFrame unmodified | Conforms to Rule S-1 |

#### 3.3.5 `drop_outliers` Requirements (DO-1 through DO-8)

| ID | Required Case | Expected Behavior | Required Assertion |
|---|---|---|---|
| **DO-1** | Grouping and IQR scanning semantics | Evaluates outliers across original data | Expected survivor mask verified |
| **DO-2** | Rows dropped strictly by integer position | Duplicate index labels do not drop twins | Exact surviving index labels |
| **DO-3** | Union of outliers across targets | Row dropped if an outlier in ANY target column | Union drop verified |
| **DO-4** | Index preservation | Surviving rows retain exact original index labels | `pd.testing.assert_index_equal` |
| **DO-5** | All rows flagged as outliers | Returns empty DataFrame preserving columns | `result.empty` and matching columns |
| **DO-6** | Missing hierarchy columns | `None`/empty warns; missing named col raises `KeyError` | Warning logged or `pytest.raises(KeyError)` |
| **DO-7** | `get_hierarchical_stats=True` | Returns statistics calculated prior to dropping rows | Stats schema and pre-drop values |
| **DO-8** | Input immutability | Source DataFrame unmodified | Conforms to Rule S-1 |

#### 3.3.6 Hierarchical Fallback Standards (HF-1 through HF-6)
- **HF-1:** Hierarchy levels MUST be evaluated from most specific to coarsest by dropping the rightmost grouping column at each relaxation step. [BP]
- **HF-2:** `min_samples` MUST count only non-null observations within the evaluated group. [BP]
- **HF-3:** An absent group or a group with fewer than `min_samples` non-null observations MUST fall through to the next coarser level without raising an exception. [BP]
- **HF-4:** Global fallback (`fallback_global=True`) MUST apply only after all hierarchical levels are completely exhausted. [BP]
- **HF-5:** Imputation statistics at coarser levels MUST be calculated from original data; in `handle_outliers`, replaced values MUST be excluded from subsequent quartile calculations. [BP]
- **HF-6:** Null values in hierarchy columns MUST be treated as valid grouping partitions at every level (`dropna=False`). [BP]

#### 3.3.7 `min_samples` Standards (MS-1 through MS-4)
- **MS-1:** Default thresholds: `fill_missing` and `fill_missing_from` default to `min_samples=1`; `handle_outliers` and `drop_outliers` default to `min_samples=5`. [BP]
- **MS-2:** Boundary contract: a group with exactly `min_samples` non-null observations supplies a statistic; a group with `min_samples - 1` non-null observations falls through. [BP]
- **MS-3:** Invalid thresholds (`True`, `False`, `0`, negative numbers, floats, strings) MUST raise `ValueError` in `fill_missing` and `fill_missing_from`. [BP]
- **MS-3a:** *(Blocked on Production Scope: PD-02)* `handle_outliers` and `drop_outliers` currently fail to validate `min_samples`. This contract is pinned by 12 strict `xfail` tests in `tests/regression/tracked_defects/test_tracked_defects_pd02.py`. [BP]
- **MS-4:** Only non-null observations count toward the `min_samples` threshold. [BP]

#### 3.3.8 Unseen Groups Standards (UG-1 through UG-4)
- **UG-1:** In `fill_missing_from`, a group present in the target but absent from the reference is an unseen group. [BP]
- **UG-2:** In `fill_missing`, a group containing zero non-null target observations is an unseen group. [BP]
- **UG-3:** In outlier methods, a group with fewer than `min_samples` observations is treated as an unseen group. [BP]
- **UG-4:** Unseen groups MUST fall through to coarser hierarchy levels, then to global fallback if enabled, and otherwise remain NaN. They MUST NOT raise data-related exceptions. [BP]

#### 3.3.9 Missing Keys Asymmetry (MK-1 through MK-6)

| Situation | `fill_missing` | `fill_missing_from` | `get_hierarchical_stats` |
|---|---|---|---|
| **MK-1:** No valid target columns remain | Warning logged; unchanged copy | Warning logged; unchanged copy | Warning logged; empty DataFrame |
| **MK-2:** Some target columns missing, others valid | Missing skipped silently | Missing skipped silently | Missing skipped silently |
| **MK-3:** Target column missing from reference | Not applicable | Raises `ValueError` | Not applicable |
| **MK-4:** Hierarchy column missing from frame | Column ignored silently | Raises `ValueError` | Column ignored silently |
| **MK-5:** Hierarchy column missing from reference | Not applicable | Raises `ValueError` | Not applicable |
| **MK-6:** Column in `match_cols` missing | Not applicable | Raises `ValueError` | Not applicable |

#### 3.3.10 Mutation and Leakage Standards (ML-1 through ML-7)
- **ML-1:** Frame transformations MUST return a new object by default and leave input data unmodified unless `inplace=True` is requested. [BP]
- **ML-2:** Class API and accessor `inplace=True` mutate the original frame in place and return `None` or the documented statistics; standalone functions do not accept `inplace`. The accessor contract is pinned by `tests/parity/inplace/`. *(Note: the variadic standalone functions still absorb an unexpected `inplace` keyword into their `**kwargs`; that function-level defect remains tracked as PD-01 and pinned in `tests/regression/tracked_defects/test_variadic_inplace.py`.)* [BP]
- **ML-3:** The `df.bynat` accessor MUST NOT mutate the underlying wrapped DataFrame unless `inplace=True` is requested, in which case the mutation MUST target that same object and preserve its identity. [BP]
- **ML-4:** Cache directories MUST remain isolated. Different cache directories MUST NOT share state. Key normalization (`1`, `1.0`, `"1"` colliding by design) MUST be pinned by tests. [BP]
- **ML-5:** `fill_missing_from` MUST NOT leak target data into reference statistics and MUST NOT mutate the reference dataset. [BP]
- **ML-6:** Enrichment caching semantics MUST be verified per provider: exceptions are never cached; translation does not cache empty strings; geocoding and currency may cache missing lookups as `None`; NLP caches valid empty extractions. [BP]
- **ML-7:** `clear_cache_for_column` MUST delete only the specified column cache bucket and preserve all unrelated column and function caches. [BP]

### 3.4 Public API, Export Boundaries, and Optional Integrations (BYNAT-API)

- **BYNAT-API-1: Public Entry Points.** Tests MUST verify public accessibility through documented entry points: `bynat`, `bynat.analytics`, `bynat.cleaning`, `bynat.caching`, `bynat.profiling`, `Analyzer`, `df.bynat`, `BaseData`, `CsvFile`, and `JsonFile`. [BP]
- **BYNAT-API-2: Strict `bynat.cleaning.__all__` Boundary.** The `bynat.cleaning` namespace MUST export ONLY `["BaseData", "CsvFile", "JsonFile"]`. Profiling functions MUST be imported from `bynat.profiling`, accessor APIs from `bynat._accessors`, and loader helpers from `bynat.cleaning.io`. Tests MUST enforce this boundary via `tests/contracts/api/test_docstring_and_signature_drift.py`. [BP]
- **BYNAT-API-3: Contract Pinning for Caching and Enrichment Defaults.** Contract tests MUST pin documented caching exports (`CacheManager`, `shared_cache_manager`, `CACHE_DIR_ENV_VAR`, `DEFAULT_CACHE_DIR`) and default enrichment providers (`GoogleTranslatorProvider`, `NominatimGeocoder`, `YFinanceRateSource`). [BP]
- **BYNAT-API-4: Signature and Docstring Synchronization.** Runtime `inspect.signature` and docstrings on `BaseData` and `df.bynat` MUST stay synchronized with shared implementation functions. Synchronization is verified by `tests/contracts/api/test_docstring_and_signature_drift.py`, with `bynat/_accessors/dataframe.py` as the shared implementation source. [BP]
- **BYNAT-API-5: Offline Provider Fakes vs Real Optional Extras Integration.**
  - Network-backed optional dependencies (`deep-translator`, `langdetect`, `geopy`, `yfinance`, `spacy`) MUST be stubbed with offline test doubles (`DictTranslator`, `BatchTranslator`, `DictGeocoder`, `FakeRates`). Live network calls are strictly prohibited.
  - Offline-capable optional extras (`pyahocorasick`, `SQLAlchemy` with SQLite) MUST execute real integration tests when installed. [BP]
- **BYNAT-API-6: Cache Directory Isolation via `BYNAT_CACHE_DIR`.** Every caching test and cleaning method exercising caching MUST redirect `BYNAT_CACHE_DIR` to a `tmp_path` fixture to prevent writing to `Settings/Cache Data/Automated`. [BP]

### 3.5 Markers, Pytest Configuration, Hypothesis Profiles, and Static Typing (BYNAT-MARK and BYNAT-CFG)

- **BYNAT-MARK-1: Seven Registered Markers & Orthogonality.** The test suite uses seven registered markers in `pyproject.toml`. Markers represent an orthogonal responsibility-selection axis independent of the type-first directory structure. The primary marker (`unit`, `integration`, or `property`) is derived from the top-level test-type directory (`tests/unit/`, `tests/integration/`, `tests/properties/`) by `pytest_collection_modifyitems` in `tests/conftest.py`; tests in the specialized type directories keep explicit primary markers:
  1. `unit`: Tests a single function, method, or class in isolation.
  2. `integration`: Tests cross-module behavior, SQLite persistence, file I/O, or real optional libraries.
  3. `property`: Hypothesis `@given(...)` property-based tests checking algebraic/structural invariants.
  4. `slow`: Multi-second stress, concurrency, or benchmark equivalence tests.
  5. `extras`: Tests requiring optional dependencies (`[translation]`, `[geocoding]`, `[currency]`, `[categorization]`, `[nlp]`, `[sql]`).
  6. `mutation`: Dedicated mutation-testing support tests designed for Cosmic Ray survivor triage.
  7. `network`: Reserved quarantine marker for externally supplied probes. **0 supported tests carry this marker.** [BP]
- **BYNAT-MARK-2: Primary Test-Type Markers.** Every standard test function MUST carry exactly one primary test-type marker (`unit`, `integration`, or `property`). Type-derived suites receive it from `tests/conftest.py`; tests under `tests/contracts/`, `tests/parity/`, `tests/equivalence/`, and `tests/regression/` MUST declare an explicit primary marker. The collection hook asserts that exactly one primary marker is present on every collected test. [BP]
- **BYNAT-MARK-3: Environment Filter Marker (`extras`).** Tests requiring optional extras MUST be marked `@pytest.mark.extras` and MUST call `pytest.importorskip("<module>")`. [SB]
- **BYNAT-MARK-4: Cost Filter Marker (`slow`).** Tests taking more than a few seconds MUST be marked `@pytest.mark.slow`. [BP]
- **BYNAT-MARK-5: Mutation Support Tests.** `pytest -m mutation` executes dedicated Python test functions added to kill surviving mutants. Running `pytest -m mutation` does NOT invoke the Cosmic Ray engine. These tests are also included in the Cosmic Ray `test-command` (see §4.3) so they kill survivors during the advisory session. [BP]
- **BYNAT-MARK-6: Reserved Quarantine Marker (`network`).** The `network` marker is registered to allow `-m "not network"` filtering. No supported test in `bynat` may access live network services. [BP]
- **BYNAT-MARK-7: Permitted Marker Combinations.** A test carries its primary type marker (`unit`, `integration`, or `property`) combined with `extras`, `slow`, or `mutation` when applicable (e.g. `@pytest.mark.integration` + `@pytest.mark.extras`). Forced over-marking is prohibited. [BP]
- **BYNAT-CFG-1: Pytest Discovery Configuration.** `pyproject.toml` configures:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = ["-ra", "-m", "not slow and not extras and not network and not mutation"]
  strict_markers = true
  strict_config = true
  ```
  Pytest discovers test files recursively across `tests/unit/`, `tests/integration/`, `tests/contracts/`, `tests/parity/`, `tests/properties/`, `tests/equivalence/`, and `tests/regression/`. [BP]
- **BYNAT-CFG-2: Default Exclusions & Explicit CLI Overrides.** Default runs exclude `slow`, `extras`, `network`, and `mutation`. Explicit CLI marker flags (e.g. `pytest -m extras`) override `addopts` to execute selected test subsets. [BP]
- **BYNAT-CFG-3: Hypothesis Profiles & CLI Option.** `tests/conftest.py` registers three Hypothesis profiles:
  - `default`: 25 examples, `deadline=None`.
  - `fast`: 25 examples, `derandomize=True`.
  - `extended`: 200 examples, `derandomize=False`, `print_blob=True`.
  Profiles are activated via `--hypothesis-profile=<name>` or `HYPOTHESIS_PROFILE=<name>`. [BP]
- **BYNAT-CFG-4: Static Type Checking with Mypy.** `pyproject.toml` includes both `bynat` and `tests` in the `[tool.mypy]` scope with `explicit_package_bases = true`. Test files MUST maintain type safety without type checker errors. [BP]
- **BYNAT-CFG-5: Strict Xfail Policy.** All `xfail` markers MUST set `strict=True` and reference a tracked issue identifier. If a bug is fixed, the strict `xfail` immediately fails CI, forcing prompt test updating. [SB]

### 3.6 Coverage, Property Invariants, Mutation Testing, and Supporting Tooling (BYNAT-METRIC and BYNAT-TOOL)

- **BYNAT-METRIC-1: Coverage Configuration and Measurement.** Coverage is measured via `coverage.py` and `pytest-cov` with branch coverage enabled (`--cov=bynat --cov-branch`). [SB]
- **BYNAT-METRIC-2: Python 3.13 Coverage Core Policy.** Due to upstream `sysmon` limitations on Python 3.13, coverage runs MUST use the `ctrace` core or run primarily under Python 3.11. [SB]
- **BYNAT-METRIC-3: Phased Coverage Floors and Core Module Targets.** Overall test suite coverage MUST satisfy `fail_under = 85`. Core modules (`bynat/cleaning/_stats.py`, `bynat/caching/manager.py`, `bynat/cleaning/enrich/_engine.py`) carry elevated coverage requirements ($\ge 95\%$ statement, $\ge 90\%$ branch). [BP]
- **BYNAT-METRIC-4: Allowed Coverage Exclusions.** Coverage exclusions are strictly restricted to:
  - `if TYPE_CHECKING:` blocks.
  - `pragma: no cover` on defensive unreachable branches, accompanied by an explanatory comment.
  - `pragma: no branch` on intentional partial branches. Broad regex exclusions are rejected. [SB]
- **BYNAT-METRIC-5: Mutation Testing Tooling and Scope.** Cosmic Ray is the primary mutation testing tool, configured via `cosmic-ray.toml` targeting core modules (`stats.py`, `engine.py`, `manager.py`) with a 30-second timeout. [SB]
- **BYNAT-METRIC-6: Mutation Score Formula and Survivor Triage.** The mutation score is calculated as:
  $$MS = \frac{K}{M - E}$$
  where $K$ is killed mutants, $M$ total mutants, and $E$ verified equivalent mutants. Survivors MUST be triaged into: Missing Test (requires new test), Equivalent Mutant (recorded), or Accepted Risk. [SB]
- **BYNAT-METRIC-7: Property-Based Invariant Verification.** Property tests in `tests/properties/` MUST verify the following invariants across all applicable transformations:
  1. Input DataFrame immutability (Rule S-1).
  2. Index preservation (Rule S-3).
  3. Row count preservation (except documented explodes/drops).
  4. Output schema and dtype stability.
  5. Determinism across repeated executions with identical seeds. [BP]
- **BYNAT-TOOL-1: Installed-Wheel Clean Virtualenv Verification.** `tools/verify_installed_wheel.py` builds a wheel in an isolated directory, installs it in a clean temporary virtualenv, and runs the test suite against the installed distribution to guarantee that packaging metadata (`py.typed`) and package files, including `bynat/_accessors/dataframe.pyi`, are complete. [BP]
- **BYNAT-TOOL-2: Performance Benchmarking Suite.** Scripts under `benchmarks/` measure performance against 0.3.0 baseline reference implementations. Benchmarks MUST NOT import test files. [BP]
- **BYNAT-TOOL-3: Documentation Synchronization Verification.** Shared docstrings and signatures are verified against the `bynat/_accessors/dataframe.py` implementation by `tests/contracts/api/test_docstring_and_signature_drift.py`; generated-stub freshness and stub-vs-runtime signatures are verified by `tests/contracts/api/test_accessor_stub.py`, with regeneration via `python tools/gen_accessor_stub.py --check`. [BP]

---

## 4. CI Integration Specification

This section documents how the Continuous Integration workflows in `.github/workflows/test.yml` (push, pull request, and manual dispatch) and `.github/workflows/scheduled-quality.yml` (weekly schedule and manual dispatch), together with pytest, implement Authority Levels 1 and 2.

### 4.1 Workflows and Job Matrix

`.github/workflows/test.yml` defines four automated CI jobs executed on every push, pull request, and manual dispatch (`workflow_dispatch`). It has no scheduled trigger and does not run the extended property, slow concurrency, or mutation sessions:

| Job Name | Operating System | Python Version | Exact Command(s) Executed | Purpose & Rules Enforced |
|---|---|---|---|---|
| `lint` | `ubuntu-latest` | 3.11 | `ruff check bynat tests benchmarks` | Code style, import sorting, and linting rules. |
| `typecheck` | `ubuntu-latest` | 3.11 | `pip install . mypy pandas-stubs pytest hypothesis`<br>`python -m mypy` | Static type checking for `bynat` and `tests` (`BYNAT-CFG-4`). |
| `test` (Matrix Leg 1) | `ubuntu-latest` | 3.11 | `pip install . pytest pytest-cov hypothesis build`<br>`python -m build`<br>`python -m compileall -q bynat tests`<br>`python -m pytest --cov=bynat --cov-branch --cov-report=term-missing --cov-report=xml`<br>`python tools/verify_installed_wheel.py` | Full core unit/integration suite, branch coverage gate (`BYNAT-METRIC-3`), and installed wheel verification (`BYNAT-TOOL-1`). |
| `test` (Matrix Legs 2-4) | `ubuntu-latest` & `windows-latest` | 3.11 & 3.13 | `pip install . pytest pytest-cov hypothesis build`<br>`python -m build`<br>`python -m compileall -q bynat tests`<br>`python -m pytest -q` | Cross-platform compatibility and matrix execution parity across Linux/Windows and Python 3.11/3.13. |
| `test-extras` | `ubuntu-latest` | 3.11 | `pip install ".[translation,geocoding,currency,categorization,nlp,sql]" pytest hypothesis`<br>`python -m pytest -m extras -rs` | Optional dependency integration suite exercising all extras (`BYNAT-MARK-3`). |

Scheduled quality checks are isolated in `.github/workflows/scheduled-quality.yml`, a dedicated workflow triggered on a weekly schedule (`cron: "0 3 * * 0"`) and on manual dispatch (`workflow_dispatch`). Separating these high-cost checks from regular PR/push CI keeps pull-request validation fast while still exercising extended property tests, concurrency stress tests, and advisory mutation testing. The workflow defines two jobs, and `scheduled-quality` requires `lint` to succeed before it starts:

| Job Name | Operating System | Python Version | Exact Command(s) Executed | Purpose & Rules Enforced |
|---|---|---|---|---|
| `lint` | `ubuntu-latest` | 3.11 | `ruff check bynat tests benchmarks` | Code style, import sorting, and linting rules; gates the `scheduled-quality` job. |
| `scheduled-quality` | `ubuntu-latest` | 3.11 | `pip install ".[dev,translation,geocoding,currency,categorization,nlp,sql]"`<br>`python -m pytest -m property --hypothesis-profile=extended`<br>`python -m pytest -m slow`<br>`cosmic-ray init cosmic-ray.toml session.sqlite`<br>`cosmic-ray exec cosmic-ray.toml session.sqlite`<br>`cr-report session.sqlite > mutation_report.txt`<br>`actions/upload-artifact@v4` (`if: always()`, artifact `mutation-report`) | Extended Hypothesis property profile (200 examples), slow concurrency suite, and advisory Cosmic Ray mutation session. The mutation step is non-blocking (`continue-on-error: true`), and the report is always uploaded as a workflow artifact. |

### 4.2 Marker Selection and Execution Architecture

Pytest test selection is governed by the orthogonal marker architecture:

| Execution Context | Command Invocations | Active Markers | Selection / Deselection Behavior |
|---|---|---|---|
| **Default PR & Local Run** | `python -m pytest -q` | `unit`, `integration`, `property` | Runs all fast core tests. `addopts` in `pyproject.toml` automatically deselects `slow`, `extras`, `network`, and `mutation`. |
| **Unit Tests Only** | `python -m pytest -m "unit and not slow and not extras"` | `unit` | Runs isolated unit tests. |
| **Integration Tests Only**| `python -m pytest -m "integration and not slow and not extras"`| `integration` | Runs SQLite, file I/O, and cross-module tests. |
| **Optional Extras CI** | `python -m pytest -m extras -rs` | `extras` | Explicit `-m extras` CLI flag overrides `addopts` default filter to run all optional integration tests. |
| **Extended Property Run** | `python -m pytest -m property --hypothesis-profile=extended` | `property` | Runs Hypothesis properties under the 200-example `extended` profile. |
| **Slow Concurrency Suite**| `python -m pytest -m slow` | `slow` | Explicit `-m slow` CLI flag runs multi-second concurrency and stress tests. |
| **Mutation Support Suite**| `python -m pytest -m mutation` | `mutation` | Explicit `-m mutation` runs dedicated Python tests designed for Cosmic Ray survivor triage. |
| **Network Quarantine** | `python -m pytest -m network` | `network` | **Collects and runs exactly 0 tests**, proving no live network tests exist. |

The extended property and slow concurrency executions are scheduled-only checks defined in `.github/workflows/scheduled-quality.yml`; the remaining contexts execute in regular PR/push CI or locally.

### 4.3 Windows and Cross-Platform Parity

- **Cross-Platform Determinism.** Tests MUST pass with identical assertion results on Windows and Ubuntu.
- **Filesystem and Path Handling.** Tests MUST use `pathlib.Path` and `tmp_path` fixtures rather than hardcoded POSIX forward slashes or platform-specific separators.
- **Pure Python Tooling.** Cosmic Ray is selected as the primary mutation testing tool because it is pure Python and operates cleanly on both Windows and Linux without requiring POSIX `fork()` system calls.
- **Scheduled Mutation Configuration.** `cosmic-ray.toml` targets the core modules (`bynat/cleaning/_stats.py`, `bynat/cleaning/enrich/_engine.py`, `bynat/caching/manager.py`) with a 30-second timeout. Its `test-command` runs the type-first suites `tests/unit`, `tests/integration`, `tests/contracts`, `tests/parity`, `tests/equivalence`, `tests/regression`, and `tests/properties` with the marker filter `not slow and not extras and not network`. The `mutation` marker tests are intentionally **included**: they target `bynat/cleaning/enrich/_engine.py::cached_map` and are the dedicated survivor-killing tests for the Cosmic Ray session, so excluding them would lower the measured mutation score. The `extras` tests under `tests/integration/enrichment/` (`test_optional_sql.py` and `test_optional_categorization.py`) are excluded by the marker filter because they exercise `save_to_sql` (`bynat/cleaning/io.py`) and `categorize_by_reference` (`bynat/cleaning/_text.py`), which are outside the mutated module set, and including them would add per-work-item runtime without killing any target-module mutant. The advisory session runs only in `.github/workflows/scheduled-quality.yml`.

### 4.4 Local vs CI Parity and Verification Invariants

Developers and automated agents can reproduce the exact CI verification pipeline locally using the following sequence of commands:
```bash
ruff check bynat tests benchmarks
python -m mypy
python tools/gen_accessor_stub.py --check
python -m pytest -q
python -m pytest -m extras -rs
python tools/verify_installed_wheel.py
```

The scheduled quality checks can be reproduced locally with:
```bash
python -m pip install ".[dev,translation,geocoding,currency,categorization,nlp,sql]"
python -m pytest -m property --hypothesis-profile=extended
python -m pytest -m slow
cosmic-ray init cosmic-ray.toml session.sqlite
cosmic-ray exec cosmic-ray.toml session.sqlite
cr-report session.sqlite > mutation_report.txt
```

---

## 5. Governance Framework

### 5.1 AI Agent Protocol

This protocol is binding on any autonomous AI agent or automated engineering system generating, refactoring, or auditing code in this repository:

1. **Epistemic Honesty & Verification.** Agents MUST execute actual verification commands and inspect exit codes and output streams. Fabricating command outputs, simulating test runs, or extrapolating test passes without execution is strictly prohibited.
2. **Authority Hierarchy Respect.** Universal standards belong in Authority Level 1; project-specific constraints belong in Authority Level 2.
3. **Strict Scope Discipline.** When implementing an assigned scope, agents MUST NOT modify files outside the authorized workstream. Agents MUST NOT modify production code (`bynat/`) during test-only remediation tasks unless explicitly authorized.
4. **No Assertion Weakening.** Agents MUST NOT relax comparison flags (e.g. adding `check_dtype=False`), remove assertions, delete failing test cases, or add blanket skips/xfails to achieve a passing test run.
5. **No Production Test Hooks.** Agents MUST NOT add `_test_mode` flags, debug arguments, or conditional branches to production code to facilitate test execution.
6. **Path Integrity.** Agents MUST ensure that 100% of repository file paths referenced in documentation or tests exist on disk.
7. **Clean Reporting.** Agents MUST report exact commands executed, exit codes, and diff summaries.

### 5.2 Authoritative References

#### External Testing and Packaging Standards
- **RFC 2119**: *Key words for use in RFCs to Indicate Requirement Levels*. [IETF RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).
- **pytest Documentation**: *Good Integration Practices*, *Fixtures*, *Parametrization*, *Warnings*, *Skip and Xfail*. [pytest docs](https://docs.pytest.org/).
- **Hypothesis**: *Settings, Profiles, and Invariant Testing*. [Hypothesis docs](https://hypothesis.readthedocs.io/).
- **coverage.py**: *Branch Coverage Measurement and Contexts*. [coverage.py docs](https://coverage.readthedocs.io/).
- **Cosmic Ray**: *Mutation Testing Theory, Concepts, and Configuration*. [Cosmic Ray docs](https://cosmic-ray.readthedocs.io/).
- **Python Packaging Authority (PyPA)**: *Downstream Packaging Guidelines and Project Verification*. [PyPA](https://packaging.python.org/).
- **Scientific Python Development Guide**: *Testing Principles, Patterns, and pytest Architecture*. [learn.scientific-python.org](https://learn.scientific-python.org/development/principles/testing/).
- **NumPy & pandas Testing Guidelines**: *Array and DataFrame Comparison Specifications*. [NumPy docs](https://numpy.org/doc/stable/reference/testing.html) & [pandas docs](https://pandas.pydata.org/docs/reference/testing.html).

#### Internal Repository Specifications
- [`README.md`](../README.md): Public functional documentation and user guide.
- [`docs/ROADMAP.md`](ROADMAP.md): Project roadmap, core principles, and definitions of done.
- [`CHANGELOG.md`](../CHANGELOG.md): Historical record of library modifications and releases.
- [`pyproject.toml`](../pyproject.toml): Build system, package metadata, pytest configuration, and coverage settings.
- [`.github/workflows/test.yml`](../.github/workflows/test.yml): Continuous Integration workflow definitions.
