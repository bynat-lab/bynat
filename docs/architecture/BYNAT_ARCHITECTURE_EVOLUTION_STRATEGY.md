# bynat Scalable Architecture Evolution Strategy

**Status:** Research and evolution-planning deliverable — no implementation performed or authorized
**Baseline commit:** `6bf68bd4c99b871e6154319eb9fd82a1e8a90a0d` (`refactor(architecture): finalize Phase 5 verification`)
**Branch:** `arch-module`
**Package version:** `0.6.6` (`pyproject.toml`)
**Primary predecessor:** [`BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md`](BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md)
**Authoritative predecessor plan:** [`docs/temb/bynat_internal_architecture_evolution_plan.md`](../temb/bynat_internal_architecture_evolution_plan.md)
**Research date:** 2026-11-22

> **Evidence labels**
>
> - **Fact** — directly observed in the local checkout at the baseline commit, or produced by an executed command.
> - **External evidence** — a finding supported by an explicitly linked external source.
> - **Interpretation** — an architectural conclusion drawn from facts and external evidence.
> - **Decision** — a concrete architectural choice made by this strategy.
> - **Recommendation** — a proposed future action; not current implementation.

**Relationship to existing documents.** This strategy builds on the internal architecture design and does not replace it. Where the design concludes "retain the current tree" ([§1](../architecture/BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md), [§8](../architecture/BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md)), this strategy explains **when that retention should end, what should replace it, and in what phases**. It does not modify [`docs/ARCHITECTURE_RESEARCH.md`](../ARCHITECTURE_RESEARCH.md), [`docs/ROADMAP.md`](../ROADMAP.md), or [`docs/TESTING_STANDARDS.md`](../TESTING_STANDARDS.md).

**Implementation authorization:** **NOT AUTHORIZED.** No file is moved, added, removed, or modified by this document. Every structural change below is a conditional recommendation gated on a trigger.

**Correction audit (this revision).** This revision corrects the strategy's internal consistency and implementability: it resolves filesystem path collisions in the growth-ready trees (§10.7), reconciles the Stage/Module/Phase model (§5, §6, §14), clarifies the public API and import-path compatibility policy (§13), and makes the growth triggers operational (§15.4). The document reviewed is `BYNAT_ARCHITECTURE_EVOLUTION_STRATEGY.md` — the only strategy document in `docs/architecture/`. The task's referenced name `BYNAT_SCALABLE_ARCHITECTURE_EVOLUTION_STRATEGY.md` does not exist in the repository; the existing document was corrected in place and not renamed.

**Focused correction pass (this revision).** This pass resolves four targeted points: the `io` `__module__` preservation strategy (§13.6), the cache backend protocol acceptance criteria (§7.3), responsibility-driven trigger decisions (§5.2, §8, §15.4), and the separation of near-term preparation (Phase 0–2) from future structural evolution (E1–E6) (§1, §14). No valid architectural decision is changed.

---

## 1. Executive architectural conclusion

**Conclusion 1 — The current architecture is correct for its current scale and must not be restructured now.**
The repository is a small, disciplined modular monolith: four approved domain packages (`cleaning`, `caching`, `analytics`, `profiling`), two private boundaries (`_accessors`, `_internal`), a Functional Core + Facades shape, and a public API expressed through exact package `__all__` lists. The internal architecture design found no ownership or cohesion defect that justifies a structural change at the baseline commit. Building subpackages now would be speculative structure, not evolution.

**Conclusion 2 — Evolution must be triggered by change reasons, not by size.**
A module or package should change when its **responsibilities change for different reasons**, when **cohesion drops**, or when **dependency direction is violated** — not when a line-count threshold is crossed. Line count is a weak signal: the largest module (`cleaning/base.py`, 2,234 lines) is 79% docstrings and is explicitly excluded from LOC-based splitting. The strategy therefore defines **trigger conditions** and treats size as a secondary indicator only.

**Conclusion 3 — The near-term work is internal normalization and enforcement, not new structure.**
The only structural work justified today is the internal content normalization already decided in the design (private alias removal, dead-wrapper removal, consumer import updates) plus one dependency-free AST contract test. This is Phase 1. It changes no public API and no module boundary.

**Conclusion 4 — The growth-ready structure is a set of conditional targets, each with an explicit trigger.**
For each plausible growth direction (cleaning expansion, analytics expansion, a second cache backend, integration growth, a new domain, cross-domain shared logic), this strategy defines a target structure and the evidence that must be present before it is built. The targets are **not** to be implemented now.

**Conclusion 5 — Public API and compatibility are frozen during internal evolution.**
Internal reorganization may move private modules freely. It may not change public import paths, package `__all__` values, signatures, docstrings, or documented behavior. A public module move is a public API change and requires explicit approval. No compatibility facade or alias is introduced to absorb an internal redesign.

**Conclusion 6 — bynat remains a modular monolith.**
There is no deployment, versioning, team-boundary, or distribution requirement that justifies extraction into separate packages or services. The evolution path is **within one installable package**, from flat modules to capability subpackages to (only if ever needed) domain-internal layers.

### 1.1 Direct answer to the driving question

> *If bynat grows substantially over the next several years, what structure should it evolve toward, what evidence triggers each transition, and in what phases can we implement them without compromising the API, behavior, or maintainability?*

- **Structure it should evolve toward:** a modular monolith whose top-level domain packages stay fixed, whose internal organization grows from flat modules to **capability subpackages** (Stage B) and, only where a capability has genuinely distinct internal layers, to **domain-internal layers** (Stage C). New coherent capabilities become **new domain packages** (Stage D). Extraction into separate distributions (Stage E) is rejected unless a concrete deployment requirement appears.
- **Evidence that triggers each transition:** the trigger tables in §5 and §6 and the decision framework in §8. The primary evidence is **change-reason divergence**, **cohesion/coupling signals**, and **dependency-direction violations**, supported (not replaced) by size and consumer counts.
- **Phases — two categories.** **(A) Near-term preparation and enforcement:** Phase 0 (baseline/decision record), Phase 1 (internal normalization + enforcement), and Phase 2 (optional enforcement hardening, on a demonstrated CI need). These phases do not convert modules into packages and do not represent future growth. **(B) Future structural evolution:** E1–E6 are conditional transitions activated only by their real-world triggers; they are not scheduled, not sequential, and may occur independently, in a different order, or never. Each phase has entry criteria, acceptance criteria, a checkpoint, and a rollback (§14, §15).

### 1.2 Stage summary

| Stage | Structure | Status | Trigger to enter |
|---|---|---|---|
| **A** | Flat domain modules; one existing capability subpackage (`cleaning/enrich`) | **Current** | — |
| **B** | Capability subpackages inside a domain | Conditional | ≥2 capability clusters in one package, each with ≥2 modules and distinct change reasons |
| **C** | Domain-internal layers (e.g., validation / transformation / I/O) | Conditional | A capability subpackage has ≥2 internal layers with distinct consumers and change reasons |
| **D** | New top-level domain package | Conditional | A coherent capability with its own public contract, lifecycle, and no dependency on existing package internals |
| **E** | Extraction into separate distributions/services | Rejected (far future) | A concrete deployment, versioning, or team-boundary requirement |

**Stage vs module state.** Stage B (capability subpackages) is a *package-level grouping*; it is often implemented through M2 conversions (a module becomes a same-named package). M1 (splitting a module into multiple modules) and M2 (converting a module into a package) are *module-level* operations. Stage C (domain-internal layers) is a *layer-level* operation inside a capability subpackage. A scenario can combine operations (for example Scenario 1 is Stage B implemented through M2 conversions). See §5 and §6. Stages A–E describe the **future** structure of the architecture; they are not near-term work. The near-term work is Phase 0–2 (§14).

---

## 2. Existing architecture assessment (reused and verified)

This section reuses the verified findings of the internal architecture design. It does not repeat the investigation; it records only what the evolution strategy depends on.

### 2.1 What exists today (Fact)

| Area | Current state | Evidence |
|---|---|---|
| Top-level packages | `cleaning`, `caching`, `analytics`, `profiling` + private `_accessors`, `_internal` | Design §2.2, §7 |
| Internal shape | Flat modules inside each domain; one capability subpackage (`cleaning/enrich`) | Design §2.2 |
| Public API | Root `__all__` = `['cleaning', 'caching', 'analytics', 'profiling', 'read_csv', 'read_json']`; package `__all__` exact | Design §2.4 |
| Dependencies | `cleaning → caching, profiling, _internal`; `profiling → _internal`; `analytics → none`; `caching → none`; `_internal → none` | Design §13 |
| Cross-package private imports | Exactly five documented edges | Design §3.3 F-3, §13.3 |
| `__all__` compliance | All 31 `.py` modules declare `__all__` | Design §3.3 F-8 |
| Import cycles | None | Design §2.5 |
| Row-wise iteration in data paths | None | Design §3.4, `BYNAT-ARCH-10` |
| Verification baseline | `693 passed, 29 deselected, 16 xfailed`; ruff clean; mypy clean (134 files) | Design §2.6 |

### 2.2 What the design already decided (Decision)

1. **Retain the approved package boundaries and the current module tree.** No package is split, merged, moved, or created; no new abstraction, manager, registry, protocol, or shared package is introduced.
2. **Normalize private helper naming and remove dead internal aliases.** Five private modules carry a canonical name plus a duplicate underscore alias; the alias layer is internal-only and is removed. The surviving migration symbol is `CacheManager._migrate_legacy_json_cache`.
3. **Retain and formalize the five cross-package private imports** as documented exceptions, enforced with `protected` contracts.
4. **Enforce with an AST contract test now; adopt Import Linter later.**
5. **Defer** the `base.py` split/generation question, analytics accessor methods, `save_to_sql` relocation, and Import Linter adoption, each with a revisit trigger.

### 2.3 What this strategy adds

The design answers "what is correct now." This strategy answers "what should change later, when, and how." The additions are:

- A **stage model** (§5, §6) that defines the next structural states.
- A **trigger framework** (§8) that converts architectural judgment into checkable conditions.
- **Six growth scenarios** (§7) that stress-test the model against plausible futures.
- A **near-term target** (§9) and **growth-ready target examples** (§10).
- A **phased roadmap** (§14) with acceptance criteria and checkpoints (§15).
- An **enforcement and governance** strategy (§16).
- A **traceability matrix** (§20).

### 2.4 Current tree (Fact)

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

---

## 3. External research and source evaluation

This section reports the external research conducted for this strategy. It distinguishes **documented source facts** from **architectural inference**. Sources are labeled **Direct fetch** (the page or repository listing was retrieved for this strategy), **Search result** (the content was retrieved through a search result), or **Prior report** (opened for the internal architecture design and reused).

### 3.1 Large-library internal organization

