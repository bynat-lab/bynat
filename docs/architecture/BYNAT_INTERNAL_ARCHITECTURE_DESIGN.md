# bynat Internal Architecture Design

**Status:** Final consistency-reviewed research and design deliverable — no implementation performed or proposed as already executed
**Baseline commit:** `6bf68bd4c99b871e6154319eb9fd82a1e8a90a0d` (`refactor(architecture): finalize Phase 5 verification`)
**Branch:** `arch-module`
**Package version:** `0.6.6` (`pyproject.toml`)
**Authoritative predecessor plan:** [`docs/temb/bynat_internal_architecture_evolution_plan.md`](../temb/bynat_internal_architecture_evolution_plan.md)
**Approved top-level plan:** [`docs/temb/bynat_architecture_refactoring_plan.md`](../temb/bynat_architecture_refactoring_plan.md)
**Research date:** 2026-11-22

> **Evidence labels**
>
> - **Fact** — directly observed in the local checkout at the baseline commit, or produced by an executed command.
> - **External evidence** — a finding supported by an explicitly linked external source that was opened for this report.
> - **Interpretation** — an architectural conclusion drawn from facts and external evidence.
> - **Decision** — a concrete architectural choice made by this design.
> - **Recommendation** — a proposed future action; not current implementation.

**Relationship to existing documents.** This is the internal architecture design required by the evolution plan. It does not replace [`docs/ARCHITECTURE_RESEARCH.md`](../ARCHITECTURE_RESEARCH.md) (the top-level research and decision record), [`docs/ROADMAP.md`](../ROADMAP.md) (the living plan), or [`docs/TESTING_STANDARDS.md`](../TESTING_STANDARDS.md). Where this design corrects an earlier research claim (the `caching._keys` consumer set, §3.3 F-3), the correction is stated explicitly.

---

## 1. Executive Decision Summary

**Decision 1 — retain the approved package boundaries and the current module tree.**
The repository is already a disciplined modular monolith with a Functional Core + Facades shape. The approved top-level structure (`cleaning`, `caching`, `analytics`, `profiling`, plus the private `_accessors` and `_internal` boundaries) is correct and is not reopened. No package is split, merged, moved, or created. No new abstraction, manager, registry, protocol, or shared package is introduced.

**Decision 2 — normalize private helper naming and remove dead internal compatibility aliases.**
Five private modules (`cleaning/_common.py`, `cleaning/_outputs.py`, `caching/_keys.py`, `caching/_migration.py`, `caching/manager.py`) currently define a canonical public-looking name in `__all__` *and* a duplicate underscore alias "for backward compatibility within the package". The alias layer is internal-only, is not public API, and previous-version compatibility is explicitly out of scope. The target keeps one canonical name per helper (the name already declared in `__all__`), updates internal import sites, and deletes the alias block and three dead private wrappers. The deleted `_migrate_legacy_json_cache` is the module-level alias in `caching/_migration.py`; the surviving symbol is the `CacheManager._migrate_legacy_json_cache` method in `caching/manager.py` (see §3.3 F-2 and the migration map). This is behavior-preserving and does not touch any public signature, docstring, stub, or test contract.

**Decision 3 — retain and formalize the documented cross-package private imports.**
`cleaning.enrich.engine` and `cleaning.enrich.translate` import `bynat.caching._keys`; `_accessors.dataframe` imports `bynat.cleaning._outputs.is_basedata_type`; `cleaning.io` and `profiling.profile` import `bynat._internal.dedupe_key`. Cache-key identity is a caching-owned invariant, BaseData-type detection is a cleaning-owned invariant consumed at the accessor adaptation seam, and `dedupe_key` is the deliberately shared private helper. Each import is retained as a narrow, documented exception to private-module privacy rather than being duplicated or promoted to public API. The complete inventory is in §3.3 (F-3) and §13.3.

**Decision 4 — enforce the architecture with an AST contract test now, and optionally adopt Import Linter later.**
The existing contract tests already pin the root API, package exports, accessor ownership, profiling independence, and `_internal` canonicalization. The design adds one dependency-free AST contract test for the package dependency matrix and private-import rule. Import Linter is recommended as a later dev-dependency adoption, not as part of this design.

**Follow-up audit (this revision).** The design was audited against source for internal consistency and completed to the Component and Behavioral levels of the evolution plan. Corrections and additions:
1. The cross-package private-import inventory is **five** edges, not one; it now includes `_accessors.dataframe → cleaning._outputs` and the two `_internal` edges (§3.3 F-3, §13.3), and enforcement represents all of them.
2. The migration proposal references only surviving symbols: the deleted symbol is the module-level alias `caching._migration._migrate_legacy_json_cache`; the surviving symbol is `CacheManager._migrate_legacy_json_cache` (§12).
3. AR-11 is justified and verified: all 31 `.py` modules declare `__all__` (§3.3 F-8, §22.1).
4. Added the component inventory (§10), module contracts (§11), behavioral contracts (§16), implementation–documentation discrepancies and test gaps (§17), and the decision register (§26).

The target tree is unchanged: the completed investigation still supports retaining the current structure. The 12 discrepancies and 15 test gaps are behavioral follow-ups, not architecture changes.

**Final consistency review (this revision).** Four targeted reviews were completed and reconciled:
1. One explicit private-helper alias policy (§6.I) listing every canonical name, every alias, every consumer (including `benchmarks/reference_impls.py`), and every migration action.
2. The cross-package private-import inventory re-scanned with **relative imports resolved** and **dynamic imports checked** (§3.3 F-3, §13.3); the completeness claim now states its exact scope.
3. Every component marked `Adjust` given an explicit decision (§10.3): 3 Required, 4 Deferred, 3 Retain.
4. The `BaseData.cache_dir` lifecycle finding classified as a **missing behavioral contract** with the precise open question (§17.3, §25 AE-Q6).

No contradictory architectural decision remains. The target tree is unchanged.

**Result:** the target tree is the current tree. The only structural change is internal content normalization in five private modules and their consumers. Every other file is retained with evidence. This is the honest result of the investigation, not a refusal to decide: each area below states the selected design, alternatives, and the evidence for the choice.

---

## 2. Repository Baseline and Evidence

### 2.1 Baseline identity (Fact)

| Item | Value |
|---|---|
| Repository root | `D:\My Own Environment Libraries\bynat\bynat` |
| Branch | `arch-module` |
| Commit | `6bf68bd4c99b871e6154319eb9fd82a1e8a90a0d` |
| Working tree | clean (`git status --porcelain` empty at investigation start) |
| Package version | `0.6.6` |
| Python | `>=3.11` |
| Core dependencies | `numpy`, `pandas` |
| Optional extras | `translation`, `geocoding`, `currency`, `categorization`, `nlp`, `sql`, `dev` |
| Test command | `./.venv-check/Scripts/python.exe -m pytest -q` |

### 2.2 Current source tree (Fact)

```text
bynat/
├── __init__.py
├── py.typed
├── _accessors/
│   ├── __init__.py
│   ├── _binding.py
│   ├── dataframe.py
│   └── dataframe.pyi
├── _internal/
│   ├── __init__.py
│   └── values.py
├── analytics/
│   ├── __init__.py
│   └── analyzer.py
├── caching/
│   ├── __init__.py
│   ├── _keys.py
│   ├── _migration.py
│   ├── _storage.py
│   └── manager.py
├── cleaning/
│   ├── __init__.py
│   ├── _common.py
│   ├── _outputs.py
│   ├── base.py
│   ├── columns.py
│   ├── io.py
│   ├── stats.py
│   ├── text.py
│   └── enrich/
│       ├── __init__.py
│       ├── currency.py
│       ├── engine.py
│       ├── geocode.py
│       ├── nlp.py
│       ├── providers.py
│       └── translate.py
└── profiling/
    ├── __init__.py
    ├── profile.py
    └── report.py
```

The repository uses a flat package layout (`bynat/` at the root), not a `src/` layout. The target tree in §8 preserves this.

### 2.3 Measured size (Fact)

Method: AST-based measurement over every tracked `bynat/**/*.py` file, excluding `__pycache__`. Total = physical lines; blank = empty/whitespace; comment = non-empty lines whose first non-whitespace char is `#`; docstring = physical span of module/class/function docstring nodes; code = the remainder. This is a comparative measure, not a quality claim.

| File | Total | Code | Blank | Comment | Docstring |
|---|---:|---:|---:|---:|---:|
| `cleaning/base.py` | 2,234 | 283 | 303 | 10 | 1,638 |
| `cleaning/stats.py` | 1,054 | 563 | 131 | 4 | 356 |
| `analytics/analyzer.py` | 737 | 297 | 148 | 0 | 292 |
| `profiling/profile.py` | 712 | 335 | 107 | 5 | 265 |
| `cleaning/columns.py` | 706 | 189 | 160 | 5 | 352 |
| `cleaning/text.py` | 523 | 207 | 128 | 1 | 187 |
| `caching/manager.py` | 460 | 137 | 102 | 1 | 220 |
| `cleaning/enrich/translate.py` | 459 | 192 | 93 | 0 | 174 |
| `cleaning/enrich/nlp.py` | 406 | 216 | 95 | 0 | 95 |
| `cleaning/io.py` | 397 | 147 | 94 | 3 | 153 |
| `profiling/report.py` | 351 | 68 | 57 | 0 | 226 |
| `cleaning/enrich/providers.py` | 259 | 45 | 59 | 0 | 155 |
| `caching/_storage.py` | 256 | 110 | 39 | 0 | 107 |
| `cleaning/enrich/currency.py` | 236 | 121 | 59 | 3 | 53 |
| `caching/_migration.py` | 232 | 151 | 28 | 2 | 51 |
| `cleaning/enrich/engine.py` | 231 | 121 | 52 | 1 | 57 |
| `_accessors/_binding.py` | 223 | 103 | 34 | 6 | 80 |
| `_accessors/dataframe.py` | 211 | 36 | 38 | 2 | 135 |
| `cleaning/enrich/geocode.py` | 182 | 84 | 42 | 0 | 56 |
| `cleaning/_outputs.py` | 129 | 36 | 32 | 1 | 60 |
| `cleaning/_common.py` | 126 | 37 | 28 | 3 | 58 |
| `caching/_keys.py` | 88 | 23 | 24 | 1 | 40 |
| `_internal/values.py` | 33 | 9 | 10 | 0 | 14 |
| `cleaning/enrich/__init__.py` | 19 | 16 | 2 | 0 | 1 |
| `__init__.py` | 18 | 10 | 3 | 0 | 5 |
| `_accessors/__init__.py` | 10 | 1 | 3 | 0 | 6 |
| `caching/__init__.py` | 8 | 7 | 1 | 0 | 0 |
| `_internal/__init__.py` | 5 | 2 | 2 | 0 | 1 |
| `analytics/__init__.py` | 5 | 2 | 2 | 0 | 1 |
| `profiling/__init__.py` | 4 | 3 | 1 | 0 | 0 |
| `cleaning/__init__.py` | 3 | 2 | 1 | 0 | 0 |
| **Total (31 files)** | **10,317** | **3,553** | **1,878** | **48** | **4,838** |

`bynat/_accessors/dataframe.pyi` (1,570 lines) is generated and excluded from the `.py` measurement.

### 2.4 Public API and export behavior (Fact)

Fresh-interpreter probe at the baseline commit:

```text
bynat.__all__            = ['cleaning', 'caching', 'analytics', 'profiling', 'read_csv', 'read_json']
bynat.read_csv.__module__ = 'bynat.cleaning.io'
df.bynat registered       = True
bynat.cleaning.__all__    = ['BaseData', 'CsvFile', 'JsonFile']
bynat.caching.__all__     = ['CacheManager', 'CACHE_DIR_ENV_VAR', 'DEFAULT_CACHE_DIR', 'shared_cache_manager']
bynat.analytics.__all__   = ['Analyzer']
bynat.profiling.__all__   = ['profile', 'ProfileReport', 'DatasetProfile', 'ColumnProfile']
```

`bynat.BaseData`, `bynat.CsvFile`, `bynat.JsonFile`, `bynat.ProfileReport`, `bynat.profile`, and `bynat.BynatAccessor` are absent from the root namespace.

### 2.5 Internal import map (Fact)

Derived from `ast` over `bynat/**/*.py`:

| Edge | Status |
|---|---|
| `bynat/__init__` → `analytics`, `caching`, `cleaning`, `profiling`, `_accessors`, `cleaning.io` | Present |
| `_accessors/dataframe` → `caching`, `cleaning` (`columns`, `io`, `stats`, `text`, `_outputs`, `enrich`), `profiling`, `_binding` | Present |
| `_accessors/_binding` → stdlib only | Present |
| `cleaning/base` → `caching`, `profiling`, `columns`, `io`, `stats`, `text`, `enrich`, `enrich.providers`, `_outputs` | Present |
| `cleaning/columns` → `_common` | Present |
| `cleaning/text` → `_common` | Present |
| `cleaning/stats` → `_common`, `_outputs` | Present |
| `cleaning/io` → `_common`, `_internal` | Present |
| `cleaning/enrich/*` → `enrich.engine`, `enrich.providers`, `_common`, `caching` | Present |
| `cleaning/enrich/engine` → `caching`, `caching._keys`, `_common` | Present |
| `cleaning/enrich/translate` → `caching`, `caching._keys`, `_common`, `engine`, `providers` | Present |
| `caching/manager` → `_migration`, `_storage` | Present |
| `caching/_migration` → `_storage` | Present |
| `profiling/profile` → `report`, `_internal` | Present |
| `analytics/analyzer` → no internal `bynat` import | Present |
| `caching` → `cleaning` / `analytics` / `profiling` | Absent |
| `profiling` → `cleaning` / `analytics` / `caching` / `_accessors` | Absent |
| functional packages → `_accessors` | Absent |
| `_internal` → any functional package | Absent |

No import cycle was found in the package graph.

### 2.6 Verification baseline (Fact, executed for this report)

```text
$ ./.venv-check/Scripts/python.exe -m pytest -q
693 passed, 29 deselected, 16 xfailed, 4 warnings in 52.07s

$ ./.venv-check/Scripts/ruff.exe check bynat tests benchmarks
All checks passed!

$ ./.venv-check/Scripts/mypy.exe
Success: no issues found in 134 source files
```

The 16 xfails are the tracked defects PD-01 (4) and PD-02 (12); the 4 warnings are upstream pandas deprecation/user warnings. Neither is an architecture failure.

---

## 3. Existing Architecture Assessment

### 3.1 Package assessment

| Package | Actual responsibility | Approved responsibility | Verdict |
|---|---|---|---|
| `cleaning` | DataFrame transformations, enrichment, file/SQL I/O, class facade | Same | Retain |
| `caching` | Cache directory resolution, public manager, SQLite persistence, legacy migration, key identity | Same | Retain |
| `analytics` | Application-independent response analytics (`Analyzer`) | Same | Retain |
| `profiling` | Non-mutating data-quality profiling and report models | Same | Retain |
| `_accessors` | pandas accessor registration, binding, delegation | Same | Retain |
| `_internal` | One canonical domain-independent value-normalization helper | Narrow shared boundary | Retain |

### 3.2 Module assessment

| Module | Responsibility | Verdict |
|---|---|---|
| `cleaning/base.py` | Supported `DataFrame` subclass facade; delegates to functional modules; owns `inplace`/stats return contracts and synchronized docstrings | Retain; do not split by LOC (79% docstrings) |
| `cleaning/columns.py` | Column rename/drop/reorder/move/reshape operations | Retain |
| `cleaning/text.py` | Keyword extraction, truncation, reference categorization | Retain |
| `cleaning/stats.py` | Hierarchical outlier/imputation/statistics operations | Retain; one coherent hierarchy domain |
| `cleaning/io.py` | JSON/CSV loaders, JSON/SQL writers | Retain; SQL optional dependency is lazily imported |
| `cleaning/_common.py` | Cleaning-scoped optional import, validation, aligned merge, subclass preservation, logger | Retain; remove duplicate aliases |
| `cleaning/_outputs.py` | Output-type validation/conversion without facade coupling | Retain; remove duplicate aliases |
| `cleaning/enrich/*` | Feature modules + shared cached-lookup engine + provider protocols/adapters | Retain |
| `caching/manager.py` | Public cache facade + process-wide shared registry | Retain; remove dead private wrappers |
| `caching/_storage.py` | SQLite connection/schema/diff persistence | Retain |
| `caching/_migration.py` | Legacy JSON migration and quarantine | Retain; remove dead aliases |
| `caching/_keys.py` | Cache-key normalization and lookup | Retain in `caching`; remove dead aliases |
| `analytics/analyzer.py` | One cohesive `Analyzer` class | Retain; no split evidence |
| `profiling/profile.py` | Profiling core algorithm | Retain |
| `profiling/report.py` | Report data models | Retain |
| `_accessors/dataframe.py` | Registered accessor + delegation | Retain |
| `_accessors/_binding.py` | Signature/docstring/cache binding mechanics | Retain |
| `_internal/values.py` | Canonical `dedupe_key` | Retain |

### 3.3 Verified findings

**F-1 — Duplicate private alias layer (confirmed defect, internal only).**
`cleaning/_common.py:121-126`, `cleaning/_outputs.py:124-129`, `caching/_keys.py:85-88`, and `caching/_migration.py:230-231` define canonical names in `__all__` and then re-bind underscore aliases "for backward compatibility within the package". Consumers import the underscore aliases (`columns.py:8`, `stats.py:9-19`, `io.py:12`, `text.py:11`, `enrich/currency.py:11`, `enrich/geocode.py:7`, `enrich/nlp.py:11`, `enrich/providers.py:9`, `enrich/translate.py:10,12-17`, `enrich/engine.py:12`). Some aliases are dead (`_is_basedata_type`, `_constructor_accepts_data`, `_quarantine_corrupt_cache_file`, `_migrate_legacy_json_cache`). Previous-version compatibility is explicitly out of scope, so the alias layer is unnecessary internal duplication.

**F-2 — Dead private wrappers in `caching/manager.py`.**
`manager.py:38-39` define `_SQLITE_DATABASE_NAME` / `_SQLITE_TIMEOUT_SECONDS` (no consumers), and `manager.py:158-160` defines `_migrate_legacy_cache`, a "compatibility name" used only by `tests/modules/caching/migration/legacy/test_legacy_rollback.py:180`. None is in `__all__` or public API. The test already calls the canonical `manager._migrate_legacy_json_cache` at lines 145, 151, 164, and 177; only line 180 uses the obsolete wrapper, so the canonical surviving symbol is unambiguous.

**F-3 — Cross-package private imports: complete inventory (confirmed).**
An AST scan of every static import in `bynat/**/*.py` — absolute imports plus relative imports resolved to their destination modules — finds five cross-package imports of private modules. All five are absolute. Sixteen relative imports target private modules, all intra-package (listed in §13.3); no relative import crosses a top-level package boundary. Dynamic imports are limited to `import_optional`'s runtime `importlib.import_module` for optional third-party packages and `cleaning/text.py`'s `importlib.import_module("ahocorasick")`; no dynamic import targets an internal module. The completeness claim is supported for static absolute and relative imports.

| # | Importing module | Imported module | Symbol(s) | Consumer / use case | Ownership rationale | Disposition |
|---|---|---|---|---|---|---|
| 1 | `cleaning/enrich/engine.py` | `caching._keys` | `_cache_value_key` | Default cache-key function for the shared cached-lookup engine | Cache-key identity is caching-owned | Keep; explicit exception |
| 2 | `cleaning/enrich/translate.py` | `caching._keys` | `_cache_has_value`, `_cache_lookup_value` | Cache probing in conditional/categorical translation | Same | Keep; explicit exception |
| 3 | `_accessors/dataframe.py` | `cleaning._outputs` | `is_basedata_type` | Accessor `profile` output adaptation for `output_type=BaseData` | BaseData ancestry detection is cleaning-owned; `_outputs` exists to avoid a lower-level-to-facade import | Keep; explicit exception |
| 4 | `cleaning/io.py` | `_internal` | `dedupe_key` | JSON append duplicate detection for unhashable cells | Deliberately shared domain-independent normalization | Keep; intended shared private package |
| 5 | `profiling/profile.py` | `_internal` | `dedupe_key` | Distinct-count and duplicate detection for unhashable values | Same | Keep; intended shared private package |

Rows 1-3 are exceptions to a strict private-module rule and must be represented in enforcement. Rows 4-5 target a top-level private *package* (`_internal`) that is the design's intended shared boundary, not an accidental coupling. The predecessor research report incorrectly stated the `_keys` consumer set as "cache manager and enrichment engine"; the manager does not import `_keys`. This design corrects that evidence.

**F-4 — Stale logger names are intentional.**
`cleaning/_common.py:21`, `caching/manager.py:31`, `caching/_storage.py:15`, `caching/_migration.py:19` use `logging.getLogger("bynat.cleaning.Cleaning")` / `"bynat.caching.Caching"`, with comments stating the pre-0.4 names are kept so existing logging configuration still applies. This is a documented compatibility decision, not an accident. Retain.

**F-5 — No architectural gap in module size or cohesion.**
The largest modules are docstring-heavy facades or cohesive domains. `base.py` is 1,638 docstring lines of 2,234; `stats.py` is one hierarchy domain; `analyzer.py` is one class. The predecessor plan explicitly excludes splitting them by LOC. No split is justified.

**F-6 — `save_to_sql` optional-dependency isolation is already correct.**
`cleaning/io.py:370` imports SQLAlchemy through `_import_optional` inside the function. Moving it to a separate module would be fragmentation, not boundary improvement. Retain.

**F-7 — `_internal` is a justified narrow shared location.**
`bynat/_internal/values.py` defines `dedupe_key`; `cleaning/io.py:10` and `profiling/profile.py:19` import it as `_dedupe_key`. `tests/cross_cutting/contracts/test_internal_shared_helpers.py` pins canonicality, no duplicate definitions, and stdlib/NumPy-only imports. This is the correct response to the plan's §4.5 constraint: a shared location with a demonstrated domain-independent responsibility, not a generic `_shared` package.

**F-8 — `__all__` compliance is complete (verified).**
All 31 `bynat/**/*.py` modules declare `__all__`. Thirty use an assignment; `bynat/_accessors/_binding.py` uses an annotated `__all__: list[str] = []`. `tests/cross_cutting/contracts/test_doc_drift.py::test_package_modules_declare_valid_all_and_remove_legacy_shims` already asserts presence, list/tuple type, and non-underscore symbol names. AR-11 is therefore justified, currently satisfied, and included in the proposed AST contract test.

### 3.4 Negative findings (investigated, not found)

- No internal import cycle.
- No functional package imports `_accessors`.
- No `profiling` import of `cleaning`, `analytics`, `caching`, or `_accessors`.
- No `analytics` import of another `bynat` package.
- No `caching` import of a functional package.
- No row-wise `apply(axis=1)`/`iterrows`/`itertuples` in data paths.
- No generic `_shared` package, plugin registry, DI container, or service/repository layer.

---

## 4. External Research Findings

Each finding names the source and whether it was opened directly for this report. Architecture inference is labeled separately.

### 4.1 Python library internals

