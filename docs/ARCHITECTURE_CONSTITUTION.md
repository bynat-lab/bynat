# bynat Architecture Constitution

**Status:** Normative and authoritative architecture constitution for `bynat`.
**Package version:** `0.6.6` (`pyproject.toml`).
**Python:** `>=3.11`. **Core dependencies:** `numpy`, `pandas`.
**Scope:** architecture rules, current structure, behavioral contracts, conditional evolution, deferred decisions, and rejected alternatives. Testing architecture/procedures, CI, linting, typing, benchmarking, and workflow content are out of scope except for the separation statement in [§7](#7-testing-scope-separation).

> **Status labels used below.**
>
> - **Normative** — binding rule; unique `ARCH-###` identifier.
> - **Current** — directly observed in the checkout at the current HEAD.
> - **Conditional** — future proposal gated on an explicit trigger; not scheduled and not current.
> - **Deferred** — deliberate non-decision with a revisit trigger.
> - **Rejected** — evaluated and excluded; the exclusion is itself normative.
>
> **Implementation authorization.** This constitution is documentation. It authorizes no source, test, configuration,
> or CI change by itself. The internal normalization in [§1.8](#18-private-helpers-aliases-and-naming) is an adopted
> rule whose implementation is complete in the current checkout (ARCH-045/ARCH-046). The helper placement and organization rules in
> [§1.15](#115-helper-placement-and-organization) are adopted normative rules whose current-state status is recorded
> in [§2.10](#210-module-responsibility-inventory-current); they do not force code moves. The public-API/core-implementation
> and helper/core-implementation ownership rules in [§1.5](#15-functional-core-facades-and-transformation-contracts)
> (ARCH-102–ARCH-104) describe the architecture implemented by commit `946eb16` and recorded in §2.10. They are
> current rules, not targets for further separation. This constitution authorizes no additional code move; any future
> architectural change requires a separate explicit decision and the procedure in ARCH-066/ARCH-099.

---

## 1. Normative rules

Rules are grouped by topic and numbered `ARCH-001` … `ARCH-104`. Each ID is unique and stable: amendments add,
repeal, or renumber explicitly under [§6](#6-governance-and-amendment-procedure).

### 1.1 Authority, scope, and evidence

| ID | Rule |
|---|---|
| ARCH-001 | This constitution is the authoritative architecture rulebook for `bynat`. |
| ARCH-002 | Every architectural statement must be labeled **Current**, **Conditional**, **Deferred**, or **Rejected**. A future proposal must never be stated as a current fact, and a current fact must never be stated as a proposal. |
| ARCH-003 | Compatibility with previous published versions is **out of scope**. Obsolete public paths and aliases are removed directly, not retained as compatibility facades. Behavior and contracts that remain part of the current intentional API are preserved because they are current correctness, not legacy compatibility. |
| ARCH-004 | `bynat` is **one installable modular monolith** with a flat package layout at the repository root (not `src/`). Extraction into separate distributions or services (Stage E) is rejected unless a concrete deployment, versioning, or team-boundary requirement appears. |
| ARCH-005 | The public surface is **frozen during internal evolution**. Internal reorganization must not change a public import path, a package `__all__` value, a public signature, a docstring, or documented behavior. A public module move is a public API change and requires explicit approval. |
| ARCH-098 | **Stable invariants, context-driven internal organization.** Keep architectural invariants stable: package ownership, dependency direction, public boundaries, and documented contracts. Choose internal module and helper organization according to the actual responsibilities, invariants, consumers, change reasons, and lifecycle of the code. Different structures are justified when those facts materially differ; superficially similar code does not require identical structure, and different-looking code does not by itself justify different structure. Flexibility is constrained by this constitution, the decision procedure in ARCH-066/ARCH-099, and the enforcement requirements in ARCH-075/ARCH-101; it is not permission for arbitrary or undocumented variation. |

### 1.2 Public API and compatibility

| ID | Rule |
|---|---|
| ARCH-006 | Root `bynat.__all__` is exactly, in order, `['cleaning', 'caching', 'analytics', 'profiling', 'read_csv', 'read_json']`. Importing `bynat` registers `df.bynat` through a private `_accessors` import. The root must not expose `BaseData`, `CsvFile`, `JsonFile`, `BynatAccessor`, `ProfileReport`, `DatasetProfile`, `ColumnProfile`, `profile`, cache internals, or provider classes. |
| ARCH-007 | Package `__all__` values are exact and non-underscore: `cleaning` → `BaseData, CsvFile, JsonFile`; `caching` → `CacheManager, CACHE_DIR_ENV_VAR, DEFAULT_CACHE_DIR, shared_cache_manager`; `analytics` → `Analyzer`; `profiling` → `profile, ProfileReport, DatasetProfile, ColumnProfile`; `cleaning.enrich` → the six provider symbols; `_internal` → `dedupe_key`; `_accessors` → `BynatAccessor`. |
| ARCH-008 | Every `bynat/**/*.py` module declares `__all__` as a list or tuple of non-underscore names. (`bynat/_accessors/_binding.py` uses the annotated form `__all__: list[str] = []`.) |
| ARCH-009 | Before moving or replacing any module path, classify it in exactly one of four categories: (1) public symbols declared in a package `__all__`; (2) public package import paths (`bynat`, `bynat.cleaning`, `bynat.caching`, `bynat.analytics`, `bynat.profiling`); (3) internal implementation module paths imported by repository code or tests; (4) documented import paths not in `__all__` (for example `bynat.cleaning.io`). Record the classification and the preservation requirement in the phase acceptance criteria. |
| ARCH-010 | An unchanged `__all__` does **not** by itself prove compatibility. `__all__` governs star-imports and the package namespace only. Direct module imports, package-attribute access, function `__module__`, `__wrapped__` identity, function identity must also be preserved. |
| ARCH-011 | A module-to-package conversion keeps the module's name (`columns.py` → `columns/`, `text.py` → `text/`, `stats.py` → `stats/`, `io.py` → `io/`, `providers.py` → `providers/`) and re-exports every symbol accessed by repository code and tests. A module and a same-named package must never coexist in one parent package. |
| ARCH-012 | For the `io` conversion, the `__module__` contract is `read_csv.__module__ == "bynat.cleaning.io"` and `read_json.__module__ == "bynat.cleaning.io"`. **Option A** (define the public functions in `io/__init__.py`) is the approved approach. **Option B** (define in a submodule and assign `__module__`) is viable only with a change to the current docstring mechanism and explicit approval. **Option C** (accept `bynat.cleaning.io.readers`) is rejected because it weakens a pinned public contract. |
| ARCH-013 | No deprecation, compatibility facade, or alias is introduced to absorb an internal redesign. Internal reorganization is a minor/patch change if the public API is unchanged. |

### 1.3 Package boundaries and ownership

| ID | Rule |
|---|---|
| ARCH-014 | `bynat.cleaning` owns DataFrame cleaning/transformation functions, enrichment, file/SQL I/O, and the supported class facade. It must not own accessor registration, the profiling core, or cache storage. |
| ARCH-015 | `bynat.caching` owns cache-directory resolution, the public `CacheManager`, SQLite persistence, legacy migration/quarantine, and cache-key identity. It must not own cleaning or analytics algorithms. |
| ARCH-016 | `bynat.analytics` owns application-independent analytics and response contracts. It must not import another `bynat` package. |
| ARCH-017 | `bynat.profiling` owns non-mutating data-quality profiling and report models. It must not import `cleaning`, `analytics`, `caching`, or `_accessors`. |
| ARCH-018 | `bynat._accessors` (private) owns pandas registration, binding, accessor signatures, delegation, and accessor-specific output adaptation only. It contains no domain algorithms. Functional packages must not import it. |
| ARCH-019 | `bynat._internal` (private) owns domain-independent value normalization. It imports only the standard library and NumPy, and imports no functional package. |
| ARCH-020 | Canonical shared-component owners are: `dedupe_key` → `_internal/keys.py`; cleaning helpers → `cleaning/_internal/`; output conversion → `cleaning/_internal/outputs.py`; cached lookup → `cleaning/enrich/_engine.py`; rate-limited mapping and translation batching → `cleaning/enrich/_internal/mapping.py`; provider contracts → `cleaning/enrich/providers.py`; cache-key identity → `_internal/keys.py` (shared with enrichment); SQLite persistence → `caching/_storage.py` with cache load/save orchestration in `caching/_persistence.py`; legacy migration → `caching/_migration.py`; profiling computations → `profiling/_internal/`; analytics implementations → `analytics/_insights.py` and `analytics/_internal/`; report models → `profiling/report.py`; analytics public API → `analytics/analyzer.py`. Consumer count is evidence of reuse, **not** proof of ownership; a shared component belongs where its invariants and change reasons are owned. These are existing responsibility-owned modules (ARCH-095), not generic helper collections; `_internal/` is the prescribed generic collection (ARCH-094), and new helper placement follows ARCH-092. Public API modules own their supported contracts and delegate; they are not alternative owners of these implementation responsibilities (ARCH-102–ARCH-103). Where a listed module currently combines a public interface with its implementation, that co-location is an adopted separation target, not a current-fact approval, and no move is authorized by this constitution. |
| ARCH-021 | Do not use `shared`, `_shared`, `common`, `utils`, or `helpers` as generic internal-helper module or package names at any scope. `_internal` is the only prescribed generic internal-helper name; create it only under ARCH-092–ARCH-094. |

### 1.4 Dependency direction and private imports

| ID | Rule |
|---|---|
| ARCH-022 | Package dependency direction is: root → public packages, canonical loaders, and `_accessors` registration; `_accessors` → supported cleaning feature APIs, `Analyzer`, `CacheManager`, and profiling; cleaning → caching, profiling adapters, and library/domain `_internal` helpers; profiling → library `_internal`; analytics → no other `bynat` package; caching → no functional package; library `_internal` → no functional package. Within each package, public API modules delegate to private core modules and `_internal/` helpers; exact private cross-package imports are enumerated in §2.5. |
| ARCH-023 | Prohibited internal edges: `caching` → `cleaning`/`analytics`/`profiling`/`_accessors`; `analytics` → any other `bynat` package; `profiling` → `cleaning`/`analytics`/`caching`/`_accessors`; `cleaning` → `analytics`/`_accessors`; any functional package → `_accessors`; any `_internal` package → a functional package. The explicit accessor delegations and private-helper dependencies recorded in §2.5 are permitted. |
| ARCH-024 | Cross-package private imports are limited to the exact, enumerated edges in the current dependency inventory (§2.5). Public API modules may import private implementation modules only to delegate their supported contract; accessor-to-cleaning and functional-to-cache/private-helper edges must remain explicit and symbol-limited. No undocumented private edge is permitted. |

| # | Importing module | Imported module | Symbol(s) | Ownership rationale |
|---|---|---|---|---|
| 1 | `cleaning.enrich._engine` | `caching._internal` | `cache_value_key` | Cache-key identity is caching-owned. |
| 2 | `cleaning.enrich._translate` | `caching._internal` | `cache_has_value`, `cache_lookup_value` | Same. |
| 3 | `_accessors.dataframe` | `cleaning._internal` | `is_basedata_type` | BaseData-type detection is cleaning-owned; the accessor is the adaptation seam. |
| 4 | `cleaning.io` | `_internal` | `dedupe_key` | `_internal` is the prescribed private value-helper collection (ARCH-094). |
| 5 | `profiling._internal.computations` | `_internal` | `dedupe_key` | Same. |
| 6–13 | `_accessors.dataframe` | `cleaning._columns`, `cleaning._stats`, `cleaning._text`, `cleaning.io`, `cleaning.enrich._currency`, `_geocode`, `_nlp`, `_translate` | canonical feature functions | The accessor directly delegates public feature contracts; these are deliberate private implementation imports in the implemented boundary. |

| ID | Rule |
|---|---|
| ARCH-025 | A new cross-package private import requires a documented exception and an enforcement entry before it is added. Private-module privacy is the default; exceptions are explicit and enumerated. |
| ARCH-026 | The internal package import graph must remain acyclic. |
| ARCH-027 | Production transformation and cleaning paths must not use row-wise iteration (`apply(axis=1)`, `iterrows()`, `itertuples()`). |

### 1.5 Functional Core, Facades, and transformation contracts

ARCH-028–ARCH-030 describe the Functional Core + Facades principles as they apply to the responsibilities and
boundaries established by commit `946eb16`. ARCH-102–ARCH-104 define those implemented public API, private core,
and `_internal/` responsibilities; they do not authorize further separation or relocation.

| ID | Rule |
|---|---|
| ARCH-028 | The adopted shape is **Functional Core + Facades**, with module ownership and delegation exactly as established by commit `946eb16`. Public interfaces and facades expose supported contracts and delegate where the implemented boundary assigns delegation; a public API module may retain substantive implementation where that is its committed responsibility. `BaseData`, `BynatAccessor`, providers, and `CacheManager` form the imperative shell where they perform I/O and external effects. Do not infer a blanket requirement to separate every public function body from its module. |
| ARCH-029 | Transformations are stateless functions with frame-first signatures. They preserve index, order, and length; they state copy-versus-mutate (`inplace`) and output-container (`output_type`) behavior explicitly. No `fit`/`transform` estimator layer and no lazy execution layer is introduced. |
| ARCH-030 | Public facades delegate to the core implementations and helpers assigned by the implemented architecture; this rule does not imply moving every public function body out of its established module. `BynatAccessor` adapts shared functions through the binding factories. The dual `BaseData._finish_with_stats` / `bynat._accessors._binding._frame_method(stats=True)` contract, including the accessor methods generated from it, is retained as a parity-pinned duplication, not silently unified. |
| ARCH-031 | Accessor eligibility is contract-based. A function belongs on `df.bynat` only when all seven criteria hold: DataFrame receiver fit; stable fluent workflow; clear receiver contract; facade independence; optional integration value; justified public API cost; no hidden external boundary. Automatic mirroring is rejected. |
| ARCH-032 | Classes and protocols are introduced only with a concrete consumer and a lifecycle or structural contract. Composition is preferred over inheritance. The only protocols are `Translator`, `Geocoder`, and `RateSource`. |
| ARCH-033 | The normative internal interface inventory is: `CacheManager`; `Analyzer`; `BaseData`/`JsonFile`/`CsvFile`; `BynatAccessor`; `Translator`/`Geocoder`/`RateSource`; `DatasetProfile`/`ColumnProfile`/`ProfileReport`; `SQLiteStorage`. |
| ARCH-100 | **Patterns are defaults, not templates.** The adopted patterns in ARCH-028–ARCH-032 are the preferred starting points where their stated responsibilities and contracts fit. Apply a pattern because it solves the concrete problem, not to make unrelated components look uniform. A deviation is valid when repository evidence shows a material difference in responsibility, invariant, ownership, consumer needs, lifecycle, or change reasons; record the reason when the deviation affects an architectural boundary. Do not invent layers, facades, classes, or abstractions solely for consistency, and do not create unexplained variation between components whose relevant constraints are materially the same. |
| ARCH-102 | **Public API, private core, and helper responsibilities follow the implemented architecture.** Public API modules expose supported contracts and exports; private core modules own the substantive implementation assigned to them by commit `946eb16`; package-local `_internal/` modules own the cohesive helper responsibilities assigned to them. Do not assume every public function is a thin facade or that every helper must be moved into `_internal/`; the current path, ownership, and delegation choices in §2.10 are authoritative. Preserve all supported paths, signatures, behavior, and pinned contracts. Do not add compatibility facades or relocate code based on a generalized template. |
| ARCH-103 | **Canonical responsibility ownership.** Public API ownership, core implementation ownership, helper ownership, and shared internal implementation ownership are distinct. Each responsibility has one canonical owner; a public API module is not an alternative domain-logic owner, and an internal implementation module is not thereby a public interface. Shared implementation has one canonical owner only when consumers share the same semantics and contract; coincidental similarity does not justify merging distinct responsibilities or contracts. |
| ARCH-104 | **Helper ownership follows the refactor.** Helpers reside at the exact private-core or `_internal/` paths established by commit `946eb16`; package-local `_internal/` packages contain the helper responsibilities assigned to them, while responsibility-specific shared implementations such as the enrichment cache engine remain at their established private-core paths. Preserve these ownership and path decisions; do not relocate helpers based on a blanket placement rule. |

### 1.6 Optional integrations and providers

| ID | Rule |
|---|---|
| ARCH-034 | Optional dependencies are imported lazily and function-locally through `import_optional`, which raises a feature-specific `ImportError` naming the distribution. Argument and configuration validation precedes the dependency import where the code checks first. |
| ARCH-035 | External services sit behind `provider=` protocols in `cleaning/enrich/providers.py`. No plugin discovery, entry-point registry, dependency-injection container, or generic integration framework is introduced. |
| ARCH-036 | `save_to_sql` remains defined in `cleaning/io.py` at its supported import path. URL construction is extracted to `cleaning/_internal/sql.py` as `build_engine_url`; `save_to_sql` retains validation, the lazy SQLAlchemy import, DataFrame preparation, engine use, and disposal. This is the implemented responsibility split; do not move or rename either function based on earlier proposals. |
| ARCH-037 | Optional extras are declared in `pyproject.toml` (`translation`, `geocoding`, `currency`, `categorization`, `nlp`, `sql`). `extract_keywords` may silently fall back to the regex path when `pyahocorasick` is absent; `categorize_by_reference` hard-requires it. |

### 1.7 CacheManager boundaries and lifecycle

| ID | Rule |
|---|---|
| ARCH-038 | `CacheManager` is the sole public cache facade. It delegates load/save orchestration to `_persistence.py`, SQLite operations to `_storage.py`, and legacy migration to `_migration.py`; the storage layer owns connection lifecycle (one connection per operation, explicit `BEGIN IMMEDIATE`, WAL mode, finite busy timeout, always closed). `CacheManager` retains its public cache operations, baseline/diff behavior, and column deletion, without private migration or quarantine wrappers. |
| ARCH-039 | `shared_cache_manager` owns the process-wide registry: one manager per resolved absolute cache directory, guarded by a module lock, created on first request, never evicted. |
| ARCH-040 | `caching` imports no functional package. `_internal/`, `_persistence.py`, `_storage.py`, and `_migration.py` are private; consumers use the public `caching` API except for the documented cache-key helper dependency. |
| ARCH-041 | Cache-key identity is owned by the shared `_internal/keys.py`. Caching and enrichment consume it through the enumerated private imports and must not own storage-identity rules. |
| ARCH-042 | `BaseData` owns its lazily created manager through instance metadata; `BynatAccessor` holds a manager by reference and resolves the shared manager lazily. `with_cache(...)` binds an explicit or shared manager. |
| ARCH-043 | No global cache singleton without scoping and no resource manager or registry beyond `shared_cache_manager` is introduced. |

### 1.8 Private helpers, aliases, and naming

| ID | Rule |
|---|---|
| ARCH-044 | The canonical name of every private helper is the name declared in its owning module's `__all__`. No module-level compatibility alias is retained; internal consumers import the canonical name. |
| ARCH-045 | **Implemented.** Redundant private wrappers and aliases were removed; canonical helpers now live in their established `_internal/` packages or responsibility-owned private modules. Consumers import the canonical names. |
| ARCH-046 | **Implemented.** Redundant private cache wrappers and aliases are removed. Cache loading and saving are implemented in `caching/_persistence.py`; migration is implemented by the module-level `migrate_legacy_json_cache` in `caching/_migration.py`, and SQLite operations by `SQLiteStorage` in `caching/_storage.py`. These private implementation functions are not `CacheManager` methods. |
| ARCH-047 | Consumer-side local naming (`cleaning/io.py` importing `dedupe_key as _dedupe_key`) is a naming convention, not a module-level alias, and remains unchanged. Profiling imports the canonical helper from `profiling/_internal/computations.py`. |
| ARCH-048 | **Implemented.** Cache migration and quarantine have canonical module-level owners; `CacheManager` does not retain private wrapper methods for them. |
| ARCH-049 | Every module that emits logs uses `logging.getLogger(__name__)`, so logger names match the actual module path. Modules that do not log do not define unused loggers. Legacy class-named logger strings are not retained. |

Helper placement and organization rules are in [§1.15](#115-helper-placement-and-organization).

### 1.9 Structural evolution model

The stage labels below describe possible structural states and conditional options, not a mandatory maturity ladder. They do not imply that every package must pass through every stage, that a higher-numbered stage is inherently better, or that a transition should occur merely because it is available. Evaluate each candidate transition against its own trigger and the decision procedure in ARCH-066/ARCH-099. A package may remain flat indefinitely; a conditional option may never be used.

| ID | Rule |
|---|---|
| ARCH-050 | **Stage A — implemented package organization (current).** Public API modules expose supported contracts; private core modules own domain implementations; package-local `_internal/` packages own cohesive private helpers. The exact current paths and ownership are recorded in §2.10 and implemented by commit `946eb16`. |
| ARCH-051 | **Stage B — capability subpackages (conditional).** Entered when one package separates into ≥2 capability clusters, each with ≥2 modules and distinct change reasons, and a package-level `__init__` can curate a coherent surface. Counts are sanity checks, not triggers. |
| ARCH-052 | **Stage C — domain-internal layers (conditional, rare).** Entered when a Stage-B capability subpackage has ≥2 internal layers with distinct consumers and change reasons, and layering reduces coupling. The procedure is: confirm the host is a subpackage; identify layers; verify reduced coupling; define a one-way dependency flow; add layer modules with `__all__`; verify no cycle, no public-path change, no new cross-package private import; record trigger and rollback. |
| ARCH-053 | **Stage D — new domain package (conditional).** Entered when a coherent capability has its own public contract, its own lifecycle, and no dependency on existing package internals. |
| ARCH-054 | **Stage E — extraction into separate distributions/services (rejected, far future).** Entered only on a concrete deployment, versioning, or team-boundary requirement. |
| ARCH-055 | Module states: **M0** single module; **M1** split one module into ≥2 modules in the same package; **M2** convert a module into a same-named package with a curated `__init__`; **M3** merge modules that always change together; **M4** add a new module to an existing package. This decision procedure governs only a future structural change that has been explicitly authorized; it does not turn the public/core/helper responsibilities established by commit `946eb16` into additional separation work. Helper-placement rules apply to their stated scope but do not permit relocating existing committed owners. |
| ARCH-056 | **Path-preservation rule.** Preserve the names, locations, import structure, and responsibility assignments established by commit `946eb16`. Do not use pre-refactor module-to-package examples in this constitution to rename, relocate, or reinterpret current modules. |
| ARCH-057 | Evolution principles: **P-1** change reasons before size; **P-2** one responsibility per module (statable without “and”); **P-3** public surface frozen; **P-4** extract shared code into a broader reuse abstraction only after multiple real consumers (Rule of Three, scoped by ARCH-097; same-branch extraction follows ARCH-092); **P-5** dependency direction is a rule, not a directory tree; **P-6** subpackages need a responsibility, not a theme; **P-7** boundaries are enforced, not aspirational; **P-8** every conditional phase is reversible without public API change; **P-9** depth is the last resort; **P-10** the container stays a modular monolith. |
| ARCH-058 | The Phase 0–2 sequence described in the historical evolution material (§3.3) is superseded by the implemented architecture in commit `946eb16`; it is not current scheduled work or authority to alter module boundaries, paths, or imports. Any future architectural change requires a separate explicit decision. |

### 1.10 Growth decision procedure and triggers

| ID | Rule |
|---|---|
| ARCH-059 | Split or group only when responsibilities change for different reasons, cohesion drops, or dependency direction is violated. Line count is a weak, secondary signal and is never sufficient. |
| ARCH-060 | Extract code into a broader reuse abstraction only with ≥2 real consumers, the same contract, and a stable domain-independent responsibility (Rule of Three, scoped by ARCH-097). Same-branch and multi-file extraction follows the narrowest-common-scope hierarchy in ARCH-092 and is not blocked by the consumer count. Similar code with different contracts is not merged; verify behavior and contracts before extracting. |
| ARCH-061 | Layering may be used as a dependency rule; a global `api/`/`domain/`/`infrastructure/` directory tree is rejected. |
| ARCH-062 | A subpackage must have a demonstrable responsibility and owner; thematic `utils/`/`helpers/`/`common/`/`_shared/` groupings are rejected. `_internal` is the single prescribed generic internal-helper name and is governed by ARCH-094; it is not a thematic grouping. |
| ARCH-063 | Every boundary must have a reviewable verification mechanism or an explicit documented exception. |
| ARCH-064 | Every conditional phase must have a rollback that restores the previous structure without a public API change. |
| ARCH-065 | Prefer flat modules; add a subpackage only when it improves navigation and ownership. |
| ARCH-066 | **Operational architectural decision procedure.** For a proposed keep, split, merge, module-to-package conversion, helper extraction, new layer, or new package: (1) state the concrete problem and the candidate components; (2) inspect current code, repository history, consumers, invariant owners, and change coupling; (3) state each candidate component's responsibility, invariants, owner, consumers, and reasons to change in one sentence each; (4) evaluate the candidate against responsibility fit, ownership clarity, cohesion, coupling and dependency direction, human discoverability, machine analyzability, and total complexity/maintenance cost; (5) compare at least one plausible alternative, including keeping the current structure when applicable; (6) replay a recent representative change where evidence exists and record which modules, owners, and boundaries it touches; (7) select the least complex option that satisfies the hard rules and materially improves the stated problem; (8) record the evidence, trade-offs, chosen structure, rejected alternative(s), trigger, verification mechanism, and rollback. This is a reasoned review, not a numerical scorecard: no single criterion or file-count threshold decides the outcome, and a criterion that is not relevant must be marked not applicable with a reason. |
| ARCH-099 | **Decision quality and justification.** A structural decision must explain why the selected organization fits the actual responsibilities and constraints better than plausible alternatives. Consider responsibility, ownership, cohesion, coupling, dependency direction, human discoverability, machine analyzability, and complexity cost together. Prefer the simplest structure that makes ownership and relationships clear while preserving the required contracts. Do not optimize for visual symmetry, uniform file counts, or theoretical future growth. If two alternatives satisfy the constraints, prefer the one with lower ongoing cognitive and maintenance cost; document material trade-offs and uncertainty rather than disguising judgment as a fixed threshold. |
| ARCH-067 | Trigger evidence weights: change-coupling **high**; one-sentence responsibility **high**; dependency-direction violation **high**; cohesion/coupling signals **high**; consumer count **medium**; module size (LOC) **low**; new optional dependency **medium**; new public contract **high**. |
| ARCH-068 | Hard rules: **R-1** never split on LOC alone; **R-2** never use `shared`, `_shared`, `utils`, `helpers`, or `common` as generic internal-helper module or package names; use `_internal` only under ARCH-092–ARCH-094; **R-3** never introduce a protocol, base class, manager, registry, or engine without a concrete consumer; **R-4** never change a public import path or `__all__` value during internal reorganization; **R-5** never add a cross-package private import without a documented exception and enforcement entry; **R-6** never introduce a cycle; **R-7** never pre-build a structure for a scenario that has not occurred; **R-11** counts (files, modules, lines, clusters) are supporting signals only; consumer counts gate broader reuse abstraction, not same-branch/multi-file extraction (ARCH-097); **R-12** a split that only moves files without improving ownership or change behavior is rejected; extracting a helper to the narrowest common scope under ARCH-092 improves ownership and is not a mere file move. |

### 1.11 Conditional evolution phases E1–E6

These are **Conditional** rules. Each phase is opened only when its trigger fires, is independent of the others, is not sequential, and may never occur. They are scenarios, not a roadmap sequence or a target that every package is expected to reach. A phase is selected only when its own evidence and decision review justify it; skipping a phase or remaining in the current structure indefinitely is valid.

| ID | Phase | Scenario | Structural transition | Trigger | Scope | Acceptance | Rollback |
|---|---|---|---|---|---|---|---|
| ARCH-069 | E1 | Cleaning grows 5–10× | Stage A→B via M2 | ≥2 capability clusters, each ≥2 modules with distinct change reasons; responsibility divergence demonstrated | `cleaning/{columns,text,stats,io}/` | Public `__all__` unchanged; dependency matrix unchanged; change-coupling shows independence; §1.2 preservation rules applied | Re-collapse subpackages |
| ARCH-070 | E2 | Analytics grows from one class to a family | M1 (module split) | ≥2 public method clusters with different dependencies and change reasons | `analytics/_*` private capability modules | `Analyzer` public contract unchanged; `analytics` still imports no `bynat` package | Re-inline modules |
| ARCH-071 | E3 | Caching gains a second backend | Stage B + relocation | A concrete second-backend requirement with its own lifecycle; `CacheManager` contract unchanged | `caching/backends/`; relocate `_storage.py` → `backends/sqlite.py` | Protocol consumer is `CacheManager`; exactly two implementations satisfy one contract; no speculative framework; no new cross-package private import | Re-inline backend |
| ARCH-072 | E4 | Integrations grow | Stage B via M2 | ≥3 provider families or a provider with its own configuration/lifecycle | `cleaning/enrich/providers/` | Provider surface unchanged; protocols keep consumers; no new cross-package private import | Re-inline providers |
| ARCH-073 | E5 | A new domain emerges | Stage D | A coherent capability with its own public contract, ≥2–3 operations, no dependency on existing package internals, distinct workflow | New top-level package with its own `__all__` | Boundary compliance is verified; dependency matrix extended; imports no functional internals | Remove package |
| ARCH-074 | E6 | Cross-domain shared logic grows | M4 (module addition) | ≥2 genuinely domain-independent helpers with stable contracts and ≥2 package consumers | library-level `_internal/<coherent_module>.py` (ARCH-094) | `_internal` stays stdlib + NumPy; imports no functional package; each helper has ≥2 real consumers | Move helper back |

### 1.12 Enforcement and fitness functions

| ID | Rule |
|---|---|
| ARCH-075 | Architecture enforcement must cover: exact public exports; the public API/private core/helper ownership boundaries established by commit `946eb16` (ARCH-102–ARCH-104); helper placement, cohesion, and `_internal` naming where those rules apply (ARCH-092–ARCH-097); permitted and prohibited dependency directions; the enumerated private-import exceptions; `_internal` independence; accessor delegation-only ownership; profiling and analytics independence; absence of cycles; module export declarations; public signature/docstring/stub alignment; the prohibition on row-wise data-path iteration; and the discoverability/analyzability expectations in ARCH-101. Enforcement must not impose additional facade or relocation rules beyond the implemented architecture. |
| ARCH-101 | **Human discoverability and machine analyzability.** A reviewer should be able to infer a module's responsibility and owner from its name, location, and nearby package boundaries without tracing unrelated code or relying on undocumented tribal knowledge. Related components and their permitted dependencies should be findable through clear ownership and explicit exports/imports; avoid intermediate modules or layers that add indirection without a concrete boundary benefit. A machine-assisted analysis should be able to identify package/module ownership, dependency edges, public/private boundaries, and documented exceptions from repository artifacts and explicit rules rather than guessing from naming similarity or directory shape alone. Do not force identical file layouts to achieve this: use the narrowest clear organization that fits each responsibility. Automate objective checks where practical; assess semantic clarity, cohesion, and whether indirection adds value through human review. |
| ARCH-076 | The enforcement mechanism MAY be a repository-native static or structural check, a dedicated dependency-analysis tool, or another reviewable mechanism selected for the repository. The mechanism MUST represent all five private-import exceptions precisely and MUST NOT require a runtime dependency merely to describe the architecture. |
| ARCH-077 | A new **module** has one responsibility, the correct owner under the implemented architecture, no unapproved cross-package private import, an explicit export boundary, and placement consistent with the committed package boundaries. Do not add a facade or relocate an existing responsibility merely to enforce a generalized interface/implementation template. A new **subpackage** requires an explicit architectural decision, curates `__init__`, adds no cycle, inherits the parent's dependency budget, and changes no public API. A new **domain package** requires an explicit architectural decision, its own public contract, ≥2–3 operations, no dependency on functional internals, and an explicit extension to the dependency matrix. |
| ARCH-078 | Every structural change review states the trigger it satisfies and its rollback. |

### 1.13 Prohibited patterns

| ID | Prohibition |
|---|---|
| ARCH-079 | No microservices, separate deployables, or separate distributions without a concrete deployment requirement. |
| ARCH-080 | No generic repository pattern, universal managers, or base classes for unrelated operations. |
| ARCH-081 | Do not use `shared`, `_shared`, `utils`, `helpers`, or `common` as generic internal-helper module or package names. `_internal` is the only prescribed generic internal-helper collection, created only under ARCH-092–ARCH-094. |
| ARCH-082 | No protocol proliferation, plugin registry, entry-point discovery, or dependency-injection container. |
| ARCH-083 | No generic transformation engine and no duplicate implementations of shared behavior. Preserve the public API, private-core, and `_internal/` responsibility assignments established by commit `946eb16`; do not split or relocate an implementation based on a blanket facade rule. |
| ARCH-084 | No Polars-style lazy execution/query-engine layer and no `fit`/`transform` estimator layer. |
| ARCH-085 | No artificially strict global layer tree; layering is a dependency rule only. |
| ARCH-086 | No splitting of `base.py`, `_stats.py`, `analyzer.py`, or `profile.py` by LOC alone. Any future structural change requires explicit authorization and must preserve the module ownership and paths established by commit `946eb16`; LOC is never sufficient justification. |
| ARCH-087 | No `caching` under `cleaning`; no `analytics → cleaning` import merely because both use DataFrames; no `profiling → analytics` dependency. |
| ARCH-088 | No `src/` layout migration, no renaming public modules to a “cleaner” tree, and no pre-building structures for scenarios that have not occurred. Preserve the public API, private core, and `_internal/` boundaries and the exact module assignments implemented by commit `946eb16`, including the `save_to_sql`/`build_engine_url` split in ARCH-036. |

### 1.14 Governance and amendment

| ID | Rule |
|---|---|
| ARCH-089 | Amendments follow [§6](#6-governance-and-amendment-procedure): add, repeal, or renumber `ARCH-###` IDs explicitly; state the trigger and rollback; preserve the public API; update the traceability matrix; never make a silent architectural change. |
| ARCH-090 | Conflicts between sources are resolved by chronology and explicit status. A later implemented status update supersedes an earlier historical section; a current checkout observation supersedes a source-reported baseline; a conditional proposal never overrides a current fact. |
| ARCH-091 | Governance is exercised through the checklists in ARCH-077, the change-review requirement in ARCH-078, and the reversibility requirement in ARCH-064. |

### 1.15 Helper placement and organization

These rules govern where a helper lives and how helper modules are grouped. They apply to new helpers and to future
reorganization; they do not force moves of existing private owner modules (ARCH-095). They are a concrete application
of ARCH-098: the placement is selected from actual consumer scope and responsibility, while the ownership and dependency
invariants remain stable. They do not require every package or branch to have the same helper-file shape. ARCH-104 makes
helper/core separation mandatory, so the one-file default in ARCH-092(a) and the single-consumer guard in ARCH-096 yield
when the single file is the core implementation a helper supports; the helper is then placed at the narrowest common
scope under ARCH-092 with the `_internal` naming, cohesion, depth, reuse, and anti-duplication rules (ARCH-093–ARCH-097),
without requiring one file per helper or forcing unrelated helpers together.

| ID | Rule |
|---|---|
| ARCH-092 | A helper belongs at the **narrowest common architectural scope** that contains all of its current consumers. Its placement follows actual usage boundaries, not a preference for keeping it in its original file or extracting every helper into a separate module. Apply the first matching level: **(a)** one file only — keep the helper private to that file; create no separate module unless a distinct architectural requirement applies (ARCH-096); **(b)** multiple files in the same submodule — place the helper at that submodule scope in a dedicated `_internal.py` module, or in a dedicated `_internal/` package when multiple dedicated helper modules are justified (ARCH-094); **(c)** sibling submodules of one parent — place the helper once at their nearest common parent in `_internal.py`, or in `_internal/` when multiple helper modules are justified, not in one sibling; **(d)** different branches of one package — walk upward recursively to their nearest common architectural scope and use `_internal.py` or `_internal/` there according to ARCH-094; **(e)** multiple top-level submodules (flat modules) of one package — place the helper in that package's `_internal.py` module or `_internal/` package, according to ARCH-094; **(f)** multiple packages — place the helper in library-level `bynat/_internal` only with a domain-independent responsibility and ≥2 real package consumers (ARCH-060, ARCH-074). A helper MAY instead live in an existing module when its responsibility naturally belongs there (ARCH-095). Never place a helper above the scope that owns all of its consumers. |
| ARCH-093 | **Helper-file cohesion.** Helpers SHOULD share a file when their responsibilities are closely related, serve the same conceptual purpose, implement closely related behavior, or are complementary parts of one operation or workflow. Helpers with unrelated purposes, different responsibilities, or independent reasons to change MUST NOT be grouped merely because they are helpers, for convenience, or under one feature label. When distinct groups of helpers exist, organize them into responsibility-named modules rather than a generic `helpers.py`. A standalone dedicated internal-helper module uses the `_internal.py` name; modules within an `_internal/` collection are named for their responsibilities. Do not split closely related helpers without a meaningful cohesion or maintainability benefit. The objective is high cohesion and clear ownership, not minimizing or maximizing file count. |
| ARCH-094 | **`_internal` is the only prescribed generic internal-helper naming convention.** A single dedicated internal-helper module MAY be a direct `_internal.py` file. When a parent directory needs multiple dedicated helper modules at the same depth, prefer an `_internal/` directory inside that same parent, especially in leaf directories where no narrower scope exists; put independently named, cohesive modules inside it. Create neither `_internal.py` nor `_internal/` for a single-file-local helper; do not create an `_internal/` directory for only one helper module. An `_internal/` directory may contain distinct responsibility-named helper modules and does not imply they belong in one file or share one responsibility; file cohesion is governed by ARCH-093. `shared`, `_shared`, `utils`, `helpers`, and `common` are not prescribed alternatives for generic helper locations. A per-package `_internal` inherits its parent's dependency budget and is distinct from library-level `bynat/_internal` (ARCH-019). |
| ARCH-095 | **Private core ownership is retained.** Responsibility-specific private core modules and the package-local `_internal/` helper packages remain at their established paths. Helpers are not relocated or renamed for architectural preference; canonical ownership follows the implemented package structure and ARCH-102–ARCH-104. |
| ARCH-096 | **Helper extraction guards.** Do not create a separate module for a helper used by only one file unless a distinct architectural requirement exists; the mandatory separation of a helper from the core implementation it supports (ARCH-104) is such a requirement. In that case keep the helper at the narrowest scope allowed by ARCH-092 and use the naming/organization in ARCH-094, without requiring one file per helper. Before extracting similar code, verify that the behavior and contracts are identical; similar code with different contracts is not merged. Never duplicate a genuinely common implementation; one canonical definition per responsibility. Never place a helper above the scope that owns all of its consumers. Never create `_internal/` speculatively or before its trigger fires. Helper modules remain internal (underscore modules/packages, never added to a public package `__all__`). Helper placement must preserve the permitted dependency directions (ARCH-022/ARCH-023) and must not introduce a cycle. |
| ARCH-097 | **Rule of Three scope.** The Rule of Three applies only to broader reuse abstraction decisions — extracting a helper into a shared-scope or cross-domain scope for general reuse. It does not block same-branch or multi-file extraction within one package or submodule: a helper consumed by multiple files in the same branch may be extracted to the narrowest common scope under ARCH-092 without a third consumer. Consumer count remains a medium-weight signal (ARCH-067) for broader reuse only. |

For example, if an `analyzer/` leaf directory has several helper modules with distinct responsibilities, keep the
modules separate under one `_internal/` collection rather than scattering them beside the primary modules or
combining unrelated functions into one file:

```text
analytics/
└── analyzer/
    ├── distributions.py
    ├── numerical.py
    └── _internal/
        ├── filters.py
        ├── rules.py
        └── response_helpers.py
```

This is illustrative, not a proposed current-tree change. A single helper module at that level may instead be
`_internal.py`; a helper used by only one file stays in that file unless ARCH-096's exception applies.

---

## 2. Current architecture reference (Current facts)

This section records the architecture as observed in the current checkout. It is reference, not proposal. The architecture implemented in commit `946eb16` is the governing design decision; the conditional examples later in this document do not authorize reverting, relocating, or redesigning it.

### 2.1 Repository identity

| Item | Value |
|---|---|
| Package version | `0.6.6` |
| Python | `>=3.11` |
| Core dependencies | `numpy`, `pandas` |
| Optional extras | `translation`, `geocoding`, `currency`, `categorization`, `nlp`, `sql`, `dev` |
| Layout | flat `bynat/` at repository root (not `src/`) |

### 2.2 Current package tree

```text
bynat/
├── __init__.py
├── py.typed
├── _accessors/
│   ├── __init__.py
│   ├── _binding.py
│   └── dataframe.py
├── _internal/
│   ├── __init__.py
│   └── values.py
├── analytics/
│   ├── __init__.py
│   ├── _insights.py
│   ├── _internal/
│   │   ├── __init__.py
│   │   ├── appliers.py
│   │   └── security.py
│   └── analyzer.py
├── caching/
│   ├── __init__.py
│   ├── _internal/
│   │   ├── __init__.py
│   │   ├── diff.py
│   │   ├── keys.py
│   │   ├── paths.py
│   │   └── quarantine.py
│   ├── _migration.py
│   ├── _persistence.py
│   ├── _storage.py
│   └── manager.py
├── cleaning/
│   ├── __init__.py
│   ├── _columns.py
│   ├── _internal/
│   │   ├── __init__.py
│   │   ├── docs.py
│   │   ├── frames.py
│   │   ├── hierarchy.py
│   │   ├── matching.py
│   │   ├── optional.py
│   │   ├── outputs.py
│   │   ├── sql.py
│   │   └── validation.py
│   ├── _stats.py
│   ├── _text.py
│   ├── base.py
│   ├── io.py
│   └── enrich/
│       ├── __init__.py
│       ├── _currency.py
│       ├── _engine.py
│       ├── _geocode.py
│       ├── _internal/
│       │   ├── __init__.py
│       │   ├── lexicon.py
│       │   ├── mapping.py
│       │   ├── nlp_options.py
│       │   └── rates.py
│       ├── _nlp.py
│       ├── providers.py
│       └── _translate.py
└── profiling/
    ├── __init__.py
    ├── _builders.py
    ├── _internal/
    │   ├── __init__.py
    │   ├── computations.py
    │   └── processing.py
    ├── profile.py
    └── report.py
```

The current tree is the explicit public-API/private-core/`_internal` organization implemented by commit `946eb16` (`refactor: split packages into public API, private core, and _internal helpers`). Public API modules define supported interfaces and delegate substantive work to private core modules; private core modules own domain implementation; `_internal/` packages contain cohesive private helpers. The public package exports remain narrow; underscore-prefixed modules are private implementation paths. The accessor is implemented in `bynat/_accessors/dataframe.py`; the repository contains no generated type stub.

### 2.3 Current public API surface

| Surface | `__all__` |
|---|---|
| `bynat` | `cleaning`, `caching`, `analytics`, `profiling`, `read_csv`, `read_json` |
| `bynat.cleaning` | `BaseData`, `CsvFile`, `JsonFile` |
| `bynat.caching` | `CacheManager`, `CACHE_DIR_ENV_VAR`, `DEFAULT_CACHE_DIR`, `shared_cache_manager` |
| `bynat.analytics` | `Analyzer` |
| `bynat.profiling` | `profile`, `ProfileReport`, `DatasetProfile`, `ColumnProfile` |
| `bynat.cleaning.enrich` | `Translator`, `Geocoder`, `RateSource`, `GoogleTranslatorProvider`, `NominatimGeocoder`, `YFinanceRateSource` |
| `bynat._internal` | `dedupe_key` |
| `bynat._accessors` | `BynatAccessor` |

Importing `bynat` registers `df.bynat`. `BaseData`, `CsvFile`, `JsonFile`, `BynatAccessor`, `ProfileReport`, and `profile` are **not** root attributes. All 31 `.py` modules declare `__all__`.

### 2.4 Current dependency matrix

The module-level dependencies follow the package direction in ARCH-022. The root binds the four public packages, canonical loaders, and accessor registration. Public API modules delegate to private core modules. Cleaning core uses cleaning `_internal/`, enrichment core uses its `_internal/` helpers and cache internals, profiling uses profiling `_internal/` plus the canonical library value helper, and caching delegates persistence orchestration to `_persistence.py`, migration to `_migration.py`, and SQLite operations to `_storage.py`. Analytics owns its implementation in `_insights.py` and `analytics/_internal/` and imports no other `bynat` package. The runtime import graph is acyclic; `tests/contracts/architecture/test_dependency_edges.py` enforces the current boundaries.

### 2.5 Current private-import exceptions

Observed in the current checkout and enforced as the exact private-import inventory by the architecture dependency contract. Package-internal relative imports are not cross-package exceptions; root accessor registration is separately required by ARCH-006.

| # | Importer | Import statement |
|---|---|---|
| 1 | `bynat/cleaning/enrich/_engine.py` | `from bynat.caching._internal import cache_value_key` |
| 2 | `bynat/cleaning/enrich/_translate.py` | `from bynat.caching._internal import cache_has_value, cache_lookup_value` |
| 3 | `bynat/_accessors/dataframe.py` | `from bynat.cleaning._internal import is_basedata_type` |
| 4 | `bynat/cleaning/io.py` | `from bynat._internal import dedupe_key as _dedupe_key` |
| 5 | `bynat/profiling/_internal/computations.py` | `from bynat._internal import dedupe_key` |
| 6 | `bynat/_accessors/dataframe.py` | Imports canonical cleaning feature modules `_columns`, `_stats`, `_text`, `io`, and `cleaning.enrich._currency`, `_geocode`, `_nlp`, `_translate` for direct delegation. |

The canonical exports are `cache_value_key`, `cache_has_value`, `cache_lookup_value` in `_internal/keys.py`, and
`is_basedata_type` in `cleaning/_internal/outputs.py`. Importers 1–2 import the canonical names.

The root package's own registration import, `bynat/__init__.py → bynat._accessors`, is separately required by ARCH-006 ("Importing `bynat` registers `df.bynat` through a private
`_accessors` import") and is a root-to-registration-package import, not a functional-package cross-package
private-module import. The dependency-graph test observes it separately as a mandatory root edge; the count of
ARCH-024 exceptions remains exactly five.

### 2.6 Compatibility surfaces

| Contract | Current value | Preservation rule |
|---|---|---|
| Root/package `__all__` | See [§2.3](#23-current-public-api-surface) | ARCH-006, ARCH-007 |
| `read_csv.__module__`, `read_json.__module__` | `"bynat.cleaning.io"` | ARCH-012 |
| Function identity | `bynat.read_csv is bynat.cleaning.io.read_csv`; likewise `read_json` | ARCH-010 |
| `cleaning.io._dedupe_key` | `is bynat._internal.dedupe_key` | ARCH-010 |
| Accessor wrapped identity | `BynatAccessor.<method>.__wrapped__ is <functional module>.<func>` for `columns`, `text`, `stats` | ARCH-010, ARCH-011 |
| Accessor signature and docstring | `functools.wraps` in `bynat/_accessors/_binding.py` preserves `__signature__` and `__doc__` from the shared functions | ARCH-010, ARCH-075 |
| Documented path | `bynat.cleaning.io` is documented and pinned | ARCH-009 |
| Package attributes | `from bynat.cleaning import columns, io, stats, text`; `from bynat.cleaning.enrich import providers` | ARCH-011 |

### 2.7 State and lifecycle (Current)

| Resource | Owner | Creation | Disposal/cleanup |
|---|---|---|---|
| SQLite connection | `CacheManager` + `SQLiteStorage` | Lazy on first access; one connection per operation | Always closed; `BEGIN IMMEDIATE`; WAL; busy timeout |
| Shared manager registry | `shared_cache_manager` | First request per resolved absolute directory; module lock | Process-wide; never evicted |
| `BaseData` cache manager | `BaseData` | Lazily on first cached call; stored via metadata | Setter clears; recreation uses `BYNAT_CACHE_DIR`/default |
| Accessor cache manager | `BynatAccessor` | Lazily on first cached call | Held by reference; `with_cache(...)` binds another |
| File handles | `read_json`, `read_csv` | Context manager | Closed by `with` |
| SQLAlchemy engine | `save_to_sql` | Per call | `engine.dispose()` in `finally` |
| Provider resources | provider instances | Per call or thread-local | Thread-local translators; per-provider rate limiter |

### 2.8 Current architecture-governance state

The repository has existing boundary-verification evidence for the root API, package exports, accessor ownership,
profiling independence, and the canonical `_internal` helper. The dependency-graph enforcement required by ARCH-075 is
provided by the AST contract test `tests/contracts/architecture/test_dependency_edges.py` in the current
checkout: it models runtime package/module edges, rejects prohibited and unlisted edges, enforces the five
private-import exceptions with their exact symbol allowlists, detects runtime cycles with TYPE_CHECKING-only imports
ignored, and rejects row-wise iteration (ARCH-027) in production transformation paths. Automated checks are
separate from human review: the AST dependency contract plus the root public-API/export contract
(`tests/contracts/api/test_root_api.py`), accessor ownership/boundary tests
(`tests/contracts/architecture/test_accessor_boundary.py`, `tests/contracts/architecture/test_accessor_delegation.py`), profiling independence
(`tests/contracts/api/test_profiling_api.py`, `tests/contracts/architecture/test_profiling_package_boundary.py`), and the canonical `_internal` helper contract
(`test_internal_shared_helpers.py`) mechanically verify names, import edges, symbols, and signatures. Semantic
helper placement, public-API/core-implementation and helper/core separation, canonical ownership, discoverability,
cohesion, and whether indirection adds value are **not** inferred from module or package names alone; they remain
a human review responsibility under ARCH-101/ARCH-102–ARCH-104 and follow the decision procedure in
ARCH-066/ARCH-099. The naming-only contract
`tests/contracts/helpers/test_prohibited_helper_names.py` enforces the prohibited generic helper names of
ARCH-021/ARCH-081 and the `_internal` naming convention of ARCH-094 at any scope. There is no grandfathered
generic helper path in the current tree; this is objective naming enforcement, not evidence of semantic placement.
Import-Linter remains optional and deferred, not an unresolved blocker under ARCH-076: the repository-native AST
contract already satisfies ARCH-076 without a runtime dependency, and Import-Linter is a Phase 2 option adopted only
on a demonstrated repository need (AE-Q5). Private alias normalization (ARCH-045/046) is implemented in the
current checkout. Helper placement and organization rules ARCH-092–ARCH-097 are adopted and normative; the current
responsibility-named owner modules remain in place (ARCH-095). Public-API/core-implementation and helper/core
separation (ARCH-102–ARCH-104) describes the current responsibilities; no automated check decides semantic
ownership, and module placement remains documented in [§2.10](#210-module-responsibility-inventory-current) and subject
to explicit review. These rules authorize no code move.

### 2.9 Behavioral contracts (Current)

These are the twenty behaviorally significant flows. They are **Current** facts about how the architecture
behaves and are the contracts any internal reorganization must preserve. Testing procedures and coverage
lists are out of scope (see [§7](#7-testing-scope-separation)); only the architectural contract is recorded.

**F1 — `BaseData` construction and `JsonFile`/`CsvFile` loading.**
Entry: `BaseData(data=None, cache_dir=None, *args, **kwargs)`; `JsonFile(data=None, json_file_path=None, key=None, cache_dir=None, ...)`; `CsvFile(data=None, csv_file_path=None, cache_dir=None, read_kwargs=None, ...)`.
Contract: `BaseData` stores `_bynat_cache_dir` and `_bynat_cache_manager=None` via `object.__setattr__` and forwards the rest to `pandas.DataFrame`. `_constructor` returns `type(self)`, so pandas operations keep the subclass. `JsonFile`/`CsvFile` reinterpret a str/PathLike `data` as a file path only when no explicit path argument is given; an existing file becomes the load path, otherwise `FileNotFoundError('JSON file not found: ...'/'CSV file not found: ...')`; an explicit path argument is ignored when `data` is not None. `read_json` raises `TypeError` for a non-dict payload with `key`, `KeyError` for a missing key, and propagates `json.JSONDecodeError` for malformed JSON. Readers return a plain `pandas.DataFrame`. Construction creates no cache directory.

**F2 — `BaseData.cache_manager` metadata propagation.**
`_metadata = ['cache_manager']` makes pandas `__finalize__` copy the manager to derived frames; the property getter reads `_bynat_cache_manager` and, when None, builds `CacheManager(cache_dir=_bynat_cache_dir)` and stores it; the setter accepts a `CacheManager` or None (None clears). `view()` returns a plain `DataFrame` with no manager. `_bynat_cache_dir` is **not** metadata, so a derived frame's manager recreation falls back to `BYNAT_CACHE_DIR`/default — the open question AE-Q6. Manager construction creates no disk state; SQLite is created lazily on first real cache access.

**F3 — `df.bynat` registration, `with_cache`, `clear_cache_for_column`.**
`bynat/__init__.py` imports `_accessors`; `@register_dataframe_accessor("bynat")` registers `BynatAccessor`. `_method_signature` drops the frame parameter and any `cache_manager` parameter; `_with_inplace` inserts `inplace` at the class-declared slot or as the first keyword-only parameter for variadic functions. Cached methods inject `cache_manager=self.cache_manager`. Default behavior returns a new plain `DataFrame` and leaves the receiver untouched; `inplace=True` calls `self._obj._update_inplace(result)` and returns None, or the statistics frame when `get_hierarchical_stats=True`. `with_cache(...)` accepts a `CacheManager`, a directory, or None and returns a new accessor; `clear_cache_for_column` calls `manager.delete_column_cache`. One process-wide manager per resolved absolute directory via `_shared_managers` guarded by a lock.

**F4 — `CacheManager.load_function_cache` legacy migration/quarantine.**
Keys are validated (TypeError non-str; ValueError empty or containing path separators). On first miss the manager initializes the SQLite schema, migrates `<func>_cache.json` once (marker in `migration_metadata`, `INSERT OR IGNORE` so existing SQLite rows win), rebuilds `{bucket:{key:value}}` from `cache_entries` ordered by bucket,key, memoizes the live dict, and deep-copies it into `_baselines`. Corrupt/moved files are quarantined to `<file>.corrupt.<time_ns>.<uuid>` reserved with `O_CREAT|O_EXCL` then `os.replace`; unsupported nested buckets or unserializable values leave the source unmarked. Corruption yields an empty cache rather than raising. SQLite lock retry loop: 6 attempts, `0.05*(attempt+1)`s. Schema: `cache_entries(func_name,bucket,key,value_json,created_at)` with PK `(func_name,bucket,key)`; index `idx_cache_entries_func_bucket`; `migration_metadata(source_name,migrated_at)`.

**F5 — `CacheManager.delete_column_cache(func_name, col_name)`.**
Both keys validated as non-empty strings without path separators. Loads the function cache (triggering init/migration/rebuild), removes `func_cache[col_name]` in place, then `save_function_cache` diffs the live cache against the deep baseline and issues exact `(func_name,bucket,key)` DELETEs in one `BEGIN IMMEDIATE` transaction. Returns None; logs INFO when deleted and when absent. Concurrent additions after load are not in the baseline, so their identities are never deleted; a stale manager preserves rows added by other managers. If save fails, the in-memory removal remains pending and the next save retries.

**F6 — `save_to_json(df, file_path, orient='records', append=False, force_ascii=False, indent=4)`.**
Empty path → ValueError. Internal `export_df = df.copy()`; datetime/datetimetz columns reformatted `'%Y-%m-%d %H:%M:%S'`. Append: read existing with `pd.read_json(orient)`, `pd.concat(ignore_index=True)`, `duplicated(keep='first')`, with a TypeError fallback that maps object columns through `_internal.dedupe_key` before `duplicated`. Non-append: compare `to_json` output with `json.load(existing)` and skip on equality. Writes with `to_json(orient,force_ascii,indent)`; `makedirs(parent, exist_ok=True)`. Returns None always; logs `[SKIP]`/`[APPEND]`/`[OVERWRITE]`. Append with unreadable/incompatible JSON raises `ValueError('Cannot append ...')` (only `ValueError` is caught); non-append unreadable/malformed existing file logs a warning and overwrites. The input frame is never mutated. A relative bare filename writes to the cwd.

**F7 — `save_to_sql(df, table_name, database_type, database_user, database_password, database_host, database_port, database_name, database_driver=None, columns_types=None, chunk_size=None, fast_executemany=False, if_exists='append', index=False)`.**
Validation order: `table_name` non-empty, `if_exists` in fail/replace/append, `database_type` non-empty, then dialect requirements — `sqlite*` needs `database_name` (`':memory:'` special); `mssql`/`sqlserver` needs all five connection fields plus `database_driver`; other dialects need all five. All checks precede the SQLAlchemy import. URL building uses `quote_plus` for user, password, and the SQL Server driver only. Lazy import via `import_optional`; `export_df = df.copy()`; tz-aware datetimes made naive on the internal copy only; `engine.dispose()` in `finally`. Returns None; database exceptions propagate.

**F8 — `read_csv(csv_file_path, **read_kwargs)` / `read_json(json_file_path, key=None)`.**
`os.fspath` + `os.path.isfile` → `FileNotFoundError` when missing. `read_json` opens utf-8, `json.load`, optional key selection, `pandas.json_normalize`; `read_csv` delegates entirely to `pandas.read_csv`. Both return a new plain `pandas.DataFrame` (not `BaseData`). An empty array payload → empty frame. `json.JSONDecodeError` and pandas parser errors propagate.

**F9 — `handle_outliers(df, *target_cols, hierarchy_cols, min_samples=5, get_hierarchical_stats=False)`.**
Missing target columns are skipped; a str `hierarchy_cols` is normalized to a one-item list; empty/None hierarchy logs a warning and returns a copy. `min_samples` is deliberately NOT validated (tracked defect PD-02). `_hierarchical_outlier_masks` evaluates the full hierarchy then pops the last column per level; per level it groups by the current hierarchy columns with `dropna=False, observed=True, sort=False`, requires `count >= min_samples`, computes `quantile([.25,.75])`, and flags numeric `< q1-1.5*IQR` or `> q3+1.5*IQR`; masks are applied with `result.loc[outliers] = np.nan` as the generator is consumed, so later levels see the NaNs. Shape/index/columns preserved; dtypes may upcast.

**F10 — `drop_outliers(...)`.**
Same validation and hierarchy semantics as F9. It accumulates a drop mask across every yielded `(target, outliers)` pair **without** mutating the result between levels (so outliers stay in later quartiles), then drops via `result.iloc[np.flatnonzero(~drop_mask)]`. Original index labels are retained (not reset); columns/dtypes unchanged.

**F11 — `fill_missing(df, *target_cols, strategy='median', hierarchy_cols=None, min_samples=1, fallback_global=False, get_hierarchical_stats=False)`.**
`min_samples` first: int ≥ 1, bool rejected, else ValueError. Then valid target columns; none → warning + unchanged copy **before** strategy validation (so an invalid strategy with no valid target does not raise). Strategy lowercased; allowed median/mean/mode/mod; mod→mode; invalid → ValueError. Per column, hierarchy levels are progressively popped; median/mean use `groupby(current_group, dropna=False)[col].transform(strategy)` masked by `transform('count') >= min_samples`; mode uses grouped non-null counts sorted by hierarchy asc + count desc, group totals ≥ min_samples, `drop_duplicates`, `left_merge_aligned` by position. `fallback_global` uses a column-wide statistic or global mode. Statistics come from `df` itself (documented leakage caveat). `hierarchy=None` + `fallback_global=False` performs no imputation. Index/order/columns preserved; dtypes may change.

**F12 — `fill_missing_from(df, dataset, *target_cols, match_cols=None, targets=None, strategy='median', hierarchy_cols=None, min_samples=1, fallback_global=False, get_hierarchical_stats=False)`.**
Validation order: dataset None/empty/duplicate columns; df duplicate columns; `match_cols` dict/str keys+values/existence in both frames; strategy; min_samples; resolved reference columns; hierarchy existence in both frames; target/hierarchy overlap; numeric dtype checks for median/mean. Statistics are computed exclusively from `dataset` (leakage-free); the reference frame is never written. Only NaN target cells are filled; `match_cols` renames reference columns for lookup and unmaps statistics labels. `hierarchy=None` + `fallback_global=True` is plain reference column-wide imputation. `target_cols` is flattened exactly one level.

**F13 — `extract_keywords(df, *source_cols, remove_extracted=False, use_regex=False, **target_cols_and_keywords)`.**
No keyword validation; str/bytes/non-iterable keyword values are wrapped as one-item lists; blank/None keywords are stripped and dropped; an empty cleaned list skips the target; missing source columns are ignored; no valid sources → unchanged copy. Valid source columns are combined `fillna('').astype(str)` with `' '` and factorized. The literal path uses a combined lookaround regex `(?<!\w)(?:k1\|k2...)(?!\w)` IGNORECASE, or a pyahocorasick automaton when installed **and** every keyword is ASCII (per-text `isascii` gate); priority = keyword list order. The regex path compiles each pattern, wraps groupless patterns in `(...)`, and uses `Series.str.extract` first capture group, highest-priority pattern wins. Results are title-cased; an existing target column is filled only where NaN and then title-cased for every non-null cell. `remove_extracted` applies patterns once per unique text and collapses whitespace. Unicode keywords force the regex path; pyahocorasick absence silently falls back.

**F14 — `categorize_by_reference(df, *source_cols, target_col, reference, default_category='Other')`.**
Hard-requires pyahocorasick (ImportError naming it). Missing source columns are ignored; no valid sources → unchanged copy before reference handling. Non-dict/empty reference → `target_col = default_category` for all rows. Keyword values non-list are wrapped; blank/None ignored; none valid → default category. The automaton is keyed by `(length, reversed-category priority, category)`; the whole-word boundary check uses `str.isalnum()` only, so `_` is not a word character and `score` DOES match inside `under_score` (a documented docstring contradiction). Longer keyword wins; equal length → later reference category wins. Case-insensitive; one map per unique text.

**F15 — `extract_entities_nlp(df, *source_cols, lexicon_source, spacy_model='en_core_web_sm', exclude_pos=None, disable=('parser','ner'), save_every=1000, noisy_terms=None, cache_manager, **target_cols_and_json_keys)`.**
Validation order includes the `noisey_terms` typo → TypeError, disable normalization (required pipes `tok2vec`/`tagger`/`attribute_ruler`/`lemmatizer`/`morphologizer` cannot be disabled; unknown pipes warn), `noisy_terms` lowercased, `exclude_pos` uppercased, `save_every` positive int, at least one target kwarg, lexicon file/dict loaded, terms extracted (none → ValueError), valid source columns, non-empty texts, `spacy_model` non-str/blank. spaCy is imported lazily only when at least one text is uncached. The cache bucket is `sha1(target_col, model_identifier, sorted(disable))[:16]` prefixed `nlp_`. Matcher patterns use `LEMMA IN [lemma.lower(), lemma.title()]` and `LOWER` text; texts are piped with `batch_size=100`; title-cased lemma spans are collected into sets; single-char non-uppercase/non-alpha and excluded-POS single tokens are rejected. Output columns are lists; ordering derives from set iteration and is not guaranteed. Per-text matcher exceptions are captured and left uncached.

**F16 — `convert_to_usd(df, *target_cols, country_col, year_col, new_cols=True, round_decimals=None, provider=None, cache_manager)`.**
Requires `country_col`/`year_col` (else warning + copy) and valid target columns. `pycountry` and `babel.numbers` are imported eagerly; the default provider imports `yfinance`. Unique country/year pairs are deduplicated and dropped when null; years are made numeric; `min_year_limit` is the earliest numeric year in the data and `current_year` is the localtime year. Currency codes resolve via `pycountry.countries.search_fuzzy(...)[0]` and `Babel.get_territory_currencies(alpha_2)[0]`; `LookupError` is cached as None. Missing rate keys walk `range(year, min_year_limit, -1)`; one `yearly_rates` call per currency covers min..max missing years; float rates are stored, None misses only for years < current_year. `(country,year) -> rate` is left-merged and the value is divided by the rate (rate is local currency per 1 USD; USD short-circuits to 1.0). New `<col>_usd` columns are appended when `new_cols=True`, else originals are overwritten; unknown currency/year → NaN. Network/provider failures are not cached; past-year misses are cached; future-year misses are re-fetched. Buckets `currency_codes` and `exchange_rates` under func_name `convert_to_usd`.

**F17 — `fill_missing_coordinates(df, *fallback_cols, lat_col, long_col, save_every=1000, user_agent='data_cleaning_core_geocoder', retry_not_found=False, provider=None, cache_manager)`.**
`save_every` positive int first; required lat/long columns and at least one valid fallback column else warning + copy. Builds `__temp_geocode_query__` from fallback columns joined `', '` skipping null/empty/`'nan'`/`'none'`/numeric values; `mask_missing = lat or long isna`. The provider defaults to `NominatimGeocoder(user_agent)`; `geocode(query)` tries the query then repeatedly drops the leftmost comma-separated part. Bucket `geocode_queries` key=str; `is_cached` treats cached None as a miss only when `retry_not_found`. Existing coordinates are preserved; only missing cells are updated; the temp column is always removed. Not-found queries are cached as None; service exceptions are uncached. Nominatim is rate-limited to 1 req/s via geopy.

**F18 — `Analyzer` methods.**
`Analyzer(dataframe)` raises TypeError for a non-DataFrame and stores a defensive copy. Five public methods: `get_categorical_distribution`, `get_numerical_aggregation`, `get_time_series`, `get_kpi_value`, `get_bins`. Filters support scalar equality, list `isin`, and dict operators (`>`,`<`,`>=`,`<=`,`!=`,`==`,`contains`); `>`,`<`,`>=`,`<=` coerce with `pd.to_numeric` while `==`/`!=` compare raw; unknown columns are ignored and invalid operations logged/skipped. Computed rules support `where`/`set_col`/`set_value`, `new_col`/`expression`, and `source_col`/`method`/`new_col`; `analytics._internal.security.is_safe_expression` blocks `__`, `@`, `import`, `lambda`, `;` case-insensitively and is documented as "a guardrail, not a full sandbox". Responses are plain JSON-serializable dicts (`{'data': ...}` plus kwargs; KPI adds `title`); empty conventions are `{'data': []}` or `{'data': None, 'title': ...}`. The analyzer does not mutate its constructor frame or method inputs.

**F19 — `profile(df, *columns, output_type=None)` and output-type adaptation.**
Core: `df` must be a `pd.DataFrame` (else TypeError); a single collection argument may be list/tuple/set; a missing named column raises KeyError. Dispatch: None/`ProfileReport` → report; dict → `report.to_dict()`; `pd.DataFrame` → `report.to_dataframe()`; anything else → TypeError. `BaseData.profile` and the module-level accessor `profile` pre-check `is_basedata_type(output_type)` and construct `output_type(data=summary_frame)`. The core computes dataset metrics (row/column/total cells, missing count/proportion, duplicate rows `keep='first'`, empty columns, deep memory, dtype counts) and per-column kind statistics (numeric, categorical, boolean, datetime, other; unavailable stats are None), using `_internal.dedupe_key` for unhashable values. `ProfileReport.columns` keeps the last occurrence of a duplicate column name while `column_list` preserves every position. Never mutates input, index, or column names; read-only.

**F20 — Optional-dependency failure behavior (cross-cutting).**
`import_optional(module_name, distribution, feature)` wraps `ImportError` as `ImportError('<feature> requires the optional '<distribution>' dependency.')`, chaining the original; it currently catches any ImportError raised during module import, masking real defects inside an installed optional package (recorded follow-up). Hard-required at call: `categorize_by_reference` → pyahocorasick; `extract_entities_nlp` → spacy/spacy.matcher; `impute_by_language`/`translate_conditional_column` → langdetect; `fill_missing_coordinates` → geopy when no provider; `convert_to_usd` → pycountry/Babel and yfinance when no provider; `save_to_sql` → SQLAlchemy after argument validation. Soft/optional: `extract_keywords` → pyahocorasick with silent regex fallback. Providers import `deep_translator`/`geopy.geocoders`/`geopy.extra.rate_limiter`/`yfinance` in their constructors. `cached_map` calls `on_fetch_start(total)` only when uncached work exists, and exceptions from it propagate. Cached methods call `get_column_cache` (which may initialize SQLite) before constructing the provider/model. `provider=` injection bypasses default imports. Failures occur before any result is produced; no partial frame is returned.

### 2.10 Module responsibility inventory (Current)

Public status legend: **Public** = reachable through an intentional package `__all__`; **Package-internal** =
importable module not re-exported in a package `__all__`; **Private** = underscore module/package outside any
public API.

| Path | Responsibility | Main contents | Internal dependencies | Status |
|---|---|---|---|---|
| `bynat/__init__.py` | Root API and accessor registration | 6-name `__all__`; package bindings; `read_csv`/`read_json`; private `_accessors` import | all packages, `_accessors`, `cleaning.io` | Public |
| `bynat/py.typed` | PEP 561 typing marker | marker file | none | Public |
| `bynat/_accessors/__init__.py` | Export the accessor class | `BynatAccessor` | `_accessors.dataframe` | Package-internal |
| `bynat/_accessors/_binding.py` | Wrapper factories for accessor methods | `_method_signature`, `_with_inplace`, `_frame_method`, `_cached_frame_method` | none | Private |
| `bynat/_accessors/dataframe.py` | Registered `df.bynat` accessor and delegation | `BynatAccessor`, module-level `profile` and analytics adapters | `cleaning`, `analytics`, `caching`, `profiling`, `_binding` | Package-internal |
| `bynat/_internal/__init__.py` | Export the canonical shared helpers | `dedupe_key`, `cache_value_key`, `cache_has_value`, `cache_lookup_value`, `is_named_type_from_module` | `_internal.keys`, `_internal.types` | Private |
| `bynat/_internal/keys.py` | Domain-independent value and cache-key normalization | `dedupe_key`, `cache_value_key`, `cache_has_value`, `cache_lookup_value` | none | Private |
| `bynat/analytics/__init__.py` | Export `Analyzer` | `Analyzer` | `analytics.analyzer` | Public |
| `bynat/analytics/analyzer.py` | Public analytics interface | `Analyzer` methods and delegation | `_insights`, analytics `_internal` | Public API |
| `bynat/caching/__init__.py` | Export cache API | `CacheManager`, constants, `shared_cache_manager` | `caching.manager` | Public |
| `bynat/caching/_internal/` | Caching-specific diff, path, and quarantine helpers | `diff`, `paths`, `quarantine` | none | Private |
| `bynat/caching/_persistence.py` | Cache load/save orchestration | `load_cache`, `persist_cache` | caching internals | Private |
| `bynat/caching/_migration.py` | Legacy JSON migration and quarantine | `migrate_legacy_json_cache`, `quarantine_corrupt_cache_file` | `caching._storage` | Private |
| `bynat/caching/_storage.py` | SQLite persistence | `SQLiteStorage`, `connect_sqlite`, constants | none | Private |
| `bynat/caching/manager.py` | Public cache API and manager | `CacheManager`, registry, constants | `_persistence`, `_migration`, `_storage`, caching `_internal` | Public API |
| `bynat/cleaning/__init__.py` | Export class facade | `BaseData`, `CsvFile`, `JsonFile` | `cleaning.base` | Public |
| `bynat/cleaning/_internal/` | Cleaning-scoped cohesive helpers | frames, hierarchy, matching, optional imports, outputs, SQL, validation, docs | cleaning core | Private helpers |
| `bynat/cleaning/base.py` | Supported `DataFrame` subclass API | `BaseData`, `JsonFile`, `CsvFile` | private cleaning cores, caching, profiling | Public API |
| `bynat/cleaning/_columns.py` | Column/reshape core | 9 functions | `_internal` | Private core |
| `bynat/cleaning/io.py` | JSON/CSV loaders, JSON/SQL writers | `read_json`, `read_csv`, `save_to_json`, `save_to_sql` | `_internal`, library `_internal` | Public API |
| `bynat/cleaning/_stats.py` | Hierarchical statistics/imputation/outliers | 5 public functions | `_internal` | Private core |
| `bynat/cleaning/_text.py` | Keyword/truncation/categorization | 3 public functions | `_internal` | Private core |
| `bynat/cleaning/enrich/__init__.py` | Export provider types | 6 provider symbols | `enrich.providers` | Package-internal |
| `bynat/cleaning/enrich/_currency.py` | Cached USD conversion | `convert_to_usd` | `caching`, cleaning `_internal`, `_engine`, `providers` | Private core |
| `bynat/cleaning/enrich/_engine.py` | Shared cached-lookup engine | `cached_map`, `SKIP`, `Fetch`, `FetchMany` | `caching`, cache `_internal`, enrichment `_internal` | Private core |
| `bynat/cleaning/enrich/_internal/` | Enrichment-specific helpers | mapping, rate-limited calls, translation batching, lexicon, NLP options, rates | enrichment core | Private helpers |
| `bynat/cleaning/enrich/_geocode.py` | Cached geocoding | `fill_missing_coordinates` | `caching`, cleaning `_internal`, `_engine`, `providers` | Private core |
| `bynat/cleaning/enrich/_nlp.py` | Cached spaCy entity extraction | `extract_entities_nlp` | `caching`, cleaning `_internal`, `_engine`, enrichment `_internal` | Private core |
| `bynat/cleaning/enrich/providers.py` | Provider protocols and default adapters | 3 protocols + 3 adapters | cleaning `_internal` | Package-internal |
| `bynat/cleaning/enrich/_translate.py` | Language imputation and cached translation | 3 public functions | `caching`, cache `_internal`, cleaning/enrichment `_internal`, `_engine`, `providers` | Private core |
| `bynat/analytics/_insights.py` | Analytics computation implementation | response builders | analytics `_internal` | Private core |
| `bynat/analytics/_internal/` | Analytics helper implementation | filtering, rule application, expression safety | analytics core | Private helpers |
| `bynat/profiling/_builders.py` | Profiling report assembly | report builders | profiling `_internal`, report models | Private core |
| `bynat/profiling/_internal/` | Profiling computations and processing | metric/type helpers | library `_internal` | Private helpers |
| `bynat/profiling/__init__.py` | Export profiling API | `profile`, 3 report models | `profiling.profile`, `profiling.report` | Public |
| `bynat/profiling/profile.py` | Public profiling API | `profile` and validation/output dispatch | `_builders`, `report` | Public API |
| `bynat/profiling/report.py` | Report data models | `ProfileReport`, `DatasetProfile`, `ColumnProfile` | none | Package-internal |

**Current organization (Current facts).** Public API modules expose supported interfaces; underscore-prefixed modules contain private core implementations; cohesive shared helper sets live in package-level `_internal/` directories; library-wide domain-independent value normalization lives in `bynat/_internal/`. Commit `946eb16` establishes this organization. Keep these file locations, names, import boundaries, and responsibility assignments as the standard; do not treat conditional growth examples as authorization to reorganize them.

**Private core and `_internal/` responsibilities (Current).** Responsibility-specific core modules retain their established underscore-prefixed names. Each package-local `_internal/` owns the cohesive helpers for that scope; `bynat/_internal/` remains the library-wide domain-independent collection and owns `dedupe_key`. The public initializers curate supported exports; internal modules are imported by canonical module path and are not compatibility facades.

### 2.11 Documented hazards and dispositions (Current)

These are verified findings about the current implementation. They are not structural proposals; each has an
explicit disposition.

| # | Finding | Disposition |
|---|---|---|
| 1 | `BaseData` methods carry literal docstrings in `bynat/cleaning/base.py` (1,569 of 2,128 lines), and accessor methods inherit shared-function docstrings through `functools.wraps` in `_accessors/_binding.py`, so docstring edits must keep those two surfaces consistent. | Behavioral/maintenance cost, not an ownership defect. Retain; drift is caught by the doc-contract tests. |
| 2 | `BaseData._finish_with_stats` and `bynat._accessors._binding._frame_method(stats=True)` (with the accessor methods it generates) independently implement the same `inplace` + statistics return semantics; parity is pinned by tests, but a semantic change could satisfy one side silently. | Parity pinned; a future contract change must update both. Retain (no structural change now). |
| 3 | `is_basedata_type` identifies `BaseData` by MRO string matching on `__name__ == 'BaseData'` and `__module__ == 'bynat.cleaning.base'`; renaming or relocating the class silently disables `BaseData` profile output adaptation. | Intentional (avoids a lower-level-to-facade import). Retain; recorded as a **relocation hazard**. |
| 4 | `shared_cache_manager` constructs a throwaway `CacheManager` probe on every call and registers managers by absolute path in a dict with no eviction; long-lived processes accumulate manager instances. | Intentional lifecycle; process-wide registry. Retain. |
| 5 | `import_optional` catches any `ImportError` raised during module import and rewrites it as a missing-dependency error, masking genuine defects inside an installed optional package. | Behavioral follow-up (narrow to `ModuleNotFoundError` for the target module, or re-raise when the module is present). |
| 6 | `analytics._internal.security.is_safe_expression` guards expressions passed to `DataFrame.eval` with a token denylist (`__`, `@`, `import`, `lambda`, `;`) documented as "a guardrail, not a full sandbox"; the dynamic eval remains a code-injection surface. | Documented guardrail, not a sandbox. Security/behavioral follow-up, not architectural. |
| 7 | `dedupe_key` serializes set, NumPy array, list, and tuple to the same JSON text (for example `[1, 2]`, `(1, 2)`, `{1, 2}`, `np.array([1, 2])` all become `'[1, 2]'`), so profiling duplicate and distinct counting treats values of different Python types as identical. | Behavioral follow-up. |
| 8 | `JsonFile`/`CsvFile` reinterpret any str or path-like `data` as a file path and raise `FileNotFoundError` when it does not exist; with an explicit path argument the string reaches pandas and raises `ValueError('DataFrame constructor not properly called!')`. | Behavioral edge case; see the F1 contract. |
| 9 | The pre-refactor `_get_file_path` wrapper and its JSON-filename logging are removed; current `delete_column_cache` logs the function and column identifiers without claiming a JSON backing file. | Resolved by the cache persistence refactor. |
| 10 | `YFinanceRateSource` uses `ticker.history(end=f'{end_year}-12-31')`; yfinance's end is exclusive, so December 31 closes are excluded from the yearly mean. | Behavioral follow-up; verify against the intended inclusive-range contract. |
| 11 | `ProfileReport.columns` keeps only the last occurrence of a duplicate column name while `column_list` preserves every position; consumers indexing by name silently lose earlier profiles. | Documented asymmetry; behavioral follow-up. |
| 12 | `NominatimGeocoder`'s default `user_agent` is still `'data_cleaning_core_geocoder'`, a stale pre-rename identifier sent to an external service; `GoogleTranslatorProvider` class knobs `max_workers`/`min_interval` are the only provider tuning surface and are implicit rather than injected. | Behavioral follow-up. |

**Component assessments marked `Adjust` — decisions.** `BaseData`, `bynat._accessors._binding._frame_method`, and
`bynat._accessors._binding._cached_frame_method` (dual inplace/stats contract): **Deferred**, no structural change now; if the contract
changes, extract one shared contract helper and pin parity. `BaseData` literal docstrings and accessor `functools.wraps` doc inheritance: **Retain**, drift already fails
the doc-contract tests. `import_optional`: **Deferred** behavioral follow-up. `cache_value_key`,
`cache_has_value`, `cache_lookup_value`: **Implemented**, covered by the alias normalization. `is_basedata_type`:
**Retain**, documented relocation hazard. `shared_cache_manager`: **Retain**, intentional lifecycle.

---

## 3. Conditional future architecture (Historical proposals; not current authority)

This section preserves earlier conditional evolution analysis. It is not a roadmap and authorizes no structural change. Where any stage, tree, module path, import convention, or example conflicts with the architecture implemented by commit `946eb16` and recorded in §2, that example is superseded and MUST NOT be used to reorganize the current architecture. A future architectural change requires a separate explicit decision; these examples do not provide that authorization.

### 3.1 Stage model

| Stage | Structure | Status | Trigger to enter |
|---|---|---|---|
| **A** | Public API modules, private core modules, and scope-specific `_internal/` packages | **Current (implemented by `946eb16`)** | — |
| **B** | Capability subpackages inside a domain | Conditional | ≥2 capability clusters, each ≥2 modules with distinct change reasons |
| **C** | Domain-internal layers (validation / transformation / I/O) | Conditional | A capability subpackage has ≥2 internal layers with distinct consumers and change reasons |
| **D** | New top-level domain package | Conditional | Coherent capability with its own public contract, lifecycle, and no dependency on existing package internals |
| **E** | Extraction into separate distributions/services | Rejected (far future) | Concrete deployment, versioning, or team-boundary requirement |

Stage B is a package-level grouping, often implemented through M2 conversions. M1 and M2 are module-level
operations. Stage C is a layer-level operation inside a capability subpackage. A scenario can combine
operations (Scenario 1 is Stage B implemented through M2 conversions).

| From | To | Trigger (all conditions required) | Anti-trigger (any condition blocks) | Verification |
|---|---|---|---|---|
| A | B | (1) ≥2 capability clusters in one package; (2) each cluster has ≥2 modules; (3) clusters have distinct change reasons; (4) a package-level `__init__` can curate a coherent surface | A cluster is a single module; a cluster is a catch-all; the split creates a cycle; the split only moves files | Change-coupling shows clusters change independently; one-sentence responsibility per subpackage |
| B | C | (1) a capability subpackage has ≥2 internal layers; (2) layers have distinct consumers; (3) layers change for different reasons; (4) layering reduces coupling | Layers are thematic; layering adds a cycle; layers are single-function | §3.1 procedure; dependency graph shows one-way layer flow; no new cycle |
| A/B | D | (1) a coherent capability with its own public contract; (2) ≥2–3 operations; (3) no dependency on existing package internals; (4) a distinct user workflow | The capability is a single function; it needs another package's private internals; it is a theme | New package passes the boundary checks; no cross-package private imports |
| Any | E | A concrete deployment, versioning, or team-boundary requirement | No such requirement | Not applicable now |

**Counts are sanity checks.** “≥2 clusters”, “≥2 modules”, and similar counts are guards against trivial
splits, not decision criteria. The criterion is demonstrated responsibility divergence and an improvement in
cohesion, change coupling, or dependency direction (R-11/R-12). **What does not trigger a stage change:** a
module crossing a line-count threshold; a new feature that fits an existing module's responsibility; a desire
for a “cleaner-looking” tree; a single new consumer of a private helper; a single optional dependency.

**Stage C transition procedure (conditional).** 1. Confirm the host is a capability subpackage (Stage B), not
a flat module. 2. Identify ≥2 internal layers with distinct consumers and change reasons. 3. Verify that
layering reduces coupling and does not add depth for its own sake. 4. Define a one-way dependency flow between
layers (for example validation → transformation → assembly) and record it in the dependency model. 5. Add
layer modules with `__all__` and update the package `__init__.py` to preserve the existing surface. 6. Verify
no cycle, no public path change, and no new cross-package private import. 7. Record the trigger, the
one-sentence responsibility of each layer, and the rollback. Illustrative only (not proposed): if
`cleaning/stats/` grew so that parameter validation, hierarchy computation, and output assembly changed for
different reasons, it could introduce `_validation.py`, `_hierarchy.py`, and `_assembly.py` with a one-way
flow `_validation → _hierarchy → _assembly`.

### 3.2 Module model

| State | Description | Entered when |
|---|---|---|
| **M0** | Single module | Default |
| **M1** | Split: one module becomes ≥2 modules in the same package | ≥2 cohesive responsibilities with different change reasons; each result non-trivial; no cycle |
| **M2** | Module → package: a module becomes a same-named package with submodules and a curated `__init__` | Responsibilities have grown into ≥2 submodules with distinct consumers/change reasons |
| **M3** | Merge: two or more modules become one | The modules always change together and form one responsibility, or a split produced anaemic modules |
| **M4** | Module addition: a new module is added to an existing package | A new cohesive responsibility with a real consumer; no split/merge needed |

**M2 naming rule.** A conversion keeps the same name (`columns.py` → `columns/`, `text.py` → `text/`,
`stats.py` → `stats/`, `io.py` → `io/`, `providers.py` → `providers/`) because repository code imports these as
package attributes (`from bynat.cleaning import columns, io, stats, text`; `from bynat.cleaning.enrich.providers import ...`).
Renaming the package would break those imports and is not a compatibility-safe internal move.

| Decision | Trigger (all required) | Anti-trigger | Acceptance |
|---|---|---|---|
| Keep unchanged | One responsibility; one reason to change; no dependency violation | — | Existing checks pass |
| Split | ≥2 responsibilities with different change reasons; each part non-trivial; no cycle; no public path change | LOC alone; a part would be a one-function module | Each part has a one-sentence responsibility; change-coupling shows independence |
| Convert to package | ≥2 sub-modules with distinct consumers; a coherent package surface; no cycle | The module is cohesive; sub-modules would be one-function | Package `__init__` curates a small surface; dependency direction preserved |
| Merge | Modules always change together and form one responsibility; or a split produced anaemic modules | Modules change for different reasons | One-sentence responsibility; no lost coverage |
| Extract shared helper | Broader reuse: ≥2 real consumers with the same contract and a stable domain-independent responsibility (ARCH-097). Same-branch/multi-file: narrowest common scope under ARCH-092, no third-consumer gate. Helper/core separation (ARCH-104) is mandatory regardless of consumer count | Similar code with different contracts; a single consumer for a new shared abstraction; widening a one-file helper into a broader shared abstraction instead of separating it from its core under ARCH-104 | Canonical owner has one definition; consumers import it; placement is the narrowest common scope; helper/core separation (ARCH-104) preserved |
| Introduce a layer | ≥2 internal layers with distinct consumers and change reasons | Thematic layering; added depth without coupling benefit | One-way dependency flow; no cycle |

**Component-level evolution.** A class/protocol is introduced only with a concrete consumer and a lifecycle or
structural contract; growth does not justify new base classes or protocols. A shared engine (like
`cleaning/enrich/_engine.py`) stays shared only while its contract is stable and its consumers are real; if a
second consumer needs a different contract, the correct move is a separate implementation, not a parameterized
engine.

### 3.3 Historical implementation phases (superseded)

The following phase table predates commit `946eb16` and is retained only as history. Its status, tree, and import-path assumptions are superseded wherever they differ from the current architecture and current verification evidence. It is not scheduled work.

| Phase | Scope | Entry | Acceptance | Checkpoint | Rollback |
|---|---|---|---|---|---|
| 0 | Freeze the baseline commit; record the strategy and decision records | This constitution accepted | Baseline commit recorded; decisions traceable | Review against the design | Not applicable (documentation only) |
| 1 | Remove private alias blocks and dead wrappers; update consumer imports; update one test reference; add the AST dependency contract check | Phase 0 complete | Full suite, ruff, mypy, and doc-sync pass; no public change; the dependency check passes and fails on a prohibited edge | Independent diff review; verify no public signature/docstring change | Revert the commit; no public API change |
| 2 | Adopt Import Linter as a dev dependency; add `protected` contracts for the five documented edges; optionally enable Ruff `PLC2701` | Phase 1 complete; a CI enforcement need is identified | `lint-imports` passes; CI job added | Verify all five edges are represented | Remove the dev dependency and config |

**Explicitly deferred (not near-term):** splitting `base.py`; a generic transformation engine; a lazy
execution layer; expanding `caching.__all__`. Analytics accessor methods were implemented (AE-Q3, [§4](#4-deferred-and-superseded-decisions)).

### 3.4 Historical conditional scenarios E1–E6 (superseded where conflicting)

Each scenario is a stress test from the earlier evolution model, **not scheduled work or authority to change the implemented architecture**. None is sequential; each may occur
independently, in a different order, or never. Each opens only when its responsibility evidence is demonstrated,
not when a count is reached.

**E1 — Cleaning grows 5–10× (Stage A→B via M2).**
Premise: `cleaning` accumulates many new transformation families (column, text, statistical, I/O, enrichment).
Trigger evidence: ≥2 capability clusters (for example column structure, text processing, statistical
operations, I/O) each with ≥2 modules; clusters change for different reasons (supporting evidence, not the
justification); the justification is demonstrated divergence in responsibilities, invariants, or ownership,
and an improvement in cohesion, change coupling, or dependency direction; a package-level `__init__` can
curate a coherent surface for each cluster.
Target structure (conditional):

```text
bynat/cleaning/
├── __init__.py                 # unchanged: exports BaseData, CsvFile, JsonFile
├── base.py                     # unchanged facade
├── _common.py                  # cleaning helpers
├── _outputs.py                 # output conversion
├── columns/                    # capability: column structure (replaces columns.py)
│   ├── __init__.py             # re-exports the 9 column functions
│   ├── rename.py
│   ├── reshape.py
│   └── split.py
├── text/                       # capability: text processing (replaces text.py)
│   ├── __init__.py             # re-exports the 3 text functions
│   ├── keywords.py
│   ├── truncation.py
│   └── categorization.py
├── stats/                      # capability: statistical operations (replaces stats.py)
│   ├── __init__.py             # re-exports the 5 statistics functions
│   ├── outliers.py
│   ├── imputation.py
│   └── hierarchy.py
├── io/                         # capability: file/SQL I/O (replaces io.py)
│   ├── __init__.py             # exposes the public reader/writer interface and delegates (ARCH-102); see §3.7
│   ├── readers.py
│   └── writers.py
└── enrich/                     # already a capability subpackage
```

Conversion constraints: each new package keeps the module's name and re-exports the symbols that repository
code and tests access (`from bynat.cleaning import columns, io, stats, text` and the accessor `__wrapped__`
identity targets). Every new module, including each submodule, declares `__all__` with non-underscore symbols.
`io/__init__.py` must additionally preserve `read_csv.__module__ == "bynat.cleaning.io"`,
`read_json.__module__ == "bynat.cleaning.io"`, and `io._dedupe_key is _internal.dedupe_key`. Acceptance:
public `__all__` unchanged; no public import path change; the public-interface/core-implementation separation follows
ARCH-102–ARCH-104 and delegates without extra wrapper layers; dependency matrix unchanged; change-coupling shows
the clusters change independently; §3.8 inventory applied. Rollback: re-collapse the subpackages.

**E2 — Analytics grows from one class to a family (M1, module split).**
Premise: `analytics` gains distributions, time series, KPI cards, histogram bins, filters/rules, possibly
forecasting. Trigger evidence: ≥2 public method clusters with different dependencies and change reasons; the
`Analyzer` facade remains the public entry point. This is **not** Stage B: no new public subpackage is
created; the capability modules stay under `analytics/`. The five modules below are illustrative
decomposition targets, not separate consumers of one helper. If this leaf directory needs several dedicated
helper modules, they are grouped in `analytics/_internal/` (ARCH-094) rather than scattered beside these
capability modules.

```text
bynat/analytics/
├── __init__.py                 # unchanged: exports Analyzer
├── analyzer.py                 # public facade; delegates to capability modules
├── _distributions.py
├── _timeseries.py
├── _kpi.py
├── _filters.py
└── _bins.py
# A single helper module, if justified later, may instead be a direct
# analytics/_internal.py (ARCH-094). An analytics/_internal/ directory is
# added only when multiple dedicated helper modules are justified.
```

Acceptance: `bynat.analytics.__all__` unchanged; `Analyzer` public methods unchanged; `analytics` still
imports no other `bynat` package. Rollback: re-inline the capability modules into `analyzer.py`.

**E3 — Caching gains a second backend (Stage B + relocation).**
Premise: a concrete requirement appears for a non-SQLite cache backend. Trigger evidence: a concrete
second-backend requirement (not hypothetical); the backend has its own connection/lifecycle specifics; the
`CacheManager` contract can remain the public facade.

```text
bynat/caching/
├── __init__.py                 # unchanged public surface
├── manager.py                  # CacheManager facade; composes a backend
├── _keys.py
├── _migration.py
└── backends/
    ├── __init__.py
    ├── base.py                 # backend protocol
    ├── sqlite.py               # current _storage.py responsibility
    └── <new_backend>.py
```

Acceptance: the protocol consumer is `CacheManager` (or the backend-selection component it delegates to) and
has exactly one consumer; exactly two concrete implementations exist — `backends/sqlite.py` and the new
backend — and both implement the same required contract; the `CacheManager` public contract is unchanged; the
protocol exists only because a real second backend exists (no generic extension framework, no further
abstraction); no new cross-package private import. Rollback: re-inline the backend into `_storage.py`.

**E4 — Integrations grow (Stage B via M2).**
Premise: enrichment gains many providers and services. Trigger evidence: ≥3 provider families, or a provider
with its own configuration/lifecycle that does not fit `providers.py`; provider implementations change for
different reasons.

```text
bynat/cleaning/enrich/
├── __init__.py
├── engine.py
├── providers/
│   ├── __init__.py             # re-exports the 6 provider symbols
│   ├── base.py                 # protocols
│   ├── translation.py
│   ├── geocoding.py
│   └── currency.py
├── translate.py
├── geocode.py
├── currency.py
└── nlp.py
```

Acceptance: `enrich.__all__` and the public feature functions unchanged; provider protocols keep their
consumers; no new cross-package private imports. Rollback: re-inline the provider modules into `providers.py`.

**E5 — A new domain emerges (Stage D).**
Premise: a coherent capability appears that is not cleaning, caching, analytics, or profiling — for example
the roadmap's `DQ-02` “declarative DataFrame quality checks”. Trigger evidence: a coherent capability with
its own public contract and ≥2–3 operations; no dependency on existing package internals; a distinct user
workflow.

```text
bynat/validation/               # conditional new domain
├── __init__.py                 # exports check_frame, ValidationReport, ...
├── core.py
└── rules.py
```

Acceptance: the new package has its own `__all__` and boundary checks; it imports no functional package
internals; the dependency matrix is extended with the new package. Rollback: remove the new package; no other
package depends on it.

**E6 — Cross-domain shared logic grows (M4, module addition).**
Premise: more domain-independent helpers appear with real consumers in ≥2 packages. Trigger evidence: ≥2
genuinely domain-independent helpers with stable contracts and ≥2 package consumers; the helpers share a
coherent responsibility (for example value normalization).

```text
bynat/_internal/                # library-level generic collection (ARCH-094)
├── __init__.py                 # curates the private internal surface
├── values.py                   # existing
└── <coherent_module>.py        # e.g. validation.py
```

Acceptance: `_internal` still imports only stdlib and NumPy; it imports no functional package; each new
helper has ≥2 real consumers; the generic collection is named `_internal` and not `shared`/`_shared` (ARCH-094).
Rollback: move the helper back to its owning domain.

**Stress-test conclusion.** The model handles all six scenarios without changing the top-level boundaries,
the public API, or the dependency direction. In every case the transition is internal and reversible, and
the trigger is a change-reason/cohesion signal rather than a size threshold. If a scenario requires a new
public contract, it is a new domain (E5), not a subpackage.

### 3.5 Filesystem validity constraint

A Python package cannot contain both `foo.py` and `foo/`. Every growth tree therefore **replaces** the module
with a same-named package; no tree lists both.

| Existing module | Growth package | Keeps the name because | Conversion |
|---|---|---|---|
| `cleaning/columns.py` | `cleaning/columns/` | `from bynat.cleaning import columns` | M2 |
| `cleaning/text.py` | `cleaning/text/` | `from bynat.cleaning import text` | M2 |
| `cleaning/stats.py` | `cleaning/stats/` | `from bynat.cleaning import stats` | M2 |
| `cleaning/io.py` | `cleaning/io/` | `from bynat.cleaning import io`; documented path | M2 |
| `cleaning/enrich/providers.py` | `cleaning/enrich/providers/` | `from bynat.cleaning.enrich.providers import ...` | M2 |

No other proposed tree contains a module/package name clash. Each package `__init__.py` re-exports the
symbols that repository code and tests access; see §3.8.

### 3.6 Dependency model evolution rules

- **New subpackages inherit the parent's dependency budget.** A `cleaning/columns/` subpackage may import
  what `cleaning/columns.py` may import, and nothing more.
- **A module-to-package conversion keeps the module's name.** Renaming the package would break
  `from bynat.cleaning import columns, io, stats, text` and `from bynat.cleaning.enrich.providers import ...`.
- **New domain packages must be independent or depend inward.** A new domain may not import another domain's
  private internals. If it needs a shared helper, the helper moves to library-level `_internal` only with ≥2 real
  consumers.
- **`_internal` may grow only with coherent, domain-independent modules.** It remains stdlib + NumPy only.
- **A per-package `_internal/` inherits its parent's dependency budget.** It is not a new top-level package and may
  import only what its parent may import; library-level `bynat/_internal` remains domain-independent (ARCH-019,
  ARCH-094).
- **`_accessors` remains delegation-only.** It never gains algorithms.
- **`analytics` and `profiling` remain independent** unless a concrete requirement changes that, with an
  explicit decision.
- **Every new cross-package private import requires a documented exception and an enforcement entry.**

| Scenario | New package | New permitted edge | Prohibited |
|---|---|---|---|
| 1 | `cleaning/{columns,text,stats,io}` | none (inherit `cleaning`) | same as today |
| 2 | `analytics/_*` | none | same |
| 3 | `caching/backends` | none (inherit `caching`) | `caching` still imports no functional package |
| 4 | `cleaning/enrich/providers` | none (inherit `enrich`) | same |
| 5 | `validation` | none (independent) | must not import functional internals |
| 6 | `_internal/<module>` | functional → `_internal` | `_internal` → functional |

### 3.7 `io` module-to-package conversion: `__module__` preservation

Python sets a function's `__module__` to the module in which the `def` executes. If `read_csv` is defined in
`bynat.cleaning.io.readers`, then `read_csv.__module__ == "bynat.cleaning.io.readers"`, and the pinned
contract `bynat.read_csv.__module__ == "bynat.cleaning.io"` fails. The contract is public and is not weakened
by the conversion. Option A remains compatible with ARCH-102 when `io/__init__.py` declares the public contract
(signature, docstring, delegation) and delegates substantive behavior to internal implementation submodules.

| Option | Mechanism | `__module__` | Docstring contract | Introspection / pickling | Verdict |
|---|---|---|---|---|---|
| A. Declare/expose the public functions in `io/__init__.py`, delegating substantive behavior to internal implementation submodules (ARCH-102) | `def read_csv(...)` executes in the package `__init__` | `bynat.cleaning.io` (natural) | Natural: the public `def` lives in the documented module | `inspect.getmodule`, `inspect.getsourcefile`, and `pickle` all resolve to `bynat.cleaning.io`; the substantive logic stays in internal modules | **Approved** |
| B. Define in `io/readers.py`, re-export, and set `__module__ = "bynat.cleaning.io"` on each public function | Metadata mutation | `bynat.cleaning.io` (assigned) | Not preserved automatically: `__module__` would be assigned, so `inspect.getmodule` and `pickle` follow the assignment while `inspect.getsourcefile` reflects `readers.py` | `inspect.getmodule`/`pickle` resolve via `__module__`; `inspect.getsourcefile` still uses `co_filename` (`readers.py`); `__module__` no longer reflects the defining module | Viable only with explicit approval and a doc-contract update |
| C. Define in `io/readers.py` and accept `__module__ == "bynat.cleaning.io.readers"` | No mutation | `bynat.cleaning.io.readers` | Natural | Introspection reports the true module | **Rejected**: changes a pinned public contract |

**Trade-offs.** `io/__init__.py` is no longer a thin re-export module; it owns the public reader/writer
contract (signatures, docstrings, delegation) while the substantive implementations stay in internal modules
(ARCH-102). If a thin `__init__` is preferred, Option B is the alternative, but it is **not
behavior-neutral**: it requires an explicit `__module__` assignment on each public function and a
change to the accessor doc-contract tests, which compare generated methods' `__doc__` with the shared functions. Option B therefore
requires explicit approval; it must not be introduced silently. Option C is rejected because it weakens the
pinned contract.

### 3.8 Compatibility inventory for the growth conversions

| Module path | Category | Relied on by | Pinned contract | Growth conversion | Preservation requirement |
|---|---|---|---|---|---|
| `bynat.cleaning.io` | 4 (documented) | root `__init__`; `base.py` docstrings; accessor doc contract; structural contract checks | `read_csv.__module__ == "bynat.cleaning.io"`; `read_json.__module__ == "bynat.cleaning.io"`; `io._dedupe_key is _internal.dedupe_key`; `bynat.read_csv is io.read_csv` | M2 → `io/` | `io/__init__.py` declares/exposes `read_csv`, `read_json`, `save_to_json`, `save_to_sql`, `IfExists`, `JsonOrient`, `_dedupe_key` and delegates substantive behavior to internal implementation submodules (ARCH-102); the public functions keep `__module__ == "bynat.cleaning.io"` (§3.7) |
| `bynat.cleaning.columns` | 3 | `base.py`; `_accessors/dataframe.py`; property/equivalence checks | `BynatAccessor.<method>.__wrapped__ is columns.<func>`; 9 column functions accessed as attributes | M2 → `columns/` | `columns/__init__.py` re-exports the 9 functions; each submodule has `__all__` |
| `bynat.cleaning.text` | 3 | `base.py`; `_accessors/dataframe.py`; property/equivalence checks | `BynatAccessor.<method>.__wrapped__ is text.<func>`; 3 text functions | M2 → `text/` | `text/__init__.py` re-exports the 3 functions; each submodule has `__all__` |
| `bynat.cleaning.stats` | 3 | `base.py`; `_accessors/dataframe.py`; doc-sync; outlier equivalence checks | `BynatAccessor.<method>.__wrapped__ is stats.<func>`; `stats.fill_missing.__doc__` equality; 5 statistics functions | M2 → `stats/` | `stats/__init__.py` re-exports the 5 functions; each submodule has `__all__` |
| `bynat.cleaning.enrich.providers` | 3 | `base.py`; `enrich/__init__.py`; accessor doc contract | `enrich.__all__` re-exports 6 provider symbols; accessor methods expose provider docstrings | M2 → `providers/` | `providers/__init__.py` re-exports the 6 provider symbols; each submodule has `__all__` |

### 3.9 Deliberately not proposed

No `src/` layout migration; no global `api/`/`domain/`/`infrastructure/` tree; no `shared`, `_shared`,
`utils`, `helpers`, or `common` generic internal-helper name (`_internal` only, ARCH-094); no
plugin/registry/DI structure; no lazy execution or query-engine layer; no `fit`/`transform` estimator layer;
no pre-built capability subpackages and no speculative `_internal/`; and no code move authorized by this constitution alone. The architecture implemented by commit `946eb16` is current and
fixed; these earlier scenarios do not authorize further separation or relocation. A future architecture change
requires a separate explicit decision.

---

## 4. Deferred and superseded decisions

These rows preserve earlier decisions and unresolved questions. They do not define current scheduled work; conflicts with the architecture implemented by commit `946eb16` are superseded by §§1–2. AE-Q3 was later decided and implemented, so its row records the outcome instead of an open question.

| ID | Item | Disposition | Revisit trigger |
|---|---|---|---|
| AE-Q1 | Should `_internal.keys` become a narrow public contract? | Keep private with a documented edge | A second consumer or a user-facing requirement |
| AE-Q2 | Should `base.py` be split or generated? | Defer | Concrete maintenance pain; docstring-generation cost |
| AE-Q3 | Should any `Analyzer` operation become an accessor method? | Implemented (supersedes Defer); every public operation is exposed on `df.bynat` and delegates to `Analyzer` | Only if the accessor delegation contract changes |
| AE-Q4 | How should SQL URL construction be owned? | Resolved by commit `946eb16`: `build_engine_url` lives in `cleaning/_internal/sql.py`; `save_to_sql` remains in `cleaning/io.py` and owns the export flow. No further move is implied. | A separate explicit architecture decision |
| AE-Q5 | Should dependency-boundary enforcement be hardened now? | No | A demonstrated repository enforcement need (Phase 2) |
| AE-Q6 | When a derived `BaseData` frame's `CacheManager` is cleared or replaced, should the recreated manager inherit the originating custom `cache_dir`? | Missing behavioral contract; no intended contract is stated in repository evidence, so none is invented | A user report or a decision to propagate `_bynat_cache_dir` through pandas metadata |
| AE-Q7 | Should a `validation` domain be created? | Defer | Roadmap `DQ-02` becomes a concrete requirement |
| AE-Q8 | Should a second cache backend be added? | Defer | A concrete backend requirement |
| AE-Q9 | Should `_internal` expand? | Defer | ≥2 domain-independent helpers with real consumers |
| AE-Q10 | Should the flat layout move to `src/`? | No | A packaging reason (none now) |

**Behavioral follow-ups are not architecture decisions.** Correctness findings and verification gaps recorded by
the source documents are outside this constitution's scope and are not duplicated here. The architecture-relevant
constraints and hazards they expose are recorded in [§2.11](#211-documented-hazards-and-dispositions-current); the
remainder are correctness/coverage follow-ups governed by `docs/TESTING_STANDARDS.md`. See [§7](#7-testing-scope-separation).

---

## 5. Rejected patterns

The prohibitions in [§1.13](#113-prohibited-patterns) are normative. The evaluated alternatives and their reasons are:

| Pattern/structure | Decision | Reason |
|---|---|---|
| Microservices / separate deployables | Reject | One small installable library; no distribution requirement |
| Generic repository pattern | Reject | No domain-model persistence; cache storage is a key-value contract |
| Universal managers | Reject | Only `CacheManager` has a demonstrated lifecycle |
| Base classes for unrelated operations | Reject | No shared algorithm hierarchy; composition is used instead |
| `shared`/`_shared` generic helper collection | Reject | `_internal` is the only prescribed generic internal-helper collection (ARCH-094) |
| Protocol proliferation | Reject | Only the three provider protocols have consumers |
| Plugin registry / entry points | Reject | No third-party plugin requirement |
| Excessive wrapper modules | Reject | Every public interface/facade must own a supported public contract; delegation-only pass-throughs without one are unnecessary (ARCH-102). Canonical interfaces are the package APIs and their documented entry points, including `BaseData` and the accessor. |
| Artificially strict layers | Reject | Layering is a dependency rule, not a directory tree |
| Generic transformation engine | Reject | Transformations are explicit functions; only the enrichment cached-lookup loop is shared |
| Duplicate implementations of shared behavior | Reject | Single canonical helper per responsibility; the alias layer is removed |
| Polars-style lazy execution layer | Reject | No lazy/optimized execution requirement |
| `fit`/`transform` estimator layer | Reject | Transformations are stateless functions |
| Splitting `base.py`/`_stats.py`/`analyzer.py` by LOC | Reject | Preserve the module ownership and paths established by commit `946eb16`; LOC is never sufficient justification for a future structural change. |
| Pre-building capability subpackages | Reject | No trigger; speculative structure |
| Global layer tree | Reject | Obscures domain ownership |
| `utils`/`helpers`/`common` catch-all modules | Reject | No responsibility statement; `_internal` is the only prescribed generic internal-helper name (ARCH-094) |
| `_internal/` for a single helper module | Reject | ARCH-094 requires ≥2 dedicated helper modules; use a direct `_internal.py` at the narrowest scope instead. A helper used by only one file still leaves that file when it supports the core implementation (ARCH-104/ARCH-096); it is placed in `_internal.py` or an `_internal/` collection per ARCH-092–ARCH-094, not left in the core file. |
| Grouping unrelated helpers in one file or collection | Reject | Violates helper-file cohesion (ARCH-093) |
| Overly high helper placement | Reject | A helper belongs at the narrowest common scope (ARCH-092) |
| DI container | Reject | No consumer |
| `src/` layout migration | Reject | Flat layout is correct; no packaging reason |
| Renaming public modules | Reject | Public API change without requirement |
| Moving `save_to_sql` to its own public module or changing its pinned public path | Reject | Commit `946eb16` keeps `save_to_sql` in `cleaning/io.py` and extracts URL construction to `cleaning/_internal/sql.py`; preserve that ownership and the supported path. |
| Keeping profiling under `cleaning` | Reject (as target) | Profiling does not transform; `cleaning` would own both transformation and diagnosis |
| Integrating profiling into `analytics` | Reject | Report diagnostics and application response analytics have different contracts |
| A broader quality/inspection umbrella now | Defer | Premature without a second substantial capability |
| `analytics → cleaning` import | Reject | Would encode an application workflow as a package dependency and reduce reuse |
| Moving `caching` under `cleaning` | Reject | Inverts the dependency direction; makes reusable persistence depend on one consumer domain |
| Global `api/`/`domain/`/`infrastructure/` layers | Reject | Obscures which package owns a behavior |
| Feature-oriented top-level tree | Reject | Would duplicate shared DataFrame/cache contracts and weaken public package boundaries |
| Entry-point plugin discovery | Reject | No external plugin surface; all implementations ship in one distribution |
| Broad root re-exports | Reject | Creates accidental API and long-term compatibility commitments |
| Retaining obsolete root aliases (`BynatAccessor`, `ProfileReport`, `profile`) | Reject | Previous-version compatibility is out of scope; they were removed directly |
| Keeping `bynat.cleaning.profile` as a compatibility facade | Reject | Obsolete path under target ownership; removed directly |
| `bynat.cleaning.Cleaning` / `bynat.caching.Caching` shims | Reject | Already removed; module loggers use `logging.getLogger(__name__)` (ARCH-049) |
| Splitting `io.py` or moving `save_to_sql` | Reject | Commit `946eb16` keeps `save_to_sql` in `cleaning/io.py` and extracts only URL construction to `cleaning/_internal/sql.py`; preserve that ownership and the supported public path. |
| Splitting `enrich/_engine.py` from the feature modules | Reject | The engine is the genuinely shared cached-lookup algorithm and retains its committed owner. |
| A generic integration framework / DI container | Reject | Concrete use cases only; no consumer for the abstraction |
| Expanding `caching.__all__` | Reject | Storage/migration/key modules stay private |

---

## 6. Governance and amendment procedure

1. **Propose.** An amendment states the `ARCH-###` IDs added, repealed, or renumbered; the trigger or reason; the
   affected current/conditional/deferred status; and the rollback.
2. **Check boundaries.** Verify the amendment against ARCH-005 (public surface frozen), ARCH-023 (prohibited edges),
   ARCH-025 (private-import exceptions), ARCH-064 (reversibility), ARCH-102–ARCH-104 (the implemented API/core/helper
   ownership boundaries), and the hard rules ARCH-068. The current ownership in §2.10 is fixed; a future architectural
   change still requires separate explicit authorization and ARCH-066/ARCH-099.
3. **Enforce.** Confirm the change has an automated check or an explicit documented exception (ARCH-063). A new
   cross-package private import requires a new exception entry before merge.
4. **Resolve conflicts.** Apply ARCH-002 and ARCH-090: label status explicitly; prefer later implemented status over
   earlier historical prose; prefer current checkout facts over source-reported baselines.
5. **Review.** A structural change review states the trigger it satisfies and its rollback (ARCH-078). Conditional
   phases are opened only through the operational review procedure (ARCH-066).

The constitution may be corrected for internal consistency without changing an architectural decision; such a
correction must say so explicitly and must not silently alter a rule.

---

## 7. Testing scope separation

This constitution defines architecture only. It does not define testing architecture, test organization, test
implementation, coverage, fixtures, CI, or test-specific acceptance criteria. Those subjects remain governed by
`docs/TESTING_STANDARDS.md` and are intentionally not duplicated here. The architectural rules in this document may
require a boundary to be verifiable, but they do not prescribe how that verification is implemented.

---

## 8. Traceability

### 8.1 Source chronology and conflict resolutions

| # | Conflict | Resolution |
|---|---|---|
| 1 | `ARCHITECTURE_RESEARCH.md` Phase 0.2/0.3 describes a four-name root and profiling under `cleaning`; its Phase 3 status update and the current code describe a six-name root and `bynat.profiling`. | The research Phase 0 sections are the historical `b2a5f43` baseline. Phase 1–3 were implemented; the six-name root, `bynat.profiling`, and `bynat/_accessors/` are **Current**. |
| 2 | Research §7 names obsolete pre-refactor cache-key owners and consumers. | The current owner is `_internal.keys`; enrichment consumers are `cleaning.enrich._engine` and `_translate`. The manager does not import cache-key helpers. |
| 3 | Research §7.1 and the design §3.3 F-7 describe `dedupe_key` ownership. | One canonical implementation exists in `bynat/_internal/keys.py`; `cleaning.io` and `profiling._internal.computations` import it. The removed `cleaning._common` path is historical only. |
| 4 | Research baseline measurements (10,171 physical LOC) differ from the design baseline (10,317). | Different commits (`b2a5f43` vs `6bf68bd`) and Phase 1–3 implementation. Not a decision conflict; the design baseline is the later one. |
| 5 | The task referenced `BYNAT_SCALABLE_ARCHITECTURE_EVOLUTION_STRATEGY.md`. | That file does not exist; the actual document is `architecture/BYNAT_ARCHITECTURE_EVOLUTION_STRATEGY.md`, corrected in place and not renamed. |
| 6 | The design and strategy decide private-alias normalization and dependency-graph enforcement. | Private-alias normalization is implemented by commit `946eb16`; current dependency checks are separately recorded in §2.8. |
| 7 | `ARCHITECTURE_RESEARCH.md` is dated 2026-11-21; the design and strategy are dated 2026-11-22. | Later documents supersede earlier historical sections; the current checkout supersedes all source baselines. |
| 8 | The strategy's Rule of Three guidance (EV-11/EV-12) recommends multiple consumers before sharing, which could be read as blocking same-branch helper extraction. | The Rule of Three is scoped to broader reuse abstraction (ARCH-097); same-branch and multi-file extraction follows the narrowest-common-scope hierarchy (ARCH-092) and is not blocked by the consumer count. |
| 9 | ARCH-022 as previously written omitted the accessor's imports of the `cleaning.enrich` feature modules, while `_accessors/dataframe.py` imports `currency`, `geocode`, `nlp`, and `translate`. | Verified correction: the actual delegation imports are now permitted edges in ARCH-022 (`_accessors` → `cleaning.enrich.{currency,geocode,nlp,translate}`) because the accessor must directly delegate those public functions; the dependency matrix in §2.4 records them. Rationale: preserve the accessor's required direct delegation without routing through a facade. Rollback would remove these imports only together with an approved alternate permitted delegation path. No public API change; stable ARCH IDs preserved. |
| 10 | Earlier rules described moving the `save_to_sql` implementation out of `cleaning/io.py`, which conflicts with the responsibility split implemented by commit `946eb16`. | Resolved: `save_to_sql` remains in `cleaning/io.py`; `build_engine_url` is in `cleaning/_internal/sql.py` (ARCH-036). No further move is authorized by the earlier proposal. |
| 11 | ARCH-092(a)/ARCH-096 kept a single-consumer helper in its file, while ARCH-104 requires helpers to be separate from the core implementation they support. | Harmonized: ARCH-104 is the distinct architectural requirement that overrides the one-file default; the helper goes to the narrowest common scope under ARCH-092 with `_internal` naming (ARCH-094), cohesion (ARCH-093), and no artificial fragmentation. A single helper uses `_internal.py` rather than `_internal/`; related helpers may share a module. |

### 8.2 Rule-to-source mapping

| Constitution topic | ARCH IDs | Primary source |
|---|---|---|
| Authority, scope, evidence, stable invariants and context-driven organization | ARCH-001–ARCH-005, ARCH-098 | Design §1; strategy §1; research Executive conclusion; this constitution's architecture decision principle |
| Public API and compatibility | ARCH-006–ARCH-013 | Design §2.4, §22.1 AR-1/AR-2; strategy §13 C-1–C-10; research §2.3–2.4, ADR-05/ADR-08 |
| Package boundaries and ownership | ARCH-014–ARCH-021 | Design §6.A–C, §7, §18; research §10.5, ADR-02/ADR-03 |
| Dependency direction and private imports | ARCH-022–ARCH-027 | Design §13, §22.1 AR-3–AR-9; research §5, §7.1 |
| Functional Core, Facades, and API/implementation separation | ARCH-028–ARCH-033, ARCH-100, ARCH-102–ARCH-104 | Design §5, §6.D–G; research §2.2, §8.4, ADR-01/ADR-07; this constitution's pattern-selection and API/implementation-separation clarifications |
| Optional integrations and providers | ARCH-034–ARCH-037 | Design §6.E, §19; research §6.4 |
| CacheManager boundaries | ARCH-038–ARCH-043 | Design §6.G, §7.2, §20.2; research §4.11, §6.3 |
| Private helpers and aliases | ARCH-044–ARCH-049 | Design §3.3 F-1/F-2, §6.I, §12 |
| Helper placement and organization | ARCH-092–ARCH-097 | This constitution [§1.15](#115-helper-placement-and-organization); user helper placement and organization rules |
| Structural evolution model | ARCH-050–ARCH-058 | Strategy §4–§6, §14 |
| Growth decision procedure and decision quality | ARCH-059–ARCH-068, ARCH-099 | Strategy §8, §15.4; design §3.2, §3.3 F-5; this constitution's decision-quality clarification |
| Conditional phases E1–E6 | ARCH-069–ARCH-074 | Strategy §7, §10, §14.4 |
| Enforcement, fitness functions, discoverability and analyzability | ARCH-075–ARCH-078, ARCH-101 | Design §22; strategy §16; research §13; this constitution's discoverability/analyzability clarification |
| Prohibited patterns | ARCH-079–ARCH-088 | Design §5, §21; strategy §18.3; research §11 |
| Governance and amendment | ARCH-089–ARCH-091 | Strategy §16.3; this constitution §6 |

### 8.3 Source decision-register mapping

| Source register | Destination |
|---|---|
| Design D-A1–D-A12 (Adopt/Adapt) | ARCH-001–ARCH-058 (current and near-term rules) |
| User helper placement and organization rules (this amendment) | ARCH-092–ARCH-097 |
| User public-API/core-implementation and helper/core separation rules (this amendment) | ARCH-102–ARCH-104 |
| Design D-D1–D-D6 (Defer) | [§4](#4-deferred-decisions) AE-Q1–AE-Q10 |
| Design D-R1–D-R14 (Reject) | [§5](#5-rejected-patterns), ARCH-079–ARCH-088 |
| Strategy P-1–P-10 | ARCH-057 |
| Strategy R-1–R-7, R-11, R-12 | ARCH-068 |
| Strategy C-1–C-10 | ARCH-009–ARCH-013 |
| Design AR-1–AR-11 / Strategy AF-1–AF-13 | ARCH-075, ARCH-076 |
| Strategy scenarios 1–6 | ARCH-069–ARCH-074 |
| Design AE-Q1–AE-Q6 / Strategy AE-Q1–AE-Q10 | [§4](#4-deferred-decisions) |

### 8.4 Source register

**Source documents**

- `architecture/BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md` — internal architecture design, baseline `6bf68bd` (removed after consolidation into this constitution).
- `architecture/BYNAT_ARCHITECTURE_EVOLUTION_STRATEGY.md` — evolution strategy, baseline `6bf68bd` (removed after consolidation into this constitution).
- `ARCHITECTURE_RESEARCH.md` — research and decision record, snapshot `b5ac64a`, Phase 0 baseline `b2a5f43` (removed after consolidation into this constitution).
- [`ROADMAP.md`](ROADMAP.md) — living plan (`DQ-02`, `DEPR-02`, `PERF-05`, `PERF-06`, `IO-01`, `COMPAT-01`).
- [`TESTING_STANDARDS.md`](TESTING_STANDARDS.md) — mandatory testing constitution (out of scope here; see [§7](#7-testing-scope-separation)).

**Repository artifacts**

- [`../pyproject.toml`](../pyproject.toml) — version, dependencies, extras, tool configuration.
- [`../bynat/__init__.py`](../bynat/__init__.py) — root API and accessor registration.
- [`../bynat/cleaning/__init__.py`](../bynat/cleaning/__init__.py), [`../bynat/caching/__init__.py`](../bynat/caching/__init__.py), [`../bynat/analytics/__init__.py`](../bynat/analytics/__init__.py), [`../bynat/profiling/__init__.py`](../bynat/profiling/__init__.py) — package exports.
- [`../bynat/_accessors/dataframe.py`](../bynat/_accessors/dataframe.py), [`../bynat/_accessors/_binding.py`](../bynat/_accessors/_binding.py) — private accessor boundary.
- [`../bynat/_internal/keys.py`](../bynat/_internal/keys.py) — canonical `dedupe_key` and cache-key helpers.
- [`../bynat/caching/manager.py`](../bynat/caching/manager.py), [`../bynat/caching/_persistence.py`](../bynat/caching/_persistence.py), [`../bynat/caching/_storage.py`](../bynat/caching/_storage.py), [`../bynat/caching/_migration.py`](../bynat/caching/_migration.py), [`../bynat/caching/_internal/`](../bynat/caching/_internal/) — cache boundary.
- [`../bynat/cleaning/_internal/`](../bynat/cleaning/_internal/), [`../bynat/cleaning/enrich/_engine.py`](../bynat/cleaning/enrich/_engine.py), [`../bynat/cleaning/enrich/_internal/`](../bynat/cleaning/enrich/_internal/), [`../bynat/cleaning/enrich/providers.py`](../bynat/cleaning/enrich/providers.py) — cleaning and enrichment core/helper ownership.
- [`../bynat/analytics/analyzer.py`](../bynat/analytics/analyzer.py), [`../bynat/analytics/_insights.py`](../bynat/analytics/_insights.py), [`../bynat/analytics/_internal/`](../bynat/analytics/_internal/), [`../bynat/profiling/_builders.py`](../bynat/profiling/_builders.py), [`../bynat/profiling/_internal/`](../bynat/profiling/_internal/) — analytics and profiling ownership.
- [`../tools/verify_installed_wheel.py`](../tools/verify_installed_wheel.py) — installed-wheel verification; the former generated-stub and docstring-synchronization tool no longer exists.
- Current repository boundary-verification artifacts — evidence for the current export, accessor, profiling, and shared-helper boundaries; their testing details remain governed by `docs/TESTING_STANDARDS.md`.

### 8.5 Source-by-source coverage

This table records where each part of each source document is captured in this constitution; the three
sources were removed without architectural loss. Source references are supplementary evidence only.

| Source | Source sections | Captured here |
|---|---|---|
| Internal design | §1 Executive decisions 1–4; follow-up audit | §1.1–§1.9, §2.8, §2.11 |
| Internal design | §2 Baseline identity, tree, measured size, public API, import map, verification | §2.1–§2.9, §2.11 |
| Internal design | §3 Package/module assessment; F-1–F-8; negative findings | §1.3, §1.8, §2.11 |
| Internal design | §4 External research E-1–E-14 | §8.6 |
| Internal design | §5 Architecture pattern evaluation | §5, §1.13 |
| Internal design | §6 Final architectural decisions A–I | §1.1–§1.9, §1.12, §5 |
| Internal design | §7 Package responsibilities and subsystems | §1.3 |
| Internal design | §8 Complete final target tree | §2.2, §3.3 |
| Internal design | §9 File-by-file responsibility specification | §2.11 |
| Internal design | §10 Component inventory, flags, `Adjust` decisions | §2.11 |
| Internal design | §11 Module contracts and dependency review | §2.10, §2.11 |
| Internal design | §12 Existing-to-target migration map | §1.8, §3.3 |
| Internal design | §13 Dependency matrix and private-import exceptions | §1.4, §2.4, §2.5 |
| Internal design | §14 Module dependency maps | §2.4 |
| Internal design | §15 Data and execution flows | §2.10 |
| Internal design | §16 Behavioral contracts F1–F20 | §2.9 |
| Internal design | §17 Discrepancies, test gaps, AE-Q6 | §2.11, §4 |
| Internal design | §18 Shared component ownership | §1.3, ARCH-020 |
| Internal design | §19 Integration and optional dependency design | §1.6 |
| Internal design | §20 Internal interfaces and lifecycle | §1.5, §2.7 |
| Internal design | §21 Rejected patterns | §5, §1.13 |
| Internal design | §22 Enforcement rules AR-1–AR-11 and mechanisms | §1.12 |
| Internal design | §23 Compatibility and migration risks | §1.2 |
| Internal design | §24 Implementation sequence | §3.3 |
| Internal design | §25 Unresolved decisions AE-Q1–AE-Q6 | §4 |
| Internal design | §26 Decision register D-A/D-D/D-R | §8.3, §8.7 |
| Internal design | §27 Research references | §8.6, §8.8 |
| Evolution strategy | §1 Executive conclusions; stage summary | §1.1, §1.9, §3.1 |
| Evolution strategy | §2 Existing architecture assessment | §2 |
| Evolution strategy | §3 External research EV-1–EV-16; limitations | §8.6 |
| Evolution strategy | §4 Evolution principles P-1–P-10 | ARCH-057 |
| Evolution strategy | §5 Package evolution model, transition table, non-triggers | §3.1 |
| Evolution strategy | §6 Module/component evolution model | §3.2 |
| Evolution strategy | §7 Growth scenarios 1–6 | §3.4, ARCH-069–ARCH-074 |
| Evolution strategy | §8 Structural decision framework, trigger weights, hard rules | §1.10 |
| Evolution strategy | §9 Near-term target architecture | §3.3 |
| Evolution strategy | §10 Growth-ready examples; filesystem validity | §3.4, §3.5 |
| Evolution strategy | §11 Current-versus-proposed tree comparison | §3.4 |
| Evolution strategy | §12 Cross-package dependency model | §3.6 |
| Evolution strategy | §13 Public API/compatibility strategy; `io` `__module__` | §1.2, §3.7, §3.8 |
| Evolution strategy | §14 Phased roadmap | §3.3, §3.4 |
| Evolution strategy | §15 Acceptance criteria, checkpoints, operational procedure | §1.10 (ARCH-066), §3.3 |
| Evolution strategy | §16 Enforcement strategy AF-1–AF-13 | §1.12 |
| Evolution strategy | §17 Deferred decisions AE-Q1–AE-Q10 | §4 |
| Evolution strategy | §18 Risks, trade-offs, rejected alternatives | §5 |
| Evolution strategy | §19 Evidence and source references | §8.6, §8.8 |
| Evolution strategy | §20 Final traceability matrix | §8.2, §8.3 |
| Architecture research | Executive conclusion; Phase 0 decisions and baseline | §1.1, §8.1 |
| Architecture research | §1 Investigation scope and LOC method | §2.1, §8.1 |
| Architecture research | §2 Current architecture | §2 |
| Architecture research | §3 Quantified module assessment | §2.11 |
| Architecture research | §4 Responsibility and cohesion assessment | §1.3, §5 |
| Architecture research | §5 Dependency analysis | §1.4, §2.4 |
| Architecture research | §6 Joint evaluation of cleaning/caching/analytics | §1.3, §5 |
| Architecture research | §7 Shared component ownership; §7.1 `_dedupe_key` correction | §1.3, §2.5, §8.1 |
| Architecture research | §8 DataFrame accessor architecture and eligibility | §1.5, ARCH-031 |
| Architecture research | §9 Comparison of architectural approaches | §5 |
| Architecture research | §10 Candidate and recommended package hierarchies | §3, §5 |
| Architecture research | §11 Prioritized refactoring opportunities | §3, §4 |
| Architecture research | §12 ADR-01–ADR-08 | §8.7 |
| Architecture research | §13 Verification baseline and limitations | §8.6 |
| Architecture research | §14 Source register | §8.8 |

### 8.6 External research findings

These are the external findings the sources relied on, with their URLs and how they were applied. They are
reference material; the constitutional rules stand independently.

**Internal-design findings (E-1–E-14).**

| ID | Finding | Application |
|---|---|---|
| E-1 | pandas documents custom accessors as namespaces registered with `register_dataframe_accessor`, initialized with the decorated object; the initializer may validate and raise `AttributeError`, and a new accessor instance is created on each attribute access. pandas aggregates its top-level namespace (`pandas.core.api`, `pandas.io.api`) and documents `pandas.core`/`pandas.compat` as PRIVATE. | Supports `df.bynat` as a stateless integration facade and a narrow root/package `__all__`, with algorithms outside the accessor. |
| E-2 | scikit-learn distinguishes Estimator/Predictor/Transformer; transformers must not change sample count and must preserve order; stateless transformations keep the interface (`FunctionTransformer`, `requires_fit=False`); `set_output` makes the output container explicit. | Adopt the contract discipline (length/order, copy, output container); reject the estimator base-class machinery. |
| E-3 | Polars separates an eager DataFrame API from a lazy `LazyFrame` that builds and optimizes a logical plan over a Rust query engine. | No lazy/optimized execution requirement; a plan/optimizer layer would be speculative. Reject. |
| E-4 | SQLAlchemy separates Core (engine, connection, pool, expression language) from ORM, isolates DBAPI specifics in dialects, and initializes engines lazily. | Adopt the layered-dependency idea locally (SQLite in `caching._storage`, SQLAlchemy in `cleaning.io.save_to_sql`, providers in `cleaning.enrich.providers`); reject the ORM. |
| E-5 | Pydantic V2 separates model definition from validation/serialization (`pydantic-core`) and marks private objects through an `_internal` subpackage. | Supports a narrow private `_internal` package and deliberate `__all__` boundaries; does not justify a schema/validator split. |
| E-6 | Functional Core, Imperative Shell separates a functional core (values in, values out) from a shell that performs I/O and effects. | bynat already implements this; adopt and preserve. |
| E-7 | A modular monolith keeps one deployable but organizes bounded contexts with explicit public interfaces; GitLab enforces privacy and explicit dependencies with a static analyzer (Packwerk). | Adopt the boundary-enforcement idea; reject multi-service extraction and event buses. |
| E-8 | NumPy documents three module tiers, computes `numpy.__all__` as a union of submodule `__all__` lists, moved `numpy.core` to private `numpy._core`, and states in NEP 52 the goals of a clear public/private distinction and one canonical location per public function. | Supports a deliberate public `__all__`, a private `_internal` package, and one canonical helper location; does not justify renaming public modules. |
| E-9 | Synthesis of E-1/E-2: a transformation contract specifies length/order preservation, copy semantics, output container, and stateless vs stateful. | bynat already states index/order preservation, `inplace`, and `output_type`; preserve these and add no stateful estimator layer. |
| E-10 | Import Linter contract types: `forbidden`, `protected`, `layers`, `independence`, `private_modules` (underscore modules scoped to their parent package), `acyclic_siblings`; configured in `.importlinter`/`setup.cfg`/`pyproject.toml`; `ignore_imports` exempts an edge. | Recommended enforcement mechanism; a `protected` contract on `bynat._internal.keys` with an allow-list is more precise than a blanket `private_modules` exception. |
| E-11 | PyPA documents naming-convention, namespace-package, and entry-point plugin discovery; entry points are justified when multiple independently distributed plugins implement one interface, unjustified when all implementations ship in one distribution. | No third-party plugin requirement; reject entry-point discovery and registries. |
| E-12 | Importing a package executes its `__init__.py`; `__all__` controls `from package import *` and signals the public surface. | Explicit root/package imports and exact `__all__` are the correct mechanism; incidental import-order attributes are not API. |
| E-13 | PEP 621 `optional-dependencies` maps each extra to `Requires-Dist` entries guarded by the extra name. | Extras are correctly declared; no change. |
| E-14 | `from module import *` excludes names beginning with `_`; PEP 8 defines the leading underscore as a weak internal-use indicator; Import Linter's `private_modules` and Ruff's preview `PLC2701 import-private-name` flag cross-module private imports. | Private modules are a convention; the design makes the convention enforceable and records the five documented exceptions. |

**Evolution-strategy findings (EV-1–EV-16).**

| ID | Finding | Application |
|---|---|---|
| EV-1 | pandas separates a curated public surface from a deep private implementation tree (`pandas/core` with many subpackages). | Separate a curated public surface from private modules; do not imitate pandas' depth, only the principle. |
| EV-2 | NumPy NEP 52: clear public/private distinction; each public function available from only one place; `numpy.core` → `numpy._core`; explicit `PUBLIC_MODULES`/`PRIVATE_BUT_PRESENT_MODULES` lists. | Supports exact `__all__` discipline, the private `_internal` package, and removal of duplicate private aliases; does not support renaming public modules. |
| EV-3 | scikit-learn treats anything not beginning with `_` as informally public; tests should import from the public package path. | Aligns with bynat's `_`-prefixed modules and the rule that internal reorganization must not change the public path. |
| EV-4 | `psf/requests` is a flat set of 19 files under `src/requests` with no subpackages. | Strongest counterexample to “growth requires subpackages”; bynat's flat modules are not a defect. |
| EV-5 | Simon Brown: package by component, not by layer; a component bundles related responsibilities behind a well-defined interface; in a modular monolith a static analyzer must enforce boundaries. | bynat's domain packages are already components; deepen components, do not impose a layer tree. |
| EV-6 | Kamil Grzybek: modular-monolith modules are self-contained, domain-oriented, with well-defined interfaces and a minimal module API, following the Dependency Rule. | Supports domain packages and small-surface, self-contained capabilities. |
| EV-7 | GitLab's hexagonal-monolith design prescribes extracting cohesive domains, defining public ports vs private details, and enforcing boundaries with Packwerk. | Supports domain boundaries and enforcement; only the principle transfers (scale differs). |
| EV-8 | arc42 “Increase Cohesion”: split a module when it carries responsibilities that change for different reasons; warnings against splitting by layer, over-splitting into anaemic modules, and helper accretion; verify with change-coupling and one-sentence responsibilities. | Primary trigger for module splits; warns against premature subpackaging. |
| EV-9 | Modularity guide: do not move files before understanding why they change; useful evidence is business capability with an owner, files that change together, rules protecting one invariant, data with one authoritative writer; a module-count KPI alone is dangerous. | Supports trigger-based evolution and the “replay the original change” verification. |
| EV-10 | Change-coupling matrix: high change + low physical proximity → consolidate; low change + high proximity → split; high/high and low/low are healthy. | Empirical method for merge/split decisions and a concrete verification technique. |
| EV-11 | Package-by-feature keeps related classes in one package, raising cohesion and lowering coupling; the Rule of Three is recommended for shared code. | Supports capability subpackages and extraction into a broader reuse abstraction only after multiple real consumers (ARCH-097). |
| EV-12 | Google Testing Blog “Don't DRY Your Code Prematurely” and the Rule of Three: abstracting on the first or second occurrence risks the wrong abstraction. | Guardrail against pre-building generic shared collections or engines; it does not block same-branch extraction (ARCH-097). |
| EV-13 | Real Python: domain-named subpackages scale better than catch-all `utils.py`/`helpers.py`; subpackages appear once an undifferentiated pile sprawls; `__init__.py` should curate the surface. “Flat is better than nested”; leading underscores mark non-public objects. | A subpackage must have a clear responsibility (never `utils/`); depth only when it improves navigation. |
| EV-14 | A module is enough for a small focused function set; a package is warranted when related responsibilities have grown into several modules; one guide suggests ~500 lines as a split hint. | The ~500-line figure is a **secondary** indicator only; “multiple purposes / unrelated change reasons” is primary. |
| EV-15 | Neal Ford: an architectural fitness function is an objective integrity assessment of an architectural characteristic; structural fitness functions (dependency rules, cycles) are the easiest place to start. | The enforcement strategy is a set of structural fitness functions. |
| EV-16 | ArchUnit, GitLab Packwerk, and Import Linter demonstrate automated boundary enforcement. | The mechanism is proven; the choice is phased to avoid a new dependency before it is needed. |

**Helper-placement synthesis.** EV-11/EV-12 recommend the Rule of Three for shared code; this constitution scopes it
to broader reuse abstraction (ARCH-097) so it does not block same-branch or multi-file extraction at the narrowest
common scope (ARCH-092). EV-13 rejects catch-all `utils.py`/`helpers.py`; `_internal` is the single prescribed
generic internal-helper naming (ARCH-094), and existing private owner modules remain in place (ARCH-095).

**Research limitations (recorded, not resolved).** The external sources are practitioner guides, library
documentation, and one NEP — not empirical studies of Python library evolution. The triggers are therefore
interpretations grounded in stated principles, not validated thresholds. Library scale differs enormously
(pandas, NumPy, scikit-learn, GitLab vs bynat); only principles transfer and no directory structure is
copied. No source provides a universally correct LOC threshold, so LOC is a secondary signal and splitting on
LOC alone is forbidden. External libraries evolve; the linked sources should be rechecked when implementation
work begins.

### 8.7 Architecture decision records

The research report's ADRs are the provenance of several constitutional rules. Each is summarized here so the
rationale survives removal of the source.

| ADR | Decision | Rejected alternatives | Constitutional rule |
|---|---|---|---|
| ADR-01 | Adopt a hybrid modular monolith with Functional Core + Facades. | Global layers; feature-only tree; microservices/plugins; unstructured monolith. | ARCH-004, ARCH-028, ARCH-102–ARCH-103 |
| ADR-02 | Keep `cleaning`, `caching`, `analytics`, `profiling` as peer package boundaries. | Analytics inside cleaning; caching inside cleaning; linear cleaning → analytics → caching pipeline. | ARCH-014–ARCH-017, ARCH-087 |
| ADR-03 | Keep shared components in their owning domain. | Generic `_shared` package; copied helpers; root utility module. | ARCH-020, ARCH-021, ARCH-103 |
| ADR-04 | Place accessor integration under `bynat/_accessors/`. | Keep expanding `cleaning/accessor.py`; per-package accessors; plugin entry points. | ARCH-018, ARCH-011 |
| ADR-05 | Treat registration/import behavior as a public contract: importing `bynat` binds the four packages and the canonical loaders and registers `df.bynat`; `BynatAccessor` is not a root export. | Expose `BynatAccessor` at root; explicit opt-in registration; per-package registration. | ARCH-006 |
| ADR-06 | Make profiling an independent top-level package. | Keep profiling under cleaning; integrate into analytics; create a broader quality umbrella immediately. | ARCH-017, §5 |
| ADR-07 | Make accessor eligibility contract-based (seven criteria). | Mirror all cleaning/analytics functions; expose only transformations; add methods ad hoc. | ARCH-031 |
| ADR-08 | Preserve narrow and intentional public exports. | Export every function at root; export all module names. | ARCH-006, ARCH-007 |

### 8.8 External source register

- Python tutorial, packages and imports: <https://docs.python.org/3/tutorial/modules.html>
- Python import system reference: <https://docs.python.org/3/reference/import.html>
- PyPA `pyproject.toml` specification: <https://packaging.python.org/en/latest/specifications/pyproject-toml/>
- PyPA plugin discovery guidance: <https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/>
- PyPA entry points specification: <https://packaging.python.org/en/latest/specifications/entry-points/>
- PEP 621, project metadata: <https://peps.python.org/pep-0621/>
- PEP 8, naming conventions: <https://peps.python.org/pep-0008/#naming-conventions>
- pandas, *Extending pandas*: <https://pandas.pydata.org/docs/development/extending.html>
- pandas accessor registration API: <https://pandas.pydata.org/docs/reference/api/pandas.api.extensions.register_dataframe_accessor.html>
- pandas, `DataFrame.transform`: <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.transform.html>
- pandas, copy on write: <https://pandas.pydata.org/docs/development/copy_on_write.html>
- pandas core tree: <https://github.com/pandas-dev/pandas/tree/main/pandas/core>
- pandas top-level tree: <https://github.com/pandas-dev/pandas/tree/main/pandas>
- scikit-learn developer guide: <https://scikit-learn.org/stable/developers/develop.html>
- scikit-learn glossary: <https://scikit-learn.org/stable/glossary.html>
- scikit-learn public initializer: <https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/__init__.py>
- scikit-learn base contracts and mixins: <https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/base.py>
- `FunctionTransformer`: <https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.FunctionTransformer.html>
- SLEP 18 `set_output`: <https://scikit-learn-enhancement-proposals.readthedocs.io/en/latest/slep018/proposal.html>
- Polars lazy API: <https://docs.pola.rs/user-guide/concepts/lazy-api/>
- Polars, a bird's-eye view: <https://pola.rs/posts/polars_birds_eye_view/>
- SQLAlchemy overview: <https://docs.sqlalchemy.org/en/latest/intro.html>
- SQLAlchemy engine configuration: <https://www.sqlalchemy.org/docs/latest/core/engines.html>
- Pydantic architecture: <https://pydantic.dev/docs/validation/latest/internals/architecture>
- NumPy module structure: <https://numpy.org/doc/stable/reference/module_structure.html>
- NumPy NEP 52: <https://numpy.org/neps/nep-0052-python-api-cleanup.html>
- NumPy `test_public_api.py`: <https://github.com/numpy/numpy/blob/main/numpy/tests/test_public_api.py>
- Functional Core, Imperative Shell: <https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell>
- GitLab hexagonal monolith: <https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/modular_monolith/hexagonal_monolith>
- Simon Brown, modular monolith: <https://simonbrown.je/modular-monolith>
- Kamil Grzybek, domain-centric modular monolith: <https://kamilgrzybek.com/blog/posts/modular-monolith-domain-centric-design>
- arc42, increase cohesion: <https://quality.arc42.org/approaches/increase-cohesion>
- Modularity: build boundaries that survive change: <https://thucde.dev/learn/docs/software-architecture/modularity>
- Change coupling: <https://kb.buildingbetterteams.de/docs/technology-product/Software/Change-Together>
- Package by feature (DZone): <https://dzone.com/articles/package-by-feature-is-demanded>
- Package by feature (Philipp Hauer): <https://phauer.com/2020/package-by-feature>
- Google Testing Blog, don't DRY prematurely: <https://testing.googleblog.com/2024/05/dont-dry-your-code-prematurely.html>
- Rule of three: <https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming)>
- Real Python, Python project structure: <https://realpython.com/python-application-layouts>
- Python module vs package: <https://www.bowmanjd.com/python-module-package/>
- Organize Python code with packages: <https://rune.codes/hub/python/organize-python-code-with-packages>
- Neal Ford, building evolutionary architectures: <https://nealford.com/books/buildingevolutionaryarchitectures.html>
- O'Reilly, fitness functions: <https://www.oreilly.com/library/view/building-evolutionary-architectures/9781492097532/ch02.html>
- InfoQ, fitness functions for your architecture: <https://www.infoq.com/articles/fitness-functions-architecture>
- ArchUnit: <https://www.archunit.org/>
- Import Linter contract types: <https://import-linter.readthedocs.io/en/stable/contract_types/>
- Import Linter private modules: <https://import-linter.readthedocs.io/en/stable/contract_types/private_modules/>
- Import Linter protected modules: <https://import-linter.readthedocs.io/en/stable/contract_types/protected/>
- Import Linter configuration: <https://import-linter.readthedocs.io/en/latest/get_started/configure>
- Ruff `import-private-name` (PLC2701): <https://docs.astral.sh/ruff/rules/import-private-name/>
- Fowler, Monolith First: <https://martinfowler.com/bliki/MonolithFirst.html>
- Fowler, Presentation-Domain-Data Layering: <https://martinfowler.com/bliki/PresentationDomainDataLayering.html>
- Fowler, Software Component: <https://martinfowler.com/bliki/SoftwareComponent.html>
- `psf/requests` source tree: <https://github.com/psf/requests/tree/main/src/requests>