**EV-1 — pandas: public aggregation over a private, subpackaged core (Direct fetch).**
pandas' top level exposes `api`, `core`, `io`, `arrays`, `errors`, `util`, `compat`, `plotting`, `tseries`, `_config`, `_libs`, `_testing`; `pandas/core` is itself a large internal tree with subpackages `arrays`, `dtypes`, `indexes`, `groupby`, `internals`, `reshape`, `strings`, `tools`, `util`, `window`, `computation`, `indexers`, `interchange`, `methods`, `ops`, `sparse`, and `_numba`, alongside modules such as `frame.py`, `series.py`, `base.py`, `api.py`. The prior report documents that `pandas.core` and `pandas.compat` are documented PRIVATE, that the top-level namespace is aggregated from `pandas.core.api` and `pandas.io.api`, and that extension hooks live in the public `pandas.api.extensions`.
Source: [pandas core tree](https://github.com/pandas-dev/pandas/tree/main/pandas/core), [pandas top-level tree](https://github.com/pandas-dev/pandas/tree/main/pandas), [pandas Extending pandas](https://pandas.pydata.org/docs/development/extending.html) (Prior report E-1).
**Application:** a mature library separates a curated public surface from a deep private implementation tree. bynat's equivalent is the package `__all__` surface over private `_common`/`_outputs`/`_keys`/`_storage`/`_migration`/`_binding` modules. The *depth* of pandas' tree is a function of its scale; bynat should not imitate the depth, only the principle.

**EV-2 — NumPy NEP 52: public/private split by underscore, one canonical location per function (Search result; opened in the prior report).**
NEP 52 ("Python API cleanup for NumPy 2.0") states the goals of "a clear distinction between what is private and what is public" and "each public function should be available from only one place," and records the rename `numpy.core` → `numpy._core` to mark it private. NumPy's `test_public_api.py` maintains explicit `PUBLIC_MODULES` and `PRIVATE_BUT_PRESENT_MODULES` lists.
Sources: [NEP 52](https://numpy.org/neps/nep-0052-python-api-cleanup.html), [NumPy module structure](https://numpy.org/doc/stable/reference/module_structure.html), [numpy test_public_api.py](https://github.com/numpy/numpy/blob/main/numpy/tests/test_public_api.py).
**Application:** supports bynat's exact `__all__` discipline, the private `_internal` package, and the removal of duplicate private aliases. It does **not** support renaming bynat's public modules.

**EV-3 — scikit-learn: public API defined by the absence of a leading underscore (Search result).**
scikit-learn's glossary states that anything not beginning with `_` is informally considered public API and that private API (functions, modules, methods beginning `_`) is not assured to be stable. Its developer guide adds that unit tests should import from the public package path even when the implementation lives deeper.
Sources: [scikit-learn Glossary](https://scikit-learn.org/stable/glossary.html), [Developing scikit-learn estimators](https://scikit-learn.org/stable/developers/develop.html).
**Application:** bynat's `_`-prefixed modules and its "tests import the public path" convention are aligned with a mainstream library. It also supports the rule that internal reorganization must not change the public path.

**EV-4 — Requests: a mature library can remain a flat module set (Direct fetch).**
The `psf/requests` package is a flat set of 19 files under `src/requests` (`api.py`, `sessions.py`, `models.py`, `adapters.py`, `auth.py`, `cookies.py`, `hooks.py`, `exceptions.py`, `utils.py`, `structures.py`, `status_codes.py`, `compat.py`, `packages.py`, `help.py`, `_internal_utils.py`, `_types.py`, `__init__.py`, `__version__.py`, `certs.py`) with no subpackages. It adopted a `src/` layout but did not fragment into capability subpackages.
Source: [psf/requests src/requests tree](https://github.com/psf/requests/tree/main/src/requests).
**Application:** this is the strongest counterexample to "growth requires subpackages." A widely used library stays flat because its modules are cohesive and its public surface is small. bynat's flat modules are not a defect.

### 3.2 Architecture evolution and structural decision criteria

**EV-5 — Modular monolith: package by component, not by layer (Search result).**
Simon Brown describes the progression package-by-layer → package-by-feature → package-by-component, and argues that a component bundles related responsibilities behind a well-defined interface so that "the fewer public types you have, the fewer the number of potential dependencies." He also notes that in a modular monolith the compiler (or a static analyzer) must enforce boundaries because process boundaries do not.
Source: [Simon Brown — Modular Monolith](https://simonbrown.je/modular-monolith).
**Application:** bynat's domain packages are already "components" in this sense. The evolution path is to deepen components, not to impose a layer tree.

**EV-6 — Domain-centric modular monolith: small module API, dependency rule inward (Search result).**
Kamil Grzybek describes modular-monolith modules as self-contained, domain-oriented, with well-defined interfaces and a minimal module API, following the Dependency Rule (dependencies point inward).
Source: [Modular Monolith: Domain-Centric Design](https://kamilgrzybek.com/blog/posts/modular-monolith-domain-centric-design).
**Application:** supports bynat's domain packages and the rule that a new capability should be a self-contained module/package with a small surface, not a set of loosely coupled helpers.

**EV-7 — GitLab: extract cohesive domains, define public vs private, enforce boundaries (Search result).**
GitLab's hexagonal-monolith design document prescribes extracting cohesive functional domains into separate directory structures using DDD, defining which parts are public ports and which are private encapsulated details, and enforcing boundaries with a static analyzer (Packwerk).
Source: [GitLab Hexagonal Monolith](https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/modular_monolith/hexagonal_monolith).
**Application:** supports bynat's domain boundaries and the enforcement strategy. GitLab's scale (a large Rails monolith) is far beyond bynat's; only the principle transfers.

**EV-8 — Cohesion: split when responsibilities change for different reasons (Search result).**
The arc42 quality model's "Increase Cohesion" approach states: split a module when it carries responsibilities that change for different reasons; redistribute responsibilities when one concern is smeared across modules. It names failure modes: splitting by layer rather than responsibility, over-splitting into anaemic modules, and accretion of helpers. Verification includes change-coupling analysis and a one-sentence responsibility statement per module.
Source: [arc42 — Increase Cohesion](https://quality.arc42.org/approaches/increase-cohesion).
**Application:** this is the primary trigger for module splits in §6 and §8. It also warns against the exact failure mode (premature subpackaging) this strategy guards against.

**EV-9 — Modularity: start from reasons to change; treat module-count KPIs as dangerous (Search result).**
A modularity guide states that the easiest modularization mistake is moving files before understanding why they change; that useful evidence includes business capabilities with a clear owner, files that repeatedly change together, rules protecting the same invariant, and data with one authoritative writer; and that "a 'module count' KPI alone is dangerous. Splitting one coherent capability into ten packages can make the architecture worse while making the metric look more modular."
Source: [Modularity: Build Boundaries That Survive Change](https://thucde.dev/learn/docs/software-architecture/modularity).
**Application:** directly supports Conclusion 2 and the trigger-based approach. It also supplies the "replay the original change" verification used in §15.

**EV-10 — Change coupling matrix: consolidate high-change/low-physical; split low-change/high-physical (Search result).**
A change-coupling matrix classifies code by change frequency and physical proximity: high change + low physical proximity → consider consolidating; low change + high physical proximity → consider splitting; high/high and low/low are healthy.
Source: [Change Coupling](https://kb.buildingbetterteams.de/docs/technology-product/Software/Change-Together).
**Application:** provides the empirical method for deciding merges and splits in §8, and a concrete verification technique (§15).

**EV-11 — Package by feature: high cohesion and low coupling at package level (Search result).**
Package-by-feature keeps all classes related to one feature in one package, raising cohesion and lowering coupling; it also enables package-local visibility. The Rule of Three is recommended for shared code: start with the code close to its usage and move it to a common package only when more real usages appear.
Sources: [DZone — Package by Feature Is Demanded](https://dzone.com/articles/package-by-feature-is-demanded), [Philipp Hauer — Package by Feature](https://phauer.com/2020/package-by-feature).
**Application:** supports capability subpackages (Stage B) and the rule that shared code is extracted only after multiple real consumers exist.

**EV-12 — Premature abstraction and the Rule of Three (Search result).**
Google's Testing Blog ("Don't DRY Your Code Prematurely") and the Rule of Three (popularized by Martin Fowler) both warn that abstracting on the first or second occurrence risks selecting the wrong abstraction; duplication that is likely to diverge should be tolerated until a stable pattern emerges.
Sources: [Google Testing Blog](https://testing.googleblog.com/2024/05/dont-dry-your-code-prematurely.html), [Rule of three](https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming)).
**Application:** the guardrail against pre-building shared packages or generic engines. It is the basis for rejecting a generic `_shared` package and a generic transformation engine.

**EV-13 — Flat vs nested, and domain-named subpackages over catch-all modules (Search result).**
Real Python notes that domain-named subpackages scale better than catch-all `utils.py`/`helpers.py`, that subpackages appear "once an undifferentiated pile of modules starts to sprawl," and that `__init__.py` should curate the public surface. A Python textbook chapter adds "flat is better than nested" and recommends leading underscores for non-public objects.
Sources: [Real Python — Python Project Structure](https://realpython.com/python-application-layouts), [The Quick Python Book, Ch. 18 — Packages](https://manning.com/preview/the-quick-python-book-fourth-edition/chapter-18).
**Application:** supports the rule that a subpackage must have a clear responsibility (never `utils/`), and that depth should be added only when it improves navigation.

**EV-14 — Module vs package: namespace and organizational hierarchy (Search result).**
A practical guide states that a single module is enough for a small focused set of functions, that a package is warranted when related responsibilities have grown into several modules, and that the `__init__.py` should expose a deliberate interface. Another guide suggests splitting a module when it exceeds ~500 lines, serves multiple purposes, or changes for unrelated reasons.
Sources: [Python Module vs. Package](https://www.bowmanjd.com/python-module-package/), [Organize Python Code with Packages](https://rune.codes/hub/python/organize-python-code-with-packages).
**Application:** the ~500-line figure is treated as a **secondary** indicator only (it is explicitly rejected as a sole trigger by the design's `base.py` finding). The "multiple purposes / unrelated change reasons" criterion is the primary one.

### 3.3 Enforcement research

**EV-15 — Architecture fitness functions (Search result).**
Neal Ford defines an architectural fitness function as "an objective integrity assessment of some architectural characteristic(s)" and describes categories (triggered vs continual, atomic vs holistic). InfoQ adds that fitness functions should be objective and automatable, and that structural fitness functions (dependency rules, cycles) are the easiest place to start.
Sources: [Neal Ford — Building Evolutionary Architectures](https://nealford.com/books/buildingevolutionaryarchitectures.html), [O'Reilly — Fitness Functions](https://www.oreilly.com/library/view/building-evolutionary-architectures/9781492097532/ch02.html), [InfoQ — Fitness Functions for Your Architecture](https://www.infoq.com/articles/fitness-functions-architecture).
**Application:** the enforcement strategy (§16) is a set of structural fitness functions: dependency direction, private-import exceptions, `__all__` presence, public API stability, no cycles, no row-wise iteration.

**EV-16 — Automated boundary enforcement (Search result; Import Linter opened in the prior report).**
ArchUnit demonstrates architecture rules as tests (package dependency, layers, cycles). GitLab uses Packwerk. Import Linter provides `forbidden`, `protected`, `layers`, `independence`, `private_modules`, and `acyclic_siblings` contracts.
Sources: [ArchUnit](https://www.archunit.org/), [Import Linter contract types](https://import-linter.readthedocs.io/en/stable/contract_types/), [Ruff import-private-name](https://docs.astral.sh/ruff/rules/import-private-name/).
**Application:** bynat uses a dependency-free AST contract test now and optionally Import Linter later. The mechanism is proven; the choice is phased to avoid a new dependency before it is needed.

### 3.4 Research limitations

- The external sources are practitioner guides, library documentation, and one NEP. They are **not** empirical studies of Python library evolution. The triggers in §8 are therefore **interpretations** grounded in stated principles, not validated thresholds.
- Library scale differs enormously (pandas, NumPy, scikit-learn, GitLab vs bynat). Only principles transfer; no directory structure is copied.
- No source provides a universally correct LOC threshold. The strategy treats LOC as a secondary signal and forbids splitting on LOC alone.
- **Correction audit (this revision) required no additional external research.** The corrections are grounded in repository evidence (pinned `__module__`/`__wrapped__` contracts, `from bynat.cleaning import columns, io, stats, text`, `tools/sync_docs.py` resolution) and in the existing external sources. No new external claims are introduced.

---

## 4. Architecture evolution principles

These principles govern every transition in §§5–8. They are **Decisions** of this strategy.

| ID | Principle | Rationale | Source |
|---|---|---|---|
| P-1 | **Change reasons before size.** Split or group only when responsibilities change for different reasons. | arc42 EV-8; modularity guide EV-9 | §3.2 |
| P-2 | **One responsibility per module, one reason to change.** A module's responsibility must be expressible in one sentence without "and". | arc42 EV-8 | §3.2 |
| P-3 | **Public surface is frozen.** Internal moves never change public import paths or `__all__`. | scikit-learn EV-3; design §23 | §3.1 |
| P-4 | **Extract shared code only after multiple real consumers.** Rule of Three; no speculative sharing. | EV-11, EV-12 | §3.2 |
| P-5 | **Dependency direction is a rule, not a directory tree.** Layers may be used as a dependency rule; a global layer directory tree is rejected. | design §5; EV-5 | §3.2 |
| P-6 | **Subpackages need a responsibility, not a theme.** Never create `utils/`, `helpers/`, `common/`, or `_shared/` without a demonstrated cross-package responsibility. | EV-13; design §6.C | §3.2 |
| P-7 | **Boundaries are enforced, not aspirational.** Every boundary must have an automated check or an explicit documented exception. | EV-15, EV-16 | §3.3 |
| P-8 | **Reversibility.** Every conditional phase must have a rollback that restores the previous structure without public API change. | Evolutionary architecture EV-15 | §3.3 |
| P-9 | **Depth is the last resort.** Prefer flat modules; add a subpackage only when it improves navigation and ownership. | EV-4, EV-13, EV-14 | §3.1, §3.2 |
| P-10 | **The container stays a modular monolith.** No service extraction without a deployment requirement. | EV-5, EV-7; design §5 | §3.2 |

---

## 5. Package evolution model

### 5.1 Stages

**Stage A — Flat domain modules (current).**
Each domain package contains flat modules plus at most one capability subpackage where a real subsystem already exists (`cleaning/enrich`). Public API is the package `__all__`. Private helpers are underscore modules.

**Stage B — Capability subpackages (conditional).**
When a package's flat modules separate into ≥2 capability clusters, each with ≥2 modules and distinct change reasons, group each cluster into a subpackage with a curated `__init__.py`. The domain package's public `__all__` does not change.

**Stage C — Domain-internal layers (conditional).**
When a capability subpackage contains ≥2 internal layers with distinct consumers and change reasons (for example validation vs transformation vs I/O), introduce internal layer modules. This is rare and must reduce coupling, not add depth.

**Stage C transition procedure (conditional).**
1. Confirm the host is a capability subpackage (Stage B), not a flat module.
2. Identify ≥2 internal layers with distinct consumers and distinct change reasons.
3. Verify that layering reduces coupling (each layer has one reason to change) and does not add depth for its own sake.
4. Define a one-way dependency flow between layers (for example validation → transformation → assembly) and record it in the dependency model (§12).
5. Add layer modules with `__all__` (AR-11) and update the package `__init__.py` to preserve the existing surface.
6. Verify no cycle, no public path change, and no new cross-package private import.
7. Record the trigger, the one-sentence responsibility of each layer, and the rollback.

**Illustrative example (not a proposal to implement now).** If `cleaning/stats/` (Scenario 1) grew so that parameter validation, hierarchy computation, and output assembly changed for different reasons and had different consumers, it could introduce internal layers `_validation.py`, `_hierarchy.py`, and `_assembly.py` with a one-way flow `_validation → _hierarchy → _assembly`. This example is illustrative only; no such layers are proposed or scheduled.

**Stage D — New domain package (conditional).**
When a coherent capability has its own public contract, its own lifecycle, and no dependency on existing package internals, create a new top-level domain package with its own `__all__` and boundary tests.

**Stage E — Extraction (rejected, far future).**
Separate distributions or services. Rejected unless a concrete deployment, versioning, or team-boundary requirement appears.

### 5.2 Stage transition table

| From | To | Trigger (all conditions required) | Anti-trigger (any condition blocks) | Verification |
|---|---|---|---|---|
| A | B | (1) ≥2 capability clusters in one package; (2) each cluster has ≥2 modules; (3) clusters have distinct change reasons; (4) a package-level `__init__` can curate a coherent surface | A cluster is a single module; a cluster is a catch-all; the split creates a cycle; the split only moves files | Change-coupling shows clusters change independently; one-sentence responsibility per subpackage |
| B | C | (1) a capability subpackage has ≥2 internal layers; (2) layers have distinct consumers; (3) layers change for different reasons; (4) layering reduces coupling | Layers are thematic; layering adds a cycle; layers are single-function | §5.1 procedure; dependency graph shows one-way layer flow; no new cycle |
| A/B | D | (1) a coherent capability with its own public contract; (2) ≥2–3 operations; (3) no dependency on existing package internals; (4) a distinct user workflow | The capability is a single function; it needs another package's private internals; it is a theme | New package passes the boundary tests; no cross-package private imports |
| Any | E | A concrete deployment, versioning, or team-boundary requirement | No such requirement | Not applicable now |

**Counts are sanity checks.** The "≥2 clusters", "≥2 modules", and similar counts in the Trigger column are guards against trivial splits, not decision criteria. The decision criterion is demonstrated responsibility divergence and an improvement in cohesion, change coupling, or dependency direction (§8.4 R-11/R-12).

### 5.3 What does not trigger a stage change

- A module crossing a line-count threshold.
- A new feature that fits an existing module's responsibility.
- A desire for a "cleaner-looking" tree.
- A single new consumer of a private helper.
- A single optional dependency.

---

## 6. Module and component evolution model

### 6.1 Module states

| State | Description | Entered when |
|---|---|---|
| **M0 — Single module** | One cohesive module | Default |
| **M1 — Split** | One module becomes ≥2 modules in the same package | ≥2 cohesive responsibilities with different change reasons; each result non-trivial; no cycle |
| **M2 — Module → package** | A module becomes a package with submodules and a curated `__init__.py`; the package keeps the module's name | The module's responsibilities have grown into ≥2 sub-modules with distinct consumers/change reasons |
| **M3 — Merge** | Two or more modules become one | The modules always change together and form one responsibility, or a split produced anaemic modules |
| **M4 — Module addition** | A new module is added to an existing package | A new cohesive responsibility with a real consumer; no split/merge needed |

**M2 naming rule.** A module-to-package conversion must keep the same name (`columns.py` → `columns/`, `stats.py` → `stats/`, `io.py` → `io/`, `providers.py` → `providers/`). This is required because repository code and tests import these as package attributes (`from bynat.cleaning import columns, io, stats, text`; `from bynat.cleaning.enrich import providers`). Renaming the package would break those imports and is not a compatibility-safe internal move.

### 6.2 Module decision table

| Decision | Trigger (all required) | Anti-trigger | Acceptance |
|---|---|---|---|
| Keep unchanged | One responsibility; one reason to change; no dependency violation | — | Existing tests pass |
| Split | ≥2 responsibilities with different change reasons; each part non-trivial; no cycle; no public path change | LOC alone; a part would be a one-function module | Each part has a one-sentence responsibility; change-coupling shows independence |
| Convert to package | ≥2 sub-modules with distinct consumers; a coherent package surface; no cycle | The module is cohesive; sub-modules would be one-function | Package `__init__` curates a small surface; dependency direction preserved |
| Merge | Modules always change together and form one responsibility; or a split produced anaemic modules | Modules change for different reasons | One-sentence responsibility; no lost coverage |
| Extract shared helper | ≥2 real consumers with the same contract; a stable domain-independent responsibility | Similar code with different contracts; a single consumer | Canonical owner has one definition; consumers import it |
| Introduce a layer | ≥2 internal layers with distinct consumers and change reasons | Thematic layering; added depth without coupling benefit | One-way dependency flow; no cycle |

### 6.3 Component-level evolution

Components (classes, protocols, engines, managers) evolve by the same rules, with two additions:

- A **class/protocol** is introduced only when it has a concrete consumer and a lifecycle or structural contract (design §6.F). Growth does not justify new base classes or protocols.
- A **shared engine** (like `cleaning/enrich/engine.py`) stays shared only while its contract is stable and its consumers are real. If a second consumer needs a different contract, the correct move is a separate implementation, not a parameterized engine.

---

## 7. Growth scenarios and stress-test results

Each scenario states a plausible future, the trigger evidence, the transition, the target structure, acceptance, and rollback. **None of these is scheduled work.** They are stress tests of the model.

### 7.1 Scenario 1 — Cleaning grows 5–10×

**Premise.** `cleaning` accumulates many new transformation families: more column operations, more text operations, more statistical operations, more I/O formats, and a larger enrichment subsystem.

**Current state.** Flat modules `columns.py`, `text.py`, `stats.py`, `io.py`, plus `enrich/`.

**Trigger evidence.**
- ≥2 capability clusters (for example column structure, text processing, statistical operations, I/O) each with ≥2 modules.
- Clusters change for different reasons (a text-feature change does not touch statistics); this is supporting evidence, not the justification.
- The justification is demonstrated divergence in responsibilities, invariants, or ownership, and an improvement in cohesion, change coupling, or dependency direction (§8.4 R-11/R-12).
- A package-level `__init__.py` can curate a coherent surface for each cluster.

**Transition.** Stage A → B for `cleaning`, implemented through M2 conversions (`columns.py` → `columns/`, `text.py` → `text/`, `stats.py` → `stats/`, `io.py` → `io/`). The module and its same-named package do not coexist; the package replaces the module.

**Target structure (conditional).**

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
│   ├── __init__.py             # defines the public readers/writers; see §13.6
│   ├── readers.py
│   └── writers.py
└── enrich/                     # already a capability subpackage
    └── ...
```

**Conversion constraints.** Each new package keeps the module's name and re-exports the symbols that repository code and tests access (`from bynat.cleaning import columns, io, stats, text` and the accessor `__wrapped__` identity targets). Every new module, including each submodule, declares `__all__` with non-underscore symbols (AR-11; `test_doc_drift.py` imports every module). `io/__init__.py` must additionally preserve `read_csv.__module__ == "bynat.cleaning.io"` and `read_json.__module__ == "bynat.cleaning.io"` (`test_root_api.py`) and expose `_dedupe_key` (`test_internal_shared_helpers.py`). The `io` conversion must follow the `__module__` preservation strategy in §13.6. See §13.4.

**Acceptance.** Public `__all__` unchanged; no public import path change; dependency matrix unchanged; full suite, ruff, mypy pass; `tools/sync_docs.py --check` passes; change-coupling shows the clusters change independently.

**Rollback.** Re-collapse the subpackages into flat modules; no public API change.

### 7.2 Scenario 2 — Analytics grows from one class to a family

**Premise.** `analytics` gains new capability clusters: distributions, time series, KPI cards, histogram bins, filters/rules, and possibly forecasting.

**Current state.** One module `analyzer.py` with one `Analyzer` class.

**Trigger evidence.**
- ≥2 public method clusters with different dependencies and change reasons.
- The `Analyzer` facade remains the public entry point; internals can be separated without changing the class's public contract.

**Transition.** M1 (split `analyzer.py` into multiple private capability modules behind the `Analyzer` facade). This is **not** Stage B: no subpackage is created; the modules stay flat inside `analytics/`.

**Target structure (conditional).**

```text
bynat/analytics/
├── __init__.py                 # unchanged: exports Analyzer
├── analyzer.py                 # public facade; delegates to capability modules
├── _distributions.py           # private capability module
├── _timeseries.py
├── _kpi.py
├── _filters.py
└── _bins.py
```

**Acceptance.** `bynat.analytics.__all__` unchanged; `Analyzer` public methods unchanged; `analytics` still imports no other `bynat` package; full suite passes.

**Rollback.** Re-inline the capability modules into `analyzer.py`.

### 7.3 Scenario 3 — Caching gains a second backend

**Premise.** A concrete requirement appears for a non-SQLite cache backend (for example a remote or in-memory backend).

**Current state.** `caching` owns SQLite persistence (`_storage.py`), key identity (`_keys.py`), migration (`_migration.py`), and the public `CacheManager`.

**Trigger evidence.**
- A concrete second backend requirement (not a hypothetical).
- The backend has its own connection/lifecycle specifics.
- The `CacheManager` contract can remain the public facade.

**Transition.** Stage B for `caching` (a new `backends/` subpackage grouping backend modules) plus a relocation of `_storage.py` into `backends/sqlite.py`. No module-to-package name collision is involved.

**Target structure (conditional).**

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

**Acceptance.**
- **Protocol consumer:** `CacheManager` (or the backend-selection/composition component it delegates to) is the component that depends on the backend protocol; the protocol has exactly one consumer.
- **Implementations:** exactly two concrete implementations exist — `backends/sqlite.py` (the current `_storage.py` responsibility) and the new backend — and both implement the same required contract (same method surface and semantics).
- **`CacheManager` contract:** its public behavior and contract are unchanged.
- **No speculative framework:** the protocol exists only because a real second backend exists; it is not a generic extension framework, and no further abstraction is added.
- No new cross-package private import is introduced; full suite, ruff, mypy, and `tools/sync_docs.py --check` pass.

**Rollback.** Re-inline the backend into `_storage.py`.

**Note.** The prior design rejected a generic integration framework. A backend protocol is justified only by a real second backend; it is not introduced speculatively. `CacheManager` is the protocol's consumer; the protocol is an abstraction over the two concrete backends, not an extension framework.

### 7.4 Scenario 4 — Integrations grow

**Premise.** Enrichment gains many providers and services (translation, geocoding, currency, NLP, and new ones).

**Current state.** `cleaning/enrich/` with `providers.py` (3 protocols + 3 adapters), `engine.py`, and feature modules.

**Trigger evidence.**
- ≥3 provider families, or a provider with its own configuration/lifecycle that does not fit `providers.py`.
- Provider implementations change for different reasons.

**Transition.** Stage B inside `enrich`, implemented through an M2 conversion (`providers.py` → `providers/`). The package keeps the name `providers` so `from bynat.cleaning.enrich.providers import ...` and `from bynat.cleaning.enrich import providers` continue to work.

**Target structure (conditional).**

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

**Acceptance.** `enrich.__all__` and the public feature functions unchanged; provider protocols keep their consumers; no new cross-package private imports; full suite passes.

**Rollback.** Re-inline the provider modules into `providers.py`.

### 7.5 Scenario 5 — A new domain emerges

**Premise.** A coherent capability appears that is not cleaning, caching, analytics, or profiling — for example the roadmap's `DQ-02` "declarative DataFrame quality checks" ([`docs/ROADMAP.md`](../ROADMAP.md)).

**Current state.** No such package.

**Trigger evidence.**
- A coherent capability with its own public contract and ≥2–3 operations.
- No dependency on existing package internals.
- A distinct user workflow.

**Transition.** Stage A → D: a new top-level domain package.

**Target structure (conditional).**

```text
bynat/validation/               # conditional new domain
├── __init__.py                 # exports check_frame, ValidationReport, ...
├── core.py
└── rules.py
```

**Acceptance.** New package has its own `__all__` and boundary tests; it imports no functional package internals; the dependency matrix is extended with the new package; full suite passes.

**Rollback.** Remove the new package; no other package depends on it.

### 7.6 Scenario 6 — Cross-domain shared logic grows

**Premise.** More domain-independent helpers appear (for example validation primitives, serialization helpers) with real consumers in ≥2 packages.

**Current state.** `_internal/values.py` with `dedupe_key`.

**Trigger evidence.**
- ≥2 genuinely domain-independent helpers with stable contracts and ≥2 package consumers.
- The helpers share a coherent responsibility (for example value normalization).

**Transition.** M4 (module addition) inside `_internal`; no stage change. Do not create a generic `_shared` package.

**Target structure (conditional).**

```text
bynat/_internal/
├── __init__.py                 # curates the shared surface
├── values.py                   # existing
└── <coherent_module>.py        # e.g. validation.py
```

**Acceptance.** `_internal` still imports only stdlib and NumPy; it imports no functional package; each new helper has ≥2 real consumers; full suite passes.

**Rollback.** Move the helper back to its owning domain.

### 7.7 Stress-test conclusion

The model handles all six scenarios without changing the top-level boundaries, the public API, or the dependency direction. In every case the transition is **internal** and **reversible**, and in every case the trigger is a change-reason/cohesion signal rather than a size threshold. The model also shows the boundary of the strategy: if a scenario requires a new public contract, it is a new domain (Scenario 5), not a subpackage. Scenario classifications: 1 = Stage B via M2; 2 = M1; 3 = Stage B + relocation; 4 = Stage B via M2; 5 = Stage D; 6 = M4.

---

## 8. Explicit structural decision framework

This framework converts architectural judgment into checkable conditions. It is a **Decision** tool for reviewers.

### 8.1 Decision procedure

**Decision rule.** The counts in this framework are sanity checks, not triggers. A split or package is justified only by demonstrated responsibility divergence (reasons to change, invariants, ownership) and by an improvement in cohesion, change coupling, or dependency direction. Meeting a numeric threshold is never sufficient.

1. **Identify the change reason.** What changed, and which responsibilities does it touch?
2. **Locate the owner.** Which module/package owns that responsibility? (§12, §18 of the design)
3. **Check cohesion.** Does the owning module still have one responsibility and one reason to change?
4. **Check coupling.** Are there new or violated dependency edges?
5. **Check consumers.** How many real consumers does the affected contract have?
6. **Select the smallest structural change** that restores one-responsibility/one-reason-to-change without violating dependency direction or public API.
7. **Record the decision** with its trigger and rollback.

### 8.2 Decision matrix

| # | Decision | Trigger conditions (ALL) | Anti-triggers (ANY blocks) | Smallest change | Verification |
|---|---|---|---|---|---|
| 1 | Keep unchanged | One responsibility; no dependency violation | — | None | Existing tests |
| 2 | Split a module | ≥2 responsibilities with different change reasons; each part non-trivial; no cycle | LOC alone; one-function parts | M1 | One-sentence responsibility per part; change-coupling |
| 3 | Convert module → package | ≥2 sub-modules with distinct consumers; coherent surface; no cycle | Cohesive module; one-function sub-modules | M2 | Curated `__init__`; dependency direction |
| 4 | Group into capability subpackage | ≥2 modules per cluster; ≥2 clusters; distinct change reasons | Single-module cluster; catch-all | A→B | Change-coupling; one-sentence responsibility |
| 5 | Introduce internal layer | ≥2 layers with distinct consumers/change reasons; reduces coupling | Thematic layering; added depth | B→C | One-way flow; no cycle |
| 6 | Extract shared helper | ≥2 real consumers; same contract; stable domain-independent responsibility | Different contracts; one consumer | M1 (new module) | One canonical definition |
| 7 | New domain package | Own public contract; ≥2–3 operations; no internal dependency | Single function; needs internals | A/B→D | Boundary tests; matrix extension |
| 8 | Integration boundary subpackage | ≥3 provider families or provider-specific lifecycle | One provider; no lifecycle | A→B | Provider surface curated |
| 9 | Merge modules | Always change together; one responsibility; or anaemic split | Different change reasons | M3 | One-sentence responsibility |
| 10 | Keep flat | One responsibility; cohesive modules; no ownership gap | — | None | Existing tests |

### 8.3 Trigger evidence sources

| Evidence | How to obtain | Weight |
|---|---|---|
| Change-coupling (files that change together) | Version-history analysis | High |
| One-sentence responsibility test | Manual review | High |
| Dependency-direction violation | AST contract test / Import Linter | High |
| Cohesion/coupling signals | Manual review + dependency graph | High |
| Consumer count | Import scan | Medium |
| Module size (LOC) | AST measurement | Low (secondary) |
| New optional dependency | Requirement | Medium (for integration boundary) |
| New public contract | API design | High (for new domain) |

### 8.4 Hard rules

- **R-1.** Never split on LOC alone.
- **R-2.** Never create `utils/`, `helpers/`, `common/`, or `_shared/` without a demonstrated cross-package responsibility.
- **R-3.** Never introduce a protocol, base class, manager, registry, or engine without a concrete consumer.
- **R-4.** Never change a public import path or `__all__` value as part of an internal reorganization.
- **R-5.** Never add a cross-package private import without a documented exception and an enforcement entry.
- **R-6.** Never introduce a cycle.
- **R-7.** Never pre-build a structure for a scenario that has not occurred.
- **R-11.** File count, module count, line count, and cluster count are supporting signals only. They are never sufficient to justify a split or a package. The justification must be demonstrated divergence in responsibilities, reasons for change, invariants, or ownership, and the change must improve cohesion, reduce unrelated change coupling, or clarify dependency direction.
- **R-12.** Similar code does not imply shared responsibility. A split that only moves files without improving ownership or change behavior is rejected.

---

## 9. Near-term target architecture

**Decision.** The near-term target is the **current tree** with the internal normalization decided in the design. No module is added, removed, renamed, or moved. No subpackage is created.

### 9.1 Near-term target tree

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
│   ├── _keys.py                 # canonical names; alias block removed
│   ├── _migration.py            # canonical names; dead aliases removed
│   ├── _storage.py
│   └── manager.py               # dead private wrappers removed
├── cleaning/
│   ├── __init__.py
│   ├── _common.py               # canonical names; alias block removed
│   ├── _outputs.py              # canonical names; alias block removed
│   ├── base.py
│   ├── columns.py               # imports updated to canonical names
│   ├── io.py                    # imports updated
│   ├── stats.py                 # imports updated
│   ├── text.py                  # imports updated
│   └── enrich/
│       ├── __init__.py
│       ├── currency.py          # imports updated
│       ├── engine.py            # imports updated (cache_value_key)
│       ├── geocode.py           # imports updated
│       ├── nlp.py               # imports updated
│       ├── providers.py         # imports updated
│       └── translate.py         # imports updated
└── profiling/
    ├── __init__.py
    ├── profile.py
    └── report.py
```

### 9.2 Near-term changes (bounded, behavior-preserving)

| Change | Scope | Public impact |
|---|---|---|
| Remove private alias blocks | `cleaning/_common.py`, `cleaning/_outputs.py`, `caching/_keys.py`, `caching/_migration.py`, `caching/manager.py` | None |
| Update consumer imports | `cleaning/{columns,io,stats,text}.py`, `cleaning/enrich/{currency,engine,geocode,nlp,providers,translate}.py`, `benchmarks/reference_impls.py` | None |
| Update one test reference | `tests/modules/caching/migration/legacy/test_legacy_rollback.py:180` | None |
| Add AST contract test | `tests/cross_cutting/contracts/test_package_dependency_rules.py` | None |

### 9.3 Near-term acceptance

- Full suite, ruff, mypy pass; `tools/sync_docs.py --check` passes.
- No public signature, docstring, stub, or export changes.
- The AST contract test passes and fails when a prohibited edge is introduced.

---

## 10. Growth-ready architecture examples

These are **conditional targets**, not scheduled work. Each is entered only when its trigger fires (§5, §8). The examples use concrete filenames so that an engineer can execute them without redesigning the architecture.

### 10.1 Cleaning — Stage B (via M2 conversions)

Trigger: ≥2 capability clusters, each with ≥2 modules and distinct change reasons.

```text
bynat/cleaning/
├── __init__.py
├── base.py
├── _common.py
├── _outputs.py
├── columns/{__init__,rename,reshape,split}.py      # replaces columns.py
├── text/{__init__,keywords,truncation,categorization}.py  # replaces text.py
├── stats/{__init__,outliers,imputation,hierarchy}.py      # replaces stats.py
├── io/{__init__,readers,writers}.py                # replaces io.py
└── enrich/…
```

### 10.2 Analytics — M1 (module split)

Trigger: ≥2 public method clusters with different dependencies and change reasons.

```text
bynat/analytics/
├── __init__.py
├── analyzer.py
└── _{distributions,timeseries,kpi,filters,bins}.py
```

### 10.3 Caching — Stage B (second backend)

Trigger: a concrete second backend requirement. The backend protocol is consumed by `CacheManager`; it is justified by the real second backend, not introduced in advance.

```text
bynat/caching/
├── __init__.py
├── manager.py
├── _keys.py
├── _migration.py
└── backends/{__init__,base,sqlite,<new_backend>}.py
```

### 10.4 Enrichment — Stage B (via M2)

Trigger: ≥3 provider families or provider-specific lifecycle.

```text
bynat/cleaning/enrich/
├── __init__.py
├── engine.py
├── providers/{__init__,base,translation,geocoding,currency}.py
├── translate.py
├── geocode.py
├── currency.py
└── nlp.py
```

### 10.5 New domain — Stage D

Trigger: a coherent capability with its own public contract and no internal dependency (for example roadmap `DQ-02`).

```text
bynat/validation/
├── __init__.py
├── core.py
└── rules.py
```

### 10.6 Shared internal — M4 (module addition)

Trigger: ≥2 domain-independent helpers with stable contracts and ≥2 package consumers.

```text
bynat/_internal/
├── __init__.py
├── values.py
└── <coherent_module>.py
```

### 10.7 Filesystem validity and module-to-package conversions

A Python package cannot contain both `foo.py` and `foo/`. Every growth-ready tree therefore **replaces** the module with a same-named package; no tree lists both. The affected conversions are:

| Existing module | Growth package | Keeps the name because | Conversion |
|---|---|---|---|
| `cleaning/columns.py` | `cleaning/columns/` | `from bynat.cleaning import columns` | M2 |
| `cleaning/text.py` | `cleaning/text/` | `from bynat.cleaning import text` | M2 |
| `cleaning/stats.py` | `cleaning/stats/` | `from bynat.cleaning import stats` | M2 |
| `cleaning/io.py` | `cleaning/io/` | `from bynat.cleaning import io`; documented path | M2 |
| `cleaning/enrich/providers.py` | `cleaning/enrich/providers/` | `from bynat.cleaning.enrich.providers import ...` | M2 |

No other proposed tree contains a module/package name clash. Each package `__init__.py` re-exports the symbols that repository code, tests, and the generated stub access; see the compatibility inventory in §13.4. The `io` conversion additionally follows the `__module__` preservation strategy in §13.6.

### 10.8 What is deliberately not shown

- No `src/` layout migration (the flat layout is correct for this repo; the design §2.2 records it).
- No global `api/`/`domain/`/`infrastructure/` layer tree.
- No `utils/`, `helpers/`, `common/`, or `_shared/` package.
- No plugin/registry/DI structure.
- No lazy execution or query-engine layer.
- No `fit`/`transform` estimator layer.

---

## 11. Current-versus-proposed tree comparison

| Current path | Near-term target | Conditional growth target | Trigger |
|---|---|---|---|
| `bynat/cleaning/columns.py` | same | `bynat/cleaning/columns/{__init__,rename,reshape,split}.py` (M2) | Scenario 1 |
| `bynat/cleaning/text.py` | same | `bynat/cleaning/text/{__init__,keywords,truncation,categorization}.py` (M2) | Scenario 1 |
| `bynat/cleaning/stats.py` | same | `bynat/cleaning/stats/{__init__,outliers,imputation,hierarchy}.py` (M2) | Scenario 1 |
| `bynat/cleaning/io.py` | same | `bynat/cleaning/io/{__init__,readers,writers}.py` (M2) | Scenario 1 |
| `bynat/cleaning/enrich/providers.py` | same | `bynat/cleaning/enrich/providers/{__init__,base,translation,geocoding,currency}.py` (M2) | Scenario 4 |
| `bynat/analytics/analyzer.py` | same | `_{distributions,timeseries,kpi,filters,bins}.py` (M1) | Scenario 2 |
| `bynat/caching/_storage.py` | same | `backends/sqlite.py` + `backends/base.py` (relocation) | Scenario 3 |
| `bynat/_internal/values.py` | same | add coherent module (M4) | Scenario 6 |
| `bynat/cleaning/_common.py` | canonical names | same | — |
| `bynat/cleaning/_outputs.py` | canonical names | same | — |
| `bynat/caching/_keys.py` | canonical names | same | — |
| `bynat/caching/_migration.py` | canonical names | same | — |
| `bynat/caching/manager.py` | dead wrappers removed | same | — |
| `bynat/__init__.py` | same | same | — |
| `bynat/_accessors/*` | same | same | — |
| `bynat/profiling/*` | same | same | — |
| (none) | — | `bynat/validation/*` | Scenario 5 |

**Unchanged files.** `bynat/__init__.py`, `bynat/py.typed`, `bynat/_accessors/*`, `bynat/profiling/*`, and the public package `__init__.py` files are unchanged in every scenario. `cleaning/base.py` is unchanged in every scenario (its split/generation question remains deferred with a revisit trigger).

---

## 12. Cross-package dependency model

### 12.1 Current permitted dependencies (Fact, reused)

| Consumer | Permitted targets |
|---|---|
| `bynat` (root) | `cleaning`, `caching`, `analytics`, `profiling`, `_accessors`, `cleaning.io` |
| `_accessors` | `cleaning` (public + `_outputs.is_basedata_type`), `caching`, `profiling` |
| `cleaning` | `caching` (public + documented `caching._keys`), `profiling`, `_internal` |
| `profiling` | `_internal` |
| `analytics` | none |
| `caching` | none |
| `_internal` | none |

### 12.2 Evolution rules for new structure

- **New subpackages inherit the parent's dependency budget.** A `cleaning/columns/` subpackage may import what `cleaning/columns.py` may import, and nothing more.
- **A module-to-package conversion keeps the module's name.** `columns.py` → `columns/`, `stats.py` → `stats/`, `io.py` → `io/`, `providers.py` → `providers/`. Renaming the package would break `from bynat.cleaning import columns, io, stats, text` and `from bynat.cleaning.enrich.providers import ...`.
- **New domain packages must be independent or depend inward.** A new domain may not import another domain's private internals. If it needs a shared helper, the helper moves to `_internal` only with ≥2 real consumers.
- **`_internal` may grow only with coherent, domain-independent modules.** It remains stdlib + NumPy only.
- **`_accessors` remains delegation-only.** It never gains algorithms.
- **`analytics` and `profiling` remain independent** unless a concrete requirement changes that, with an explicit decision.
- **Every new cross-package private import requires a documented exception and an enforcement entry.**

### 12.3 Dependency matrix after each scenario

| Scenario | New package | New permitted edge | Prohibited |
|---|---|---|---|
| 1 | `cleaning/{columns,text,stats,io}` | none (inherit `cleaning`) | same as today |
| 2 | `analytics/_*` | none | same |
| 3 | `caching/backends` | none (inherit `caching`) | `caching` still imports no functional package |
| 4 | `cleaning/enrich/providers` | none (inherit `enrich`) | same |
| 5 | `validation` | none (independent) | must not import functional internals |
| 6 | `_internal/<module>` | functional → `_internal` | `_internal` → functional |

---

## 13. Public API and compatibility strategy

### 13.1 Four import-path categories

An unchanged `__all__` does **not** by itself prove compatibility. `__all__` governs star-imports and the package namespace; it does not govern direct module imports, package-attribute access, function `__module__`, `__wrapped__` identity, or generated stubs. Every module path must be classified before it is moved or replaced.

| Category | Description | Examples | Move policy |
|---|---|---|---|
| 1. Public symbols | Names declared in a package `__all__` | `BaseData`, `CsvFile`, `JsonFile`, `CacheManager`, `Analyzer`, `profile`, `ProfileReport`, `read_csv`, `read_json` | Frozen; a change is a public API change |
| 2. Public package import paths | The importable package namespaces | `bynat`, `bynat.cleaning`, `bynat.caching`, `bynat.analytics`, `bynat.profiling` | Frozen |
| 3. Internal implementation module paths | Non-exported modules imported by repository code or tests | `bynat.cleaning.columns`, `.text`, `.stats`, `.enrich.providers`, `.enrich.engine`, `bynat.caching._keys`, `._storage`, `._migration` | Movable only with the preservation rules in §13.4 |
| 4. Documented import paths not in `__all__` | Paths named in `docs/` or `BYNAT-API` but not exported | `bynat.cleaning.io` (documented in `BYNAT-API-2` and `ARCHITECTURE_RESEARCH.md`) | Movable only with the preservation rules in §13.4 |

### 13.2 Public `__all__` surfaces (Fact)

| Surface | Value |
|---|---|
| `bynat.__all__` | `['cleaning', 'caching', 'analytics', 'profiling', 'read_csv', 'read_json']` |
| `bynat.cleaning.__all__` | `['BaseData', 'CsvFile', 'JsonFile']` |
| `bynat.caching.__all__` | `['CacheManager', 'CACHE_DIR_ENV_VAR', 'DEFAULT_CACHE_DIR', 'shared_cache_manager']` |
| `bynat.analytics.__all__` | `['Analyzer']` |
| `bynat.profiling.__all__` | `['profile', 'ProfileReport', 'DatasetProfile', 'ColumnProfile']` |

### 13.3 Classification procedure and compatibility rules

**Procedure before moving or replacing a module path.**
1. Is the path (or a symbol it defines) declared in a package `__all__`? → Category 1/2; frozen.
2. Is the path imported as a package attribute by repository code or tests (`from bynat.cleaning import columns, io, stats, text`)? → Category 3; the attribute and its accessed symbols must be preserved.
3. Is the path named in `docs/` or `BYNAT-API`? → Category 4; the documented path and any pinned `__module__` must be preserved.
4. Is the path otherwise private? → Category 3; movable, but `__all__`, `__wrapped__` identity, and `tools/sync_docs.py` resolution must be preserved.
5. Record the classification and the preservation requirement in the phase's acceptance criteria.

**Compatibility rules.**

| Rule | Description |
|---|---|
| C-1 | Public import paths are frozen. |
| C-2 | Public `__all__` values are frozen. |
| C-3 | Public signatures and docstrings are frozen (docstring drift is already tested). |
| C-4 | Documented behavior (`inplace`, `output_type`, index/order preservation, cache sharing) is frozen. |
| C-5 | Private modules may move freely **only** when no repository code, test, doc, stub, or pinned `__module__`/`__wrapped__` contract depends on the path; no compatibility alias is created for a move. |
| C-6 | A public module move is a public API change and requires explicit approval. |
| C-7 | Internal reorganization is a minor/patch change if the public API is unchanged. |
| C-8 | No deprecation or facade is introduced to absorb an internal redesign. |
| C-9 | A module-to-package conversion keeps the module's name and re-exports every symbol accessed by repository code, tests, and the generated stub. |
| C-10 | A move that would change a pinned `__module__` or `__wrapped__` identity target requires explicit approval, not a silent implementation. |

**When is an internal move genuinely safe?** When the path is Category 3, no repository code/test/doc/stub imports it, no `__module__`/`__wrapped__` is pinned, and the move does not change `__all__`. **When is explicit approval required?** When the path is Category 1/2/4, when a `__module__` or `__wrapped__` contract is pinned, or when the move changes a documented path.

### 13.4 Compatibility inventory for the growth conversions

| Module path | Category | Relied on by | Pinned contract | Growth conversion | Preservation requirement |
|---|---|---|---|---|---|
| `bynat.cleaning.io` | 4 (documented) | `bynat/__init__.py`; `base.py` docstrings; `_accessors/dataframe.pyi`; `tests/cross_cutting/contracts/test_root_api.py`; `tests/cross_cutting/accessor/test_accessor.py`; `tests/cross_cutting/contracts/test_internal_shared_helpers.py`; `tools/sync_docs.py` | `read_csv.__module__ == "bynat.cleaning.io"`; `read_json.__module__ == "bynat.cleaning.io"`; `io._dedupe_key is _internal.dedupe_key`; `bynat.read_csv is io.read_csv` | M2 → `io/` | `io/__init__.py` defines or re-exports `read_csv`, `read_json`, `save_to_json`, `save_to_sql`, `IfExists`, `JsonOrient`, `_dedupe_key`; `read_csv`/`read_json` keep `__module__ == "bynat.cleaning.io"` (see §13.6) |
| `bynat.cleaning.columns` | 3 | `base.py` (`from . import columns`); `_accessors/dataframe.py`; `tests/cross_cutting/accessor/test_accessor_package_boundary.py`; `tests/cross_cutting/contracts/test_properties.py`; `tests/modules/columns/*` | `BynatAccessor.<method>.__wrapped__ is columns.<func>`; 9 column functions accessed as attributes | M2 → `columns/` | `columns/__init__.py` re-exports the 9 functions; each submodule has `__all__` |
| `bynat.cleaning.text` | 3 | `base.py`; `_accessors/dataframe.py`; accessor boundary test; `tests/cross_cutting/contracts/test_properties.py`; `tests/cross_cutting/equivalence/test_equivalence_keywords.py` | `BynatAccessor.<method>.__wrapped__ is text.<func>`; 3 text functions | M2 → `text/` | `text/__init__.py` re-exports the 3 functions; each submodule has `__all__` |
| `bynat.cleaning.stats` | 3 | `base.py`; `_accessors/dataframe.py`; accessor boundary test; `tests/cross_cutting/contracts/test_doc_drift.py`; `tests/cross_cutting/equivalence/test_equivalence_outliers.py`; `tools/sync_docs.py` | `BynatAccessor.<method>.__wrapped__ is stats.<func>`; `stats.fill_missing.__doc__` equality; 5 statistics functions | M2 → `stats/` | `stats/__init__.py` re-exports the 5 functions; each submodule has `__all__` |
| `bynat.cleaning.enrich.providers` | 3 | `base.py`; `enrich/__init__.py`; `_accessors/dataframe.pyi`; `tests/modules/enrichment/*` | `enrich.__all__` re-exports 6 provider symbols; stub imports 3 | M2 → `providers/` | `providers/__init__.py` re-exports the 6 provider symbols; each submodule has `__all__` |

### 13.5 Compatibility risk per scenario

| Scenario | Public API risk | Mitigation |
|---|---|---|
| 1–4, 6 | None (internal moves) | Keep public paths; run contract tests; apply §13.4 |
| 5 | New surface (additive) | New package `__all__`; no change to existing surfaces |
| Any | Accidental public path change | AST contract test asserts root/package `__all__`; §13.4 inventory |

### 13.6 `io` module-to-package conversion: `__module__` preservation

**Behavior.** Python sets a function's `__module__` to the module in which the `def` executes. If `read_csv` is defined in `bynat.cleaning.io.readers`, then `read_csv.__module__ == "bynat.cleaning.io.readers"`, and the pinned assertions `bynat.read_csv.__module__ == "bynat.cleaning.io"` and `bynat.read_json.__module__ == "bynat.cleaning.io"` (`tests/cross_cutting/contracts/test_root_api.py`) fail. The contract is public and is not weakened by the conversion.

**Viable options.**

| Option | Mechanism | `__module__` | `tools/sync_docs.py` | Introspection / pickling | Verdict |
|---|---|---|---|---|---|
| A. Define the public functions in `io/__init__.py` | `def read_csv(...)` executes in the package `__init__` | `bynat.cleaning.io` (natural) | Works: it parses `io/__init__.py` and finds the top-level `def` | `inspect.getmodule`, `inspect.getsourcefile`, and `pickle` all resolve to `bynat.cleaning.io`; no hidden state | **Recommended** |
| B. Define in `io/readers.py`, re-export, and set `__module__ = "bynat.cleaning.io"` on each public function | Metadata mutation | `bynat.cleaning.io` (assigned) | Breaks: `_stub_function` resolves `func.__module__` to `io/__init__.py` and looks for a top-level `def read_csv` there | `inspect.getmodule`/`pickle` resolve via `__module__`; `inspect.getsourcefile` still uses `co_filename` (`readers.py`); `__module__` no longer reflects the defining module | Viable only with a `tools/sync_docs.py` update and explicit approval |
| C. Define in `io/readers.py` and accept `__module__ == "bynat.cleaning.io.readers"` | No mutation | `bynat.cleaning.io.readers` | Works | Introspection reports the true module | **Rejected**: changes a pinned public contract; weakens the requirement |

**Recommended approach (Option A).** Keep the public function definitions in `io/__init__.py`; use `io/readers.py` and `io/writers.py` for private helpers and for new format implementations. This preserves `__module__`, function identity, `inspect` behavior, pickling, and `tools/sync_docs.py` resolution with no hidden compatibility mechanism.

**Trade-offs.** `io/__init__.py` is no longer a thin re-export module; it owns the public reader/writer definitions. If a thin `__init__` is preferred, Option B is the alternative, but it is **not behavior-neutral**: it requires an explicit `__module__` assignment on each public function and a `tools/sync_docs.py` change to locate source via `inspect.getsourcefile`/`co_filename`. Option B therefore requires explicit approval; it must not be introduced silently. Option C is rejected because it weakens the pinned contract.

**Concrete tests (to add when E1 is implemented).**
- `bynat.read_csv.__module__ == "bynat.cleaning.io"` and `bynat.read_json.__module__ == "bynat.cleaning.io"` (existing `test_root_api.py`).
- `bynat.read_csv is bynat.cleaning.io.read_csv` and `bynat.read_json is bynat.cleaning.io.read_json` (identity).
- `inspect.signature(bynat.read_csv) == inspect.signature(bynat.cleaning.io.read_csv)`.
- `from bynat.cleaning.io import read_csv, read_json, save_to_json, save_to_sql, IfExists, JsonOrient` succeeds.
- `bynat.cleaning.io._dedupe_key is bynat._internal.dedupe_key`.
- `importlib.import_module("bynat.cleaning.io.readers")` and `...io.writers` succeed; each submodule declares `__all__`.
- `pickle.loads(pickle.dumps(bynat.read_csv)) is bynat.read_csv`.
- `tools/sync_docs.py --check` passes.

---

## 14. Phased implementation roadmap

**Implementation authorization: NOT AUTHORIZED.** This roadmap is the plan to follow if implementation is later authorized. It contains two different categories of work:

**A. Near-term preparation and enforcement.** Phase 0 records the accepted baseline and decisions; Phase 1 normalizes existing internal imports/wrappers and adds the dependency contract test; Phase 2 optionally strengthens enforcement when a demonstrated CI need exists. These phases do not convert current modules into packages and do not represent the future growth of the architecture.

**B. Future structural evolution.** E1–E6 are conditional transitions activated only by their respective real-world triggers. They are not scheduled implementation tasks, not a sequence every domain must follow, and they may occur independently, in a different order, or never.

### 14.1 Phase 0 — Baseline and decision record

- **Scope:** freeze the baseline commit; record this strategy; add architecture decision records for the stage model and triggers.
- **Entry:** this document accepted.
- **Acceptance:** baseline commit recorded; decisions traceable.
- **Checkpoint:** review against the design.
- **Rollback:** not applicable (documentation only).

### 14.2 Phase 1 — Internal normalization (immediate)

- **Scope:** remove private alias blocks and dead wrappers; update consumer imports; update one test reference; add the AST contract test.
- **Entry:** Phase 0 complete.
- **Tasks:** design §24 Steps 1–2.
- **Acceptance:** full suite, ruff, mypy pass; `tools/sync_docs.py --check` passes; no public change; AST test passes and fails on a prohibited edge.
- **Checkpoint:** independent review of the diff; verify no public signature/docstring change.
- **Rollback:** revert the commit; no public API change.

### 14.3 Phase 2 — Enforcement hardening (optional)

- **Scope:** adopt Import Linter as a dev dependency; add `protected` contracts for the five documented edges; optionally enable Ruff `PLC2701`.
- **Entry:** Phase 1 complete; CI enforcement need identified.
- **Acceptance:** `lint-imports` passes; CI job added.
- **Checkpoint:** verify all five edges are represented.
- **Rollback:** remove the dev dependency and config.

### 14.4 Conditional evolution phases E1–E6 (Category B — future structural evolution)

The phases are named **E** (evolution) to avoid confusion with **Stage C** (domain-internal layers). Each maps unambiguously to one scenario and one structural transition.

| Phase | Scenario | Structural transition | Trigger | Scope | Acceptance | Rollback |
|---|---|---|---|---|---|---|
| E1 | 1 — Cleaning growth | Stage A→B via M2 | §7.1 | `cleaning/{columns,text,stats,io}/` | §15.1 + change-coupling; §13.4 inventory | Re-collapse subpackages |
| E2 | 2 — Analytics growth | M1 (module split) | §7.2 | `analytics/_*` | `Analyzer` contract unchanged | Re-inline modules |
| E3 | 3 — Second cache backend | Stage B + relocation | §7.3 | `caching/backends/` | Protocol consumer is `CacheManager`; two implementations satisfy one contract; `CacheManager` contract unchanged; no speculative framework | Re-inline backend |
| E4 | 4 — Integration growth | Stage B via M2 | §7.4 | `enrich/providers/` | Provider surface unchanged | Re-inline providers |
| E5 | 5 — New domain | Stage D | §7.5 | `validation/` | Boundary tests pass; matrix extended | Remove package |
| E6 | 6 — Shared logic growth | M4 (module addition) | §7.6 | `_internal/<module>` | `_internal` stays stdlib+NumPy | Move helper back |

**Rule.** E1–E6 are not scheduled. Each is opened only when its trigger fires, and each is closed by its acceptance criteria. A trigger is not a numeric threshold: each phase opens only when the §7.x responsibility evidence is demonstrated (divergence in responsibilities, reasons for change, invariants, or ownership, and an improvement in cohesion, change coupling, or dependency direction), not when a count is reached (§8.4 R-11/R-12).

### 14.5 What is explicitly not in the roadmap

- No pre-building of subpackages.
- No `src/` layout migration.
- No generic layer tree.
- No plugin/registry/DI structure.
- No lazy execution layer.
- No `fit`/`transform` estimator layer.
- No splitting of `base.py`, `stats.py`, or `analyzer.py` by LOC.

---

## 15. Phase-specific acceptance criteria and checkpoints

### 15.1 Universal acceptance criteria

Every phase must satisfy:

1. Full test suite passes (`./.venv-check/Scripts/python.exe -m pytest -q`).
2. `ruff check bynat tests benchmarks` passes.
3. `mypy` passes.
4. `tools/sync_docs.py --check` passes.
5. Public `__all__` values and public signatures are unchanged.
6. The AST contract test passes (dependency matrix, private imports, `__all__`, no cycles).
7. The change is reversible without public API change.

### 15.2 Phase checkpoints

| Phase | Checkpoint | Evidence |
|---|---|---|
| 0 | Strategy accepted | This document |
| 1 | Normalization complete | Test/lint/type/sync output; diff review |
| 2 | Enforcement adopted (optional) | `lint-imports` output; CI config |
| E1 | Cleaning restructured | Change-coupling; boundary tests; §13.4 |
| E2 | Analytics restructured | `Analyzer` parity tests |
| E3 | Backend added | `CacheManager` contract tests |
| E4 | Providers grouped | Provider protocol tests |
| E5 | New domain added | New boundary tests; matrix extension |
| E6 | Shared module added | `_internal` import test |

### 15.3 Verification techniques

- **Change-coupling analysis** (EV-10): confirm that split modules change independently.
- **One-sentence responsibility test** (EV-8): each module's responsibility is statable without "and".
- **Dependency-graph replay** (EV-9): replay a recent change and count how many modules/owners must be touched; improvement is the proof.
- **Boundary tests:** AST contract test, Import Linter, existing package-boundary tests.
- **Public API parity:** root/package `__all__` tests, signature/docstring drift tests.

### 15.4 Operational review procedure for opening a conditional phase

When a trigger is suspected, apply this repeatable procedure. It produces the evidence the phase's acceptance criteria require; it does not replace architectural judgment with a numeric KPI.

1. **Inspect repository history.** For the candidate modules, collect `git log --name-only` / `git log --stat` across recent releases and build a change-coupling matrix (which files change together). Include the owners of the affected invariants.
2. **Identify independent change clusters.** Group files that change together. Classify each group: high change + high physical proximity is healthy; high change + low proximity suggests consolidation; low change + high proximity is a split candidate.
3. **Distinguish genuine responsibility divergence from coincidental similarity.** For each candidate cluster, write a one-sentence responsibility and identify its invariant and its owner. Genuine divergence: a change in one cluster does not require editing the other, and the clusters protect different invariants. Coincidental similarity: similar code but the same change reason, the same invariant, or a shared owner.
4. **Assess ownership and maintainability improvement.** Replay a recent real change and count the modules and owners that must be touched. Check the dependency direction and the existence of a cycle. A valid split reduces the number of modules/owners touched for a change in one responsibility and does not create a one-function module.
5. **Record the decision and the evidence.** The phase record states the trigger, the one-sentence responsibilities, the change-coupling result, the replay result, and the rollback.

**Evidence that justifies rejecting the proposed split.**
- The candidate clusters change together (high change coupling).
- One cluster is a single function or would be a one-function module.
- The split creates a cycle or violates the dependency direction.
- The split only moves files without changing ownership or change reasons.
- The split would require a public API change or a new cross-package private import.
- The "divergence" is coincidental code similarity with a shared invariant or owner.
- The split creates a catch-all (`utils/`, `helpers/`) or a thematic layer.

**Thresholds.** The counts in §5–§8 (for example "≥2 clusters", "≥2 modules per cluster") are sanity checks to avoid trivial splits, not targets. They are not KPIs and are never sufficient to justify a split. The decision criterion is the responsibility evidence in steps 1–4: demonstrated divergence in responsibilities, reasons for change, invariants, or ownership, and an improvement in cohesion, change coupling, or dependency direction (§8.4 R-11/R-12). A split that only moves files without improving ownership or change behavior is rejected.

---

## 16. Architecture enforcement strategy

### 16.1 Fitness functions

| ID | Fitness function | Mechanism | Phase |
|---|---|---|---|
| AF-1 | Root `__all__` is exact | `test_root_api.py` | Now |
| AF-2 | Package `__all__` exact and non-underscore | `test_doc_drift.py` | Now |
| AF-3 | Dependency directions follow the matrix | AST contract test | Phase 1 |
| AF-4 | No functional package imports `_accessors` | `test_accessor_package_boundary.py` | Now |
| AF-5 | `_internal` imports only stdlib + NumPy | `test_internal_shared_helpers.py` | Now |
| AF-6 | `profiling` imports no functional package | `test_profiling_package_boundary.py` | Now |
| AF-7 | `analytics` imports no other `bynat` package | AST contract test | Phase 1 |
| AF-8 | `_accessors` contains no domain algorithms | `test_accessor_package_boundary.py` | Now |
| AF-9 | Cross-package private imports are exactly the five documented edges | AST contract test | Phase 1 |
| AF-10 | No row-wise iteration in data paths | AST inspection / execution guards | Now (`BYNAT-ARCH-10`) |
| AF-11 | Every module declares `__all__` | `test_doc_drift.py` + AST test | Now / Phase 1 |
| AF-12 | No import cycle | AST contract test | Phase 1 |
| AF-13 | Public signatures/docstrings match stubs | `test_doc_drift.py` | Now |

### 16.2 Mechanisms and phasing

- **Now (no new dependency):** existing contract tests + the AST contract test.
- **Phase 2 (optional dev dependency):** Import Linter with `protected` contracts for `bynat.caching._keys`, `bynat.cleaning._outputs`, `bynat._internal`; `private_modules` scoped to `bynat`; `acyclic_siblings`; optional Ruff `PLC2701`.
- **CI:** run the contract tests in the existing test job; run Import Linter in a dedicated job if adopted.

### 16.3 Governance

- **New module checklist:** one responsibility; correct owner; no new cross-package private import; `__all__` declared; tests in the owning module directory (`BYNAT-ARCH-2`).
- **New subpackage checklist:** trigger satisfied; curated `__init__`; no cycle; dependency budget inherited; public API unchanged.
- **New domain package checklist:** own public contract; ≥2–3 operations; no internal dependency; boundary tests; matrix extension.
- **Change review:** every structural PR states the trigger it satisfies and its rollback.

---

## 17. Deferred decisions and revisit triggers

| ID | Item | Disposition | Revisit trigger |
|---|---|---|---|
| AE-Q1 | Should `caching._keys` become a narrow public contract? | Keep private with a documented edge | A second consumer or a user-facing requirement |
| AE-Q2 | Should `base.py` be split or generated? | Defer | Concrete maintenance pain; docstring-generation cost |
| AE-Q3 | Should any `Analyzer` operation become an accessor method? | Defer | A concrete stable DataFrame contract |
| AE-Q4 | Should `save_to_sql` move to its own module? | No | Never (lazy import already isolates the dependency) |
| AE-Q5 | Should Import Linter be adopted now? | No | CI enforcement need (Phase 2) |
| AE-Q6 | `BaseData.cache_dir` inheritance on derived-frame manager recreation | Missing behavioral contract | A user report or a decision to propagate `_bynat_cache_dir` through metadata |
| AE-Q7 | Should a `validation` domain be created? | Defer | Roadmap `DQ-02` becomes a concrete requirement |
| AE-Q8 | Should a second cache backend be added? | Defer | A concrete backend requirement |
| AE-Q9 | Should `_internal` expand? | Defer | ≥2 domain-independent helpers with real consumers |
| AE-Q10 | Should the flat layout move to `src/`? | No | A packaging reason (none now) |

Each deferral has a stated revisit trigger. None prevents the near-term work.

---

## 18. Risks, trade-offs, and rejected alternatives

### 18.1 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Premature subpackaging | Medium | Fragmentation, churn | Trigger-gated stages; hard rules R-1–R-7 |
| Wrong shared abstraction | Medium | Coupling, rework | Rule of Three; extract only with ≥2 real consumers |
| Public API breakage during a move | Low | Compatibility | C-1–C-8; AST contract test |
| Enforcement drift | Low | Boundary erosion | Fitness functions AF-1–AF-13; CI |
| Over-engineering for a scenario that never occurs | Medium | Wasted structure | Conditional phases E1–E6; no pre-building |
| Change-coupling evidence misread | Medium | Wrong split/merge | Combine with one-sentence responsibility and dependency review |

### 18.2 Trade-offs

- **Flat vs nested.** Flat is easier to navigate and matches Requests (EV-4); nested is added only when ownership demands it.
- **AST test vs Import Linter.** The AST test has no new dependency and is immediate; Import Linter is more expressive but adds a dev dependency. Phased.
- **Trigger-based vs schedule-based evolution.** Trigger-based avoids speculative structure but requires discipline to record triggers. This strategy records them.

### 18.3 Rejected alternatives

| Alternative | Decision | Reason |
|---|---|---|
| Pre-build capability subpackages now | Reject | No trigger; speculative structure |
| Global `api/`/`domain/`/`infrastructure/` layers | Reject | Obscures domain ownership; design §5 |
| Generic `_shared` package | Reject | No demonstrated cross-package responsibility |
| `utils/`/`helpers/` catch-all modules | Reject | No responsibility statement |
| Plugin registry / entry points | Reject | No third-party plugin requirement |
| DI container | Reject | No consumer |
| Generic transformation engine | Reject | Transformations are explicit functions |
| Lazy execution / query engine | Reject | No lazy/optimized requirement |
| `fit`/`transform` estimator layer | Reject | Transformations are stateless functions |
| Microservices / separate distributions | Reject | One installable library |
| `src/` layout migration | Reject | Flat layout is correct; no packaging reason |
| Splitting `base.py`/`stats.py`/`analyzer.py` by LOC | Reject | Cohesive; size is documentation or one domain |
| Moving `save_to_sql` to its own module | Reject | Lazy import already isolates the dependency |
| Renaming public modules to match a "cleaner" tree | Reject | Public API change without requirement |

---

## 19. Evidence and source references

### 19.1 External sources

| ID | Source | URL | Type |
|---|---|---|---|
| EV-1 | pandas, core and top-level trees | <https://github.com/pandas-dev/pandas/tree/main/pandas/core> | Direct fetch |
| EV-1 | pandas, *Extending pandas* | <https://pandas.pydata.org/docs/development/extending.html> | Prior report |
| EV-2 | NumPy, *NEP 52 — Python API cleanup* | <https://numpy.org/neps/nep-0052-python-api-cleanup.html> | Search result |
| EV-2 | NumPy, *Module structure* | <https://numpy.org/doc/stable/reference/module_structure.html> | Direct fetch |
| EV-2 | NumPy, `test_public_api.py` | <https://github.com/numpy/numpy/blob/main/numpy/tests/test_public_api.py> | Search result |
| EV-3 | scikit-learn, *Glossary* | <https://scikit-learn.org/stable/glossary.html> | Search result |
| EV-3 | scikit-learn, *Developing estimators* | <https://scikit-learn.org/stable/developers/develop.html> | Search result |
| EV-4 | psf/requests, `src/requests` tree | <https://github.com/psf/requests/tree/main/src/requests> | Direct fetch |
| EV-5 | Simon Brown, *Modular Monolith* | <https://simonbrown.je/modular-monolith> | Search result |
| EV-6 | Kamil Grzybek, *Modular Monolith: Domain-Centric Design* | <https://kamilgrzybek.com/blog/posts/modular-monolith-domain-centric-design> | Search result |
| EV-7 | GitLab, *Hexagonal Monolith* | <https://handbook.gitlab.com/handbook/engineering/architecture/design-documents/modular_monolith/hexagonal_monolith> | Search result |
| EV-8 | arc42, *Increase Cohesion* | <https://quality.arc42.org/approaches/increase-cohesion> | Search result |
| EV-9 | *Modularity: Build Boundaries That Survive Change* | <https://thucde.dev/learn/docs/software-architecture/modularity> | Search result |
| EV-10 | *Change Coupling* | <https://kb.buildingbetterteams.de/docs/technology-product/Software/Change-Together> | Search result |
| EV-11 | DZone, *Package by Feature Is Demanded* | <https://dzone.com/articles/package-by-feature-is-demanded> | Search result |
| EV-11 | Philipp Hauer, *Package by Feature* | <https://phauer.com/2020/package-by-feature> | Search result |
| EV-12 | Google Testing Blog, *Don't DRY Your Code Prematurely* | <https://testing.googleblog.com/2024/05/dont-dry-your-code-prematurely.html> | Search result |
| EV-12 | *Rule of three* | <https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming)> | Search result |
| EV-13 | Real Python, *Python Project Structure* | <https://realpython.com/python-application-layouts> | Search result |
| EV-13 | *The Quick Python Book*, Ch. 18 | <https://manning.com/preview/the-quick-python-book-fourth-edition/chapter-18> | Search result |
| EV-14 | *Python Module vs. Package* | <https://www.bowmanjd.com/python-module-package/> | Search result |
| EV-14 | *Organize Python Code with Packages* | <https://rune.codes/hub/python/organize-python-code-with-packages> | Search result |
| EV-15 | Neal Ford, *Building Evolutionary Architectures* | <https://nealford.com/books/buildingevolutionaryarchitectures.html> | Search result |
| EV-15 | O'Reilly, *Fitness Functions* | <https://www.oreilly.com/library/view/building-evolutionary-architectures/9781492097532/ch02.html> | Search result |
| EV-15 | InfoQ, *Fitness Functions for Your Architecture* | <https://www.infoq.com/articles/fitness-functions-architecture> | Search result |
| EV-16 | ArchUnit | <https://www.archunit.org/> | Search result |
| EV-16 | Import Linter, *Contract types* | <https://import-linter.readthedocs.io/en/stable/contract_types/> | Prior report |
| EV-16 | Ruff, *import-private-name* | <https://docs.astral.sh/ruff/rules/import-private-name/> | Prior report |

### 19.2 Internal sources

- [`BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md`](BYNAT_INTERNAL_ARCHITECTURE_DESIGN.md) — baseline, decisions, dependency matrix, module contracts, enforcement rules.
- [`docs/temb/bynat_internal_architecture_evolution_plan.md`](../temb/bynat_internal_architecture_evolution_plan.md)
- [`docs/temb/bynat_architecture_refactoring_plan.md`](../temb/bynat_architecture_refactoring_plan.md)
- [`docs/ARCHITECTURE_RESEARCH.md`](../ARCHITECTURE_RESEARCH.md)
- [`docs/ROADMAP.md`](../ROADMAP.md) — `DQ-02`, `DEPR-02`, `PERF-05`, `PERF-06`, `IO-01`, `COMPAT-01`.
- [`docs/TESTING_STANDARDS.md`](../TESTING_STANDARDS.md) — `BYNAT-ARCH-1`–`BYNAT-ARCH-12`, `BYNAT-API-2`.
- [`pyproject.toml`](../../pyproject.toml)
- [`bynat/`](../../bynat/) source tree at the baseline commit.

---

## 20. Final traceability matrix

| Decision / phase | Principle | Trigger | External evidence | Internal evidence |
|---|---|---|---|---|
| Retain current tree now | P-1, P-9 | No trigger | EV-4, EV-13, EV-14 | Design §1, §3.3 F-5 |
| Trigger-based evolution | P-1, P-2 | — | EV-8, EV-9, EV-10 | Design §3.2 |
| Near-term normalization | P-3, P-7 | Immediate | EV-2, EV-3 | Design §6.I, §12 |
| Stage B (capability subpackages) | P-2, P-6, P-9 | §5.2 | EV-5, EV-6, EV-8, EV-11 | Design §6.A, §7 |
| Stage C (domain-internal layers) | P-5 | §5.2 | EV-5 | Design §5 |
| Stage D (new domain) | P-6 | §5.2 | EV-6, EV-7 | Design §6.A, §7 |
| Stage E rejected | P-10 | — | EV-5, EV-7 | Design §5, §21 |
| Module split/merge rules | P-1, P-2 | §6.2 | EV-8, EV-10 | Design §3.2 |
| Shared-helper extraction | P-4, P-6 | §6.2 | EV-11, EV-12 | Design §6.C, §18 |
| Public API frozen | P-3 | — | EV-2, EV-3 | Design §2.4, §23 |
| Fitness functions | P-7 | — | EV-15, EV-16 | Design §22 |
| Scenario 1 (cleaning) | P-2, P-6 | §7.1 | EV-8, EV-11, EV-13 | Design §3.2, §7.1 |
| Scenario 2 (analytics) | P-2 | §7.2 | EV-8 | Design §7.3 |
| Scenario 3 (cache backend) | P-6 | §7.3 | EV-5, EV-6 | Design §7.2 |
| Scenario 4 (integrations) | P-4, P-6 | §7.4 | EV-11, EV-12 | Design §7.1, §19 |
| Scenario 5 (new domain) | P-6 | §7.5 | EV-6, EV-7 | Roadmap `DQ-02` |
| Scenario 6 (shared expansion) | P-4, P-6 | §7.6 | EV-11, EV-12 | Design §6.C, §18 |
| Phase 0 | P-7 | Immediate | EV-15 | This document |
| Phase 1 | P-3, P-7 | Immediate | EV-2, EV-3 | Design §24 |
| Phase 2 | P-7 | Demonstrated CI need (optional) | EV-16 | Design §22.2 |
| Evolution phases E1–E6 | P-1, P-8 | Scenario triggers | EV-8, EV-9, EV-10 | §7, §14.4 |
| Path-collision resolution | P-3, P-6 | This correction | EV-13, EV-14 | §10.7, §13.4; repo import scan |
| Stage/Module/Phase reconciliation | P-1, P-2 | This correction | EV-8, EV-9 | §5, §6, §14 |
| Operational trigger procedure | P-1, P-7 | This correction | EV-8, EV-9, EV-10 | §15.4 |

### 20.1 Acceptance self-review

| Criterion | Coverage |
|---|---|
| Existing architecture assessment uses previous findings | §2 |
| External research conducted and cited, with limitations | §3 |
| Evolution principles stated | §4 |
| Package evolution model with stages and triggers | §5 |
| Module/component evolution model | §6 |
| Six growth scenarios stress-tested | §7 |
| Explicit structural decision framework | §8 |
| Near-term target architecture | §9 |
| Growth-ready examples with real filenames | §10 |
| Current vs proposed tree comparison | §11 |
| Cross-package dependency model | §12 |
| Public API and compatibility strategy | §13 |
| Phased roadmap, immediate vs conditional | §14 |
| Phase acceptance criteria and checkpoints | §15 |
| Enforcement strategy | §16 |
| Deferred decisions with revisit triggers | §17 |
| Risks, trade-offs, rejected alternatives | §18 |
| Evidence and source references | §19 |
| Traceability matrix | §20 |
| Path collisions resolved and trees filesystem-valid | §10.7, §11, §13.4 |
| Stage/Module/Phase model consistent | §5, §6, §14 |
| Public API/import-path compatibility policy unambiguous | §13 |
| Growth triggers operational | §15.4 |
| No implementation performed | This file is the only write |
| No material question left unanswered | §17 lists deferrals with triggers |

### 20.2 Final statement

The near-term architecture is the current tree plus internal normalization and enforcement. The long-term architecture is a modular monolith that deepens its domain packages only when change reasons, cohesion, and dependency direction demand it. Every transition is conditional, reversible, and public-API-preserving. The strategy is complete and implementable without redesign.

### 20.3 Change summary (this correction audit)

| Correction | Location | Change |
|---|---|---|
| Filesystem path collisions | §10.7, §11, §13.4 | Growth trees now replace `columns.py`/`text.py`/`stats.py`/`io.py`/`providers.py` with same-named packages; no tree lists both; conversion constraints recorded |
| Naming consistency | §7.1, §10.1, §11 | `statistics/` renamed to `stats/` so `from bynat.cleaning import stats` keeps working |
| Malformed current tree | §2.4 | Removed the stray comment line and duplicate entries |
| Stage/Module classification | §5, §6, §7.2, §7.3, §7.4, §7.6, §10.2, §12.3, §14.4 | Scenario 2 reclassified as M1; Scenario 3 as Stage B + relocation; Scenario 4 as Stage B via M2; Scenario 6 as M4; Stage C procedure and illustrative example added |
| Roadmap phases | §1.1, §14, §15.2 | Phase 2 marked optional; C1–C6 renamed E1–E6; each phase mapped to scenario and transition |
| Compatibility policy | §13 | Four import-path categories, classification procedure, C-1–C-10, and a compatibility inventory added; `__all__`-only fallacy stated |
| Operational triggers | §15.4 | Repeatable review procedure and rejection evidence added; thresholds demoted to sanity checks |
| Research note | §3.4 | States that no additional external research was required |

### 20.4 Final consistency audit

- **Filesystem validity.** Every proposed tree was checked for module/package name clashes. The only clashes were the four named conversions; each is resolved by replacing the module with a same-named package. No tree contains both `foo.py` and `foo/`.
- **Stage/Module/Phase consistency.** M1/M2/M3/M4 are module-level; Stages A–E are package-level. Scenario classifications match their proposed structures. E1–E6 are distinct from Stage C.
- **Roadmap consistency.** Phase 0 and Phase 1 are immediate; Phase 2 is optional; E1–E6 are conditional and trigger-gated. No optional phase is described as immediate.
- **Compatibility consistency.** The four categories, the classification procedure, and the inventory agree with the repository's pinned contracts (`test_root_api.py`, `test_accessor_package_boundary.py`, `test_doc_drift.py`, `test_internal_shared_helpers.py`, `tools/sync_docs.py`).
- **Tree/dependency consistency.** Each growth tree's new subpackages inherit the parent's dependency budget; no new cross-package private import is introduced; `_internal` remains stdlib + NumPy.
- **No speculative structure.** No new abstraction, protocol, manager, registry, or engine is introduced; no stage is scheduled without a trigger.
- **Two categories.** Phase 0–2 are near-term preparation and enforcement; E1–E6 are future structural evolution. No phase is presented as authorized implementation, and no E-phase is scheduled.
- **No implementation.** Only this document was modified.

### 20.5 Focused correction report (this pass)

| Point | Sections changed | Correction |
|---|---|---|
| 1. `__module__` preservation | §7.1, §10.7, §13.4, §13.6 | Added the technical strategy: `__module__` follows the defining module; Option A (define in `io/__init__.py`) recommended; Option B (explicit `__module__` plus a `tools/sync_docs.py` change) viable only with approval; Option C (weaken the contract) rejected; concrete tests defined |
| 2. Cache backend protocol acceptance | §7.3, §10.3, §14.4 | Acceptance now names the protocol consumer (`CacheManager`), requires two concrete implementations satisfying one contract, preserves the `CacheManager` contract, and forbids a speculative framework |
| 3. Responsibility-driven triggers | §1.2, §5.2, §7.1, §8.1, §8.4, §14.4, §15.4 | Added R-11/R-12 and a decision rule; counts are sanity checks, not triggers; splits that only move files are rejected |
| 4. Separate preparation from evolution | §1.1, §1.2, §14, §14.4, §20.4 | Phase 0–2 labelled near-term preparation; E1–E6 labelled future structural evolution; E-phases are conditional, independent, unordered, and may never occur |

**Selected `__module__` approach.** Option A: define the public `io` functions in `io/__init__.py`; submodules hold private helpers and new formats. Trade-off: `io/__init__.py` is not a thin re-export. Option B (explicit `__module__` assignment plus a `tools/sync_docs.py` update) is viable but not behavior-neutral and requires explicit approval; Option C (accept `bynat.cleaning.io.readers`) is rejected because it weakens the pinned contract.

**Unresolved issue requiring a decision.** None for the near term. If E1 is implemented with a thin `io/__init__.py` (Option B), the explicit `__module__` assignment and the `tools/sync_docs.py` change require approval; the strategy records this rather than assuming the move is behavior-neutral.

### 20.6 Final verification (this pass)

- The four corrections are reflected in every relevant section and cross-reference.
- No valid architectural decision was changed; the current architecture, growth targets, stages, and compatibility rules are unchanged.
- No phase is presented as authorized implementation; Phase 0–2 remain preparation/enforcement and E1–E6 remain conditional.
- The document still distinguishes current architecture, near-term normalized architecture, conditional growth-ready structures, module-level transitions, and package-level stages.
- All proposed trees remain filesystem-valid with no module/package name collisions.
- The compatibility policy (§13) and the `io` implementation details (§13.6) do not contradict one another.
- No source code, tests, or configuration were modified; no implementation was performed or authorized.