**E-1 — pandas public aggregation, private core, and accessor extension (opened).**
pandas documents custom accessors as namespaces registered with `register_dataframe_accessor`, initialized with the decorated object; the initializer may validate and raise `AttributeError`, and a new accessor instance is created on each attribute access, so accessor state is not retained. pandas assembles its top-level namespace by aggregation (`pandas/__init__.py` imports from `pandas.core.api` and `pandas.io.api` and declares `__all__` for type checkers), documents `pandas.core` and `pandas.compat` as PRIVATE, and exposes extension hooks through the public `pandas.api.extensions`.
Sources: [pandas Extending pandas](https://pandas.pydata.org/docs/development/extending.html), [pandas API reference index](https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/reference/index.rst), [pandas/core/api.py](https://raw.githubusercontent.com/pandas-dev/pandas/main/pandas/core/api.py), [pandas/core/accessor.py](https://raw.githubusercontent.com/pandas-dev/pandas/main/pandas/core/accessor.py).
Application: supports `df.bynat` as a stateless integration facade and a narrow root/package `__all__`, with algorithms outside the accessor and private implementation modules clearly distinguished from public API.

**E-2 — scikit-learn estimator/transformer contract (opened).**
scikit-learn distinguishes Estimator (`fit`), Predictor (`predict`), and Transformer (`transform`, `fit_transform`), and documents that transformers "should never change the number of input samples, and the output of `transform` should correspond to its input samples in the same given order." It keeps the same interface for stateless transformations (`FunctionTransformer`, `requires_fit=False`) and makes the output container explicit through `set_output` (`default`/`pandas`/`polars`). It separates public API from private tools and keeps compositional mixins in `sklearn/base.py`.
Sources: [Developing scikit-learn estimators](https://scikit-learn.org/stable/developers/develop.html), [sklearn/base.py](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/base.py), [FunctionTransformer](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.FunctionTransformer.html), [SLEP 18 set_output](https://scikit-learn-enhancement-proposals.readthedocs.io/en/latest/slep018/proposal.html).
Application: bynat transformations are stateless functions with explicit frame-first signatures and index/order preservation, not `fit`/`transform` estimators. Adopt the *contract discipline* (explicit length/order, copy, and output-container guarantees), reject the estimator base-class machinery.

**E-3 — Polars lazy/eager and query engine (opened).**
Polars separates an eager DataFrame API from a lazy `LazyFrame` that builds a logical plan, optimizes it, and executes a physical plan. The Python layer is a frontend over a Rust query engine.
Sources: [Polars Lazy API](https://docs.pola.rs/user-guide/concepts/lazy-api/), [A bird's eye view of Polars](https://pola.rs/posts/polars_birds_eye_view/).
Application: bynat has no lazy/optimized execution requirement; adding a plan/optimizer layer would be speculative. Reject.

**E-4 — SQLAlchemy layered Core/ORM and dialect separation (opened).**
SQLAlchemy documents distinct functional areas organized into layers: Core (engine, connection, pool, SQL expression language) and ORM building on Core, with dialects isolating DBAPI/database specifics and lazy engine initialization.
Sources: [SQLAlchemy Overview](https://docs.sqlalchemy.org/en/latest/intro.html), [Engine Configuration](https://www.sqlalchemy.org/docs/latest/core/engines.html).
Application: bynat's I/O and caching boundaries should own their external specifics (SQLite in `caching._storage`, SQLAlchemy in `cleaning.io.save_to_sql`, providers in `cleaning.enrich.providers`) and expose a small contract. Adopt the *layered dependency* idea locally, not the ORM.

**E-5 — Pydantic schema/validator separation and private `_internal` convention (opened).**
Pydantic V2 separates model definition (`pydantic`) from validation/serialization (`pydantic-core`) and communicates through a serializable core schema; it explicitly identifies private objects through a `_internal` subpackage and a strict public/private split.
Sources: [Pydantic Architecture](https://pydantic.dev/docs/validation/latest/internals/architecture), [Pydantic v2 announcement](https://pydantic.dev/docs/validation/1.10/blog/pydantic-v2).
Application: supports a narrow private `_internal` package and deliberate `__all__` boundaries. It does not justify a schema/validator split in bynat.

**E-6 — Functional Core, Imperative Shell (opened).**
The pattern separates a functional core (values in, values out) from an imperative shell that performs I/O and external effects, making the core easy to test without test doubles.
Source: [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell).
Application: bynat already implements this: functional modules are the core; `BaseData`, the accessor, providers, and `CacheManager` are the shell. Adopt and preserve.

**E-7 — Modular monolith and bounded contexts (opened/search).**
A modular monolith keeps one deployable but organizes code into bounded contexts with explicit public interfaces and enforced boundaries; GitLab's design document describes extracting cohesive domains into modules with small public interfaces and using a static analyzer (Packwerk) to enforce privacy and explicit dependencies.
Sources: [GitLab Hexagonal Monolith](https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/modular_monolith/hexagonal_monolith), [Modular Monolith is the new Microservices](https://mathieueveillard.com/articles/modular-monolith).
Application: bynat is a small modular monolith with domain packages and enforced boundaries. Adopt the boundary-enforcement idea; reject multi-service extraction and event buses.

**E-8 — NumPy public/private module tiers and NEP 52 (opened).**
NumPy documents three module tiers (main, special-purpose, legacy), computes `numpy.__all__` as a union of submodule `__all__` lists, moved the former `numpy.core` implementation to the private `numpy._core`, and states in NEP 52 the goals of "a clear distinction between what is private and what is public" and "each public function should be available from only one place." `numpy.lib` is a curated public wrapper over private `_*_impl` modules.
Sources: [NumPy module structure](https://numpy.org/doc/stable/reference/module_structure.html), [NEP 52](https://numpy.org/neps/nep-0052-python-api-cleanup.html), [numpy/__init__.py](https://raw.githubusercontent.com/numpy/numpy/v2.2.0/numpy/__init__.py), [numpy/lib/__init__.py](https://raw.githubusercontent.com/numpy/numpy/v2.2.0/numpy/lib/__init__.py).
Application: supports a deliberate public `__all__`, a private implementation package (`_internal`), and one canonical location per helper. It does not justify renaming bynat's public modules.

**E-9 — Transformation contract synthesis (inference from E-1, E-2).**
Across pandas and scikit-learn, a robust transformation contract specifies four axes explicitly: (i) length/order preservation (sklearn forbids changing sample count and requires same-order correspondence; pandas `DataFrame.transform` requires the same size along the axis), (ii) copy semantics (pandas copy-on-write means derived frames behave as copies; sklearn cloning copies constructor arguments and yields an unfitted estimator), (iii) output container/type (sklearn `set_output`; pandas `.array` zero-copy vs `.to_numpy()` conversion), and (iv) stateless vs stateful (sklearn `FunctionTransformer` keeps the interface with `requires_fit=False`).
Sources: [pandas DataFrame.transform](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.transform.html), [pandas Copy on write](https://pandas.pydata.org/docs/development/copy_on_write.html).
Application: bynat already states (i) index/order preservation and (ii) `inplace` copy-vs-mutate contracts, and (iii) `output_type` conversion. The design preserves these and does not add a stateful estimator layer.

### 4.2 Architecture enforcement

**E-10 — Import Linter contract types (opened).**
Import Linter analyzes imports and checks user-defined contracts. Contract types include `forbidden`, `protected` (a module may be imported only by an allow-list), `layers`, `independence`, `private_modules` (underscore modules are scoped to their parent package; direct imports only), and `acyclic_siblings`. Contracts are configured in `.importlinter`, `setup.cfg`, or `pyproject.toml`; `ignore_imports` exempts a specific edge, and `broken_contract_guidance` supplies remediation text. The `private_modules` contract was added in Import Linter 2.17.
Sources: [Contract types](https://import-linter.readthedocs.io/en/stable/contract_types/), [Forbidden](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/), [Protected](https://import-linter.readthedocs.io/en/stable/contract_types/protected/), [Private modules](https://import-linter.readthedocs.io/en/stable/contract_types/private_modules/), [Configure](https://import-linter.readthedocs.io/en/stable/get_started/configure), [Release notes](https://import-linter.readthedocs.io/en/stable/release_notes/).
Application: the recommended enforcement mechanism. A `protected` contract on `bynat.caching._keys` with an allow-list of `bynat.cleaning.enrich.engine` and `bynat.cleaning.enrich.translate` is more precise than a blanket `private_modules` exception.

### 4.3 Integration and dependencies

**E-11 — Plugin discovery is a deliberate mechanism, not a default (opened).**
PyPA documents three plugin-discovery approaches — naming convention, namespace packages, and package metadata (entry points) — and notes that namespace packages are complex and that one bad plugin can make the project unimportable. Entry points advertise `group`/`name`/`object reference` and are resolved lazily with `EntryPoint.load()`. The trade-off is inference: entry points are justified when multiple independently distributed plugins implement one interface; they are unjustified when all implementations ship in one distribution, where a plain import or internal registry is simpler.
Sources: [Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/), [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/), [importlib.metadata](https://docs.python.org/3/library/importlib.metadata.html).
Application: bynat has no third-party plugin requirement. Reject entry-point discovery and registries.

**E-12 — Package initialization and `__all__` (opened).**
Python executes a package `__init__.py` on import, and `__all__` controls `from package import *` and signals the public surface.
Sources: [Python Modules](https://docs.python.org/3/tutorial/modules.html), [Python import system](https://docs.python.org/3/reference/import.html).
Application: explicit root/package imports and exact `__all__` are the correct mechanism; incidental import-order attributes are not API.

**E-13 — `pyproject.toml` optional dependencies (opened).**
PEP 621 `optional-dependencies` maps each extra to `Requires-Dist` entries guarded by the extra name, so an extra is installed only when requested.
Sources: [PEP 621](https://peps.python.org/pep-0621/), [PyPA `pyproject.toml` specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/).
Application: bynat's extras are correctly declared; no change.

**E-14 — Private-module convention and its enforcement (opened).**
Python's `from module import *` excludes names beginning with `_`; PEP 8 defines the leading underscore as a weak "internal use" indicator; `__all__` controls star-imports from packages. Enforcement is tool-based: Import Linter's `private_modules` contract and Ruff's preview `PLC2701 import-private-name` rule both flag cross-module private imports.
Sources: [Python Modules](https://docs.python.org/3/tutorial/modules.html), [PEP 8 naming conventions](https://peps.python.org/pep-0008/#naming-conventions), [Ruff import-private-name](https://docs.astral.sh/ruff/rules/import-private-name/), [Import Linter private modules](https://import-linter.readthedocs.io/en/stable/contract_types/private_modules/).
Application: bynat's private modules (`_common`, `_outputs`, `_keys`, `_migration`, `_storage`, `_binding`, `_internal`, `_accessors`) are a convention; the design makes the convention enforceable and records the documented exceptions in §13.3.

---

## 5. Architecture Pattern Evaluation

| Pattern | Problem addressed | Fit for bynat | Complexity cost | Maintenance impact | Performance impact | Compatibility impact | Decision |
|---|---|---|---|---|---|---|---|
| Modular monolith | Domain boundaries without deployment overhead | Strong; already the container | Low | Simplifies | None | None | **Adopt (retain)** |
| Functional Core / Imperative Shell | Separate computation from effects | Strong; already present | Low | Simplifies testing | None | None | **Adopt (retain)** |
| Layered architecture (as dependency rule) | Enforce dependency direction | Useful as a rule, not as a directory tree | Low if rule-only | Clarifies | None | None | **Adapt** (rule only) |
| Hexagonal / Ports and Adapters | Isolate external services | Partial; provider protocols already do this | High if formalized | Adds indirection | None | None | **Reject** (providers are enough) |
| Clean Architecture | Rings of entities/use cases/interface adapters | Poor; bynat has no use-case layer | High | Complicates | None | None | **Reject** |
| Domain-oriented packages | Ownership by domain | Strong; current packages are domains | Low | Simplifies | None | None | **Adopt (retain)** |
| Composition over inheritance | Reuse without deep hierarchies | Strong; providers, engine, binding use composition | Low | Simplifies | None | None | **Adopt (retain)** |
| Protocol-based interfaces | Structural external contracts | Justified only for providers | Low (3 protocols) | Appropriate | `runtime_checkable` cost only on checks | None | **Adopt (retain, do not expand)** |
| Plugin / extension architecture | Third-party extensions | No requirement | High | Complicates | Discovery overhead | New API | **Reject** |
| Pipeline / transformation architecture | Composable multi-stage transforms | Partial; enrichment engine is an internal pipeline | Medium if generalized | Would add a generic engine | Unnecessary overhead | None | **Reject** (keep the concrete enrichment engine) |

---

## 6. Final Architectural Decisions

### A. Package-internal organization

**Decision:** each approved package keeps its current internal organization. Subsystems:

| Package | Subsystems | Modules |
|---|---|---|
| `cleaning` | Functional transformations (`columns`, `text`, `stats`), I/O (`io`), enrichment (`enrich`), facade (`base`), private helpers (`_common`, `_outputs`) | current modules |
| `caching` | Public facade (`manager`), persistence (`_storage`), migration (`_migration`), key identity (`_keys`) | current modules |
| `analytics` | Analytics response engine (`analyzer`) | current module |
| `profiling` | Profiling core (`profile`), report models (`report`) | current modules |
| `_accessors` | Registration/delegation (`dataframe`), binding mechanics (`_binding`) | current modules |
| `_internal` | Value normalization (`values`) | current module |

**Reason:** ownership matches change reasons and dependency direction; no subsystem is large enough or independent enough to require a new package. **Alternatives rejected:** global layers (`api`/`domain`/`infrastructure`) obscure domain ownership; a quality umbrella beyond `profiling` is premature; `_shared` is unjustified.

### B. Module boundaries

**Decision:** retain every current module boundary. Split none; merge none. **Reason:** each module has one coherent responsibility; the only multipurpose private module (`_common`) is cleaning-scoped with no non-cleaning consumer, so splitting it would fragment a coherent helper set. **Alternatives rejected:** splitting `base.py`/`stats.py`/`analyzer.py` by LOC; splitting `io.py` to isolate SQL; splitting `enrich/engine.py` from feature modules.

### C. Shared internal components

**Decision:** canonical owners are `bynat/_internal/values.py` (`dedupe_key`), `cleaning/_common.py` (cleaning helpers), `cleaning/_outputs.py` (output conversion), `cleaning/enrich/engine.py` (cached lookup), `cleaning/enrich/providers.py` (provider contracts), `caching/_keys.py` (cache-key identity), `caching/_storage.py` (SQLite), `caching/_migration.py` (migration). Import direction is functional packages → owner; owners never import consumers. **Reason:** invariants and change reasons are owned by the domain. **Alternatives rejected:** a generic `_shared` package; duplicating key normalization in enrichment; moving `_keys` into `enrich` (would make a consumer own storage identity).

### D. Data transformation architecture

**Decision:** keep the Functional Core + Facades shape.

- Pure data transformations: `cleaning/columns.py`, `text.py`, `stats.py`, `profiling/profile.py`, `analytics/analyzer.py`.
- Validation/normalization: `_common.require_positive_int`, `_outputs.validate_output_type`, `_internal.dedupe_key`, `caching/_keys`.
- Data access/I/O: `cleaning/io.py`, `caching/_storage.py`, `caching/_migration.py`.
- External integrations: `cleaning/enrich/providers.py`, `cleaning/enrich/*`, `save_to_sql`.
- Stateful operations: `CacheManager`, provider instances, `shared_cache_manager`.
- Public API orchestration: `BaseData` and `BynatAccessor`.

**Reason:** this is the existing, tested separation. **Alternatives rejected:** a generic transformation engine/registry; a `fit`/`transform` estimator layer.

### E. Integration architecture

**Decision:** optional integrations stay lazy and isolated: providers behind `provider=` protocols; SQLAlchemy behind `_import_optional` in `save_to_sql`; Aho-Corasick behind `_import_optional` in `text.py`; spaCy behind `_import_optional` in `nlp.py`. No plugin discovery, no DI container. **Reason:** concrete use cases only. **Alternatives rejected:** entry-point plugins; a generic integration framework.

### F. Internal interfaces

**Decision:** ordinary functions are the default. Classes/protocols exist only where they have real consumers:

| Interface | Kind | Consumer | Reason |
|---|---|---|---|
| `CacheManager` | Class | cleaning, accessor, enrichment | Owns SQLite lifecycle, baselines, shared registry |
| `Analyzer` | Class | analytics public API | Holds a defensive copy and a response workflow |
| `BaseData`/`JsonFile`/`CsvFile` | Classes | public class API | `DataFrame` subclass with metadata and `inplace` contracts |
| `BynatAccessor` | Class | pandas registration | pandas requires a registered class |
| `Translator`, `Geocoder`, `RateSource` | Protocols | enrichment features + `provider=` | Structural external-service contracts |
| `DatasetProfile`, `ColumnProfile`, `ProfileReport` | Dataclasses | profiling public API | Structured report models |
| `SQLiteStorage` | Class | manager, migration | Owns connection/schema/diff details |

**Reason:** each has a concrete consumer and lifecycle. **Alternatives rejected:** protocols for internal helpers; base classes for unrelated operations.

### G. State and lifecycle

**Decision:** `CacheManager` owns SQLite connections (created per operation, explicit `BEGIN IMMEDIATE`, WAL, finite busy timeout, always closed); `shared_cache_manager` owns the process-wide registry with a lock; `BaseData` owns its lazily created manager via metadata; the accessor holds a manager by reference. File handles are context-managed; `save_to_sql` disposes its engine in `finally`. Provider resources are thread-local or per-call. **Reason:** demonstrated lifecycle responsibility. **Alternatives rejected:** a global cache singleton without scoping; a resource manager/registry beyond `shared_cache_manager`.

### H. Architecture enforcement

**Decision:** enforce with (1) existing contract tests, (2) one new dependency-free AST contract test for the dependency matrix and private-import rule, and (3) optional later Import Linter adoption. **Reason:** no new runtime dependency; the rule is checkable from source. **Alternatives rejected:** relying on review alone; adding Import Linter as a hard dependency in this phase.

### I. Private helper alias policy

**Policy.** The canonical name of every private helper is the name declared in its owning module's `__all__`. No compatibility alias is retained: previous-version compatibility is out of scope, and no alias has an external consumer. Internal consumers import the canonical name.

| Helper owner | Canonical names (`__all__`) | Aliases removed | Consumers to migrate |
|---|---|---|---|
| `cleaning/_common.py` | `import_optional`, `require_positive_int`, `left_merge_aligned`, `like`, `logger`, `FrameT`, `HIERARCHICAL_STATS_COLUMNS` | `_import_optional`, `_require_positive_int`, `_left_merge_aligned`, `_like`, `_HIERARCHICAL_STATS_COLUMNS` | `cleaning/io.py`, `cleaning/text.py`, `cleaning/columns.py`, `cleaning/stats.py`, `cleaning/enrich/{currency,engine,geocode,nlp,providers,translate}.py`, `benchmarks/reference_impls.py` |
| `cleaning/_outputs.py` | `is_basedata_type`, `validate_output_type`, `convert_output`, `constructor_accepts_data`, `convert_default_output` | `_is_basedata_type` (dead), `_validate_output_type`, `_convert_output`, `_constructor_accepts_data` (dead), `_convert_default_output` | `cleaning/stats.py` |
| `caching/_keys.py` | `cache_value_key`, `cache_has_value`, `cache_lookup_value` | `_cache_value_key`, `_cache_has_value`, `_cache_lookup_value` | `cleaning/enrich/engine.py`, `cleaning/enrich/translate.py` |
| `caching/_migration.py` | `migrate_legacy_json_cache`, `quarantine_corrupt_cache_file` | `_migrate_legacy_json_cache` (dead), `_quarantine_corrupt_cache_file` (dead) | none |
| `caching/manager.py` | `CacheManager`, `shared_cache_manager`, `resolve_cache_dir`, constants | `_SQLITE_DATABASE_NAME` (dead), `_SQLITE_TIMEOUT_SECONDS` (dead), `_migrate_legacy_cache` (test-only wrapper) | `tests/modules/caching/migration/legacy/test_legacy_rollback.py:180` |

**Not a compatibility alias.** `cleaning/io.py` and `profiling/profile.py` import the canonical `dedupe_key` under a local `_dedupe_key` name. That is a consumer-side naming convention, not a module-level alias with a separate definition; it remains unchanged.

**True wrappers.** `CacheManager._quarantine_corrupt_cache_file` and `CacheManager._migrate_legacy_json_cache` are delegating methods, not aliases; they remain. Only `CacheManager._migrate_legacy_cache` is an obsolete wrapper and is removed.

**Justification.** Every removed alias is private-module-internal, absent from `__all__`, and either dead or used only by bynat-project consumers that can import the canonical name. No alias is retained as a compatibility mechanism, so no retained alias requires a compatibility justification.

---

## 7. Package Responsibilities and Subsystems

### 7.1 `bynat.cleaning`

Owns DataFrame cleaning/transformation functions, enrichment, file/SQL I/O, and the supported class facade. Public exports: `BaseData`, `CsvFile`, `JsonFile`. Subsystems: transformations, I/O, enrichment, facade, private helpers. Must not own: accessor registration, profiling core, cache storage.

### 7.2 `bynat.caching`

Owns cache directory resolution, the public `CacheManager`, SQLite persistence, legacy migration/quarantine, and cache-key identity. Public exports: `CacheManager`, `shared_cache_manager`, `CACHE_DIR_ENV_VAR`, `DEFAULT_CACHE_DIR`. Must not own: cleaning/analytics algorithms.

### 7.3 `bynat.analytics`

Owns application-independent analytics and response contracts. Public export: `Analyzer`. Must not import another `bynat` package.

### 7.4 `bynat.profiling`

Owns non-mutating data-quality profiling and report models. Public exports: `profile`, `ProfileReport`, `DatasetProfile`, `ColumnProfile`. Must not import cleaning, analytics, caching, or `_accessors`.

### 7.5 `bynat._accessors` (private)

Owns pandas registration, binding, accessor signatures, and accessor-specific output adaptation. Must not own algorithms, report models, cache storage, or provider implementations. Functional packages must not import it.

### 7.6 `bynat._internal` (private)

Owns domain-independent value normalization. Must import only stdlib and NumPy. Must not import functional packages.

---

## 8. Complete Final Target Project Tree

```text
bynat/                                  # flat layout at repository root (not src/)
├── __init__.py                         # root API: 6 names + private accessor registration
├── py.typed                            # PEP 561 marker
├── _accessors/                         # private pandas integration boundary
│   ├── __init__.py                     # exports BynatAccessor
│   ├── _binding.py                     # signature/docstring/cache wrapper factories
│   ├── dataframe.py                    # registered df.bynat accessor + delegation
│   └── dataframe.pyi                   # generated accessor stub (tools/sync_docs.py)
├── _internal/                          # private cross-package value normalization
│   ├── __init__.py                     # exports dedupe_key
│   └── values.py                       # canonical dedupe_key
├── analytics/
│   ├── __init__.py                     # exports Analyzer
│   └── analyzer.py                     # Analyzer class
├── caching/
│   ├── __init__.py                     # exports CacheManager, constants, shared_cache_manager
│   ├── _keys.py                        # cache-key normalization/lookup (canonical names)
│   ├── _migration.py                   # legacy JSON migration/quarantine (canonical names)
│   ├── _storage.py                     # SQLite connection/schema/diff persistence
│   └── manager.py                      # CacheManager + shared registry (dead wrappers removed)
├── cleaning/
│   ├── __init__.py                     # exports BaseData, CsvFile, JsonFile
│   ├── _common.py                      # cleaning helpers (canonical names, no alias block)
│   ├── _outputs.py                     # output conversion (canonical names, no alias block)
│   ├── base.py                         # BaseData/JsonFile/CsvFile facade
│   ├── columns.py                      # column/reshape operations
│   ├── io.py                           # JSON/CSV loaders, JSON/SQL writers
│   ├── stats.py                        # hierarchical statistics/imputation/outliers
│   ├── text.py                         # keyword/truncation/categorization
│   └── enrich/
│       ├── __init__.py                 # provider exports
│       ├── currency.py                 # cached USD conversion
│       ├── engine.py                   # shared cached-lookup engine
│       ├── geocode.py                  # cached geocoding
│       ├── nlp.py                      # cached spaCy entity extraction
│       ├── providers.py               # provider protocols + default adapters
│       └── translate.py                # language imputation + cached translation
└── profiling/
    ├── __init__.py                     # exports profile + report models
    ├── profile.py                      # profiling core algorithm
    └── report.py                       # report data models
```

No file is added, removed, renamed, or moved. The only edits are internal content normalization in the five private modules listed in §12.

---

## 9. File-by-File Responsibility Specification

Public status legend: **Public** = reachable through an intentional package `__all__`; **Package-internal** = importable module not re-exported in a package `__all__`; **Private** = underscore module/package outside any public API.

| Path | Responsibility | Main contents | Dependencies (internal) | Public status | Origin | Rationale |
|---|---|---|---|---|---|---|
| `bynat/__init__.py` | Root API and accessor registration | 6-name `__all__`; package bindings; `read_csv`/`read_json`; private `_accessors` import | all packages, `_accessors`, `cleaning.io` | Public | Existing | Approved root contract |
| `bynat/py.typed` | PEP 561 typing marker | marker file | none | Public | Existing | Typed package |
| `bynat/_accessors/__init__.py` | Export the accessor class | `BynatAccessor` | `_accessors.dataframe` | Package-internal | Existing | Private integration boundary |
| `bynat/_accessors/_binding.py` | Wrapper factories for accessor methods | `_method_signature`, `_with_inplace`, `_frame_method`, `_cached_frame_method` | none | Private | Existing | Integration mechanics, no algorithms |
| `bynat/_accessors/dataframe.py` | Registered `df.bynat` accessor and delegation | `BynatAccessor`, module-level `profile` adapter | `cleaning`, `caching`, `profiling`, `_binding` | Package-internal | Existing | Accessor ownership |
| `bynat/_accessors/dataframe.pyi` | Generated typing surface | stub methods | generated | Package-internal | Existing (generated) | Editor/typing support |
| `bynat/_internal/__init__.py` | Export the canonical value helper | `dedupe_key` | `_internal.values` | Private | Existing | Narrow shared boundary |
| `bynat/_internal/values.py` | Domain-independent value normalization | `dedupe_key` | none | Private | Existing | Canonical shared helper |
| `bynat/analytics/__init__.py` | Export `Analyzer` | `Analyzer` | `analytics.analyzer` | Public | Existing | Package API |
| `bynat/analytics/analyzer.py` | Application-independent analytics responses | `Analyzer` + private helpers | none | Public | Existing | Cohesive domain class |
| `bynat/caching/__init__.py` | Export cache API | `CacheManager`, constants, `shared_cache_manager` | `caching.manager` | Public | Existing | Package API |
| `bynat/caching/_keys.py` | Cache-key normalization and lookup | `cache_value_key`, `cache_has_value`, `cache_lookup_value` | none | Private | Existing (content normalized) | Caching-owned key identity |
| `bynat/caching/_migration.py` | Legacy JSON migration and quarantine | `migrate_legacy_json_cache`, `quarantine_corrupt_cache_file` | `caching._storage` | Private | Existing (content normalized) | Migration ownership |
| `bynat/caching/_storage.py` | SQLite persistence | `SQLiteStorage`, `connect_sqlite`, constants | none | Private | Existing | Storage ownership |
| `bynat/caching/manager.py` | Public cache facade and shared registry | `CacheManager`, `resolve_cache_dir`, `shared_cache_manager`, constants | `caching._migration`, `caching._storage` | Public | Existing (dead wrappers removed) | Cache lifecycle ownership |
| `bynat/cleaning/__init__.py` | Export class facade | `BaseData`, `CsvFile`, `JsonFile` | `cleaning.base` | Public | Existing | Package API |
| `bynat/cleaning/_common.py` | Cleaning-scoped shared helpers | `import_optional`, `require_positive_int`, `left_merge_aligned`, `like`, `logger`, `FrameT`, `HIERARCHICAL_STATS_COLUMNS` | none | Private | Existing (content normalized) | Cleaning owns its helper semantics |
| `bynat/cleaning/_outputs.py` | Output-type validation/conversion | `is_basedata_type`, `validate_output_type`, `convert_output`, `constructor_accepts_data`, `convert_default_output` | none | Private | Existing (content normalized) | Avoids lower-level→facade coupling |
| `bynat/cleaning/base.py` | Supported `DataFrame` subclass facade | `BaseData`, `JsonFile`, `CsvFile`, `_shares_doc` | `cleaning` modules, `enrich`, `caching`, `profiling`, `_outputs` | Public | Existing | Supported class API |
| `bynat/cleaning/columns.py` | Column/reshape operations | 9 functions | `_common` | Package-internal | Existing | Cohesive transformation module |
| `bynat/cleaning/io.py` | JSON/CSV loaders, JSON/SQL writers | `read_json`, `read_csv`, `save_to_json`, `save_to_sql` | `_common`, `_internal` | Package-internal | Existing | I/O boundary |
| `bynat/cleaning/stats.py` | Hierarchical statistics/imputation/outliers | 5 public functions + hierarchy helpers | `_common`, `_outputs` | Package-internal | Existing | One hierarchy domain |
| `bynat/cleaning/text.py` | Keyword/truncation/categorization | 3 public functions + matchers | `_common` | Package-internal | Existing | Cohesive text module |
| `bynat/cleaning/enrich/__init__.py` | Export provider types | 6 provider symbols | `enrich.providers` | Package-internal | Existing | Provider contract surface |
| `bynat/cleaning/enrich/currency.py` | Cached USD conversion | `convert_to_usd` | `caching`, `_common`, `engine`, `providers` | Package-internal | Existing | Enrichment feature |
| `bynat/cleaning/enrich/engine.py` | Shared cached-lookup engine | `_cached_map`, `_rate_limited_map`, `SKIP`, `Fetch`, `FetchMany` | `caching`, `caching._keys`, `_common` | Private | Existing | Genuinely shared enrichment algorithm |
| `bynat/cleaning/enrich/geocode.py` | Cached geocoding | `fill_missing_coordinates` | `caching`, `_common`, `engine`, `providers` | Package-internal | Existing | Enrichment feature |
| `bynat/cleaning/enrich/nlp.py` | Cached spaCy entity extraction | `extract_entities_nlp` | `caching`, `_common`, `engine` | Package-internal | Existing | Enrichment feature |
| `bynat/cleaning/enrich/providers.py` | Provider protocols and default adapters | 3 protocols + 3 adapters | `_common` | Package-internal | Existing | External-service contracts |
| `bynat/cleaning/enrich/translate.py` | Language imputation and cached translation | 3 public functions | `caching`, `caching._keys`, `_common`, `engine`, `providers` | Package-internal | Existing | Enrichment feature |
| `bynat/profiling/__init__.py` | Export profiling API | `profile`, 3 report models | `profiling.profile`, `profiling.report` | Public | Existing | Package API |
| `bynat/profiling/profile.py` | Non-mutating profiling core | `profile` + kind/stat helpers | `profiling.report`, `_internal` | Package-internal | Existing | Profiling ownership |
| `bynat/profiling/report.py` | Report data models | `ProfileReport`, `DatasetProfile`, `ColumnProfile` | none | Package-internal | Existing | Report ownership |

---

## 10. Component Architecture Inventory

The file-by-file table in §9 records modules; this section records the components that materially affect architecture or behavior. The inventory was produced by a read-only component investigation and independently checked against source by the supervisor. **Assessment** values are Keep / Adjust / Split / Merge / Relocate / Defer.

### 10.1 Component inventory

| Component | Kind | Module | Responsibility | Consumers | Inputs | Outputs | State | Side effects | Dependencies | Tests | Assessment | Rationale |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BaseData | pandas.DataFrame subclass facade | bynat/cleaning/base.py | Supported DataFrame subclass that owns cache metadata, the inplace/get_hierarchical_stats return contract, and delegation of every transformation to functional modules; adapts profiling output for BaseData. | bynat/cleaning/__init__.py; JsonFile and CsvFile subclass it; BaseData methods used by tests/cross_cutting/accessor/test_parity.py and test_accessor.py; tests/cross_cutting/base_api/* | data, cache_dir, plus per-method transformation arguments | Self, None on inplace=True, or hierarchical statistics when get_hierarchical_stats=True | _metadata ['cache_manager']; _bynat_cache_dir and _bynat_cache_manager stored via object.__setattr__ | cached helpers persist through CacheManager; inplace paths mutate the receiver via _update_inplace; construction writes nothing | pandas, numpy; bynat.caching.CacheManager; bynat.profiling.profile; cleaning columns/io/stats/text/enrich and enrich.providers; ._outputs.is_basedata_type | tests/cross_cutting/base_api/test_base_constructors.py (constructor, cache-manager bundling, file loading, missing-path errors); tests/cross_cutting/base_api/inplace/test_base_inplace.py (identity, silence, non-alias results); tests/cross_cutting/base_api/inplace/test_base_inplace_failures.py; tests/cross_cutting/base_api/test_base_early_exits.py (independent copies); tests/cross_cutting/accessor/test_parity.py (accessor equality); tests/cross_cutting/accessor/test_accessor.py (manager shared across pandas operations) | Adjust | Ownership and delegation are correct and parity-tested, but base.py is 2,234 lines with 1,638 docstring lines duplicated from functional modules via _shares_doc and mirrored literally for tools/sync_docs.py; its inplace/stats finish logic duplicates _frame_method(stats=True). |
| JsonFile | DataFrame subclass constructor adapter | bynat/cleaning/base.py | Resolve the data versus json_file_path argument, load through cleaning.io.read_json, then initialize BaseData. | bynat/cleaning/__init__.py; tests/modules/io/test_io_read.py; tests/cross_cutting/base_api/test_base_constructors.py; tests/cross_cutting/contracts/test_root_api.py | data, json_file_path, key, cache_dir, extra DataFrame args | JsonFile instance | inherits BaseData cache state | reads a JSON file; raises FileNotFoundError, TypeError for key on non-dict payload, KeyError for a missing key | os; .io.read_json; BaseData | tests/modules/io/test_io_read.py (positional path constructors, read errors); tests/cross_cutting/base_api/test_base_constructors.py (reads local JSON, view returns plain DataFrame); tests/cross_cutting/contracts/test_root_api.py (export identity, hidden at root) | Keep | Thin loader delegation with direct constructor coverage; the string-or-path reinterpretation of data is recorded as questionable rather than structural. |
| CsvFile | DataFrame subclass constructor adapter | bynat/cleaning/base.py | Resolve the data versus csv_file_path argument, parse through cleaning.io.read_csv with read_kwargs, then initialize BaseData. | bynat/cleaning/__init__.py; tests/modules/io/test_io_read.py; tests/cross_cutting/base_api/test_base_constructors.py; tests/cross_cutting/contracts/test_root_api.py | data, csv_file_path, cache_dir, read_kwargs, extra DataFrame args | CsvFile instance | inherits BaseData cache state | reads a CSV file; raises FileNotFoundError for a missing path | os; .io.read_csv; BaseData | tests/modules/io/test_io_read.py (positional path constructors, malformed/empty handling); tests/cross_cutting/base_api/test_base_constructors.py (reads local CSV with sep); tests/cross_cutting/contracts/test_root_api.py (export identity) | Keep | Same thin loader pattern as JsonFile with direct coverage; shares the path-like data ambiguity noted as questionable. |
| BynatAccessor | registered pandas accessor class | bynat/_accessors/dataframe.py | Register df.bynat, bind a frame by reference plus an optional CacheManager, expose delegating transformation/export methods generated by binding factories, and adapt profiling output for BaseData. | bynat/__init__.py (imports _accessors for registration); bynat/_accessors/__init__.py; pandas users via df.bynat | pandas_obj, cache_manager, plus per-method transform arguments | new frames, None on inplace, BynatAccessor from with_cache | _obj held by reference; _cache_manager lazily resolved to shared_cache_manager() | inplace methods call self._obj._update_inplace; cached methods read and write SQLite through CacheManager | pandas; bynat.caching CacheManager and shared_cache_manager; cleaning columns/io/stats/text/enrich; profiling.profile; ._binding factories; ._outputs.is_basedata_type | tests/cross_cutting/accessor/test_accessor.py (registration, plain-frame outputs, signatures hide frame/cache_manager, one shared manager per directory); test_parity.py; inplace/test_argument_binding.py; inplace/test_variadic_capture.py; inplace/test_mutation.py; test_accessor_profile.py; test_accessor_package_boundary.py; contracts/test_doc_drift.py (stub signature sync) | Keep | AST boundary tests prove delegation-only ownership; the stateful contract of frame reference plus lazy shared manager is documented and asserted. |
| CacheManager | stateful cache facade class | bynat/caching/manager.py | Public cache lifecycle: directory resolution, lazy SQLite schema, memoized nested caches per function, baseline-diff persistence, column deletion, legacy migration trigger, and quarantine wrapper. | bynat/cleaning/base.py (BaseData.cache_manager); cleaning/enrich/engine.py and feature modules via cache_manager keyword; _accessors/dataframe.py; bynat/caching/__init__.py | cache_dir; validated func_name and col_name keys | dict caches; None for save and delete operations | caches, _baselines, cache_dir_path, cache_dir, SQLiteStorage instance | creates cache directory and database lazily; BEGIN IMMEDIATE transactions; WAL mode; logs; save failures are swallowed with rollback and pending changes preserved | sqlite3, copy, json, datetime, threading; caching._storage; caching._migration | tests/modules/caching/persistence/test_persistence_core.py (round trip, key and directory validation, env default); test_persistence_save.py (diff, removals, rollback); test_persistence_load.py (rebuild, memoization, SQLite authoritative); test_persistence_eviction.py (deep-copy baseline, last-writer-wins); test_persistence_delete_column.py; test_persistence_recovery.py (rollback, quarantine, unserializable values); tests/modules/caching/migration/test_migration_sqlite.py; tests/modules/caching/test_concurrency.py; tests/modules/enrichment/test_enrich_engine.py | Keep | Single owner of storage lifecycle and diff semantics with dense behavioral coverage; only stale log wording and dead compatibility wrappers are questionable. |
| SQLiteStorage | SQLite persistence class | bynat/caching/_storage.py | Configure SQLite connections, create the cache_entries/index/migration_metadata schema, rebuild nested caches from rows, and apply prepared diffs in one transaction. | bynat/caching/manager.py; bynat/caching/_migration.py | cache_dir_path, timeout, func_name, prepared_entries, removal_identities | connection; rebuilt nested dict; boolean commit success | cache_dir_path and timeout; one connection per operation, always closed | makedirs; PRAGMA busy_timeout/WAL/synchronous=FULL; INSERT OR REPLACE and exact DELETE; rollback and close on failure | sqlite3, json, os, logging | tests/modules/caching/persistence/test_persistence_core.py (round trip); test_persistence_save.py (transaction cases); test_persistence_load.py (rebuild); test_persistence_recovery.py (commit failure, quarantine); caching migration tests | Keep | Private module owns schema and transaction details; dependency direction is caching-internal only; covered by the persistence suite. |
| Analyzer | analytics engine class | bynat/analytics/analyzer.py | Defensive copy plus a filter/rules pipeline producing JSON-serializable categorical distributions, numerical aggregations, time series, KPI cards, and histogram bins. | bynat/analytics/__init__.py; tests/modules/analytics/* | dataframe; filters, computed rules, target and grouping columns, KPI and bin configuration | plain response dictionaries such as {'data': []} or {'data': None, 'title': ...} | self.dataframe defensive copy | does not mutate the caller frame; evaluates rule expressions through DataFrame.eval after a token guard | pandas, numpy, operator, logging; no bynat package imports | tests/modules/analytics/test_analytics_contract.py; test_analytics_distributions.py; test_analytics_filters_rules.py; test_analytics_series_kpi_bins.py | Keep | The only bynat package with zero internal dependencies; one cohesive class with contract coverage; the dynamic eval guardrail is a flagged risk, not an ownership defect. |
| DatasetProfile | dataclass implementing Mapping | bynat/profiling/report.py | Dataset-level quality metrics: row/column/total counts, missing count and proportion, duplicate rows with keep='first', empty columns, memory bytes, dtype counts. | bynat/profiling/profile.py; bynat/profiling/__init__.py; tests/modules/profile/* | row_count, column_count, total_cells, missing statistics, duplicate count, empty column count, memory usage, dtype counts | attribute and key access, to_dict(), iteration over 10 fields | immutable dataclass values | none | dataclasses.asdict, collections.abc.Mapping, pandas | tests/modules/profile/test_profile_general.py (report structure and access patterns); test_profile_edges.py (empty/all-missing frames); test_profile_contract.py (key sets, value types, JSON serialization); test_profiling_package_boundary.py (exports, forbidden imports) | Keep | Plain data model with Mapping contract and serialization guarantees pinned by contract tests; no behavior beyond aggregation. |
| ColumnProfile | dataclass implementing Mapping | bynat/profiling/report.py | Per-column quality metrics and kind-specific descriptive statistics (numeric, categorical, boolean, datetime, other) with unavailable statistics represented as None. | bynat/profiling/profile.py; bynat/profiling/__init__.py; tests/modules/profile/* | name, dtype, inferred_type, kind, counts and proportions, distinctness, stats dict | attribute and key access, to_dict(), iteration over 11 fields | immutable dataclass values | none | dataclasses.asdict, collections.abc.Mapping | tests/modules/profile/test_profile_general.py (statistics per kind); test_profile_edges.py (bool-before-int, timedelta, tz-aware, pd.Categorical); test_profile_contract.py (stable key sets and types); test_profiling_package_boundary.py | Keep | Pure report model; field contract is explicitly stability-tested, which is the right place for the guarantee. |
| ProfileReport | dataclass implementing Mapping | bynat/profiling/report.py | Top-level report combining DatasetProfile with per-column profiles; exposes columns dict, positional column_list, to_dict, to_dataframe, and repr. | bynat/profiling/profile.py; bynat/profiling/__init__.py; _accessors/dataframe.py profile adapter; tests/modules/profile/* | dataset, columns mapping, column_list | Mapping access for 'dataset' and 'columns'; to_dict(); summary pd.DataFrame; repr summary | immutable dataclass values | none | dataclasses, collections.abc.Mapping, pandas | tests/modules/profile/test_profile_general.py (output_type parameter, structure); test_profile_edges.py (duplicate column names, clean scalar); test_profile_contract.py (JSON of mixed frame); tests/cross_cutting/accessor/test_accessor_profile.py (BaseData adaptation) | Keep | Serialization surface is tested end to end; the duplicate-column-name asymmetry between columns and column_list is documented but flagged. |
| Translator | runtime_checkable Protocol | bynat/cleaning/enrich/providers.py | Structural contract for translating one text into a target language; falsy results stay uncached; optional translate_batch, max_workers, min_interval attributes change execution strategy. | bynat/cleaning/enrich/translate.py (typing and default injection); bynat/cleaning/base.py (provider typing); bynat/cleaning/enrich/__init__.py; tests/modules/enrichment/translate/test_translate_batch.py | text, target_lang | translated str or falsy None | none (protocol only) | none at protocol level | typing.Protocol, runtime_checkable | tests/modules/enrichment/translate/test_translate_batch.py (default providers satisfy protocols; plain provider accepted; empty translations skipped) | Keep | One of three justified protocols; structural typing lets plain callables be injected and is tested. |
| Geocoder | runtime_checkable Protocol | bynat/cleaning/enrich/providers.py | Structural contract for resolving a location query to (latitude, longitude) or None; None is cached as a not-found result unless retry_not_found is set. | bynat/cleaning/enrich/geocode.py; bynat/cleaning/base.py; bynat/cleaning/enrich/__init__.py; tests/modules/enrichment/geocode/* | query string | (float, float) or None | none (protocol only) | none at protocol level | typing.Protocol, runtime_checkable | tests/modules/enrichment/geocode/test_geocode.py (default Nominatim construction, plain provider, errors not cached, misses cached, save_every validation) | Keep | Minimal external-service contract with clear not-found caching semantics, pinned by tests. |
| RateSource | runtime_checkable Protocol | bynat/cleaning/enrich/providers.py | Structural contract returning mean yearly exchange rates of one USD in a currency over an inclusive year range; years without data are omitted. | bynat/cleaning/enrich/currency.py; bynat/cleaning/base.py; bynat/cleaning/enrich/__init__.py; tests/modules/enrichment/currency/* | currency code, start_year, end_year | Mapping[int, float] of year to amount of currency per USD | none (protocol only) | none at protocol level | typing.Protocol, runtime_checkable, collections.abc.Mapping | tests/modules/enrichment/currency/test_currency.py (default YFinance construction, one download per currency, failures not cached, lookback and missing years) | Keep | Clear unit convention (currency per USD, divide in convert_to_usd) is documented and tested. |
| GoogleTranslatorProvider | default Translator adapter class | bynat/cleaning/enrich/providers.py | Wrap deep_translator.GoogleTranslator with per-thread, per-target-language instances and class knobs max_workers=4 and min_interval=0.2. | bynat/cleaning/enrich/translate.py (_translate_cached default provider); bynat/cleaning/enrich/__init__.py | feature name; translate(text, target_lang) | translated text or whatever GoogleTranslator returns including None | thread-local translator cache keyed by target language; class-level rate knobs | network translation calls; lazily imports deep_translator and raises feature ImportError at construction | threading; .._common.import_optional via alias _import_optional; deep_translator (optional) | tests/modules/enrichment/translate/test_translate_batch.py (default Google translator constructed, one translator per thread reused, translate_batch path used in save_every chunks, empty translations not cached) | Keep | Provider state lifecycle is deliberate (per-thread clients) and asserted; the alias-based import is covered by the questionable list. |
| NominatimGeocoder | default Geocoder adapter class | bynat/cleaning/enrich/providers.py | Build a geopy Nominatim geolocator wrapped in RateLimiter and resolve queries to coordinates. | bynat/cleaning/enrich/geocode.py (default provider); bynat/cleaning/enrich/__init__.py | user_agent, min_delay_seconds, feature; geocode(query) | (latitude, longitude) floats or None | bound rate-limited callable; lazy optional imports | network geocoding calls spaced by the rate limiter; raises feature ImportError at construction | .._common.import_optional via alias; geopy.geocoders and geopy.extra.rate_limiter (optional) | tests/modules/enrichment/geocode/test_geocode.py (default Nominatim construction, accepts plain provider, errors not cached, query shortening and miss caching, non-positive save_every rejection) | Keep | External service isolation is correct; the default user_agent string 'data_cleaning_core_geocoder' is stale branding and is flagged. |
| YFinanceRateSource | default RateSource adapter class | bynat/cleaning/enrich/providers.py | Download one Yahoo Finance history range for '{currency}=X' and average daily closes per calendar year within the requested range. | bynat/cleaning/enrich/currency.py (default provider); bynat/cleaning/enrich/__init__.py | feature; yearly_rates(currency, start_year, end_year) | dict[int, float] mapping year to mean rate, empty when no history | lazy yfinance module reference | network download; provider exceptions propagate so they are not cached; lazily imports yfinance | .._common.import_optional via alias; pandas; yfinance (optional) | tests/modules/enrichment/currency/test_currency.py (yearly means from one download, one download per currency, failures not cached, missing-year lookback) | Keep | Adapter keeps network specifics inside providers; the exclusive end date is flagged as a correctness question, not an ownership issue. |
| _frame_method | accessor wrapper factory | bynat/_accessors/_binding.py | Adapt a shared functional implementation into an accessor method: replace the frame parameter with self, optionally insert inplace, copy the implementation signature/docstring, and implement the mutation/None and stats return contract. | bynat/_accessors/dataframe.py (class attribute bindings) | func, inplace flag, stats flag, inplace_before parameter name | method callable with generated __signature__ and __doc__ | stateless closure over func and flags | when inplace, calls self._obj._update_inplace(result) and returns None or statistics | functools.wraps, inspect; TYPE_CHECKING import of BynatAccessor | tests/cross_cutting/accessor/test_accessor_package_boundary.py (callable and __module__); inplace/test_argument_binding.py (positional and keyword-only binding); inplace/test_variadic_capture.py; inplace/test_mutation.py; contracts/test_doc_drift.py (runtime signature vs stub); contracts/test_tracked_defects.py | Adjust | Re-implements the BaseData._finish/_finish_with_stats contract and duplicates the positional-flag slicing already present in _cached_frame_method; parity tests pin equivalence, so drift would be silent at runtime. |
| _cached_frame_method | accessor wrapper factory for cached functions | bynat/_accessors/_binding.py | Like _frame_method but injects self.cache_manager into the shared cached implementation and hides it from the signature. | bynat/_accessors/dataframe.py (cached enrichment and NLP bindings) | func, inplace flag, inplace_before parameter name | method callable that forwards cache_manager=self.cache_manager | stateless closure; reads accessor cache_manager at call time | cached reads/writes through CacheManager; inplace mutation via _update_inplace | functools.wraps, inspect | tests/cross_cutting/accessor/test_accessor.py (cached methods use selected cache); inplace/test_argument_binding.py; inplace/test_mutation.py; tests/modules/enrichment/* (behavior through accessor); contracts/test_doc_drift.py | Adjust | Needed because cached implementations take cache_manager, but it duplicates the inplace branch logic of _frame_method and the finish logic of BaseData. |
| _method_signature | signature introspection helper | bynat/_accessors/_binding.py | Build the accessor-facing inspect.Signature by dropping the frame parameter and any cache_manager parameter and prepending self. | _frame_method and _cached_frame_method within the same module | func callable | inspect.Signature | none | none | inspect | tests/cross_cutting/accessor/test_accessor_package_boundary.py (callable); exercised by every signature parity assertion in tests/cross_cutting/accessor/* and contracts/test_doc_drift.py | Keep | Single mechanical owner of the signature transformation; pure and indirectly covered by signature parity suites. |
| _with_inplace | signature manipulation helper | bynat/_accessors/_binding.py | Insert an inplace parameter at the class-declared slot, or as the first keyword-only parameter when the wrapped function is variadic, and report whether it is keyword-only plus its positional index. | _frame_method and _cached_frame_method within the same module | signature, before parameter name | (new signature, keyword_only bool, position int) | none | raises ValueError when before is unknown or insertion would precede a required parameter | inspect | tests/cross_cutting/accessor/test_accessor_package_boundary.py (callable); behavior pinned by inplace/test_argument_binding.py and inplace/test_variadic_capture.py | Keep | Complex but single-purpose and thoroughly exercised through positional/keyword-only binding tests. |
| _shares_doc | import-time docstring decorator | bynat/cleaning/base.py | Copy a shared implementation's cleaned docstring onto a BaseData method at import time, keeping editor/type-checker visibility. | BaseData methods in bynat/cleaning/base.py (decorator applied throughout) | func whose docstring is copied | decorator that assigns method.__doc__ and returns the method | none after import | mutates __doc__ at import time | typing Callable and TypeVar | tests/cross_cutting/contracts/test_doc_drift.py (docstrings and stubs in sync; accessor stub matches runtime signatures) | Adjust | Creates two sources of truth for the same text: runtime assignment here plus literal docstrings mirrored by tools/sync_docs.py; 1,638 of 2,234 base.py lines are docstrings and drift is only caught by a test. |
| import_optional | lazy optional-dependency importer | bynat/cleaning/_common.py | Import a feature dependency only when the feature is used and raise a feature-specific ImportError naming the distribution. | bynat/cleaning/io.py (save_to_sql), text.py (Aho-Corasick), enrich/providers.py, enrich/translate.py, enrich/nlp.py, enrich/currency.py; all currently import the underscore alias | module_name, distribution, feature | imported ModuleType | none | importlib.import_module side effect; raises chained ImportError on failure | importlib, types.ModuleType | tests/modules/enrichment/optional/test_optional_sqlalchemy.py; test_optional_ahocorasick.py; tests/modules/enrichment/translate/test_translate_impute.py (missing langdetect); tests/modules/enrichment/nlp/test_nlp.py (required disabled components) | Adjust | Correct lazy boundary, but the except ImportError clause rewrites any ImportError raised during the module body as a missing-dependency error, masking real defects; consumers use the alias _import_optional rather than the __all__ name. |
| require_positive_int | parameter validation helper | bynat/cleaning/_common.py | Reject booleans, non-integers, and values below 1 for sampling and cache checkpoint parameters. | enrich/geocode.py, enrich/nlp.py, enrich/translate.py via the alias _require_positive_int | value, arg_name | None | none | raises ValueError | typing.Any | tests/modules/enrichment/translate/test_translate_conditional.py (non-positive sample_size/number_of_samples/save_every); tests/modules/enrichment/geocode/test_geocode.py (save_every); tests/modules/enrichment/nlp/test_nlp.py | Keep | Small, pure, and directly covered by validation tests; the alias duplication is a private-hygiene issue, not a contract one. |
| left_merge_aligned | aligned merge helper | bynat/cleaning/_common.py | Left-merge a right frame onto shared columns and relabel the result positionally so it inherits the left frame's index, including duplicate and multi-level indexes. | cleaning/stats.py (three call sites), cleaning/enrich/currency.py; imported as _left_merge_aligned | frame, right, on list | merged pd.DataFrame indexed like frame | none | none | pandas | tests/cross_cutting/workflows/fill_missing_from/test_fill_missing_from_leakage.py and test_fill_missing_from_imputation.py; tests/modules/stats/hierarchical_stats/test_hierarchical_stats_aggregation.py; tests/modules/enrichment/currency/test_currency.py | Keep | Solves a real index-preservation problem for named/duplicate/multi-level indexes and is covered through stats and currency workflows. |
| like | frame-type propagation helper | bynat/cleaning/_common.py | Return data as the same frame type as df, rebuilding through _constructor and __finalize__ so pandas metadata propagates; plain DataFrames pass through. | cleaning/columns.py (melt_transform_pivot result wrapping) via the alias _like | df supplying type/metadata, data frame | FrameT-typed frame | none | none | pandas, typing.TypeVar FrameT, typing.cast | tests/modules/columns/test_columns_pivot.py; tests/modules/columns/test_columns_structural.py; tests/cross_cutting/base_api/test_base_constructors.py (melt result keeps cache manager) | Keep | Keeps subclass and metadata semantics consistent with BaseData._constructor; single call site but architecturally meaningful for subclass preservation. |
| dedupe_key | value normalization helper | bynat/_internal/values.py | Return a hashable stand-in for unhashable values: sets sorted by string form, NumPy arrays to lists, and list/dict/tuple serialized with json.dumps(sort_keys=True, default=str). | bynat/cleaning/io.py (save_to_json append deduplication), bynat/profiling/profile.py (duplicate-row and distinct-count keys); both import it as _dedupe_key | any value | hashable value usable in sets and groupby keys | none | none | json, typing.Any, numpy | tests/cross_cutting/contracts/test_internal_shared_helpers.py (normalization, canonical identity, no duplicate definitions, stdlib+NumPy only imports); tests/modules/io/test_io_append.py (dedupe dict cells by JSON content); tests/modules/profile/test_profile_edges.py (unhashable duplicate rows); tests/modules/profile/test_profiling_package_boundary.py | Keep | Canonical shared helper with explicit ownership and enforcement tests; the cross-type key conflation is recorded as questionable. |
| cache_value_key | cache-key normalization helper | bynat/caching/_keys.py | Convert a lookup value into a stable string key: integers and integral floats collapse to the same string so values survive a save/load round trip; everything else uses str. | cache_has_value and cache_lookup_value in the same module; cleaning/enrich/engine.py as the default key callable (imported via the alias _cache_value_key) | value | normalized str key | none | none | typing.Any, numpy | No direct test; exercised through tests/modules/enrichment/test_enrich_engine.py cache-hit and checkpoint behavior and the caching persistence suite | Adjust | Key identity belongs in caching, but the only cross-package consumer imports the private alias _cache_value_key instead of the canonical cache_value_key declared in __all__. |
| cache_has_value | cache membership helper | bynat/caching/_keys.py | Check a cache bucket for a value under the normalized key first, falling back to the raw in-memory key for older caches; unhashable values count as absent. | cleaning/enrich/translate.py via the alias _cache_has_value as the is_cached predicate | cache dict, value | bool | none | none | numpy, typing.Any | No direct test; exercised by translate caching tests (tests/modules/enrichment/translate/*) and test_enrich_engine.py | Adjust | Deliberate normalized-plus-raw lookup contract, but the sole external consumer uses the alias name while the canonical name is exported. |
| cache_lookup_value | cache read helper | bynat/caching/_keys.py | Read a cached value by normalized key with a raw-key fallback, returning the original value when absent. | cleaning/enrich/translate.py via the alias _cache_lookup_value at two map-back sites | cache dict, value | cached value or the original value | none | none | typing.Any | No direct test; exercised by translate tests verifying translated values are mapped back and re-used from cache | Adjust | Correct fallback semantics; ownership is right, but the alias import keeps a compatibility layer alive that the design says should be removed. |
| is_basedata_type | type predicate helper | bynat/cleaning/_outputs.py | Decide whether a type is BaseData or a subclass without importing the facade, by inspecting the MRO for a class named BaseData defined in bynat.cleaning.base. | cleaning/base.py (profile output adaptation), _accessors/dataframe.py (accessor profile adaptation), validate_output_type | candidate output_type | bool | none | none | typing.Any | tests/cross_cutting/accessor/test_accessor_package_boundary.py (binding and delegation); tests/cross_cutting/accessor/test_accessor_profile.py (BaseData output adaptation); indirectly test_profile_general.py output_type parameter | Adjust | Avoids lower-level to facade coupling, but identifies the class by literal __name__ and __module__ strings; renaming or relocating BaseData silently disables output adaptation. |
| validate_output_type | output contract validator | bynat/cleaning/_outputs.py | Accept None, dict, pandas.DataFrame, or a BaseData-family class; raise TypeError otherwise. | cleaning/stats.py get_hierarchical_stats via the alias _validate_output_type | output_type | None | none | raises TypeError | pandas; .is_basedata_type logic | tests/modules/stats/hierarchical_stats/test_hierarchical_stats_output_types.py; tests/modules/stats/hierarchical_stats/test_hierarchical_stats_validation.py | Keep | Central output contract shared by stats; behavior pinned by output-type tests. |
| convert_output | output converter | bynat/cleaning/_outputs.py | Convert a frame to the supported output types: None or DataFrame passthrough, dict becomes {column: values_list}, anything else is called as output_type(data=data). | convert_default_output in the same module; cleaning/stats.py via the alias _convert_output at three sites | data frame, output_type | frame, dict, or constructed object | none | constructs caller-supplied output types | pandas, typing.Any | tests/modules/stats/hierarchical_stats/test_hierarchical_stats_output_types.py; tests/modules/stats/hierarchical_stats/test_hierarchical_stats_aggregation.py | Keep | Schema-light conversion with an explicit constructor convention; covered by output-type tests. |
| _hierarchical_outlier_masks | generator algorithm helper | bynat/cleaning/stats.py | Yield (target_col, outlier_mask) per hierarchy level using grouped 1.5*IQR bounds gated by min_samples non-null observations, dropping the last hierarchy column each level; re-reads the frame so caller mutation affects later levels. | handle_outliers and drop_outliers in the same module | frame, target_cols, hierarchy_cols, min_samples | iterator of (target_col, boolean ndarray) | generator; processed mask per target column across levels | none directly; consumes caller frame state across yields | numpy, pandas, collections.abc Iterator/Sequence | tests/modules/stats/test_outliers.py (min_samples boundary, non-null counting, missing target columns skipped, no-hierarchy warning/unchanged copy); tests/cross_cutting/equivalence/test_equivalence_outliers.py; tests/cross_cutting/contracts/test_properties.py | Keep | Cohesive hierarchy algorithm whose mutation-sensitive contract is documented and tested; deliberately not split by LOC. |
| shared_cache_manager | process-wide registry function | bynat/caching/manager.py | Return one CacheManager per resolved absolute cache directory, guarded by a module lock, creating and registering a manager on first request. | _accessors/dataframe.py cache_manager property and with_cache; bynat/caching/__init__.py; tests/cross_cutting/contracts/test_root_api.py and test_doc_drift.py | cache_dir or None | shared CacheManager instance | module-level _shared_managers dict plus lock; managers never evicted | constructs a probe CacheManager on every call; registers managers permanently | threading.Lock; CacheManager | tests/cross_cutting/contracts/test_doc_drift.py (documented export); tests/cross_cutting/accessor/test_accessor.py (one shared manager per directory, pandas operations share the manager); tests/cross_cutting/contracts/test_root_api.py | Adjust | Lifecycle responsibility is real, but every call builds a throwaway CacheManager probe and the registry has no eviction or cleanup, so long-lived processes accumulate managers. |
| resolve_cache_dir | path resolution helper | bynat/caching/manager.py | Resolve a cache directory without creating anything: explicit argument, else BYNAT_CACHE_DIR when non-empty, else DEFAULT_CACHE_DIR. | CacheManager.__init__ | cache_dir or None | str or PathLike directory | none | reads os.environ only | os, PathLike; CACHE_DIR_ENV_VAR and DEFAULT_CACHE_DIR constants | tests/modules/caching/persistence/test_persistence_core.py (defaults to environment variable then legacy path) | Keep | Pure resolution with explicit precedence and direct test coverage. |
| connect_sqlite | connection factory | bynat/caching/_storage.py | Open a SQLite connection and apply busy_timeout, WAL, and synchronous=FULL pragmas, closing and propagating on pragma failure. | SQLiteStorage.connect; CacheManager delegates through storage | database_path, timeout | configured sqlite3.Connection | connection created per call | PRAGMA statements; closes connection on failure | sqlite3 | tests/modules/caching/persistence/test_persistence_core.py (round trip through configured connection); persistence recovery tests | Keep | Encapsulates durability settings in one private place; no duplicated connection logic elsewhere. |
| migrate_legacy_json_cache | legacy migration helper | bynat/caching/_migration.py | Import a legacy per-function JSON cache file into SQLite, quarantining corrupt files and recording migration metadata. | CacheManager._migrate_legacy_json_cache (called from load_function_cache) | cache_dir_path, func_name, file_path, storage, initialize_fn, connect_fn | None | delegates to SQLiteStorage and quarantine helper | reads legacy JSON, writes SQLite, may quarantine a corrupt file | caching._storage.SQLiteStorage; json, os, sqlite3, logging | tests/modules/caching/migration/test_migration_sqlite.py; tests/modules/caching/migration/legacy/test_legacy_import.py; test_legacy_quarantine.py; test_legacy_rollback.py; tests/modules/caching/persistence/test_persistence_load.py (public-path migration) | Keep | Migration ownership is isolated and heavily tested; only the extra compatibility alias wrapper in manager.py is questionable. |
| quarantine_corrupt_cache_file | corrupt-file isolation helper | bynat/caching/_migration.py | Move a corrupt cache file aside without overwriting an existing quarantine target. | caching/_migration.py; CacheManager._quarantine_corrupt_cache_file wrapper | file_path | quarantine path or None | filesystem side effect only | renames/moves files and logs | os, shutil or os.replace as implemented, logging | tests/modules/caching/migration/legacy/test_legacy_quarantine.py; tests/modules/caching/persistence/test_persistence_recovery.py (corrupt cache quarantined and replaced with empty dict) | Keep | Explicit corruption handling with recovery coverage; the manager wrapper is one of several unused compatibility shims. |
| _cached_map | shared cached-lookup engine | bynat/cleaning/enrich/engine.py | Resolve the unique non-null values of a series through persistent cache buckets: probe cache, fetch or fetch_many in save_every chunks, checkpoint via CacheManager, and return the bucket for caller mapping. | cleaning/enrich/currency.py, geocode.py, nlp.py, translate.py | series, fetch/fetch_many, bucket name(s), save_every, cache_manager, func_name, key/is_cached/on_fetch_start hooks, action/label | cache bucket dict or dict of buckets | pending map and unsaved flag local to the call; caches live in CacheManager | provider network calls, CacheManager checkpoints and SQLite writes, logging; exceptions are logged and left uncached, SKIP stays uncached | threading, time, concurrent.futures, pandas; bynat.caching.CacheManager; bynat.caching._keys alias _cache_value_key; .._common.logger | tests/modules/enrichment/test_enrich_engine.py (checkpoint/skip/retry, multi-bucket requires every bucket, batch wrong or surplus length, no save when nothing unprocessed, exceptions in place) | Keep | Genuinely shared algorithm owned inside enrich; dense behavioral coverage justifies keeping it unified rather than per-feature. |
| _rate_limited_map | concurrent mapping helper | bynat/cleaning/enrich/engine.py | Call a function on every item preserving order, with at most max_workers concurrent calls and at least min_interval seconds between call starts, returning exceptions in place. | cleaning/enrich/translate.py _translate_all | func, items, max_workers, min_interval | list of results or exceptions in input order | shared next_start timestamp under a lock | time.sleep pacing and ThreadPoolExecutor use | threading, time, concurrent.futures | tests/modules/enrichment/test_enrich_engine.py (concurrency, start spacing, exceptions returned in place) | Keep | Concrete rate-limit primitive with deterministic tests; only used by translation today, which is acceptable shared-engine reuse. |
| SKIP | sentinel object | bynat/cleaning/enrich/engine.py | Signal from a fetch that a value should be left uncached quietly, without a failure warning. | _cached_map; cleaning/enrich/translate.py _translate_cached | returned by fetch callables | identity comparison in engine | module singleton | none | none | tests/modules/enrichment/test_enrich_engine.py (skips and retries failures); tests/modules/enrichment/translate/test_translate_batch.py (empty translations skipped and not cached) | Keep | Small but meaningful contract between providers and the cache engine; tested through skip behavior. |
| profile | profiling core function | bynat/profiling/profile.py | Compute dataset-level and per-column data-quality metrics, detect kinds, and return ProfileReport or the requested dict/DataFrame output without mutating the input. | bynat/profiling/__init__.py; cleaning/base.py BaseData.profile; _accessors/dataframe.py profile adapter | df, optional *columns selection, output_type | ProfileReport, dict, or DataFrame according to output_type | none; builds report models | none on input; duplicate/distinct counting uses _internal.dedupe_key | datetime, math, numpy, pandas; bynat._internal.dedupe_key; .report models | tests/modules/profile/test_profile_general.py (entry points, no mutation, structure, output_type, missing/duplicate/unhashable semantics, per-kind stats, nullable dtypes); test_profile_edges.py; test_profile_contract.py; tests/cross_cutting/accessor/test_accessor_profile.py | Keep | Non-mutating core with strict output contracts and independent-package enforcement; clearly the profiling owner. |
| read_csv | public reader function | bynat/cleaning/io.py | Parse a CSV file into a plain pandas.DataFrame by forwarding to pandas.read_csv. | bynat/__init__.py (root read_csv identity); cleaning/base.py CsvFile constructor | csv_file_path, **read_kwargs | pd.DataFrame | none | reads a file; raises on empty or malformed files and directory paths | pandas, os | tests/cross_cutting/contracts/test_root_api.py (identity, signature, load); tests/modules/io/test_io_read.py (round trip, unicode, malformed/empty, directory rejection) | Keep | Root API identity is pinned to cleaning.io; plain-frame return is intentional and tested. |
| read_json | public reader function | bynat/cleaning/io.py | Read and flatten a JSON payload with pandas.json_normalize, optionally selecting a top-level key. | bynat/__init__.py (root read_json identity); cleaning/base.py JsonFile constructor | json_file_path, key | pd.DataFrame with dotted flattened keys | none | reads a file; raises FileNotFoundError, malformed-JSON errors, TypeError/KeyError for key misuse | json, pandas, os | tests/cross_cutting/contracts/test_root_api.py (identity, signature, load, flattened keys); tests/modules/io/test_io_read.py (round trip, malformed payload, missing key, empty array, non-dict payload) | Keep | Root API identity pinned; key semantics directly tested. |
| save_to_json | writer function | bynat/cleaning/io.py | Write a frame to JSON only when content changed, with orient, append, ASCII, indent options and datetime formatting; append deduplicates cells using dedupe_key. | cleaning/base.py BaseData.save_to_json; _accessors/dataframe.py | df, file_path, orient, append, force_ascii, indent | None | none | reads existing file for comparison, writes/rewrites JSON, logs; never mutates source frame | json, os, pandas; ._common logger and import_optional alias; _internal.dedupe_key via alias | tests/modules/io/test_io_json.py (orients, table schema, ascii, indent, skip unchanged, overwrite changed, unreadable existing, datetime formatting, no source mutation, empty round trip, cwd-relative paths, directory/file-parent errors); tests/modules/io/test_io_append.py (append dedupe of dict cells, list columns, unreadable refusal) | Keep | Change-detection and append semantics are substantial and fully covered; uses canonical shared dedupe_key through the private alias. |
| save_to_sql | writer function | bynat/cleaning/io.py | Build a SQLAlchemy URL and write a frame to a SQL table, with dialect handling, credential encoding, chunking, and engine disposal in finally. | cleaning/base.py BaseData.save_to_sql; _accessors/dataframe.py | df, table_name, database_type/user/password/host/port/name, driver, column types, chunk size, fast_executemany, if_exists, index | None | engine created per call | imports SQLAlchemy lazily, connects and writes, disposes engine; converts timezone-aware datetimes on an internal copy | ._common.import_optional alias; SQLAlchemy (optional); pandas | tests/modules/enrichment/optional/test_optional_sqlalchemy.py; tests/modules/io/test_io_json.py (rejects invalid arguments before connecting) | Keep | Optional dependency is already isolated by the lazy import; moving it would fragment the I/O boundary without improving it. |
| _finish_with_stats | facade return-contract helper | bynat/cleaning/base.py | Implement the BaseData outcome contract for statistics-capable methods: return frame or (frame, statistics) when inplace=False; mutate and return statistics or None when inplace=True. | BaseData.handle_outliers, drop_outliers, fill_missing, fill_missing_from | outcome, inplace, with_stats | frame, tuple, statistics, or None | none | calls self._update_inplace on the receiver when inplace | pandas | tests/cross_cutting/base_api/inplace/test_base_inplace.py; tests/cross_cutting/accessor/test_parity.py; tests/modules/stats/hierarchical_stats/* | Keep | Correct owner of the class-side contract, but the same semantics are re-implemented by _frame_method(stats=True); duplication is flagged. |
| get_hierarchical_stats | public statistics function | bynat/cleaning/stats.py | Compute per-level hierarchical medians/means and a fixed-schema statistics frame, honoring output_type conversion and skipping invalid inputs with a warning. | cleaning/base.py BaseData.get_hierarchical_stats; _accessors/dataframe.py | df, target cols, hierarchy cols, strategy, mode, output_type and related options | statistics DataFrame (or dict/BaseData via conversion) | none | logs warnings for invalid configurations | numpy, pandas; ._common alias helpers; ._outputs validation/conversion aliases | tests/modules/stats/hierarchical_stats/test_hierarchical_stats_aggregation.py; test_hierarchical_stats_output_types.py; test_hierarchical_stats_mode.py; test_hierarchical_stats_flags.py; test_hierarchical_stats_validation.py | Keep | Cohesive hierarchy-domain entry point with broad contract coverage; the only multipurpose private helper set it uses is cleaning-scoped. |

### 10.2 Questionable components and flags

Flags raised by the component investigation. Each was checked against source by the supervisor; the disposition states whether it is an architectural issue, a behavioral defect, or a documented intentional design. Alias-related flags are resolved by the single policy in §6.I; every `Adjust` assessment is resolved in §10.3.
1. _shares_doc docstring duplication: base.py carries 1,638 docstring lines duplicating functional docstrings, applied at runtime by _shares_doc and mirrored literally by tools/sync_docs.py; tests/cross_cutting/contracts/test_doc_drift.py fails on any drift, so every docstring edit must touch multiple artifacts. — **Disposition:** Verified: `base.py:30-53`; `tools/sync_docs.py` mirrors docstrings. Behavioral/maintenance cost, not an ownership defect. Defer.
2. Dual inplace/stats contract: BaseData._finish_with_stats (base.py:175-199) and _frame_method(stats=True) (binding.py:152-160) independently implement the same inplace plus get_hierarchical_stats semantics; parity tests pin equivalence but a semantic change could satisfy one side silently. — **Disposition:** Verified: `base.py:175-199` and `_binding.py:152-160`. Parity is pinned by tests; a future change must update both. Defer (no structural change now).
3. is_basedata_type identifies BaseData by MRO string matching on __name__ == 'BaseData' and __module__ == 'bynat.cleaning.base' (cleaning/_outputs.py:17-28); renaming or relocating the class silently disables BaseData profile output adaptation. — **Disposition:** Verified: `_outputs.py:17-28` matches `__name__`/`__module__`. Fragile to relocation; the class and module are stable and approved. Retain; note as a relocation hazard.
4. Cross-package private edge uses alias names rather than canonical exports: cleaning/enrich/engine.py:12 imports _cache_value_key and cleaning/enrich/translate.py:10 imports _cache_has_value/_cache_lookup_value, although caching/_keys.py __all__ declares cache_value_key/cache_has_value/cache_lookup_value. The documented exception is wired to the compatibility alias layer slated for removal. — **Disposition:** Verified: `engine.py:12`, `translate.py:10`. The alias layer is slated for removal; consumers will import the canonical `cache_*` names. Adjust (covered by the alias normalization).
5. shared_cache_manager constructs a throwaway CacheManager probe on every call (manager.py:434-437, 459-460) and registers managers by absolute path in a dict with no eviction or cleanup; long-lived processes accumulate manager instances. — **Disposition:** Reviewed; no architectural change.
6. Dead internal compatibility wrappers: caching/manager.py:158-160 _migrate_legacy_cache is referenced only by tests/modules/caching/migration/legacy/test_legacy_rollback.py:180, and manager.py:38-39 _SQLITE_DATABASE_NAME/_SQLITE_TIMEOUT_SECONDS have no consumers; both sit outside __all__. — **Disposition:** Verified: `manager.py:38-39,158-160`. Remove (Decision 2).
7. import_optional catches any ImportError raised during module import and rewrites it as 'feature requires optional dependency' (cleaning/_common.py:44-49), masking genuine defects inside an installed optional package. — **Disposition:** Reviewed; no architectural change.
8. Analyzer._is_safe_expression feeds expressions to DataFrame.eval with a token denylist ('__', '@', 'import', 'lambda', ';') documented as 'a guardrail, not a full sandbox' (analytics/analyzer.py:54-80); architecture-wise the dynamic eval remains a code-injection surface despite the filter. — **Disposition:** Verified: `analyzer.py:54-80`. Documented as a guardrail, not a sandbox. Security/behavioral follow-up, not architectural.
9. dedupe_key serializes set, NumPy array, list, and tuple to the same JSON text (for example [1, 2], (1, 2), {1, 2}, np.array([1, 2]) all become '[1, 2]'), so profiling duplicate and distinct counting treats values of different Python types as identical. — **Disposition:** Reviewed; no architectural change.
10. JsonFile and CsvFile reinterpret any str or path-like data argument as a file path and raise FileNotFoundError when it does not exist (base.py:2149-2157 and 2221-2229), so passing a non-tabular string that looks path-like fails opaquely instead of reaching the DataFrame constructor. — **Disposition:** Verified: `base.py:2148-2157,2220-2229`. Behavioral edge case; see discrepancy D-1.
11. CacheManager still logs legacy '<func>_cache.json' filenames in delete_column_cache and _get_file_path (manager.py:227, 425, 427) after persistence moved to SQLite, so operator-facing messages misdescribe storage. — **Disposition:** Reviewed; no architectural change.
12. YFinanceRateSource uses ticker.history(end=f'{end_year}-12-31') (providers.py:246); yfinance's end is exclusive, so December 31 closes are excluded from the yearly mean. Verify against the intended inclusive-range contract before relying on boundary-year values. — **Disposition:** Reviewed; no architectural change.
13. ProfileReport.columns keeps only the last occurrence of a duplicate column name while column_list preserves every position (report.py:235-249); consumers indexing by name silently lose earlier profiles, an asymmetry that is documented but easy to misuse. — **Disposition:** Reviewed; no architectural change.
14. NominatimGeocoder's default user_agent is still 'data_cleaning_core_geocoder' (providers.py:151), a stale pre-rename identifier sent to an external service; likewise GoogleTranslatorProvider class knobs max_workers/min_interval are the only provider tuning surface and are implicit rather than injected. — **Disposition:** Reviewed; no architectural change.

### 10.3 Component assessments marked `Adjust` — decisions

| Component | Verified issue | Decision | Required action | Scope | Evidence |
|---|---|---|---|---|---|
| `BaseData` | `_finish_with_stats` duplicates the accessor's `inplace` + statistics return logic | Deferred | None now; if the contract changes, extract one shared contract helper and pin parity | Maintainability | `base.py:175-199`, `_binding.py:152-160`; parity tests |
| `_frame_method` | Mutation/finalization logic duplicates `BaseData._finish*` | Deferred | None now | Maintainability | `_binding.py:138-167` |
| `_cached_frame_method` | Same duplication for cached methods | Deferred | None now | Maintainability | `_binding.py:198-223` |
| `_shares_doc` | One docstring is applied at runtime and mirrored literally by `tools/sync_docs.py` | Retain | None; drift already fails `test_doc_drift.py` | Intentional static-analysis design | `base.py:30-53` |
| `import_optional` | Catches any `ImportError`, including one raised inside an installed optional package | Deferred | Behavioral follow-up: narrow to `ModuleNotFoundError` for the target module, or re-raise when the module is present | Behavioral correctness | `_common.py:52-57` |
| `cache_value_key` | Consumers import the `_cache_value_key` alias | Required | Remove the alias; `engine.py` imports `cache_value_key` | Internal (Decision 2 / §6.I) | `_keys.py:86`; `engine.py:12` |
| `cache_has_value` | Consumers import the `_cache_has_value` alias | Required | Remove the alias; `translate.py` imports `cache_has_value` | Internal (Decision 2 / §6.I) | `_keys.py:87`; `translate.py:10` |
| `cache_lookup_value` | Consumers import the `_cache_lookup_value` alias | Required | Remove the alias; `translate.py` imports `cache_lookup_value` | Internal (Decision 2 / §6.I) | `_keys.py:88`; `translate.py:10` |
| `is_basedata_type` | Identifies `BaseData` by MRO `__name__`/`__module__` string match | Retain | None; documented relocation hazard | Intentional (avoids lower-level-to-facade import) | `_outputs.py:17-28` |
| `shared_cache_manager` | Builds a throwaway `CacheManager` probe per call; registry never evicts | Retain | None; process-wide registry is intentional | Intentional lifecycle | `manager.py:434-460` |

No `Adjust` assessment remains without a decision.

## 11. Module Contracts and Dependency Review

This section completes the module-level contract assessment. No module shows an ownership leak or unnecessary implementation coupling; the only cross-package private edges are the five documented in §13.3. No abstraction is introduced to remove a direct dependency.

### 11.1 Module contract inventory

| Module | Responsibility | Main symbols | Inputs / outputs | State / side effects | Invariants | Dependency direction | Test coverage gaps |
|---|---|---|---|---|---|---|---|
| bynat.cleaning.base | Class-based facade: BaseData/JsonFile/CsvFile DataFrame subclasses, inplace/statistics return contracts, cache-manager metadata, synchronized docstrings via _shares_doc. | ['BaseData', 'JsonFile', 'CsvFile', '_shares_doc'] | Constructors accept tabular data or file paths plus cache_dir; transformation methods mirror functional module signatures minus frame plus inplace; profile adapts BaseData output types; save_to_json/save_to_sql return None. | Instance attributes _bynat_cache_dir/_bynat_cache_manager; _metadata=['cache_manager'] drives pandas __finalize__ sharing; inplace uses _update_inplace; clear_cache_for_column/view helpers. | Results are copies by default including early exits; inplace=True returns None or stats; subclass preserved through _constructor; docstrings are synced with functional implementations by tools/sync_docs.py and doc-drift tests. | Imports bynat.caching (public), bynat.profiling, and cleaning.columns/io/stats/text/enrich (functional core); no functional module imports base. | ['Derived-frame cache_dir loss after clearing manager', 'file constructors with explicit path plus non-existent string data', 'view()/pickle metadata edge cases'] |
| bynat._accessors (dataframe.py + _binding.py) | Private pandas-accessor integration boundary: registers df.bynat, adapts shared functions to accessor methods, owns inplace binding and cache-manager injection; contains no domain algorithms. | ['BynatAccessor', 'profile (module wrapper)', '_method_signature', '_with_inplace', '_frame_method', '_cached_frame_method'] | Methods take the caller's arguments plus generated inplace; cached methods receive self.cache_manager; non-cached pass only the frame; with_cache accepts dir/CacheManager/None and returns a new accessor. | Holds _obj by reference and optional _cache_manager; default manager from shared_cache_manager(); process-wide _shared_managers registry with lock. | Generated signatures/docs mirror implementations; frame and cache_manager hidden; inplace parity with BaseData calling convention; accessor transformations return plain DataFrames. | Imports bynat.caching, cleaning functional modules, cleaning._outputs.is_basedata_type, profiling; must not import root bynat (boundary test). | ['Registration idempotence/warnings', 'manager assignment races', 'variadic inplace positional parity'] |
| bynat.cleaning.columns | Pure column tidying/reshaping helpers shared by the classes and accessor. | ['drop_by_substring', 'drop_CLASS_columns', 'rename_by_substring', 'rename_all_DOTS', 'reorder_columns', 'melt_transform_pivot', 'move_column', 'align_lat_lng', 'split_list_objects'] | Each takes FrameT first and returns FrameT; melt_transform_pivot/split_list_objects can change shape and reset indexes. | Copies frames; never mutates inputs; no caches or I/O. | Missing columns yield unchanged copies or are ignored per method; melt pivot output has fresh RangeIndex and aggfunc resolves duplicates; split explode resets index. | Depends only on pandas, _common (_like/FrameT); no reverse dependency. | ['melt_transform_pivot exotic pivot layouts', 'split_list_objects sentinel/all and scalar-index interactions', 'non-string column names in rename/reorder edge cases partially covered'] |
| bynat.cleaning.text | Keyword extraction, truncation, and reference-lexicon categorization. | ['extract_keywords', 'truncate_after_substring', 'categorize_by_reference', '_optional_ahocorasick', '_first_literal_matches', '_first_regex_matches', '_remove_patterns'] | Functions take FrameT first plus keyword/column kwargs and return FrameT; categorize_by_reference requires pyahocorasick. | Copies; optional automaton built per call; no persistent state. | Literal whole-word matching with priority order; regex capture-group semantics; title-casing; existing target column only NaN-filled but then title-cased; categorize longest-match and later-reference tie-break. | Depends on pandas/numpy/re/importlib and _common; optional pyahocorasick; no dependency on other cleaning modules. | ['categorize underscore boundary', 'extract_keywords duplicate keywords', 'invalid regex error behavior', 'categorize non-dict reference with no valid sources'] |
| bynat.cleaning.stats | Hierarchical outlier masking, imputation (self and reference-based), and hierarchical statistics output. | ['handle_outliers', 'drop_outliers', 'fill_missing', 'fill_missing_from', 'get_hierarchical_stats', '_hierarchical_outlier_masks', '_normalize_hierarchy', '_compute_hierarchical_stats'] | Functions take FrameT first; hierarchy methods return frame or (frame,stats); get_hierarchical_stats returns DataFrame/BaseData/dict per output_type. | Copies; uses _left_merge_aligned; no caches; asserts unique logical stat keys. | min_samples validated only in fill_missing/fill_missing_from (int>=1, bool rejected), not in outlier methods; hierarchy relaxation removes last column; group_key tuples; output ordering strategy->target->hierarchy; leakage-free fill_missing_from statistics. | Depends on pandas/numpy and _common/_outputs; no enrichment/cache dependencies. | ['PD-02 min_samples outlier validation xfails', 'nested target flattening depth', 'match_cols collision', 'mode tie determinism', 'non-BaseData subclass default output'] |
| bynat.cleaning.io | Local JSON/CSV loaders and JSON/SQL writers; owns optional SQLAlchemy import. | ['read_csv', 'read_json', 'save_to_json', 'save_to_sql', 'JsonOrient', 'IfExists'] | Readers return plain DataFrame; writers return None; save_to_json supports append/dedupe/compare; save_to_sql builds SQLAlchemy URLs. | Filesystem writes/reads; save_to_sql engine per call disposed in finally; no frame mutation. | Missing files FileNotFoundError; datetime normalization formats; append dedupe keeps first; SQL dialect validation before dependency import. | Depends on pandas, _common._import_optional, _internal.dedupe_key, urllib.parse; optional SQLAlchemy. | ['save_to_json zero-byte append', 'save_to_sql non-SQLite dialects', 'non-ValueError append read failures'] |
| bynat.cleaning.enrich.engine | Shared cached-lookup loop for all enrichment features: unique-value extraction, cache hit testing, batched fetching, checkpointing, and failure handling. | ['_cached_map', '_rate_limited_map', 'SKIP', 'Fetch', 'FetchMany'] | Input series/values + bucket name(s) + save_every + manager/func_name/key/is_cached/fetch_many/on_fetch_start/action/label; returns the live cache bucket (or dict of buckets). | Mutates manager buckets and saves checkpoints; thread pool for parallel fetches; exceptions captured per item. | Nulls/duplicates removed first-seen; outcome stored unless SKIP or Exception; fetch_many length mismatch fails whole chunk; checkpoint every save_every and final save when unsaved; on_fetch_start called once only when work exists and its exceptions propagate. | Imports bynat.caching and caching._keys (documented private cross-package import); no cleaning/text/stats dependencies. | ['Multi-bucket partial-cached semantics partially covered', 'rate limiter timing precision', 'on_fetch_start exception propagation specifically'] |
| bynat.cleaning.enrich.providers | Provider protocols and default external-service adapters. | ['Translator', 'Geocoder', 'RateSource', 'GoogleTranslatorProvider', 'NominatimGeocoder', 'YFinanceRateSource'] | Protocols define translate/geocode/yearly_rates; defaults wrap deep_translator, geopy Nominatim (1 req/s), yfinance Ticker history. | Thread-local translator cache; rate limiter; lazy optional imports raising ImportError on construction. | Structural runtime_checkable protocols; falsy translation left uncached; None geocode cached as miss; yearly_rates keys int years, rate = currency per USD. | Imports _common._import_optional and pandas (YFinance means); optional third-party deps only. | ['Real service calls are fake/monkeypatched', 'GoogleTranslator per-thread behavior tested with fakes', 'YFinance real download untested'] |
| bynat.cleaning.enrich.translate | Language detection imputation and cached translation of categorical/conditional columns. | ['impute_by_language', 'translate_conditional_column', 'translate_categorical_column', '_translate_all', '_translate_cached'] | Take FrameT + target/reference columns + langdetect target; return FrameT with translated/imputed target values. | Copies; uses langdetect seed 0; caches translations under func_name buckets; provider constructed lazily only when translations needed. | Exact normalized match then language detection then title-cased fallback; conditional partitions skip when sampled language matches threshold; empty/error translations left untranslated and uncached; translated values Title-Cased. | Imports caching, _common, engine, providers; optional langdetect/deep-translator. | ['safe partition avoids deep-translator import (tested)', 'language-detection error fallback branches', 'thread-pool provider path with max_workers/min_interval'] |
| bynat.cleaning.enrich.geocode | Geocode missing coordinates through cached provider lookups. | ['fill_missing_coordinates'] | FrameT + fallback columns + lat/long names + save_every/user_agent/retry_not_found/provider; returns FrameT with coordinates filled. | Temporary helper column removed; caches tuples/None; provider lazy. | Existing coordinates preserved; only missing fields updated; failed queries shortened; misses cached; errors uncached. | Imports caching, _common, engine, providers; optional geopy. | ['retry_not_found full cycle', 'asymmetric lat/long missing with numeric fallbacks'] |
| bynat.cleaning.enrich.currency | Cached local-currency to USD conversion. | ['convert_to_usd', '_lookback_years'] | FrameT + target columns + country/year columns + new_cols/round_decimals/provider; returns FrameT with converted columns. | Caches currency codes and yearly rates; one provider call per currency; misses cached selectively. | Divide by rate; USD short-circuit; lookback down to earliest year in data; unknown -> NaN; network errors uncached. | Imports caching, _common, engine, providers; optional pycountry/Babel/yfinance. | ['Real pycountry/Babel/yfinance', 'requested year before data minimum', 'future-year misses'] |
| bynat.cleaning.enrich.nlp | spaCy-backed cached lexicon entity extraction. | ['extract_entities_nlp', '_normalize_nlp_disable', '_nlp_cache_bucket', '_lexicon_terms'] | FrameT + source columns + lexicon + model/config + cache_manager + target/json-key kwargs; returns FrameT with list columns. | Lazy spaCy load; matcher built per call; cache buckets isolated by hash. | Required pipes non-disableable; unknown pipes warn; config validation precedes model load; per-text failures uncached. | Imports caching, _common, engine; optional spacy. | ['Real spaCy model execution', 'entity list ordering', 'cached-run-without-spaCy'] |
| bynat.caching.manager | High-level CacheManager and process-wide shared manager registry. | ['CacheManager', 'shared_cache_manager', 'resolve_cache_dir', 'CACHE_DIR_ENV_VAR', 'DEFAULT_CACHE_DIR'] | CacheManager(cache_dir=None) with load/get/save/delete methods; shared_cache_manager(cache_dir=None) -> per-absolute-path manager. | caches/_baselines dicts; SQLite lazy initialization; shared registry with lock. | Key validation; memoized live dict; baseline deep copy advanced only on successful save; failures logged/swallowed; deletion limited to known identities. | Imports caching._storage/_migration; stdlib only plus those; no cleaning/analytics/profiling dependencies. | ['Environment-variable resolution order covered; registry eviction none by design', 'save failure followed by manager reuse partially covered'] |
| bynat.caching._storage / _migration / _keys | SQLite schema/persistence primitives; legacy JSON migration and quarantine; cache key/value normalization helpers. | ['SQLiteStorage', 'connect_sqlite', 'SQLITE_DATABASE_NAME', 'SQLITE_TIMEOUT_SECONDS', 'migrate_legacy_json_cache', 'quarantine_corrupt_cache_file', 'cache_value_key', 'cache_has_value', 'cache_lookup_value'] | Storage connects/initializes/rebuilds/saves diffs; migration imports one JSON file; keys normalize values to stable strings. | Creates cache dir/DB, WAL/FULL synchronous pragmas, transactions, quarantine renames. | INSERT OR REPLACE last-writer-wins; exact DELETEs; one-time migration marker; integral float/int key collapse; raw-key fallback lookups. | _storage standalone stdlib; _migration imports _storage; _keys imports numpy only; manager composes them. | ['Migration rollback/concurrency well covered', 'quarantine path exhaustion fallback covered by monkeypatch', 'tuple->list JSON round-trip normalization not asserted'] |
| bynat.cleaning._common / _outputs / _internal.values | Shared internal primitives: optional imports, positive-int validation, aligned left merge, frame-type wrapping; output-type validation/conversion/BaseData detection; canonical dedupe_key. | ['import_optional', 'require_positive_int', 'left_merge_aligned', 'like', 'logger', 'FrameT', 'HIERARCHICAL_STATS_COLUMNS', 'validate_output_type', 'convert_output', 'convert_default_output', 'constructor_accepts_data', 'is_basedata_type', 'dedupe_key'] | Pure helpers consumed across cleaning/caching/accessor/profiling boundaries. | None; module-level legacy-compatible aliases retained. | Only BaseData-family classes pass output validation; default output falls back when constructor cannot bind data; dedupe_key returns hashable JSON strings for list/dict/tuple/set/ndarray. | _common/_outputs import pandas only (plus typing/inspect); _internal imports stdlib+numpy; consumers may import these private helpers per documented exceptions. | ['Alias blocks are intentional per design', 'convert_default_output edge for non-BaseData subclass indirectly exposed'] |
| bynat.analytics.analyzer | Application-independent analytics aggregations returning JSON-ready dict payloads. | ['Analyzer'] | Analyzer(DataFrame) defensive copy; five public methods with filters/rules/orient/kwargs returning dicts. | Copies; eval-based rules guarded; logging warnings. | Never mutates source; empty payload conventions; safe-expression blocklist; observed=True groupbys; round/int conversions. | Imports numpy/pandas/operator/logging only; independent of cleaning/caching/profiling. | ['orient variants beyond records in depth', 'numpy float32 KPI path', 'eval-dependent rule coverage with local variables'] |
| bynat.profiling.profile / report | Non-mutating data-quality profiling core and report models. | ['profile', 'ProfileReport', 'DatasetProfile', 'ColumnProfile'] | profile(df,*columns,output_type) -> ProfileReport/dict/DataFrame; report models implement Mapping and to_dict/to_dataframe. | Read-only; no caches/I/O; internal dedupe_key normalization. | Duplicate keep='first'; proportions relative to selection; unavailable stats None; duplicate-name last-wins in columns dict but column_list positional. | profile imports _internal.dedupe_key and .report; no cleaning/caching/analytics dependencies. | ['Explicit ProfileReport output_type', 'memory failure path', 'custom unsupported output_type message'] |

## 12. Existing-to-Target Migration Map

Action legend: **Keep** = file and content unchanged; **Keep/normalize** = file kept, internal content normalized; **Update imports** = import statements updated to canonical names; **Update test** = one test reference updated.

| Current path | Target path | Action | Reason | Compatibility notes |
|---|---|---|---|---|
| `bynat/__init__.py` | same | Keep | Root contract already exact | None |
| `bynat/py.typed` | same | Keep | Packaging marker | None |
| `bynat/_accessors/__init__.py` | same | Keep | Private boundary | None |
| `bynat/_accessors/_binding.py` | same | Keep | Wrapper mechanics | None |
| `bynat/_accessors/dataframe.py` | same | Keep | Accessor ownership | None |
| `bynat/_accessors/dataframe.pyi` | same | Keep | Generated stub | Regenerate only if accessor signatures change; none do |
| `bynat/_internal/__init__.py` | same | Keep | Canonical shared export | None |
| `bynat/_internal/values.py` | same | Keep | Canonical `dedupe_key` | None |
| `bynat/analytics/__init__.py` | same | Keep | Package API | None |
| `bynat/analytics/analyzer.py` | same | Keep | Cohesive class | None |
| `bynat/caching/__init__.py` | same | Keep | Package API | None |
| `bynat/caching/_keys.py` | same | Keep/normalize | Delete `_cache_value_key`/`_cache_has_value`/`_cache_lookup_value` alias assignments | Private module; no public API |
| `bynat/caching/_migration.py` | same | Keep/normalize | Delete the module-level aliases `_quarantine_corrupt_cache_file` and `_migrate_legacy_json_cache` (dead); the surviving public name is `migrate_legacy_json_cache` | Private module; no surviving-symbol conflict |
| `bynat/caching/_storage.py` | same | Keep | Storage internals | None |
| `bynat/caching/manager.py` | same | Keep/normalize | Delete `_SQLITE_DATABASE_NAME`, `_SQLITE_TIMEOUT_SECONDS`, `_migrate_legacy_cache`; keep `CacheManager._migrate_legacy_json_cache` | Private symbols; one test line updated |
| `bynat/cleaning/__init__.py` | same | Keep | Package API | None |
| `bynat/cleaning/_common.py` | same | Keep/normalize | Delete `_HIERARCHICAL_STATS_COLUMNS`, `_import_optional`, `_require_positive_int`, `_left_merge_aligned`, `_like` aliases | Private module |
| `bynat/cleaning/_outputs.py` | same | Keep/normalize | Delete `_is_basedata_type`, `_validate_output_type`, `_convert_output`, `_constructor_accepts_data`, `_convert_default_output` aliases | Private module |
| `bynat/cleaning/base.py` | same | Keep | Facade; docstring generation unaffected | None |
| `bynat/cleaning/columns.py` | same | Update imports | `_like` → `like` | Internal only |
| `bynat/cleaning/io.py` | same | Update imports | `_import_optional` → `import_optional` | Internal only |
| `bynat/cleaning/stats.py` | same | Update imports | `_HIERARCHICAL_STATS_COLUMNS`→`HIERARCHICAL_STATS_COLUMNS`, `_left_merge_aligned`→`left_merge_aligned`, `_convert_*`→`convert_*`, `_validate_output_type`→`validate_output_type` | Internal only |
| `bynat/cleaning/text.py` | same | Update imports | `_import_optional` → `import_optional` | Internal only |
| `bynat/cleaning/enrich/__init__.py` | same | Keep | Provider exports | None |
| `bynat/cleaning/enrich/currency.py` | same | Update imports | `_import_optional`→`import_optional`, `_left_merge_aligned`→`left_merge_aligned` | Internal only |
| `bynat/cleaning/enrich/engine.py` | same | Update imports | `_cache_value_key`→`cache_value_key` | Internal only; documented private edge |
| `bynat/cleaning/enrich/geocode.py` | same | Update imports | `_require_positive_int`→`require_positive_int` | Internal only |
| `bynat/cleaning/enrich/nlp.py` | same | Update imports | `_import_optional`→`import_optional`, `_require_positive_int`→`require_positive_int` | Internal only |
| `bynat/cleaning/enrich/providers.py` | same | Update imports | `_import_optional`→`import_optional` | Internal only |
| `bynat/cleaning/enrich/translate.py` | same | Update imports | `_cache_has_value`→`cache_has_value`, `_cache_lookup_value`→`cache_lookup_value`, `_import_optional`→`import_optional`, `_require_positive_int`→`require_positive_int` | Internal only |
| `bynat/profiling/__init__.py` | same | Keep | Package API | None |
| `bynat/profiling/profile.py` | same | Keep | Profiling core | None |
| `bynat/profiling/report.py` | same | Keep | Report models | None |
| `tests/modules/caching/migration/legacy/test_legacy_rollback.py` | same | Update test | `manager._migrate_legacy_cache` → `manager._migrate_legacy_json_cache` (the surviving manager method; the test already calls it at lines 145, 151, 164, 177) | Test-only; behavior unchanged |
| `benchmarks/reference_impls.py` | same | Update imports | `_left_merge_aligned` → `left_merge_aligned` | Benchmark support file; also copied by `tools/verify_installed_wheel.py` |

No source file is intentionally excluded from restructuring. `tools/sync_docs.py`, `tools/verify_installed_wheel.py`, and the remaining `benchmarks/` scripts are unaffected because no public path, package-data path, or generated-artifact path changes. `benchmarks/reference_impls.py` is the one non-`bynat/` consumer of a removed alias and is updated in the table above; `tests/` changes are limited to the one migration-method reference.

---

## 13. Package Dependency Matrix

### 13.1 Permitted internal dependencies

| Consumer | Permitted targets | Notes |
|---|---|---|
| `bynat` (root) | `cleaning`, `caching`, `analytics`, `profiling`, `_accessors`, `cleaning.io` | Explicit bindings; `_accessors` is registration-only |
| `_accessors` | `cleaning` (public modules + `_outputs.is_basedata_type`), `caching`, `profiling` | Delegation only; no algorithms |
| `cleaning` | `caching` (public API + documented `caching._keys`), `profiling`, `_internal` | Facade delegates to profiling; enrichment uses cache |
| `profiling` | `_internal` | No functional package |
| `analytics` | none | Fully independent |
| `caching` | none | No functional package |
| `_internal` | none | stdlib + NumPy only |

### 13.2 Prohibited internal dependencies

| Consumer | Prohibited targets |
|---|---|
| `caching` | `cleaning`, `analytics`, `profiling`, `_accessors` |
| `analytics` | `cleaning`, `caching`, `profiling`, `_accessors` |
| `profiling` | `cleaning`, `analytics`, `caching`, `_accessors` |
| `cleaning` | `analytics`, `_accessors` |
| functional packages | `_accessors` |
| `_internal` | any `bynat` functional package |
| `_accessors` | `_internal` (no use case; add only with evidence) |

### 13.3 Documented private-import exceptions

A strict private-module rule would flag five edges. Three are genuine exceptions and must be represented in enforcement; two target the intended shared private package `_internal`.

| Edge | Allowed because | Enforcement representation |
|---|---|---|
| `cleaning.enrich.engine → caching._keys` | Cache-key identity is caching-owned | `protected` on `bynat.caching._keys` with allow-list |
| `cleaning.enrich.translate → caching._keys` | Same | Same |
| `_accessors.dataframe → cleaning._outputs` | BaseData-type detection is cleaning-owned and the accessor is the adaptation seam | `protected` on `bynat.cleaning._outputs` with allow-list |
| `cleaning.io → _internal` | `_internal` is the intended shared private package | `protected` on `bynat._internal` with allow-list |
| `profiling.profile → _internal` | Same | Same |

No other cross-package private-module import exists. The AST contract test asserts this exact set; Import Linter represents it with `protected` contracts plus `private_modules` scoped to the remaining underscore modules.

**Scanning scope and limitations.** The inventory was produced by an AST scan of every static import in `bynat/**/*.py`, with relative imports resolved to their destination modules. All five cross-package private imports are absolute. The 16 intra-package relative imports of private modules are: `_accessors/dataframe → _accessors._binding`; `caching/_migration → caching._storage`; `caching/manager → caching._migration` and `caching._storage`; `cleaning/base → cleaning._outputs`; `cleaning/columns`, `cleaning/io`, `cleaning/stats`, `cleaning/text`, and `cleaning/enrich/{currency,engine,geocode,nlp,providers,translate} → cleaning._common`; and `cleaning/stats → cleaning._outputs`. No relative import crosses a top-level package boundary. Dynamic imports (`importlib.import_module`) appear only in `cleaning/_common.py` (runtime optional dependency) and `cleaning/text.py` (`"ahocorasick"`) and never target an internal module. Completeness is claimed for static absolute and relative imports only; dynamic imports of optional third-party packages are out of scope by design.

---

## 14. Module Dependency Maps

### 14.1 `cleaning`

```text
cleaning/__init__ ──> base
base ──> columns, io, stats, text, enrich, enrich.providers, caching, profiling, _outputs
columns ──> _common
text ──> _common
stats ──> _common, _outputs
io ──> _common, _internal
enrich/currency ──> caching, _common, enrich.engine, enrich.providers
enrich/geocode ──> caching, _common, enrich.engine, enrich.providers
enrich/nlp ──> caching, _common, enrich.engine
enrich/translate ──> caching, caching._keys, _common, enrich.engine, enrich.providers
enrich/engine ──> caching, caching._keys, _common
enrich/providers ──> _common
_common ──> (pandas, stdlib)
_outputs ──> (pandas, stdlib)
```

### 14.2 `caching`

```text
caching/__init__ ──> manager
manager ──> _migration, _storage
_migration ──> _storage
_storage ──> (sqlite3, stdlib)
_keys ──> (numpy, stdlib)      # consumed by cleaning.enrich (documented exception)
```

### 14.3 `profiling`

```text
profiling/__init__ ──> profile, report
profile ──> report, _internal
report ──> (pandas, stdlib)
```

### 14.4 `analytics`

```text
analytics/__init__ ──> analyzer
analyzer ──> (numpy, pandas, stdlib)
```

### 14.5 `_accessors`

```text
_accessors/__init__ ──> dataframe
dataframe ──> cleaning (columns, io, stats, text, _outputs, enrich), caching, profiling, _binding
_binding ──> (stdlib only)
```

### 14.6 `_internal`

```text
_internal/__init__ ──> values
values ──> (json, typing, numpy)
```

---

## 15. Data and Execution Flows

### 15.1 Class facade transformation (`BaseData.fill_missing`)

```text
BaseData.fill_missing
    │
    ▼
stats.fill_missing(df, ...)                      [functional core]
    ├── _common.left_merge_aligned / logger
    └── _outputs.validate_output_type / convert_output
    │
    ▼
BaseData._finish_with_stats(outcome, inplace, with_stats)
    ├── inplace=False → return frame (or (frame, stats))
    └── inplace=True  → self._update_inplace(frame); return stats or None
```

### 15.2 Accessor cached enrichment (`df.bynat.translate_conditional_column`)

```text
BynatAccessor.translate_conditional_column        [_cached_frame_method-generated]
    │
    ▼
translate.translate_conditional_column(self._obj, ..., cache_manager=...)
    ├── enrich.engine._cached_map(...)
    │       ├── caching._keys.cache_has_value / cache_lookup_value
    │       ├── CacheManager.get_column_cache / save_function_cache
    │       │       └── _storage.save_diff (BEGIN IMMEDIATE, INSERT OR REPLACE / DELETE)
    │       └── providers.Translator / GoogleTranslatorProvider (lazy deep_translator)
    └── inplace=True → accessor self._obj._update_inplace(result); return None
```

### 15.3 Profiling (`BaseData.profile` / `df.bynat.profile`)

```text
BaseData.profile ──────────────► profiling.profile(df, ...)         [profiling core]
df.bynat.profile ─► dataframe.profile ─► _profiling_profile(df, ...) + is_basedata_type adaptation
    │
    ▼
profiling.profile ──> report.DatasetProfile / ColumnProfile / ProfileReport
    │
    ▼
output_type=None → ProfileReport; dict → to_dict(); DataFrame → to_dataframe();
output_type=BaseData → output_type(data=summary_df)   [cleaning boundary only]
```

### 15.4 Cache persistence

```text
CacheManager.save_function_cache
    ├── diff live cache against _baselines
    ├── _storage.save_diff
    │       └── BEGIN IMMEDIATE → INSERT OR REPLACE / exact DELETE → commit
    ├── success → advance baseline
    └── failure → log, rollback, preserve pending in-memory changes
```

### 15.5 Enrichment cached lookup

```text
enrich feature ──> engine._cached_map
    ├── unique non-null values
    ├── probe cache (_keys.cache_has_value / cache_lookup_value)
    ├── fetch / fetch_many (provider; per-item failures logged and skipped)
    ├── store under _keys.cache_value_key
    └── checkpoint save_function_cache every save_every values
```

---

## 16. Behavioral and Implementation Contracts

The §15 flows show representative paths; this section records the behaviorally significant contracts in detail. Each entry distinguishes **Verified** (read in code), **Documented** (docstring/README), **Intended** (design intent), and **Unverified** (not established here). Discrepancies are listed in §17, not silently resolved.

### 16.1 BaseData construction and JsonFile/CsvFile loading (`F1`)

- **Entry point:** bynat.cleaning.base.BaseData.__init__(data=None, cache_dir=None, *args, **kwargs); JsonFile.__init__(data=None, json_file_path=None, key=None, cache_dir=None, ...); CsvFile.__init__(data=None, csv_file_path=None, cache_dir=None, read_kwargs=None, ...)
- **Input validation:** BaseData forwards data/*args/**kwargs to pandas.DataFrame after storing _bynat_cache_dir and _bynat_cache_manager=None via object.__setattr__. JsonFile/CsvFile: when data is str/PathLike and no explicit file path is given, os.path.isfile decides; existing file becomes the load path, otherwise FileNotFoundError('JSON file not found: ...'/'CSV file not found: ...'). Explicit file_path is ignored if data is not None. read_json validates key: TypeError for non-dict payload, KeyError for missing key.
- **Main operations and collaborators:** JsonFile -> bynat.cleaning.io.read_json (json.load -> key select -> pandas.json_normalize) -> BaseData/JsonFile; CsvFile -> io.read_csv -> pandas.read_csv(**read_kwargs).
- **Data transformations:** Nested JSON objects become dotted column names via json_normalize; CSV parsing/dtype inference delegated to pandas.
- **Mutation and inplace behavior:** Constructors only build new frames; no inplace parameter; source files untouched.
- **Return type and output-container behavior:** BaseData/JsonFile/CsvFile instances (pandas.DataFrame subclasses); read_csv/read_json return plain pandas.DataFrame. Empty data with no path yields an empty frame.
- **Index / ordering / shape / dtype invariants:** _constructor returns type(self) so pandas operations keep the subclass; cache manager lazy; construction creates no cache directory; path arguments must exist when used as data.
- **State changes and cache effects:** _bynat_cache_dir stored; _bynat_cache_manager stays None until first cache_manager access; manager creation itself creates no disk state.
- **External side effects:** Reads one local file; no network, no writes.
- **Error and recovery behavior:** FileNotFoundError for missing load path; TypeError/KeyError for bad key; json.JSONDecodeError propagates for malformed JSON; pandas parser errors propagate for CSV. With explicit file_path plus a non-existent string data, pandas raises ValueError('DataFrame constructor not properly called!') instead of the documented FileNotFoundError.
- **Relevant tests:** tests/cross_cutting/base_api/test_base_constructors.py::test_json_and_csv_constructors_read_local_files; tests/cross_cutting/base_api/test_base_constructors.py::test_file_constructors_raise_for_missing_paths; tests/modules/io/test_io_read.py::test_file_constructors_accept_positional_paths; tests/modules/io/test_io_read.py::test_read_json_key_on_non_dict_payload_raises_typeerror; tests/modules/io/test_io_read.py::test_read_json_missing_key_raises_keyerror
- **Uncovered cases:** JsonFile/CsvFile with explicit path plus non-existent path string in data (ValueError, not FileNotFoundError); data already tabular plus explicit file_path (path ignored); bytes/os.PathLike path handling; key selecting a non-list value

### 16.2 BaseData.cache_manager metadata propagation (`F2`)

- **Entry point:** BaseData.cache_manager property getter/setter; _metadata=['cache_manager']; BaseData._constructor; BaseData.view()
- **Input validation:** Setter accepts CacheManager or None. Getter reads self.__dict__.get('_bynat_cache_manager'); on None builds CacheManager(cache_dir=self.__dict__.get('_bynat_cache_dir')) and stores it.
- **Main operations and collaborators:** CacheManager(cache_dir) -> resolve_cache_dir -> os.path.expandvars/expanduser/abspath; SQLiteStorage created but not initialized.
- **Data transformations:** pandas operations call __finalize__, which copies _metadata attributes; the cache_manager property is read on the source and assigned through the setter on the derived frame, so the same manager object is shared.
- **Mutation and inplace behavior:** Assigning None clears the instance manager; next access builds a fresh manager. No frame data mutation.
- **Return type and output-container behavior:** CacheManager instance; view() returns a new plain pandas.DataFrame with no manager attribute.
- **Index / ordering / shape / dtype invariants:** Slices/copies/chained ops share one manager; manager identity is stable; _bynat_cache_dir is NOT metadata, so a derived frame's manager recreation falls back to BYNAT_CACHE_DIR/default, losing the parent's custom directory.
- **State changes and cache effects:** First access creates the manager object only; SQLite directory/database are still created lazily on first real cache access/save.
- **External side effects:** None until cache initialization.
- **Error and recovery behavior:** CacheManager constructor raises TypeError for non-str/PathLike and ValueError for empty cache_dir; these propagate from first cache_manager access.
- **Relevant tests:** tests/cross_cutting/accessor/inplace/test_mutation.py::test_accessor_inplace_on_a_basedata_frame_preserves_its_cache_manager; tests/cross_cutting/accessor/test_accessor.py::test_pandas_operations_share_the_legacy_cache_manager; tests/cross_cutting/base_api/test_base_constructors.py::test_melt_transform_pivot_result_keeps_the_cache_manager; tests/cross_cutting/base_api/test_base_constructors.py::test_public_cleaning_imports_use_the_bundled_cache_manager
- **Uncovered cases:** Clearing a derived frame's manager silently changes its cache directory to env/default; pickling/unpickling metadata behavior; interplay of view() with later cached calls

### 16.3 df.bynat registration, with_cache, clear_cache_for_column (`F3`)

- **Entry point:** bynat/__init__.py imports ._accessors; @pd.api.extensions.register_dataframe_accessor('bynat') BynatAccessor in bynat/_accessors/dataframe.py; method factories in bynat/_accessors/_binding.py
- **Input validation:** _method_signature drops the first (frame) parameter and any cache_manager parameter; _with_inplace inserts inplace at the BaseData slot or keyword-only after variadic args. Cached methods pass cache_manager=self.cache_manager. Non-transform methods reject inplace via their generated signature.
- **Main operations and collaborators:** BynatAccessor delegates to cleaning.columns/text/stats/io, cleaning.enrich.*, profiling.profile; cache_manager property lazily calls shared_cache_manager(); with_cache resolves a CacheManager instance directly or shared_cache_manager(dir/None); clear_cache_for_column calls manager.delete_column_cache.
- **Data transformations:** Plain functional calls return plain pandas.DataFrame results; cached functions receive the accessor's manager; inplace=True wraps self._obj._update_inplace(result).
- **Mutation and inplace behavior:** Default: wrapped frame untouched and a new frame returned. inplace=True mutates self._obj by reference and returns None, or the statistics frame for handle_outliers/drop_outliers/fill_missing/fill_missing_from with get_hierarchical_stats=True.
- **Return type and output-container behavior:** Plain pandas.DataFrame (not BaseData) for transformations; get_hierarchical_stats/profile return their declared containers; save_to_json/save_to_sql/with_cache/clear_cache_for_column return None/accessor/None.
- **Index / ordering / shape / dtype invariants:** Generated __signature__/__doc__ come from the shared implementation; frame and cache_manager are hidden; one process-wide manager per resolved absolute cache directory via _shared_managers guarded by a lock; explicit CacheManager is reused as-is.
- **State changes and cache effects:** Process-wide registry retains managers forever; accessor's default manager is created on first cached call.
- **External side effects:** Only through delegated cache/external-service functions.
- **Error and recovery behavior:** Missing optional dependencies surface from the delegated call; validation errors propagate before cache use; pandas raises for unknown accessor attributes.
- **Relevant tests:** tests/cross_cutting/accessor/test_accessor.py::test_importing_bynat_registers_the_accessor; tests/cross_cutting/accessor/test_accessor.py::test_accessor_uses_one_shared_cache_manager_per_directory; tests/cross_cutting/accessor/test_accessor.py::test_accessor_cached_methods_use_the_selected_cache; tests/cross_cutting/accessor/inplace/test_argument_binding.py; tests/cross_cutting/accessor/inplace/test_variadic_capture.py; tests/cross_cutting/accessor/test_parity.py
- **Uncovered cases:** Repeated import/submodule import re-registration warning behavior; thread races assigning _cache_manager; positional inplace parity for variadic methods where the accessor makes inplace keyword-only while BaseData accepts it positionally

### 16.4 CacheManager.load_function_cache legacy migration/quarantine (`F4`)

- **Entry point:** CacheManager.load_function_cache(func_name) -> dict; helpers CacheManager._initialize_sqlite, _migrate_legacy_json_cache, _rebuild_function_cache_from_sqlite; _migration.migrate_legacy_json_cache/quarantine_corrupt_cache_file
- **Input validation:** _validate_cache_key: TypeError non-str; ValueError empty or containing path separators/basename mismatch.
- **Main operations and collaborators:** First miss: initialize SQLite schema (creates cache dir), migrate <func>_cache.json once, rebuild {bucket:{key:value}} from cache_entries ordered by bucket,key, memoize in caches, deep-copy into _baselines. Migration marks basename in migration_metadata, INSERT OR IGNORE so existing SQLite rows win.
- **Data transformations:** JSON payload -> Python via json.loads; corrupt/moved file -> quarantine path '<file>.corrupt.<time_ns>.<uuid>' reserved with O_CREAT\|O_EXCL then os.replace; unsupported nested buckets or unserializable values leave source unmarked; unreadable JSON logs warning.
- **Mutation and inplace behavior:** Writes SQLite rows and marker; moves corrupt source aside; memoizes live dict; baseline snapshot updated only after successful load.
- **Return type and output-container behavior:** Live mutable dict (same object on repeat calls); {} when no rows; caller mutations persist until save_function_cache.
- **Index / ordering / shape / dtype invariants:** Migration at most once per basename; SQLite precedence; locked-database retry loop (6 attempts, 0.05*(attempt+1)s) around initialization; transaction rolled back on failure; concurrent migration safe.
- **State changes and cache effects:** caches[func_name] and _baselines[func_name]; SQLite schema tables cache_entries(func_name,bucket,key,value_json,created_at; PK func_name,bucket,key), index idx_cache_entries_func_bucket, migration_metadata(source_name,migrated_at).
- **External side effects:** Creates cache directory and cache.sqlite3 on first access; WAL mode; may rename corrupt JSON files.
- **Error and recovery behavior:** sqlite3.Error propagates after rollback if not a lock or after final attempt; JSON decode/unicode/top-level non-object -> quarantine + warning; OSError read -> warning; corruption still yields an empty cache rather than raising.
- **Relevant tests:** tests/modules/caching/persistence/test_persistence_load.py; tests/modules/caching/migration/legacy/test_legacy_import.py; tests/modules/caching/migration/legacy/test_legacy_quarantine.py; tests/modules/caching/migration/legacy/test_legacy_rollback.py; tests/modules/caching/migration/test_migration_sqlite.py; tests/modules/caching/persistence/test_persistence_recovery.py::test_corrupt_cache_is_quarantined_and_replaced_with_empty_dict
- **Uncovered cases:** Quarantine reservation exhaustion fallback path only exercised via monkeypatch; basename marker collisions across directories; value JSON that is valid but decodes to non-bucket structures

### 16.5 CacheManager.delete_column_cache (`F5`)

- **Entry point:** CacheManager.delete_column_cache(func_name, col_name) -> None
- **Input validation:** Both keys validated as non-empty strings without path separators (TypeError/ValueError).
- **Main operations and collaborators:** load_function_cache (triggers init/migration/rebuild) -> delete func_cache[col_name] in place -> save_function_cache diffs live cache against the deep baseline and issues exact (func_name,bucket,key) DELETEs in one BEGIN IMMEDIATE transaction.
- **Data transformations:** Bucket mapping removed from live dict; SQLite rows for baseline identities removed.
- **Mutation and inplace behavior:** Mutates live in-memory cache and deletes persisted rows; unrelated buckets/functions untouched.
- **Return type and output-container behavior:** None; INFO logged both when deleted and when absent ('No cache found for column ...').
- **Index / ordering / shape / dtype invariants:** Concurrent additions after load are not in the baseline so their identities are never deleted; a stale manager preserves rows added by other managers; if save fails the in-memory removal remains pending and the next save retries.
- **State changes and cache effects:** Baseline unchanged on failed save; advanced only after commit; SQLite rows removed atomically.
- **External side effects:** SQLite write; cache directory created lazily.
- **Error and recovery behavior:** Save failures are caught/logged by save_function_cache and swallowed; validation errors propagate.
- **Relevant tests:** tests/modules/caching/persistence/test_persistence_delete_column.py::test_delete_column_cache_persists_existing_bucket_removal; tests/modules/caching/persistence/test_persistence_delete_column.py::test_delete_column_cache_leaves_unrelated_buckets_intact; tests/modules/caching/persistence/test_persistence_delete_column.py::test_delete_column_cache_leaves_unrelated_function_intact; tests/modules/caching/persistence/test_persistence_delete_column.py::test_delete_column_cache_missing_bucket_is_a_no_op; tests/modules/caching/persistence/test_persistence_delete_column.py::test_delete_column_cache_failed_transaction_is_retryable; tests/modules/caching/test_concurrency.py::test_delete_column_cache_stale_manager_preserves_concurrent_additions
- **Uncovered cases:** Delete when the bucket is present in SQLite but absent from this manager's baseline after a concurrent rewrite; save failure followed by process exit (pending removal durability)

### 16.6 save_to_json (append/dedupe/compare) (`F6`)

- **Entry point:** bynat.cleaning.io.save_to_json(df, file_path, orient='records', append=False, force_ascii=False, indent=4) -> None; BaseData.save_to_json / accessor save_to_json wrappers
- **Input validation:** os.fspath(file_path).strip() (None -> '') then ValueError if empty; orient not locally validated (pandas); df never required to be a DataFrame by local code.
- **Main operations and collaborators:** Internal export_df=df.copy(); datetime/datetetimetz columns reformatted with dt.strftime('%Y-%m-%d %H:%M:%S'). Existing file: append -> pd.read_json(orient), pd.concat(ignore_index=True), duplicated(keep='first'), TypeError fallback maps object columns through _internal.dedupe_key then duplicated; non-append -> to_json string compared with json.load(existing) and skip on equality. Write with to_json(orient,force_ascii,indent); makedirs(parent, exist_ok=True).
- **Data transformations:** Append resets to RangeIndex; dedupe keeps first occurrence; list/dict cells compared by canonical JSON text (sort_keys=True, default=str); datetime strings fixed format.
- **Mutation and inplace behavior:** Input df untouched; destination file overwritten/appended; parent directories created.
- **Return type and output-container behavior:** None always; no write when a non-append payload equals existing content; logs [SKIP]/[APPEND]/[OVERWRITE].
- **Index / ordering / shape / dtype invariants:** Datetime serialization format is stable; relative bare filename writes to cwd; table orient writes schema+rows; force_ascii/indent forwarded.
- **State changes and cache effects:** None; logging only.
- **External side effects:** Filesystem create/overwrite; reads existing file for comparison.
- **Error and recovery behavior:** Empty path ValueError; append with unreadable/incompatible JSON raises ValueError('Cannot append ...') (only catches ValueError); non-append unreadable/malformed existing file logs warning and overwrites; directory target and parent-is-file errors propagate (tested).
- **Relevant tests:** tests/modules/io/test_io_json.py; tests/modules/io/test_io_append.py::test_save_to_json_append_deduplicates_dict_cells_by_json_content; tests/modules/io/test_io_append.py::test_save_to_json_append_refuses_to_overwrite_unreadable_file; tests/modules/io/test_io_append.py::test_save_to_json_append_to_missing_or_empty_file_writes_rows; tests/cross_cutting/accessor/test_accessor.py::test_accessor_save_to_json
- **Uncovered cases:** Zero-byte existing file with append (raises instead of writing rows); append read failure that is not a ValueError (e.g., PermissionError); bytes file_path; orient-specific append semantics beyond records

### 16.7 save_to_sql (`F7`)

- **Entry point:** bynat.cleaning.io.save_to_sql(df, table_name, database_type, database_user, database_password, database_host, database_port, database_name, database_driver=None, columns_types=None, chunk_size=None, fast_executemany=False, if_exists='append', index=False) -> None
- **Input validation:** Order: table_name non-empty, if_exists in fail/replace/append, database_type non-empty, then dialect requirements. sqlite* needs database_name (':memory:' special); mssql/sqlserver needs all five connection fields plus database_driver; other dialects need all five. All checks happen before the optional SQLAlchemy import.
- **Main operations and collaborators:** URL building: sqlite:///db_name or sqlite:///:memory:; SQL Server URL with quote_plus(driver/user/pass) and ?driver=...; generic dialect URL with quote_plus(user/pass). Lazy sqlalchemy import via _import_optional; export_df=df.copy(); datetimetz columns tz_localize(None); engine=create_engine(url, **engine_kwargs); DataFrame.to_sql(...dtype=columns_types, chunksize=chunk_size or None); engine.dispose() in finally.
- **Data transformations:** Timezone-aware datetimes made naive on the internal copy only; input df never modified.
- **Mutation and inplace behavior:** Writes/append/replaces remote table rows; no frame mutation; engine always disposed.
- **Return type and output-container behavior:** None; database exceptions propagate.
- **Index / ordering / shape / dtype invariants:** if_exists forwarded to pandas; index flag controls index column; chunk_size None means single batch; fast_executemany passed for SQL Server even when False.
- **State changes and cache effects:** None; per-call engine lifecycle.
- **External side effects:** Network/database writes via SQLAlchemy; credentials placed (partly URL-encoded) in the URL.
- **Error and recovery behavior:** ValueError for invalid table/type/if_exists/credentials; ImportError naming SQLAlchemy if missing; database/ODBC errors propagate after engine disposal.
- **Relevant tests:** tests/modules/io/test_io_read.py::test_save_to_sql_rejects_invalid_arguments_before_connecting; tests/modules/enrichment/optional/test_optional_sqlalchemy.py (real SQLite, if_exists, chunk_size, columns_types, index, timezone normalization, error propagation, missing dependency, source immutability)
- **Uncovered cases:** Real non-SQLite dialects (postgres/mysql/mssql) and pyodbc fast_executemany; ':memory:' persistence semantics across dispose; SQL identifier quoting/injection edge cases

### 16.8 read_csv / read_json (`F8`)

- **Entry point:** bynat.cleaning.io.read_csv(csv_file_path, **read_kwargs) / read_json(json_file_path, key=None); re-exported as bynat.read_csv / bynat.read_json
- **Input validation:** os.fspath + os.path.isfile -> FileNotFoundError('CSV file not found: ...'/'JSON file not found: ...'); read_json key truthiness -> TypeError if payload not dict, KeyError if key absent.
- **Main operations and collaborators:** read_json opens utf-8, json.load, optional key selection, pandas.json_normalize; read_csv delegates entirely to pandas.read_csv.
- **Data transformations:** JSON nested objects flattened to dotted columns; CSV dtype inference by pandas.
- **Mutation and inplace behavior:** None; files opened read-only.
- **Return type and output-container behavior:** New plain pandas.DataFrame (not BaseData), even for BaseData-adjacent callers.
- **Index / ordering / shape / dtype invariants:** All pandas.read_csv keywords forwarded; unicode preserved (utf-8); empty array payload -> empty frame.
- **State changes and cache effects:** None.
- **External side effects:** Local file read only.
- **Error and recovery behavior:** FileNotFoundError; json.JSONDecodeError propagates for malformed JSON; pandas parser errors propagate.
- **Relevant tests:** tests/modules/io/test_io_read.py (reader errors, header-only CSV, malformed/empty files, directory rejection, JSON key errors, round trips); tests/cross_cutting/accessor/test_accessor.py::test_read_json_and_read_csv_return_plain_frames
- **Uncovered cases:** key selecting a scalar/non-list value; non-UTF-8 encodings; read_csv path-like objects beyond str/Path

### 16.9 handle_outliers (`F9`)

- **Entry point:** bynat.cleaning.stats.handle_outliers(df, *target_cols, hierarchy_cols, min_samples=5, get_hierarchical_stats=False); BaseData.handle_outliers / accessor handle_outliers add inplace
- **Input validation:** Target columns absent from df are skipped; hierarchy_cols str normalized to one-item list; empty/None hierarchy logs warning and returns copy; min_samples is deliberately NOT validated (tracked PD-02 strict xfails); missing named hierarchy column raises KeyError from groupby.
- **Main operations and collaborators:** Optional hierarchical stats computed from original df first (median default). Copy result; generator _hierarchical_outlier_masks evaluates full hierarchy then pops the last column per level; per level groupby([hierarchy cols], dropna=False, observed=True, sort=False), count>=min_samples validity, quantile([.25,.75]) mapped by group id; flags numeric < q1-1.5*IQR or > q3+1.5*IQR; masks applied with result.loc[outliers]=np.nan as the generator is consumed, so later levels see NaNs.
- **Data transformations:** Outlier values become np.nan; dtypes may upcast; shape/index/columns preserved.
- **Mutation and inplace behavior:** Standalone returns copy; BaseData/accessor inplace updates receiver via _update_inplace and returns None, or the stats frame when get_hierarchical_stats=True.
- **Return type and output-container behavior:** Frame, or (frame, statistics) when requested; statistics default-output type follows the receiver class (BaseData family supported).
- **Index / ordering / shape / dtype invariants:** Rows judged only at the most specific valid level; null hierarchy keys form groups; no merge-back; processed rows excluded later; missing target columns ignored.
- **State changes and cache effects:** None; stats computation is pure.
- **External side effects:** Logging warning only.
- **Error and recovery behavior:** KeyError for missing hierarchy column; pandas groupby/quantile errors propagate; invalid min_samples accepted silently (defect).
- **Relevant tests:** tests/modules/stats/test_outliers.py (including PD-02 xfails and min_samples boundary); tests/modules/stats/hierarchical_stats/test_hierarchical_stats_flags.py::test_hierarchy_stats_are_extracted_before_progressive_fill; tests/cross_cutting/equivalence/test_equivalence_outliers.py; tests/cross_cutting/contracts/test_properties.py::test_handle_outliers_properties
- **Uncovered cases:** min_samples validation (tracked defect); non-numeric target columns; generator/tuple hierarchy_cols; all-null hierarchy levels

### 16.10 drop_outliers (`F10`)

- **Entry point:** bynat.cleaning.stats.drop_outliers(df, *target_cols, hierarchy_cols, min_samples=5, get_hierarchical_stats=False); BaseData/accessor inplace variants
- **Input validation:** Same as handle_outliers: missing targets skipped, str hierarchy normalized, empty hierarchy warns/no drops, min_samples unvalidated, missing named hierarchy KeyError.
- **Main operations and collaborators:** Stats from original df when requested; copy result; accumulate drop_mask across every yielded (target,outliers) mask without mutating result between levels (so outliers stay in later quartiles); drop via result.iloc[np.flatnonzero(~drop_mask)].
- **Data transformations:** Row subset selected positionally; original index labels retained (not reset); columns/dtypes unchanged.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None/stats.
- **Return type and output-container behavior:** Filtered frame or (filtered_frame, statistics).
- **Index / ordering / shape / dtype invariants:** Outliers accumulated across all requested targets (any flag drops the row); positional drop makes duplicated index labels safe; no rows dropped when hierarchy empty.
- **State changes and cache effects:** None.
- **External side effects:** Warning log for empty hierarchy.
- **Error and recovery behavior:** KeyError missing hierarchy; pandas errors propagate; invalid min_samples silent.
- **Relevant tests:** tests/modules/stats/test_outliers.py; tests/cross_cutting/equivalence/test_equivalence_outliers.py::test_handle_and_drop_outliers_match_legacy; tests/cross_cutting/equivalence/test_equivalence_outliers.py::test_outlier_masks_do_not_merge; tests/cross_cutting/contracts/test_properties.py::test_drop_outliers_properties
- **Uncovered cases:** min_samples validation; interaction of duplicate index labels with get_hierarchical_stats; target column appearing twice

### 16.11 fill_missing (`F11`)

- **Entry point:** bynat.cleaning.stats.fill_missing(df, *target_cols, strategy='median', hierarchy_cols=None, min_samples=1, fallback_global=False, get_hierarchical_stats=False); BaseData/accessor inplace variants
- **Input validation:** min_samples first: int>=1, bool rejected, else ValueError. Then valid target columns; none -> warning + unchanged copy BEFORE strategy validation. Strategy lowercased; allowed median/mean/mode/mod; mod->mode; invalid -> ValueError. Hierarchy str normalized; missing hierarchy columns ignored.
- **Main operations and collaborators:** Copy result; optional stats from original df with requested strategy. Per column: progressively pop hierarchy levels; median/mean via groupby(current_group, dropna=False)[col].transform(strategy) masked by transform('count')>=min_samples; mode via grouped counts of non-null values sorted by hierarchy asc + count desc, group totals >= min_samples, drop_duplicates, left_merge_aligned by position. fallback_global uses column-wide df statistic (median/mean) or global mode; unfilled remain NaN.
- **Data transformations:** NaN cells filled in result copy; dtypes may change; index/order/columns preserved; mode tie order depends on a non-stable sort (default quicksort) here.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None or stats.
- **Return type and output-container behavior:** Imputed frame or (imputed_frame, statistics).
- **Index / ordering / shape / dtype invariants:** Statistics come from df itself (documented leakage caveat); groups below min_samples fall through; hierarchy=None + fallback_global=False performs no imputation; index preserved.
- **State changes and cache effects:** None.
- **External side effects:** Warnings for no valid targets; logging only.
- **Error and recovery behavior:** ValueError strategy/min_samples; TypeError propagates from pandas for non-numeric targets under numeric strategy; no-valid-target invalid strategy does not raise (see discrepancy).
- **Relevant tests:** tests/modules/stats/test_fill_missing.py; tests/modules/stats/hierarchical_stats/test_hierarchical_stats_flags.py; tests/cross_cutting/workflows/fill_missing_from/test_fill_missing_from_imputation.py::test_existing_fill_missing_remains_unchanged; tests/cross_cutting/contracts/test_properties.py::test_fill_missing_properties
- **Uncovered cases:** Invalid strategy combined with zero valid target columns; mode tie determinism across platforms; fallback_global with non-numeric target without hierarchy (raises TypeError, tested) vs with hierarchy; duplicate target column names

### 16.12 fill_missing_from (`F12`)

- **Entry point:** bynat.cleaning.stats.fill_missing_from(df, dataset, *target_cols, match_cols=None, targets=None, strategy='median', hierarchy_cols=None, min_samples=1, fallback_global=False, get_hierarchical_stats=False); BaseData/accessor inplace variants
- **Input validation:** Ordered: dataset None/empty/duplicate columns; df duplicate columns; match_cols dict/str keys+values/existence in both frames; strategy; min_samples; resolved reference columns; hierarchy existence in both frames; target/hierarchy overlap; numeric dtype checks for median/mean (reference and non-all-NaN target).
- **Main operations and collaborators:** Flatten target_cols one level (list/tuple/set elements), append targets (str or Iterable), dedupe first-seen. Compute stats exclusively from dataset: median/mean groupby(ref hierarchy)+agg masked by count>=min_samples; mode grouped counts sorted ref-hierarchy asc + count desc, drop_duplicates, rename mapped ref->target, left_merge_aligned. Optional stats computed from dataset then reverse-mapped to target spellings. Reference is never written.
- **Data transformations:** Result copy; only NaN target cells filled; target index/order and existing values preserved; match_cols renames reference columns for lookup and unmaps stats labels.
- **Mutation and inplace behavior:** Standalone neither df nor dataset modified; inplace updates receiver only and returns None/stats.
- **Return type and output-container behavior:** Imputed frame or (imputed_frame, statistics); no targets -> copy, stats empty schema when requested.
- **Index / ordering / shape / dtype invariants:** Leakage-free statistics (property-tested); hierarchy=None+fallback_global=True is plain reference column-wide imputation; min_samples counts non-null reference observations; hierarchy cols must exist in both frames.
- **State changes and cache effects:** None.
- **External side effects:** Warnings for no valid targets; logging only.
- **Error and recovery behavior:** ValueError dataset/columns/strategy/min_samples/overlap; TypeError dataset/match_cols/dtype; reference lookup errors propagate from pandas.
- **Relevant tests:** tests/cross_cutting/workflows/fill_missing_from/test_fill_missing_from_contracts.py; tests/cross_cutting/workflows/fill_missing_from/test_fill_missing_from_imputation.py; tests/cross_cutting/workflows/fill_missing_from/test_fill_missing_from_leakage.py; tests/modules/stats/test_stats_inplace.py
- **Uncovered cases:** Flattening nested specs deeper than one level (raises TypeError); many-to-one match_cols collisions in stats reverse mapping; targets supplied as a dict; empty df with get_hierarchical_stats

### 16.13 extract_keywords (optional Aho-Corasick) (`F13`)

- **Entry point:** bynat.cleaning.text.extract_keywords(df, *source_cols, remove_extracted=False, use_regex=False, **target_cols_and_keywords); BaseData/accessor variants with inplace
- **Input validation:** No keyword validation; str/bytes/non-iterable keyword values wrapped as one-item list; blank/None keywords stripped and dropped; empty cleaned list skips the target; missing source columns ignored; no valid sources -> unchanged copy.
- **Main operations and collaborators:** Combine valid source columns fillna('').astype(str) with ' '; factorize combined text. Literal path: combined lookaround regex (?<!\w)(?:k1\|k2...)(?!\w) IGNORECASE, or pyahocorasick automaton when installed AND every keyword is ASCII, with per-text isascii gate; priority = keyword list order. Regex path: compile each pattern, wrap groupless patterns in (...), Series.str.extract first capture group, highest-priority pattern wins. Title-case results; existing target column filled only where NaN; remove_extracted applies patterns once per unique text and collapses whitespace.
- **Data transformations:** New columns appended; existing target column's non-null values are also title-cased; source columns optionally rewritten; row count/index unchanged.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None.
- **Return type and output-container behavior:** Frame of same family as df; extracted columns object/string dtype with NaN where unmatched.
- **Index / ordering / shape / dtype invariants:** Whole-word literal matching treats underscore as a word character (_is_ascii_word_char); literal and Aho-Corasick paths agree (equivalence-tested with the real automaton); first keyword in list wins; Unicode keywords force regex path.
- **State changes and cache effects:** None.
- **External side effects:** re.error for invalid regex; no dependency error when pyahocorasick is absent (silent fallback).
- **Error and recovery behavior:** Regex compile errors propagate; missing dependency silently falls back.
- **Relevant tests:** tests/cross_cutting/equivalence/test_equivalence_keywords.py::test_extract_keywords_aho_corasick_and_regex_paths_agree; tests/cross_cutting/equivalence/test_equivalence_keywords.py::test_extract_keywords_literal_matches_legacy; tests/cross_cutting/equivalence/test_equivalence_keywords.py::test_extract_keywords_overlapping_keywords_respect_priority; tests/modules/text/test_text.py; tests/modules/text/test_text_inplace.py
- **Uncovered cases:** Duplicate keywords; invalid regex error type/message; existing-column title-casing side effect; keywords that are empty after stripping alongside valid ones

### 16.14 categorize_by_reference (required Aho-Corasick) (`F14`)

- **Entry point:** bynat.cleaning.text.categorize_by_reference(df, *source_cols, target_col, reference, default_category='Other'); BaseData/accessor variants
- **Input validation:** Missing source columns ignored; no valid sources -> unchanged copy before reference handling. reference non-dict/empty -> target_col=default_category for all rows. Keyword values non-list wrapped; blank/None ignored; none valid -> default category. Requires pyahocorasick via _import_optional (ImportError naming pyahocorasick).
- **Main operations and collaborators:** Combine source columns fillna('').astype(str) with ' '; build automaton with (length, reversed-category priority, category); whole-word boundary check uses str.isalnum() only; longer keyword wins, equal length later reference category wins; map each unique text once.
- **Data transformations:** Adds or overwrites target_col with category strings; row count/index unchanged.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None.
- **Return type and output-container behavior:** Frame of same family; target column object dtype.
- **Index / ordering / shape / dtype invariants:** Case-insensitive; automaton cache-free per call; default_category applied on no match; underscore is NOT treated as a word character despite the docstring claiming score does not match under_score.
- **State changes and cache effects:** None.
- **External side effects:** ImportError when pyahocorasick missing; no other I/O.
- **Error and recovery behavior:** ImportError; no regex fallback by design; non-dict reference treated as empty.
- **Relevant tests:** tests/modules/enrichment/optional/test_optional_ahocorasick.py (longest match, word boundaries/case, multi-source, overwrite, blanks, real automaton, missing dependency)
- **Uncovered cases:** Underscore boundary case (implementation matches inside under_score); non-list dict keyword value iteration; no valid sources combined with invalid reference (returns copy without target column)

### 16.15 extract_entities_nlp (optional spaCy) (`F15`)

- **Entry point:** bynat.cleaning.enrich.nlp.extract_entities_nlp(df, *source_cols, lexicon_source, spacy_model='en_core_web_sm', exclude_pos=None, disable=('parser','ner'), save_every=1000, noisy_terms=None, cache_manager, **target_cols_and_json_keys); BaseData/accessor variants
- **Input validation:** Order: 'noisey_terms' typo -> TypeError; disable normalization (None/str/iterable of str, empties rejected, required pipes tok2vec/tagger/attribute_ruler/lemmatizer/morphologizer rejected); noisy_terms lowercased; exclude_pos uppercased; save_every positive int; at least one target kwarg; lexicon file/dict loaded; terms extracted; none -> ValueError; valid source columns else copy; non-empty texts else copy; spacy_model non-str/blank ValueError. spaCy imported lazily only when there is at least one uncached text.
- **Main operations and collaborators:** Bucket sha1(target_col, model_identifier, sorted(disable))[:16] prefixed nlp_. start() imports spacy + spacy.matcher, loads model, warns unknown disable components, builds Matcher patterns (LEMMA IN [lemma.lower(), lemma.title()] and LOWER text). extract() pipes texts batch_size=100, collects title-cased lemma spans into sets, rejects single-char non-uppercase/non-alpha, excluded POS for single tokens, noisy terms; _cached_map(fetch_many) checkpoints every save_every.
- **Data transformations:** New object columns of entity lists; empty-string rows get []; row count/index unchanged.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None.
- **Return type and output-container behavior:** Frame with appended list-valued columns; ordering within each list derives from set iteration and is not guaranteed.
- **Index / ordering / shape / dtype invariants:** Cache isolated by target/model/disable; required pipes cannot be disabled; unknown pipes warn and continue; no valid terms/config raises before loading spaCy.
- **State changes and cache effects:** Writes nlp_<hash> buckets through the manager; DB/schema may be initialized by get_column_cache before the spaCy import attempt.
- **External side effects:** Loads a local spaCy model; no network.
- **Error and recovery behavior:** ImportError naming spacy; OSError from spaCy model load; ValueError/TypeError config; per-text matcher exceptions captured as outcomes and left uncached by _cached_map.
- **Relevant tests:** tests/modules/enrichment/nlp/test_nlp.py (disable configs/cache isolation, noisy terms, required/unknown components, bad configuration, noisey spelling); tests/modules/enrichment/nlp/test_nlp_inplace.py
- **Uncovered cases:** Real spaCy model execution (spacy absent from the environment); output list ordering determinism; fully cached run with spaCy uninstalled; exclude_pos with multi-token matches

### 16.16 convert_to_usd (`F16`)

- **Entry point:** bynat.cleaning.enrich.currency.convert_to_usd(df, *target_cols, country_col, year_col, new_cols=True, round_decimals=None, provider=None, cache_manager); BaseData/accessor variants
- **Input validation:** Required country/year columns else warning + copy; valid target columns else warning + copy; empty frame -> copy; pycountry and babel.numbers imported eagerly; provider constructed (default YFinanceRateSource imports yfinance); unique country/year pairs drop_duplicates().dropna(); numeric years via to_numeric; if no valid years/pairs -> copy; min_year_limit = earliest numeric year in data; current year = localtime year.
- **Main operations and collaborators:** Currency cache via _cached_map over unique stripped countries using pycountry.countries.search_fuzzy(...)[0] and Babel get_territory_currencies(alpha_2)[0]; LookupError cached as None. exchange_rates bucket: determine missing rate keys by walking lookback range(year, min_year_limit, -1); fetch one yearly_rates call per currency covering min..max missing years; store float rates, store None misses only for years < current_year. Build (country,year)->rate mapping (USD=1.0), left_merge_aligned onto result, divide value/rate, optional round.
- **Data transformations:** New '<col>_usd' columns (float) appended when new_cols=True, else originals overwritten; unknown currency/year -> NaN; input df untouched.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None.
- **Return type and output-container behavior:** Frame of same family; converted columns float with NaN where no rate.
- **Index / ordering / shape / dtype invariants:** Rate is local currency per 1 USD (divide); one provider call per currency; USD rows divide by 1.0 without lookup; network/provider failures not cached; past-year misses cached; future-year misses re-fetched.
- **State changes and cache effects:** Caches buckets 'currency_codes' and 'exchange_rates' under func_name 'convert_to_usd'; save_function_cache called only when cache_updated.
- **External side effects:** pycountry/Babel local lookups; Yahoo Finance download via provider unless overridden.
- **Error and recovery behavior:** ImportError naming pycountry/Babel/yfinance; provider exceptions caught per currency, logged, not cached; missing columns/no targets return unchanged copy.
- **Relevant tests:** tests/modules/enrichment/currency/test_currency.py; tests/modules/enrichment/currency/test_currency_inplace.py; tests/cross_cutting/equivalence/test_equivalence_enrichment.py::test_perf01_convert_to_usd_matches_legacy
- **Uncovered cases:** Requested year earlier than the earliest year in the data (lookback range empty); future-year miss caching; all-USD data still importing yfinance via default provider; round_decimals negative/None combinations

### 16.17 fill_missing_coordinates (`F17`)

- **Entry point:** bynat.cleaning.enrich.geocode.fill_missing_coordinates(df, *fallback_cols, lat_col, long_col, save_every=1000, user_agent='data_cleaning_core_geocoder', retry_not_found=False, provider=None, cache_manager); BaseData/accessor variants
- **Input validation:** save_every positive int first (ValueError); required lat/long columns else warning + copy; at least one valid fallback column else warning + copy.
- **Main operations and collaborators:** Copy result; build '__temp_geocode_query__' from fallback columns joined ', ' skipping null/empty/'nan'/'none'/numeric values; mask_missing = lat or long isna; unique queries; provider lazily NominatimGeocoder(user_agent) or injected; geocode(query) tries the query then repeatedly drops the leftmost comma-separated part; returns tuple(lat,long) or None; _cached_map bucket 'geocode_queries' key=str, is_cached treats cached None as miss only when retry_not_found; checkpoint every save_every. Map coordinates, update only missing lat/long cells, drop temp column.
- **Data transformations:** Latitude/longitude cells filled with floats; existing valid coordinates preserved; helper column always removed; row count/index unchanged.
- **Mutation and inplace behavior:** Standalone copy; inplace updates receiver and returns None.
- **Return type and output-container behavior:** Frame of same family; coordinate columns may upcast to float/object depending on assignment.
- **Index / ordering / shape / dtype invariants:** Not-found queries cached as None; network/service exceptions uncached; failed queries shorten left-to-right; query build order follows fallback_cols.
- **State changes and cache effects:** Bucket 'geocode_queries' under func_name 'fill_missing_coordinates'; SQLite initialized by get_column_cache before the geopy import attempt.
- **External side effects:** Nominatim requests rate-limited to 1/s via geopy; user_agent configurable.
- **Error and recovery behavior:** ImportError naming geopy when no provider; provider exceptions caught per query by _cached_map and left uncached; no raise for not-found.
- **Relevant tests:** tests/modules/enrichment/geocode/test_geocode.py (provider injection, Nominatim construction/default, save_every validation, shortening/caching misses, errors not cached); tests/modules/enrichment/geocode/test_geocode_inplace.py
- **Uncovered cases:** retry_not_found=True end-to-end behavior; mixed lat-present/long-missing asymmetry with non-string fallback cells; duplicate identical queries; provider returning malformed coordinates

### 16.18 Analyzer methods (`F18`)

- **Entry point:** bynat.analytics.analyzer.Analyzer(dataframe); get_categorical_distribution, get_numerical_aggregation, get_time_series, get_kpi_value, get_bins
- **Input validation:** Constructor TypeError for non-DataFrame; defensive copy. Filters: scalar equality, list isin, dict operators (>,<,>=,<=,!=,==,contains); comparisons >,<,>=,<= coerce with pd.to_numeric, ==/!= compare raw; unknown columns ignored; invalid operations logged/skipped. Rules: where/set_col/set_value, new_col/expression, source_col/method/new_col; _is_safe_expression blocks __, @, import, lambda, ; case-insensitively. bins rejects bool/non-int/<=0.
- **Main operations and collaborators:** _apply_filters -> _apply_computed_rules -> pandas aggregations; categorical uses value_counts desc; numerical drops null y, groupby(observed=True).agg, rounds numeric, sorts desc, recomputes Others from underlying rows; time series parses dates with errors='coerce', tz-naive, buckets M/Y/H/daily, reindexes full range filling 0; KPI count or column agg with scalar/rounding/int normalization; bins uses np.histogram with two-decimal labels.
- **Data transformations:** Always works on copies; responses built as {'data': ...} plus kwargs; get_kpi_value returns {'data','title',...}.
- **Mutation and inplace behavior:** No mutation of the constructor frame or method inputs.
- **Return type and output-container behavior:** Plain JSON-serializable dicts; empty conventions {'data': []} or {'data': None, 'title': ...}.
- **Index / ordering / shape / dtype invariants:** top_n/show_others collapse with is_others and others_breakdown; others values recomputed from rows; proportions relative to filtered data; time-series x ascending; filters applied in mapping order.
- **State changes and cache effects:** None.
- **External side effects:** Warnings via logging.getLogger('bynat.analytics.analyzer').
- **Error and recovery behavior:** Aggregation/filter/rule failures logged and skipped or returned as empty payloads; eval guard prevents risky expressions.
- **Relevant tests:** tests/modules/analytics/test_analytics_contract.py; tests/modules/analytics/test_analytics_distributions.py; tests/modules/analytics/test_analytics_filters_rules.py; tests/modules/analytics/test_analytics_series_kpi_bins.py
- **Uncovered cases:** orient values other than records in depth; timezone-aware time-series transitions; KPI numpy float32 handling; show_others when top_n >= category count; rules using method= on non-callable attributes

### 16.19 profiling and output_type adaptation (`F19`)

- **Entry point:** bynat.profiling.profile.profile(df, *columns, output_type=None); BaseData.profile(*columns, output_type=None) and module-level accessor profile(df, *columns, output_type=None) intercept BaseData-family output types
- **Input validation:** Core: df isinstance pd.DataFrame else TypeError; a single collection argument may be list/tuple/set; missing named column KeyError. Dispatch: None/ProfileReport -> report; dict -> report.to_dict(); pd.DataFrame -> report.to_dataframe(); anything else TypeError. BaseData/accessor profile pre-check is_basedata_type(output_type) and constructs output_type(data=summary_frame).
- **Main operations and collaborators:** Dataset metrics (row/column/total cells, missing count/proportion, duplicate rows keep='first', empty columns, deep memory, dtype counts); per-column kind detection and numeric/categorical/boolean/datetime/other statistics; unhashable normalization via _internal.dedupe_key; ProfileReport/DatasetProfile/ColumnProfile dataclasses.
- **Data transformations:** Summary dataframe one row per profiled column with stat_-prefixed flattened stats; dict/attribute access mapping protocol.
- **Mutation and inplace behavior:** Never mutates input, index, or column names.
- **Return type and output-container behavior:** ProfileReport \| dict \| pd.DataFrame \| requested BaseData subclass.
- **Index / ordering / shape / dtype invariants:** Column metrics relative to selected subset; duplicate keep='first'; std None for n<2; outliers_count None for n<5; columns dict last-wins on duplicate names while column_list preserves positions; memory 0 when measurement fails; all values native primitives.
- **State changes and cache effects:** None; profile is read-only.
- **External side effects:** None.
- **Error and recovery behavior:** TypeError for bad input/output_type; KeyError for missing column; statistics fall back to None on failure.
- **Relevant tests:** tests/modules/profile/test_profile_general.py; tests/modules/profile/test_profile_edges.py; tests/modules/profile/test_profile_contract.py; tests/cross_cutting/accessor/test_accessor_profile.py; tests/modules/profile/test_profiling_package_boundary.py
- **Uncovered cases:** Explicit output_type=ProfileReport test; Non-BaseData custom output_type error message; memory_usage failure fallback; single-string collection selection ambiguity

### 16.20 Optional-dependency failure behavior (cross-cutting) (`F20`)

- **Entry point:** bynat.cleaning._common.import_optional(module_name, distribution, feature); provider constructors in cleaning/enrich/providers.py; _cached_map(on_fetch_start=...)
- **Input validation:** Failures are deferred to method use. Hard-required at call: categorize_by_reference -> pyahocorasick; extract_entities_nlp -> spacy/spacy.matcher; impute_by_language and translate_conditional_column -> langdetect; fill_missing_coordinates -> geopy when no provider; convert_to_usd -> pycountry/Babel and yfinance when no provider; save_to_sql -> SQLAlchemy after argument validation. Soft/optional: extract_keywords -> pyahocorasick with silent regex fallback.
- **Main operations and collaborators:** import_optional wraps ImportError as ImportError('<feature> requires the optional '<distribution>' dependency.') chaining the original. Providers import deep_translator/geopy.geocoders/geopy.extra.rate_limiter/yfinance in their constructors. _cached_map calls on_fetch_start(total) only when uncached work exists, and exceptions from it propagate to the caller.
- **Data transformations:** None before import; failures do not mutate frames.
- **Mutation and inplace behavior:** Failures occur before any result is produced; inplace=True validation happens first but no mutation occurs on failure.
- **Return type and output-container behavior:** Raises ImportError; no partial frame returned.
- **Index / ordering / shape / dtype invariants:** Import errors name the extra to install; validation errors precede dependency imports where the code checks first (save_to_sql arguments, fill_missing_coordinates save_every, NLP disable/save_every/target/lexicon config, translate_conditional threshold/sample sizes).
- **State changes and cache effects:** Cached methods call get_column_cache (initializing SQLite) before constructing the provider/model in on_fetch_start, so a missing geopy/spacy/deep-translator can still create the cache directory/database even though no lookup occurs. convert_to_usd imports pycountry/Babel before any cache access.
- **External side effects:** None after a missing-dependency failure beyond possible SQLite initialization.
- **Error and recovery behavior:** Callers can inject provider= to bypass default imports; extract_keywords needs no fallback action; no automatic retry.
- **Relevant tests:** tests/modules/enrichment/optional/test_optional_ahocorasick.py::test_optional_categorization_reports_missing_dependency_at_method_use; tests/modules/enrichment/optional/test_optional_sqlalchemy.py::test_save_to_sql_reports_missing_sqlalchemy_dependency; tests/modules/enrichment/nlp/test_nlp.py::test_extract_entities_nlp_raises_for_bad_configuration; tests/modules/enrichment/translate/test_translate_batch.py::test_optional_integration_reports_missing_dependency_at_method_use; tests/modules/enrichment/translate/test_translate_conditional.py::test_translate_conditional_missing_langdetect_raises_documented_import_error; tests/modules/enrichment/geocode/test_geocode.py; tests/modules/enrichment/currency/test_currency.py
- **Uncovered cases:** SQLite-created-before-provider-import side effect; provider constructor ImportError chaining text; save_to_sql validation with a mocked sqlalchemy present but broken; hard-required dependency failures combined with inplace=True (class API test exists for variadic inplace failures)

## 17. Implementation–Documentation Discrepancies and Test Gaps

These are behavioral/correctness findings, not architectural defects. They are recorded for follow-up and are not part of the structural target.

### 17.1 Implementation–documentation discrepancies

Reported as discrepancies, not silently resolved. Each was verified against source by the supervisor.
1. README.md (extract_entities_nlp section) says the misspelled `noisey_terms` name remains as a separate deprecated compatibility alias for `noisy_terms`; the implementation raises TypeError for `noisey_terms` in both bynat/cleaning/enrich/nlp.py (lines 220-224) and bynat/cleaning/base.py (lines 1920-1924), CHANGELOG 0.3.0 says it was removed, and tests assert rejection (tests/modules/enrichment/nlp/test_nlp.py::test_extract_entities_nlp_rejects_the_noisey_terms_spelling).
2. categorize_by_reference docstrings claim matching is restricted to whole words so 'score' does not trigger on 'under_score'; the automaton boundary check uses str.isalnum() only (bynat/cleaning/text.py lines 508 and 511), so '_' is not treated as a word character and 'score' DOES match inside 'under_score'. Verified with the real pyahocorasick package (result ['X','X'] for texts ['under_score','score']); no test covers the underscore case.
3. extract_keywords docstrings say repeated calls into the same target column 'will NEVER overwrite previously extracted values'; implementation fills only NaN cells but then applies .str.title() to every non-null cell of that column (bynat/cleaning/text.py lines 281-289), rewriting existing values (verified: 'kept' became 'Kept'). The documented non-destructive-update contract is therefore stronger than the behavior.
4. get_hierarchical_stats docstring says a signature-incompatible default subclass falls back to a plain pandas.DataFrame; only BaseData-family subclasses reach the constructor-acceptance check because validate_output_type(type(df)) runs first (bynat/cleaning/stats.py lines 884-887) and raises TypeError for any other pandas.DataFrame subclass (verified: a custom non-BaseData subclass raised TypeError instead of falling back).
5. fill_missing docstring lists ValueError for an unknown strategy unconditionally; implementation validates the strategy only after the no-valid-target-columns early return (bynat/cleaning/stats.py lines 346-363), so fill_missing(df, 'missing_col', strategy='bogus') logs a warning and returns an unchanged copy instead of raising (verified).
6. fill_missing_from docstring says nested lists/tuples/sets in target_cols are flattened; implementation flattens exactly one level (bynat/cleaning/stats.py lines 618-631), so a doubly nested spec such as [['salary'], 'bonus'] leaves a list element and raises TypeError ('cannot use list as a dict key') (verified).
7. JsonFile/CsvFile class docstrings say a path-like data that does not exist raises FileNotFoundError; when an explicit json_file_path/csv_file_path is also supplied, the path-existence branch is skipped and the string reaches pandas, raising ValueError('DataFrame constructor not properly called!') instead (bynat/cleaning/base.py lines 2148-2160 and 2220-2232; verified).
8. categorize_by_reference docstring says a non-dictionary or empty reference assigns default_category to every row; implementation returns an unchanged copy before touching reference whenever no source columns are valid (bynat/cleaning/text.py lines 445-449), so target_col is not created in that combination (verified).
9. Analyzer._apply_filters docstring says comparison operators coerce both sides with pd.to_numeric; implementation applies numeric coercion only to >, <, >=, <= and compares == and != raw (bynat/analytics/analyzer.py lines 138-151).
10. save_to_sql docstring says credentials are URL-encoded before being placed in the connection URL; only database_user, database_password, and the SQL Server driver are quote_plus-encoded, while host, port, and database_name are interpolated raw (bynat/cleaning/io.py lines 353-368).
11. README/base documentation state that BaseData shares its CacheManager with every derived frame, but the cache directory (_bynat_cache_dir) is not pandas metadata; after clearing a derived frame's manager, recreation uses BYNAT_CACHE_DIR/default instead of the parent's custom directory (bynat/cleaning/base.py lines 81, 119-120, 138-144; verified).
12. README says Aho-Corasick is used for ASCII text when pyahocorasick is installed; the actual gate also requires every keyword to be ASCII (bynat/cleaning/text.py line 52), so a keyword list containing any non-ASCII term always uses the regex path even for ASCII text.

### 17.2 Test coverage gaps

1. Tracked defect PD-02: handle_outliers/drop_outliers do not validate min_samples; pinned by 12 strict xfail tests in tests/modules/stats/test_outliers.py (bool/0/negative/float/string values are accepted).
2. Tracked defect PD-01: standalone variadic functions (extract_keywords, truncate_after_substring, split_list_objects, melt_transform_pivot) absorb an unexpected inplace keyword into **kwargs; pinned by strict xfails in tests/cross_cutting/contracts/test_tracked_defects.py.
3. categorize_by_reference underscore word-boundary behavior is untested, leaving the docstring/implementation contradiction undetected by the suite.
4. extract_keywords title-casing of pre-existing target-column values on repeated calls is untested and contradicts the documented non-destructive-update note.
5. fill_missing invalid-strategy behavior when no target column exists is untested (early return precedes validation).
6. fill_missing_from flattening deeper than one nesting level is untested (raises unhashable-list TypeError).
7. get_hierarchical_stats default output for a non-BaseData pandas.DataFrame subclass is untested; it raises TypeError rather than the documented fallback.
8. Clearing a derived BaseData frame's cache_manager and observing the cache directory reset to env/default is untested.
9. Real optional integrations are absent from the default environment: spacy, deep-translator, langdetect, geopy, pycountry, Babel, and yfinance are not installed; CI's extras job installs only categorization and sql per README, so spaCy/NLP, translation, geocoding, and currency paths are exercised only with monkeypatched fakes, and save_to_sql real coverage is SQLite-only.
10. extract_entities_nlp output list order derives from set iteration and has no deterministic-order test or documented ordering contract.
11. convert_to_usd edge cases are untested: requested year earlier than the earliest year in the data, future-year miss caching, and all-USD data still importing yfinance through the default provider.
12. save_to_json edge cases untested: zero-byte existing file with append=True (raises rather than writing), non-ValueError read failures during append, and bytes file_path.
13. profiling edge cases untested: explicit output_type=ProfileReport, custom unsupported output_type error text, and memory_usage failure fallback.
14. Cache value type normalization across save/load (for example tuple becoming list after JSON round-trip) is not asserted by tests.
15. fill_missing vs get_hierarchical_stats mode tie-breaking use different sort stability (default quicksort vs mergesort); cross-platform determinism is untested.

### 17.3 `BaseData.cache_dir` lifecycle resolution

**Verified behavior (runtime probe at the baseline commit).**

| Step | Observed |
|---|---|
| `BaseData(data, cache_dir=custom)` | `_bynat_cache_dir = custom`; manager directory = `custom` |
| `derived = df[["a"]]` | `type(derived) is BaseData`; `derived._bynat_cache_dir is None`; `derived.cache_manager is df.cache_manager` (shared); manager directory = `custom` |
| `derived.cache_manager = None` | next access rebuilds with `cache_dir=None` → `BYNAT_CACHE_DIR`/default; manager directory = env/default |

**Classification: missing behavioral contract requiring an explicit decision.** The implementation is internally consistent: `_metadata = ['cache_manager']` propagates the manager object, while `_bynat_cache_dir` is not metadata, so a derived frame never carries the originating custom directory. The documented promise is that the *manager* is shared with derived frames, which holds; no document states that the custom directory survives an explicit manager clear or replace on a derived frame.

**Precise open question.** When a derived `BaseData` frame's `CacheManager` is explicitly cleared or replaced, should the recreated manager inherit the originating frame's custom `cache_dir`, or is the `BYNAT_CACHE_DIR`/default directory the intended result?

**Options once a decision is made.**
- Treat as intentional: document that clearing a derived frame's manager resets to the environment/default directory.
- Treat as a defect: propagate `_bynat_cache_dir` through pandas metadata (add it to `_metadata`) so recreation inherits the originating directory. Acceptance criterion: after `derived.cache_manager = None`, `derived.cache_manager.cache_dir_path` equals the originating frame's `cache_dir`.

No code change is made in this review. The question is recorded as AE-Q6 in §25.

## 18. Shared Component Ownership

| Component | Canonical owner | Consumers | Import direction | Decision |
|---|---|---|---|---|
| `dedupe_key` | `_internal/values.py` | `cleaning.io`, `profiling.profile` | functional → `_internal` | Keep canonical |
| cleaning helpers | `cleaning/_common.py` | cleaning modules, enrichment | cleaning-internal | Keep; remove alias layer |
| output conversion | `cleaning/_outputs.py` | `stats`, `base`, `_accessors` | cleaning-internal + accessor | Keep; remove alias layer |
| cached lookup | `cleaning/enrich/engine.py` | enrichment features | enrich-internal | Keep |
| provider contracts | `cleaning/enrich/providers.py` | enrichment features, facades | enrich-internal + facade | Keep |
| cache-key identity | `caching/_keys.py` | `cleaning.enrich.engine`, `cleaning.enrich.translate` | documented private edge | Keep in caching |
| SQLite persistence | `caching/_storage.py` | `manager`, `_migration` | caching-internal | Keep |
| legacy migration | `caching/_migration.py` | `manager` | caching-internal | Keep |
| cache facade/registry | `caching/manager.py` | cleaning, accessor | functional → caching | Keep |
| report models | `profiling/report.py` | `profiling.profile` | profiling-internal | Keep |
| profiling core | `profiling/profile.py` | `base`, accessor | facade → profiling | Keep |
| analytics engine | `analytics/analyzer.py` | analytics public API | none | Keep |
| accessor binding | `_accessors/_binding.py` | `_accessors.dataframe` | accessor-internal | Keep |

**Ownership rule.** Consumer count is evidence of reuse, not proof of ownership. A shared component belongs where its invariants and change reasons are owned. Similar code with different contracts is not merged.

---

## 19. Integration and Optional Dependency Design

| Extra | Optional packages | Import site | Lazy? | Boundary |
|---|---|---|---|---|
| `translation` | `deep-translator`, `langdetect` | `enrich/providers.py`, `enrich/translate.py` | Yes (`import_optional`) | provider protocol |
| `geocoding` | `geopy` | `enrich/providers.py` | Yes | provider protocol |
| `currency` | `Babel`, `pycountry`, `yfinance` | `enrich/currency.py`, `enrich/providers.py` | Yes | provider protocol |
| `categorization` | `pyahocorasick` | `cleaning/text.py` | Yes | internal matcher |
| `nlp` | `spacy` | `enrich/nlp.py` | Yes | provider/lexicon |
| `sql` | `SQLAlchemy` | `cleaning/io.py` | Yes | I/O boundary |

**Decisions:**
- Optional imports stay function-local through `import_optional`, which raises a feature-specific `ImportError` naming the distribution.
- External services are behind `provider=` protocols in `enrich/providers.py`; no plugin discovery or entry points.
- `save_to_sql` remains in `cleaning/io.py`; the optional dependency is already isolated by the lazy import, so a separate module would be fragmentation.
- No integration framework, DI container, or registry is introduced.

---

## 20. Internal Interfaces and Lifecycle

### 20.1 Interfaces

| Interface | Kind | Consumers | Reason |
|---|---|---|---|
| `CacheManager` | class | cleaning, accessor, enrichment | SQLite lifecycle, baselines, shared registry |
| `Analyzer` | class | analytics public API | defensive copy + response workflow |
| `BaseData`/`JsonFile`/`CsvFile` | classes | public class API | `DataFrame` subclass, metadata, `inplace` contracts |
| `BynatAccessor` | class | pandas registration | pandas registration requires a class |
| `Translator`/`Geocoder`/`RateSource` | protocols | enrichment + `provider=` | structural external-service contracts |
| report models | dataclasses | profiling public API | structured report contracts |
| `SQLiteStorage` | class | manager, migration | connection/schema/diff ownership |

### 20.2 Lifecycle and state

| Resource | Owner | Creation | Disposal/cleanup |
|---|---|---|---|
| SQLite database/connection | `CacheManager` + `SQLiteStorage` | Lazy on first access | Per-operation connection closed; `BEGIN IMMEDIATE`; WAL; busy timeout |
| Shared manager registry | `shared_cache_manager` | First request per resolved directory | Process-wide, thread-safe, never evicted |
| `BaseData` cache manager | `BaseData` | Lazily on first cached call | Stored in instance metadata; setter clears |
| Accessor cache manager | `BynatAccessor` | Lazily on first cached call | Held by reference; `with_cache(...)` binds another |
| File handles | `read_json`, `read_csv` | Context manager | Closed by `with` |
| SQLAlchemy engine | `save_to_sql` | Per call | `engine.dispose()` in `finally` |
| Provider resources | provider instances | Per call / thread-local | Thread-local translators; rate limiter per provider |

No manager, registry, or container is introduced beyond `shared_cache_manager`, which has a demonstrated lifecycle responsibility.

---

## 21. Rejected Patterns and Structures

| Pattern/structure | bynat-specific decision | Reason |
|---|---|---|
| Microservices / separate deployables | Reject | One small installable library; no distribution requirement |
| Generic repository pattern | Reject | No domain-model persistence; cache storage is a key-value contract |
| Universal managers | Reject | Only `CacheManager` has a demonstrated lifecycle |
| Base classes for unrelated operations | Reject | No shared algorithm hierarchy; composition is used instead |
| Generic `_shared` package | Reject | Only one domain-independent helper exists; it lives in `_internal` |
| Protocol proliferation | Reject | Only the three provider protocols have consumers |
| Plugin registry / entry points | Reject | No third-party plugin requirement |
| Excessive wrapper modules | Reject | Facades are limited to `BaseData` and the accessor |
| Artificially strict layers | Reject | Layering is a dependency rule, not a directory tree |
| Generic transformation engine | Reject | Transformations are explicit functions; only the enrichment cached-lookup loop is shared |
| Duplicate implementations of shared behavior | Reject | Single canonical helper per responsibility; alias layer removed |
| Polars-style lazy execution layer | Reject | No lazy/optimized execution requirement |
| `fit`/`transform` estimator layer | Reject | bynat transformations are stateless functions |
| Entry-point plugin discovery | Reject | No external plugin surface |
| Splitting `base.py`/`stats.py`/`analyzer.py` by LOC | Reject | Cohesive; size is documentation or one domain |

---

## 22. Architecture Enforcement Strategy

### 22.1 Rules

| ID | Rule |
|---|---|
| AR-1 | Root `__all__` is exactly `['cleaning', 'caching', 'analytics', 'profiling', 'read_csv', 'read_json']` |
| AR-2 | Package `__all__` values are exact and non-underscore |
| AR-3 | Dependency directions follow §13; prohibited edges are absent |
| AR-4 | No functional package imports `_accessors` |
| AR-5 | `_internal` imports only stdlib and NumPy |
| AR-6 | `profiling` imports no functional package or `_accessors` |
| AR-7 | `analytics` imports no other `bynat` package |
| AR-8 | `_accessors` contains no domain algorithms (delegation only) |
| AR-9 | Cross-package private-module imports are exactly the five documented edges in §13.3; no others exist |
| AR-10 | No row-wise iteration in data paths |
| AR-11 | Every module declares `__all__` (verified: all 31 `.py` modules; `_accessors/_binding.py` uses an annotated `__all__: list[str] = []`) |

### 22.2 Mechanisms

**Now (no new dependency):** existing contract tests plus a proposed AST contract test `tests/cross_cutting/contracts/test_package_dependency_rules.py` that parses `bynat/**/*.py`, builds the import graph, and asserts AR-3–AR-9 and AR-11. This mirrors the existing `test_internal_shared_helpers.py` and `test_accessor_package_boundary.py` approach.

Existing coverage:
- `tests/cross_cutting/contracts/test_root_api.py` — AR-1, root namespace, reader identity, fresh import order.
- `tests/cross_cutting/contracts/test_doc_drift.py` — AR-2, package exports, stub/docstring sync.
- `tests/cross_cutting/contracts/test_internal_shared_helpers.py` — AR-5, canonical `dedupe_key`.
- `tests/cross_cutting/accessor/test_accessor_package_boundary.py` — AR-4, AR-8, accessor delegation, no root import.
- `tests/modules/profile/test_profiling_package_boundary.py` — AR-6, profiling exports and forbidden imports.

**Later (optional dev dependency):** Import Linter configured in `pyproject.toml` with:
- `forbidden` contracts for prohibited edges;
- `independence` between `analytics`, `profiling`, and `caching`;
- a `protected` contract on `bynat.caching._keys` with allow-list `bynat.cleaning.enrich.engine`, `bynat.cleaning.enrich.translate`;
- a `protected` contract on `bynat.cleaning._outputs` with allow-list `bynat.cleaning.stats`, `bynat.cleaning.base`, `bynat._accessors.dataframe`;
- a `protected` contract on `bynat._internal` with allow-list `bynat.cleaning.io`, `bynat.profiling.profile`;
- `private_modules` scoped to `bynat` for the remaining underscore modules, with `ignore_imports` for the protected edges above;
- `acyclic_siblings` on `bynat`.

Optionally enable Ruff's preview `PLC2701 import-private-name` rule to flag cross-module private imports at lint time. Import Linter is not added in this design phase because the task forbids adding dependencies now; the AST test provides equivalent immediate enforcement without a new dependency.

---

## 23. Compatibility and Migration Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Missing an internal import site during alias removal | Low | Import error at import time | Grep all alias names; run full suite, ruff, mypy |
| `_migrate_legacy_cache` removal breaks a test | Low | Test failure | Update line 180 to `manager._migrate_legacy_json_cache`; run caching migration tests |
| Canonical rename changes private symbol identity | Low | None at runtime | Private modules only; no public `__all__` change |
| Import Linter flags a documented private-import edge | Certain | Enforcement failure | Represent all five edges with `protected` contracts and scoped `private_modules`; the AST test asserts the exact set |
| Generated stub drift | Low | Type-check/doc drift | No accessor signature change; run `tools/sync_docs.py --check` |
| Public API change | None expected | — | No public signature, docstring, stub, or export changes |

No deprecation, facade, or public alias is introduced. No existing public API is removed.

---

## 24. Implementation Sequence and Checkpoints

This design is documentation-only. If implementation is later authorized, use these bounded steps.

**Step 1 — Private alias normalization (bounded, behavior-preserving).**
Scope: `cleaning/_common.py`, `cleaning/_outputs.py`, `caching/_keys.py`, `caching/_migration.py`, `caching/manager.py`, plus the consumer import updates in §12 and the one test update.
Checkpoint: full suite, ruff, mypy, `tools/sync_docs.py --check` pass; no public signature or docstring change.

**Step 2 — Enforcement test.**
Scope: add `tests/cross_cutting/contracts/test_package_dependency_rules.py`.
Checkpoint: new test passes; existing contract tests pass; the test fails when a prohibited edge is introduced (verify by temporary mutation, then revert).

**Step 3 — Documentation reconciliation.**
Scope: update `docs/ARCHITECTURE_RESEARCH.md`/`docs/ROADMAP.md` only where they describe the corrected `_keys` consumer set and the internal normalization.
Checkpoint: no stale claims about alias names or `_keys` ownership.

**Step 4 — Optional Import Linter adoption (deferred).**
Scope: add the dev dependency and `pyproject.toml` contracts; record the `_keys` exception.
Checkpoint: `lint-imports` passes; CI job added.

**Explicitly deferred (not part of this design):** splitting `base.py`; analytics accessor methods (no use case); a generic transformation engine; a lazy execution layer; expanding `caching.__all__`.

---

## 25. Unresolved Decisions and Genuine Blockers

**No material design blocker.** The following are deliberate deferrals, not open questions:

| ID | Item | Disposition |
|---|---|---|
| AE-Q1 | Should `caching._keys` become a narrow public contract? | Keep private with a documented edge; revisit only if a second consumer or a user-facing requirement appears |
| AE-Q2 | Should `base.py` be split or generated? | Defer; size is 79% docstrings and the facade is cohesive |
| AE-Q3 | Should any `Analyzer` operation become an accessor method? | No concrete use case; defer |
| AE-Q4 | Should `save_to_sql` move to its own module? | No; lazy import already isolates the optional dependency |
| AE-Q5 | Should Import Linter be adopted now? | No; AST test first, Import Linter as an optional later dev dependency |
| AE-Q6 | When a derived `BaseData` frame's `CacheManager` is cleared or replaced, should the recreated manager inherit the originating custom `cache_dir`? | Missing behavioral contract; see §17.3. Repository evidence does not state the intended contract, so none is invented |

Each deferral has a stated revisit trigger. None prevents implementing the target tree.

**Behavioral follow-ups are not blockers.** The 12 implementation–documentation discrepancies and 15 test coverage gaps in §17 are recorded as tracked correctness/coverage follow-ups. They do not require a structural change and are outside the architecture target; several are already pinned as tracked defects (PD-01, PD-02).

---

## 26. Decision Register

Outcomes: **Adopt**, **Adapt**, **Defer**, **Reject**. Every entry is traceable to the evidence in §§2–§25.

| ID | Area | Outcome | Decision | Evidence / rationale | Revisit trigger |
|---|---|---|---|---|---|
| D-A1 | Container architecture | Adopt | Modular monolith with domain packages | §5, §6.A; current boundaries | A new coherent domain with multiple operations |
| D-A2 | Functional organization | Adopt | Functional Core + Facades | §6.D; shared functions behind `BaseData`/accessor | — |
| D-A3 | Package boundaries | Adopt | `cleaning`/`caching`/`analytics`/`profiling` + private `_accessors`/`_internal` | Approved plan; §7 | Approved-requirement conflict |
| D-A4 | Shared helpers | Adopt | Domain-owned helpers; one narrow `_internal` | §6.C, §14 | A non-cleaning consumer of a cleaning helper |
| D-A5 | Private alias normalization | Adopt | Remove the alias layer and dead private wrappers | §3.3 F-1/F-2, §12 | — |
| D-A6 | Cross-package private imports | Adapt | Keep the five documented edges; enforce with `protected` contracts | §3.3 F-3, §13.3 | A new cross-package private import |
| D-A7 | Accessor integration | Adopt | `_accessors` owns registration/binding only | §8, §14.5 | — |
| D-A8 | Profiling independence | Adopt | Profiling core independent of cleaning/analytics/caching | §11, §13, boundary tests | — |
| D-A9 | Analytics independence | Adopt | No internal `bynat` imports | §13.2, §14 | A concrete cache/cleaning requirement |
| D-A10 | Transformation architecture | Adopt | Stateless functions; no estimator layer | §5, §6.D | — |
| D-A11 | Integration architecture | Adapt | Lazy optional imports; provider protocols; no plugins | §6.E, §19 | A third-party plugin requirement |
| D-A12 | Enforcement | Adapt | Dependency-free AST contract test now; Import Linter later | §22 | CI enforcement need |
| D-D1 | `base.py` split or generation | Defer | Cohesive facade; size is mostly docstrings | §3.2, §3.3 F-5 | Concrete maintenance pain |
| D-D2 | Analytics accessor methods | Defer | No concrete fluent use case | §6.F | A concrete stable DataFrame contract |
| D-D3 | Import Linter + Ruff `PLC2701` | Defer | No new dependency in this phase | §22.2 | CI enforcement need |
| D-D4 | Implementation–documentation discrepancies (12) | Defer | Behavioral/correctness follow-ups, not structural | §17.1 | Prioritized correctness work |
| D-D5 | Test coverage gaps (15) | Defer | Coverage follow-ups, including the two tracked defects | §17.2 | Test-phase work |
| D-D6 | `caching._keys` public contract | Defer | Keep private with an allow-list | §13.3, §25 | Second consumer or user requirement |
| D-R1 | Microservices / separate deployables | Reject | One small installable library | §5, §21 | — |
| D-R2 | Generic repository pattern | Reject | No domain-model persistence | §21 | — |
| D-R3 | Universal managers | Reject | Only `CacheManager` has a demonstrated lifecycle | §21 | — |
| D-R4 | Base classes for unrelated operations | Reject | Composition is used instead | §5, §21 | — |
| D-R5 | Generic `_shared` package | Reject | Only one domain-independent helper exists | §6.C, §21 | — |
| D-R6 | Protocol proliferation | Reject | Only three provider protocols have consumers | §6.F, §21 | — |
| D-R7 | Plugin registry / entry points | Reject | No third-party plugin requirement | §4 E-11, §21 | — |
| D-R8 | Generic transformation engine | Reject | Transformations are explicit functions | §5, §21 | — |
| D-R9 | Lazy execution / query-engine layer | Reject | No lazy or optimized execution requirement | §4 E-3, §21 | — |
| D-R10 | `fit`/`transform` estimator layer | Reject | bynat transformations are stateless functions | §4 E-2, §21 | — |
| D-R11 | Splitting modules by LOC | Reject | Modules are cohesive; size is documentation or one domain | §3.2, §3.3 F-5 | — |
| D-R12 | Moving caching under cleaning | Reject | Caching is a peer infrastructure package | §6.A, §13 | — |
| D-R13 | `analytics → cleaning` dependency | Reject | Analytics is independent | §6.A, §13.2 | — |
| D-R14 | `profiling → analytics` dependency | Reject | Profiling is independent | §6.A, §13.2 | — |

---

## 27. Research References

### 27.1 External sources

| ID | Source | URL | Opened |
|---|---|---|---|
| E-1 | pandas, *Extending pandas* | <https://pandas.pydata.org/docs/development/extending.html> | Yes |
| E-1 | pandas, *API reference index* | <https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/source/reference/index.rst> | Yes |
| E-2 | scikit-learn, *Developing scikit-learn estimators* | <https://scikit-learn.org/stable/developers/develop.html> | Yes |
| E-2 | scikit-learn, `sklearn/base.py` | <https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/base.py> | Search result |
| E-2 | scikit-learn, *FunctionTransformer* | <https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.FunctionTransformer.html> | Yes |
| E-2 | scikit-learn, *SLEP 18 set_output* | <https://scikit-learn-enhancement-proposals.readthedocs.io/en/latest/slep018/proposal.html> | Search result |
| E-3 | Polars, *Lazy API* | <https://docs.pola.rs/user-guide/concepts/lazy-api/> | Yes |
| E-3 | Polars, *A bird's eye view of Polars* | <https://pola.rs/posts/polars_birds_eye_view/> | Search result |
| E-4 | SQLAlchemy, *Overview* | <https://docs.sqlalchemy.org/en/latest/intro.html> | Yes |
| E-4 | SQLAlchemy, *Engine Configuration* | <https://www.sqlalchemy.org/docs/latest/core/engines.html> | Search result |
| E-5 | Pydantic, *Architecture* | <https://pydantic.dev/docs/validation/latest/internals/architecture> | Yes |
| E-5 | Pydantic, *V2 announcement* | <https://pydantic.dev/docs/validation/1.10/blog/pydantic-v2> | Search result |
| E-6 | Destroy All Software, *Functional Core, Imperative Shell* | <https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell> | Yes |
| E-7 | GitLab, *Hexagonal Monolith* | <https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/modular_monolith/hexagonal_monolith> | Search result |
| E-7 | Mathieu Eveillard, *Modular Monolith* | <https://mathieueveillard.com/articles/modular-monolith> | Search result |
| E-8 | NumPy, *Module structure* | <https://numpy.org/doc/stable/reference/module_structure.html> | Yes |
| E-8 | NumPy, *NEP 52 — Python API cleanup* | <https://numpy.org/neps/nep-0052-python-api-cleanup.html> | Yes |
| E-9 | pandas, *DataFrame.transform* | <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.transform.html> | Yes |
| E-9 | pandas, *Copy on write* | <https://pandas.pydata.org/docs/development/copy_on_write.html> | Yes |
| E-10 | Import Linter, *Contract types* | <https://import-linter.readthedocs.io/en/stable/contract_types/> | Yes |
| E-10 | Import Linter, *Private modules* | <https://import-linter.readthedocs.io/en/stable/contract_types/private_modules/> | Yes |
| E-10 | Import Linter, *Configure* | <https://import-linter.readthedocs.io/en/latest/get_started/configure> | Search result |
| E-10 | Import Linter, *Protected modules* | <https://import-linter.readthedocs.io/en/stable/contract_types/protected/> | Yes |
| E-11 | PyPA, *Creating and discovering plugins* | <https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/> | Yes |
| E-11 | PyPA, *Entry points specification* | <https://packaging.python.org/en/latest/specifications/entry-points/> | Yes |
| E-12 | Python, *Modules* | <https://docs.python.org/3/tutorial/modules.html> | Yes |
| E-12 | Python, *Import system* | <https://docs.python.org/3/reference/import.html> | Search result |
| E-13 | PEP 621, *Storing project metadata in pyproject.toml* | <https://peps.python.org/pep-0621/> | Yes |
| E-13 | PyPA, *pyproject.toml specification* | <https://packaging.python.org/en/latest/specifications/pyproject-toml/> | Search result |
| E-14 | PEP 8, *Naming conventions* | <https://peps.python.org/pep-0008/#naming-conventions> | Yes |
| E-14 | Ruff, *import-private-name (PLC2701)* | <https://docs.astral.sh/ruff/rules/import-private-name/> | Yes |

### 27.2 Internal sources

- [`docs/temb/bynat_internal_architecture_evolution_plan.md`](../temb/bynat_internal_architecture_evolution_plan.md)
- [`docs/temb/bynat_architecture_refactoring_plan.md`](../temb/bynat_architecture_refactoring_plan.md)
- [`docs/ARCHITECTURE_RESEARCH.md`](../ARCHITECTURE_RESEARCH.md)
- [`docs/ROADMAP.md`](../ROADMAP.md)
- [`docs/TESTING_STANDARDS.md`](../TESTING_STANDARDS.md)
- [`pyproject.toml`](../../pyproject.toml)
- [`bynat/__init__.py`](../../bynat/__init__.py)
- [`bynat/cleaning/__init__.py`](../../bynat/cleaning/__init__.py)
- [`bynat/cleaning/_common.py`](../../bynat/cleaning/_common.py)
- [`bynat/cleaning/_outputs.py`](../../bynat/cleaning/_outputs.py)
- [`bynat/cleaning/base.py`](../../bynat/cleaning/base.py)
- [`bynat/_accessors/__init__.py`](../../bynat/_accessors/__init__.py)
- [`bynat/_accessors/_binding.py`](../../bynat/_accessors/_binding.py)
- [`bynat/_accessors/dataframe.py`](../../bynat/_accessors/dataframe.py)
- [`bynat/_internal/__init__.py`](../../bynat/_internal/__init__.py)
- [`bynat/_internal/values.py`](../../bynat/_internal/values.py)
- [`bynat/caching/__init__.py`](../../bynat/caching/__init__.py)
- [`bynat/caching/_keys.py`](../../bynat/caching/_keys.py)
- [`bynat/caching/_migration.py`](../../bynat/caching/_migration.py)
- [`bynat/caching/_storage.py`](../../bynat/caching/_storage.py)
- [`bynat/caching/manager.py`](../../bynat/caching/manager.py)
- [`bynat/analytics/__init__.py`](../../bynat/analytics/__init__.py)
- [`bynat/analytics/analyzer.py`](../../bynat/analytics/analyzer.py)
- [`bynat/profiling/__init__.py`](../../bynat/profiling/__init__.py)
- [`bynat/profiling/profile.py`](../../bynat/profiling/profile.py)
- [`bynat/profiling/report.py`](../../bynat/profiling/report.py)
- [`tools/sync_docs.py`](../../tools/sync_docs.py)
- [`tools/verify_installed_wheel.py`](../../tools/verify_installed_wheel.py)
- [`tests/cross_cutting/contracts/test_root_api.py`](../../tests/cross_cutting/contracts/test_root_api.py)
- [`tests/cross_cutting/contracts/test_doc_drift.py`](../../tests/cross_cutting/contracts/test_doc_drift.py)
- [`tests/cross_cutting/contracts/test_internal_shared_helpers.py`](../../tests/cross_cutting/contracts/test_internal_shared_helpers.py)
- [`tests/cross_cutting/accessor/test_accessor_package_boundary.py`](../../tests/cross_cutting/accessor/test_accessor_package_boundary.py)
- [`tests/modules/profile/test_profiling_package_boundary.py`](../../tests/modules/profile/test_profiling_package_boundary.py)

---

## Acceptance self-review

| Criterion | Coverage |
|---|---|
| Supplied plan read and followed | §1–§27 map to the plan's levels and checkpoints |
| Repository baseline inspected | §2 (commit, tree, imports, LOC, fresh probe, verification) |
| Approved top-level structure respected | §1 Decision 1, §8 |
| External research conducted and cited | §4, §27 (opened vs search-result labeled) |
| Alternatives compared | §5, §6 |
| Concrete decisions made | §6 A–I, §26 |
| Decision register with Adopt/Adapt/Defer/Reject | §26 |
| Every package has internal organization | §7 |
| Complete target tree | §8 |
| Every file has a responsibility | §9 |
| Component architecture inventory (Level 3) | §10 (48 components + 14 flags) |
| Module contracts and dependency review (Level 5) | §11 |
| Every affected file has a migration disposition | §12 |
| Dependencies defined | §13, §14 |
| Execution flows mapped | §15 |
| Behavioral contracts (Level 4) | §16 (20 flows) |
| Implementation–documentation discrepancies and test gaps | §17 (12 + 15) |
| Shared helper ownership resolved | §18 |
| Unnecessary patterns rejected | §21 |
| Public API/compatibility preserved | §1, §23 |
| Enforcement rules specified and coverage mapped | §22 |
| Contradictions resolved (private imports, migration alias, AR-11) | §1 follow-up, §3.3 F-3/F-8, §13.3, §22.1 |
| Private-helper alias policy unambiguous and consistent | §6.I, §12 |
| Absolute, relative, and dynamic imports inspected; completeness claim scoped | §3.3 F-3, §13.3 |
| Every `Adjust` component has an explicit decision | §10.3 |
| `BaseData.cache_dir` lifecycle finding resolved as a contract question | §17.3, §25 AE-Q6 |
| Final consistency review completed and reconciled | §1 follow-up, §26 |
| Internally consistent | §6 and §26 match §8–§22 |
| No implementation changes | This file is the only write |
| No material question left unanswered | §25 lists deferrals with revisit triggers |
