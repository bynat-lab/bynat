# bynat Architecture Refactoring Plan

**Scope:** ARCH-03 / Issue #62  
**Status:** Proposed execution plan  
**Planning date:** 2026-11-21

## 1. Objective

Refine `bynat` into a clearly bounded modular monolith while preserving the current architectural direction: **Functional Core + Facades**.

The goal is to establish clear ownership for Cleaning, Caching, Analytics, Profiling, and the pandas DataFrame accessor; make the root public API intentional; and verify the resulting architecture through tests and static checks.

This is an internal architecture refactor. There are currently no users whose old-version imports need to be preserved. Therefore, **backward compatibility with previous published versions is not a requirement**. The target API and the current repository's intended contracts are the source of truth. Obsolete root-level aliases and outdated import paths may be removed directly when the relevant phase reaches them.

## 2. Target project structure

```text
bynat/
├── __init__.py
│
├── _accessors/
│   ├── __init__.py
│   ├── dataframe.py
│   └── _binding.py
│
├── cleaning/
│   ├── __init__.py
│   ├── base.py
│   ├── ...
│   └── enrich/
│       └── ...
│
├── caching/
│   ├── __init__.py
│   └── ...
│
├── analytics/
│   ├── __init__.py
│   └── ...
│
└── profiling/
    ├── __init__.py
    ├── profile.py
    ├── report.py
    └── ...
```

The tree is a target direction, not a requirement to create empty or speculative modules. Add files only where a real responsibility requires them.

## 3. Package responsibilities

| Package | Responsibility |
|---|---|
| `cleaning` | DataFrame cleaning, transformations, enrichment, file I/O, and the supported class facade (`BaseData`, `CsvFile`, `JsonFile`) |
| `caching` | Cache management, persistent storage, key handling, and migrations |
| `analytics` | Application-independent analytical operations, metrics, and response contracts |
| `profiling` | Non-mutating data inspection, data-quality diagnostics, profile metrics, and structured profile reports |
| `_accessors` | pandas accessor registration, method binding, accessor-facing signatures, and accessor-specific adaptation |

The accessor is an integration facade, not an algorithm owner. Algorithms remain in their functional packages.

## 4. Architectural rules

### 4.1 Dependency direction

| Dependency | Rule |
|---|---|
| `cleaning` → `caching` | Allowed where required by existing cache-backed cleaning/enrichment behavior |
| `analytics` → `cleaning` | Not allowed merely because both work with DataFrames |
| `analytics` → `caching` | Not allowed without a concrete requirement |
| `profiling` → `cleaning` | Not allowed in the profiling core |
| `profiling` → `analytics` | Not allowed |
| `_accessors` → functional packages | Allowed; accessor methods delegate to package-owned implementations |
| Functional packages → `_accessors` | Not allowed |

### 4.2 Public API

The root package exposes only the four intended package entry points:

- `bynat.cleaning`
- `bynat.caching`
- `bynat.analytics`
- `bynat.profiling`

Importing `bynat` also registers `df.bynat`. The accessor implementation class itself is not a root-level public export.

Target `bynat/__init__.py` shape:

```python
from . import analytics, caching, cleaning, profiling
from . import _accessors as _accessor_registration

__all__ = [
    "cleaning",
    "caching",
    "analytics",
    "profiling",
]
```

Each package controls its own narrow, intentional public API through its `__init__.py` and explicit `__all__` where appropriate. Do not broadly re-export implementation details.

Examples of intended imports:

```python
import bynat

from bynat.cleaning import BaseData, CsvFile, JsonFile
from bynat.profiling import profile, ProfileReport
```

The root should not expose individual classes, functions, reports, or accessor implementation symbols such as `BaseData`, `ProfileReport`, `profile`, `read_csv`, `read_json`, or `BynatAccessor`.

### 4.3 Compatibility policy

Backward compatibility with previous published versions is explicitly out of scope. There is no existing user base requiring preservation of old import paths.

Accordingly:

- Do not retain root-level aliases solely for compatibility with earlier versions.
- Do not keep obsolete import paths or facades unless they serve a current, intentional API contract.
- Remove or update tests, docs, examples, and stubs that assert obsolete APIs.
- Preserve behavior and contracts that remain part of the target API, including the class facade and `df.bynat`; this is functional correctness, not legacy-version compatibility.

## 5. Execution phases

## Phase 0 — Architecture Decisions and Baseline

**Goal:** Freeze the target architecture and establish a reliable baseline before implementation.

### Tasks

1. Confirm the target project structure and package responsibilities.
2. Confirm the root public API: four package objects plus automatic `df.bynat` registration.
3. Confirm the public exports of each package and maintain explicit, minimal `__all__` declarations where appropriate.
4. Confirm the dependency rules in Section 4.1.
5. Identify and classify current root-level aliases and outdated import paths for removal or relocation. Do not preserve them merely for old-version compatibility.
6. Record the current test, lint, and type-check baseline.
7. Identify all affected tests, docs, examples, stubs, and documentation-generation tooling.

### Acceptance criteria

- Target architecture and public API are explicitly agreed.
- Package ownership and dependency rules are documented.
- Obsolete root exports and import paths are identified for direct cleanup.
- Baseline verification results are recorded.
- No production implementation changes are made in this phase.

**Exit gate:** Phase 0 is accepted before Phase 1 begins.

## Phase 1 — Profiling Extraction

**Goal:** Make `bynat.profiling` the owner of profiling implementation and report models.

### Tasks

1. Create the `bynat.profiling` package.
2. Extract the profiling core from `cleaning/profile.py`.
3. Move profile report models into the profiling package.
4. Remove profiling-core dependencies on `cleaning._common` and `cleaning._outputs`.
5. Decide helper ownership, including `_dedupe_key`, based on the invariant each helper represents. Do not create a generic shared package merely to move a helper.
6. Separate core report computation from `BaseData`-specific output adaptation.
7. Update `BaseData.profile()` to delegate to the profiling package.
8. Update the accessor's profiling method to delegate to the profiling package; the accessor itself will be migrated in Phase 2.
9. Remove obsolete profiling ownership/import paths from Cleaning once all intended callers have been redirected.
10. Update profiling tests, documentation, examples, and typing surfaces.

### Acceptance criteria

- `bynat.profiling` owns the actual profiling implementation and report models.
- Profiling core has no imports from Cleaning.
- Profiling has no dependency on Analytics.
- No circular imports exist.
- `BaseData.profile()` and `df.bynat.profile()` preserve their intended behavior.
- Profile results, report structure, serialization, and return types satisfy the approved contracts.
- All relevant profiling and cross-cutting tests pass.

**Exit gate:** Profiling ownership is independent and verified before moving the accessor integration boundary.

## Phase 2 — Accessor Migration

**Goal:** Move pandas integration out of Cleaning into the private library-level `_accessors` package.

### Tasks

1. Create `bynat/_accessors/`.
2. Move DataFrame accessor registration and implementation into the new package.
3. Move binding/wrapper mechanics, including the equivalents of `_frame_method` and `_cached_frame_method`, into the accessor integration boundary.
4. Keep all underlying algorithms in their owning functional packages.
5. Ensure accessor methods delegate to Cleaning, Caching, Profiling, or other eligible package APIs.
6. Keep the accessor focused on DataFrame-receiver operations with clear, stable mutation and return contracts.
7. Do not automatically mirror every public function as an accessor method.
8. Update generated typing stubs and `tools/sync_docs.py` or other tooling that depends on the old accessor location.
9. Remove the old accessor implementation from Cleaning after all references have been migrated.

### Acceptance criteria

- Importing `bynat` registers `df.bynat` automatically.
- The accessor implementation is owned by `_accessors`, not Cleaning.
- `_accessors` contains integration and binding logic only, not domain algorithms.
- Accessor methods delegate to the correct functional package.
- No circular dependency exists between `_accessors`, the root package, and functional packages.
- Existing intended accessor methods preserve their documented signatures, mutation behavior, and return contracts.
- Typing stubs, docstrings, and generated documentation are synchronized.
- All accessor and cross-cutting tests pass.

**Exit gate:** Accessor registration and delegation work through the new private integration boundary.

## Phase 3 — Root API Alignment

**Goal:** Make the root initializer match the agreed public API exactly.

### Tasks

1. Explicitly import `analytics`, `caching`, `cleaning`, and `profiling` in `bynat/__init__.py`.
2. Import `_accessors` through a private registration-only import so `df.bynat` is registered when `bynat` is imported.
3. Set root `__all__` to the four package names only.
4. Remove individual root-level exports such as `BynatAccessor`, `ProfileReport`, `profile`, `read_csv`, and `read_json`.
5. Remove incidental or import-order-dependent root package attributes.
6. Update public API tests, documentation, examples, and any internal imports to use the intended package paths.

### Acceptance criteria

The following works:

```python
import bynat

bynat.cleaning
bynat.caching
bynat.analytics
bynat.profiling

df.bynat
```

The intended class and package-level APIs work:

```python
from bynat.cleaning import BaseData, CsvFile, JsonFile
from bynat.profiling import profile, ProfileReport
```

The root namespace does not expose individual implementation objects:

```python
bynat.BaseData
bynat.ProfileReport
bynat.BynatAccessor
bynat.read_csv
bynat.read_json
```

These names must not be part of the root public API.

**Exit gate:** Root exports, `__all__`, and import-time accessor registration match the approved contract.

## Phase 4 — Package Boundaries and Documentation

**Goal:** Ensure the final package structure has intentional exports, clear ownership, and accurate documentation.

### Tasks

1. Review every package-level `__init__.py`.
2. Keep package exports minimal and intentional; maintain explicit `__all__` where appropriate.
3. Ensure private helpers, storage internals, migrations, and implementation classes are not accidentally exported.
4. Audit internal imports against the dependency rules.
5. Review `cleaning._common.py` by helper ownership and invariants; do not create `bynat._shared` without a demonstrated domain-independent responsibility.
6. Update package documentation, API examples, type stubs, and generated docs.
7. Update `docs/ARCHITECTURE_RESEARCH.md` and `docs/ROADMAP.md` to describe the architecture that was actually implemented.
8. Remove stale references to old module paths and obsolete root exports.

### Acceptance criteria

- Each package has a clear and documented responsibility.
- Package-level public exports match the approved API.
- No accidental broad re-exports exist.
- Dependency directions comply with Section 4.1.
- Documentation, examples, stubs, and implementation agree.
- No unrelated refactoring has been introduced.

## Phase 5 — Final Architecture Verification

**Goal:** Verify the completed refactor against every architectural and behavioral acceptance criterion.

### Verification checklist

- [ ] Project tree matches the approved target structure.
- [ ] Root exposes only `cleaning`, `caching`, `analytics`, and `profiling`.
- [ ] Importing `bynat` registers `df.bynat`.
- [ ] Each package owns its implementation and public API.
- [ ] Profiling core is independent of Cleaning and Analytics.
- [ ] Accessor integration is located in `_accessors`.
- [ ] Accessor methods delegate to package-owned implementations.
- [ ] No circular imports exist.
- [ ] No prohibited dependency directions exist.
- [ ] `BaseData`, `CsvFile`, and `JsonFile` continue to satisfy their intended contracts.
- [ ] `df.bynat` continues to satisfy its intended contracts.
- [ ] Return types, mutation behavior, and signatures match the approved API.
- [ ] `__all__` declarations are explicit and intentional.
- [ ] Documentation and typing stubs are synchronized.
- [ ] All required tests pass.
- [ ] Ruff passes.
- [ ] Mypy passes.
- [ ] Wheel and sdist build successfully.
- [ ] The built distribution installs and passes an appropriate smoke test.

### Acceptance rule

A documented residual gap is not considered completed work. Every acceptance criterion must either be implemented and verified, or remain explicitly blocked pending a decision. Partial acceptance requires a genuine blocker or explicit approval.

## 6. Out of scope

The following are not part of this architecture refactor unless new evidence establishes a concrete need:

- Splitting `BaseData` solely because of its physical line count.
- Splitting `stats.py` solely because of its physical line count.
- Creating a generic top-level `bynat._shared` or `common` package without a clear owner-independent contract.
- Moving Caching under Cleaning.
- Making Analytics depend on Cleaning.
- Making Profiling depend on Analytics.
- Replacing the class API with the pandas accessor.
- Automatically exposing every public function through `df.bynat`.
- Adding Analytics accessor methods without a concrete use case and eligibility review.
- Introducing service, repository, dependency-injection, or microservice layers without a demonstrated requirement.
- Preserving obsolete APIs solely for compatibility with previous published versions.

## 7. Execution and review protocol

Every phase follows the same workflow:

1. Review the phase scope and acceptance criteria.
2. Inspect the current implementation and identify affected files.
3. Implement only the changes authorized by that phase.
4. Add or update tests in accordance with `docs/TESTING_STANDARDS.md`.
5. Run the focused tests, then the required broader test suite.
6. Review public API, import behavior, dependencies, and documentation impact.
7. Have the supervisor independently verify every acceptance criterion against implementation and test evidence.
8. Return any feasible missing work for completion; do not mark it complete merely because the gap was documented.
9. Proceed to the next phase only after the current phase is accepted.

No phase should be combined with another merely for convenience. Keeping Profiling extraction, Accessor migration, and Root API alignment separate makes regressions easier to isolate and review.

## 8. Recommended execution order

| Order | Phase | Priority | Main outcome |
|---:|---|---|---|
| 1 | Phase 0 — Architecture Decisions and Baseline | P1 | Approved target contract and baseline |
| 2 | Phase 1 — Profiling Extraction | P1 | Independent `bynat.profiling` |
| 3 | Phase 2 — Accessor Migration | P1 | Private `_accessors` integration package |
| 4 | Phase 3 — Root API Alignment | P1 | Four root package exports and automatic accessor registration |
| 5 | Phase 4 — Package Boundaries and Documentation | P2 | Intentional exports and synchronized docs |
| 6 | Phase 5 — Final Architecture Verification | P1 | Verified architecture and distribution |
