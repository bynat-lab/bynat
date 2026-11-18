---
name: bynat-documentation-conventions
description: Use when editing bynat. Preserve repository conventions.
version: 0.1.0
author: bynat
license: MIT
platforms: [linux, macos, windows]
---

# bynat Documentation and Maintenance Conventions

Use this skill when working in the `bynat` repository. Treat repository files as authoritative and preserve the existing organization, terminology, public behavior, and documentation roles. This skill records conventions; it does not authorize changes by itself.

## When to Use

- Editing `docs/ROADMAP.md`, `CHANGELOG.md`, or `README.md`.
- Changing public Python behavior in `bynat/`.
- Adding or updating tests for `BaseData`, `CacheManager`, or optional integrations.
- Reviewing whether implementation, tests, roadmap, changelog, and README remain consistent.
- Auditing, correcting, completing, or standardizing docstrings in `bynat/`.
- Refreshing the tracked `graphify-out/` repository graph after code changes (see `references/graphify-refresh.md`).

Do not use this skill as permission to modify files when the user requests read-only inspection.

## Repository Documentation Roles

### `docs/ROADMAP.md`

Use for repository-backed planning, architectural principles, milestones, decisions, dependencies, quality gates, and historical corrections.

Preserve its structure:

1. `# bynat Roadmap`
2. Introductory code-grounding statement.
3. `## 1. Project context`
4. `## 2. Principles`
5. `## 3. Current state (version)` with `### Done` and a version/item/location table.
6. `## 4. Backlog` with milestones and `### Later or optional`.
7. `## 5. Decisions`.
8. `## 6. Definition of done`.
9. `## 7. Corrections to the previous roadmap draft`.

New backlog work uses stable fourth-level task headings such as `#### `CACHE-01`: ...` and labels such as `Problem`, `Plan`, `Done when`, and `Not doing`. Name real methods, files, and tests. State dependencies, priorities, effort, exclusions, and unresolved decisions explicitly. Do not describe planned work as implemented.

### `CHANGELOG.md`

Use only for implemented, user-visible release behavior.

Preserve its structure:

1. `# Changelog`.
2. Descending `## <version>` headings.
3. Optional release introduction.
4. Existing categories: `### Breaking changes`, `### Added`, `### Fixed`, and `### Changed`.

Write concise bullets. Put compatibility-impacting behavior under `Breaking changes`. Describe actual caller-visible behavior, not plans, internal investigations, or unresolved design choices. Preserve historical entries and version order.

### `README.md`

Use for current user-facing package documentation.

Preserve its section order:

1. `# bynat`
2. `## Status`
3. `## Installation` and `### Requirements`
4. `## Public API`
5. `## Caching` with CacheManager examples and method table.
6. `## Cleaning` with practical examples, constructors, and BaseData method table.
7. `## Limitations and operational notes`.
8. `## Development and verification`.
9. `## License`.

Use concise explanatory prose, fenced `bash` and `python` examples, Markdown tables, and inline code for APIs and parameters. Document actual defaults, return values, exceptions, optional dependencies, and operational limitations. Do not put roadmap task IDs, open decisions, audit logs, or speculative features in the README.

## Python and Test Conventions

- The established package-level imports are `bynat.caching` and `bynat.cleaning`'s documented class APIs. The top-level `bynat/__init__.py` deliberately re-exports exactly five names (`BynatAccessor`, `ProfileReport`, `profile`, `read_csv`, `read_json`) and registers the `df.bynat` accessor; do not broaden `__all__` further to expose other submodule functions, accessors, or report classes. Use explicit paths such as `bynat.cleaning.profile`, `bynat.cleaning.accessor`, and `bynat.cleaning.io` for those APIs.
- Preserve `BaseData` as a `pandas.DataFrame` subclass and preserve `_constructor`/`_metadata` behavior.
- Preserve the established `inplace=False` new-object and `inplace=True` mutation/`None` convention unless an explicit compatibility decision changes it.
- Give the Accessor's `inplace` flag the SAME parameter kind and positional index as the corresponding `BaseData` method; never impose keyword-only as a blanket rule. `BaseData` accepts `inplace` positionally for most methods (`frame.truncate_after_substring(False, True, title="-")` is a supported, tested call), so a keyword-only Accessor flag silently changes the calling convention and breaks Class/Accessor parity. Derive the insertion index from the shared function's parameters (see `references/accessor-inplace.md`); only methods whose shared function takes variadic positional arguments have a genuine keyword-only `inplace`. A positional `inplace` placed ahead of another parameter captures positional arguments meant for that parameter and can silently return `None`; extracting it by truncation (`args = args[:index]`) instead of removal (`args = args[:index] + args[index + 1 :]`) silently drops the arguments that follow it, so surplus positionals are ignored where the Class API raises `TypeError`; conversely, variadic methods with `**kwargs` or dynamic column mappings (`**target_cols_and_*`) absorb `inplace` as a target column or transform option unless it is extracted before the shared call. Compare `inspect.signature` of the class method, the shared function, and the accessor — parameter kind AND positional index — before changing a public signature.
- For in-place DataFrame mutation in the Accessor, mutate `self._obj` via `self._obj._update_inplace(result)`; this updates the block manager in place, preserving object identity (`id(df)`), caller references, index, and shape identically to `BaseData`. `accessor.py` is inside the mypy scope and pandas-stubs does not declare `_update_inplace`, so mypy resolves it through `DataFrame.__getattr__` as `Series[Any]` and reports `[operator]`; put `# type: ignore[operator]` on that call. `warn_unused_ignores = true`, so suppress nothing else, and note `base.py` needs no ignore because it is excluded from mypy.
- The Accessor exposes an `inplace` flag on the same transformations `BaseData` supports, declared at the same parameter position as that method. Compute the shared-function result first, then mutate and return `None`; `handle_outliers`, `drop_outliers`, `fill_missing`, and `fill_missing_from` return the hierarchical statistics instead of `None` when `get_hierarchical_stats=True`. `bynat/cleaning/accessor.pyi` is generated by `tools/sync_docs.py`, so a runtime-only wrapper keyword must also be taught to `_stub_function`, and `tests/cross_cutting/contracts/test_doc_drift.py` pins both the stub and exact accessor parameter-key lists. See `references/accessor-inplace.md`.
- Use the repository's local check environment `.venv-check/` (the interpreter `tools/verify_installed_wheel.py` expects) for verification; bare system interpreters may lack the dev/test dependencies. It does not carry the optional integration extras (`langdetect`, `deep_translator`, `geopy`, `pycountry`, `babel`, `yfinance`, `spacy`). Reuse the existing fakes in `tests/modules/enrichment/helpers.py` (`install_langdetect`, `install_currency_lookup`, `install_spacy`, `DictTranslator`, `RateSource`, `Geocoder`) instead of hand-rolling `sys.modules` stubs. When probing cached enrichment or NLP methods, set `BYNAT_CACHE_DIR` to a scratch directory outside the repository: the default `Settings/Cache Data/Automated/cache.sqlite3` persists across runs and a cache hit returns before the code path under test, so a probe can appear to pass without ever reaching it.
- Use module loggers through `logging.getLogger(__name__)`.
- Use `_import_optional` for optional integrations and raise a clear feature-specific `ImportError` when unavailable.
- Keep NumPy and pandas as core dependencies; keep integrations optional and lazy.
- Do not add row-wise `DataFrame.apply(..., axis=1)`, `iterrows`, or `itertuples` to data paths.
- Loops over unique values are acceptable for external calls and Python-object processing.
- Invalid caller arguments raise; missing columns generally log a warning and are skipped.
- Per-item external failures are logged and skipped, not cached.
- Match the existing code's spacing style, including spaces around keyword assignment in calls.
- Tests use pytest functions, `tmp_path`, `monkeypatch`, exact assertions, and fake modules for network-backed integrations.
- When one parametrized test mixes core cases with cases that need an optional extra, mark the individual `pytest.param(..., marks=pytest.mark.extras)` and gate that case in the body with a conditional `pytest.importorskip`. Never mark the whole function (it needlessly gates the core cases) and never leave it unmarked (the optional case raises `ImportError` in the default run). Confirm the `-m extras` job installs the extra and the default job does not. See `references/test-suite-quality.md`.
- Organize the test tree by FUNCTIONAL RELATIONSHIP between the tests, never as a mirror of the production source layout; a production package or module boundary is not by itself a reason to create a test directory. Create a nested directory only when two or more files cover different aspects of the SAME narrower responsibility, and name it for that responsibility. Never let `test_<area>_a.py`, `test_<area>_b.py`, … accumulate at the parent level. A responsibility spanning several areas belongs in `tests/cross_cutting/<topic>/`. Resolve ambiguity toward the parent level unless a concrete narrower responsibility can be named. See `references/test-suite-quality.md`.
- Test files target a 200-line maximum (`BYNAT-ARCH-4`) and are split along functional boundaries, never by line count alone. Exceeding 200 lines requires a documented justification naming the single responsibility that cannot be split without breaking ownership or fixture reuse; record pre-existing violators as the tracked adoption backlog (`BYNAT-ARCH-4a`) rather than sanctioned exceptions.
- For a public-signature fix, add the regression test first and confirm it fails against the old signature (RED), then apply the smallest fix and confirm GREEN; run the focused suite before the full suite.
- Keep tests offline and avoid secrets, user files, network access, and external services.

## Docstring Conventions and Audit

Use when the task is to audit, correct, complete, or standardize docstrings across `bynat/`.

### Always-on rules

- The shared functions in `columns`, `text`, `stats`, `profile`, `io`, and `enrich` are the single source of truth for docstrings. `BaseData`'s literal docstrings and `bynat/cleaning/accessor.pyi` are generated from them. Edit the shared function, then run `python tools/sync_docs.py`; never hand-edit the generated literals or the stub.
- Keep one section order: summary paragraph, `Notes:`, `Args:`, `Returns:`, `Raises:`, `Example:`/`Examples:`, `Attributes:`. `Examples:` (plural) marks a docstring carrying two or more example blocks; do not normalize it to `Example:`.
- Document only parameters that exist, with their real defaults, and only exceptions the implementation actually raises or deliberately propagates. Probe the behavior; never restate an existing docstring as fact.
- `tools/sync_docs.py` cannot render a docstring containing `"""` or ending in a backslash, so keep examples free of triple quotes.
- `tools/sync_docs.py --check` exits 1 on drift and therefore aborts an `&&` chain. Run the write form first, then `--check` as its own command, then the suite.
- A shared docstring is attached to three surfaces at once: the standalone module function, the `BaseData` method, and the `df.bynat` accessor method. Only the standalone function has no `inplace` parameter, so a mutation or return claim must be true for that function too, or be explicitly scoped to it — for example, write "The standalone function never modifies ``df``." Any `inplace`-bearing wrapper additionally needs both modes and their exact return values stated. Keep the documented contract identical to the code path that produces it; see `references/docstring-audit.md` for the wording.
- An audit scoped to docstrings leaves `README.md`, `docs/ROADMAP.md`, and `CHANGELOG.md` untouched. Report a docstring-versus-README contradiction as a finding with `file:line` instead of silently editing out of scope.

### Verify the change is documentation-only

Run the skill's `scripts/verify_docs_only.py` from the repository root. It parses `HEAD` and the working tree, strips docstrings and attribute docstrings, and compares `ast.dump`; any file it reports as changed has a non-docstring edit.

Load `references/docstring-audit.md` for the ordered procedure, the per-API probe checklist, and the verification command list.

## Procedure for Future Changes

1. Read the target implementation, nearby tests, and relevant documentation before editing.
2. Identify the closest existing example and match its structure, wording, and formatting.
3. Verify the public boundary before changing exports: inspect `__init__.py`, `__all__`, defining modules, README import examples, and changelog statements. Test the exact documented import forms in a fresh interpreter. If a documented path fails, correct the documentation or the explicitly intended export; do not add broad package-level re-exports merely to make a stale example pass, because importing a submodule can bind a module object on the package without making it the intended callable API.
4. For public-API documentation alignment, audit `docs/ROADMAP.md` and `README.md` as separate scopes, preferably with independent narrow reviews. Search for contradictory active plans before editing, then distinguish historical release text from current guidance. For the class-based cleaning API, state that `BaseData`, `JsonFile`, `CsvFile`, and `bynat/cleaning/base.py` remain supported, describe `df.bynat` as optional/complementary, and document `inplace=True` as mutation plus `None` where supported. Do not carry deprecation/removal language from an earlier design into current roadmap or README guidance; keep unrelated aliases such as misspelled-parameter deprecations separate.
4. Define the smallest file scope required by the request. For multi-subtask behavior changes—especially storage, concurrency, or public-cache changes—split the work into one small ordered implementation step per dispatch: inspect the exact seam, delegate only that step, inspect the actual diff, run its focused tests, then start the next step. Never dispatch an entire phase as one unreviewed change. If a provider stalls or fails, preserve verified work and retry only the current bounded step; after repeated failure, implement that same bounded step directly rather than restarting the phase.
5. For repository-wide typing, hover, or autocomplete work, record a reproducible external baseline before implementation: use a scratch environment outside the repository, probe both mypy and Pyright when available, and capture exact `reveal_type` output for the named public APIs, accessor paths, and compatibility imports. Treat missing tooling as setup work to resolve, not as evidence about the code, and use a platform-correct scratch path before interpreting failures.
6. When the request requires subagents, keep implementation ownership bounded by non-overlapping files, inspect each actual diff, and require concrete reports naming symbols, commands, test results, assumptions, and unresolved concerns. Do not accept a generic "typing fixed" or "tests pass" report. Delegation is for implementation only: never delegate repository inspection, test execution, or evidence collection for an audit or verification task — the report's authority is that the auditor ran the commands. When the user states that a task must be executed personally, do the whole task yourself and do not spawn any subagent.
5. Build a coverage matrix before adding tests: map each acceptance criterion to exact existing test names, distinguish sequential simulations from genuine multiprocessing, and add only the smallest missing scenario. This prevents duplicating passing coverage while leaving a hidden conflict case untested.
5. For SQLite cache concurrency, distinguish sequential stale-manager simulations from genuine multiprocessing evidence. Use separate spawned processes, independent `CacheManager` instances, a shared baseline established before the workers start, explicit event/queue synchronization, bounded joins, worker result/error reporting, and cleanup when the acceptance criterion requires cross-process coverage. Never use sleeps or scheduler timing to establish commit order; a sequential two-manager test proves baseline identity scoping, but it does not prove process-level writer behavior.
6. For cache save/delete claims, test the failure path separately from the success path: assert rollback, unchanged baseline identity/content, retained in-memory pending changes, and a successful retry. Test disjoint-key merge and same-key last-committed-writer-wins independently so a passing aggregate test cannot hide a missing conflict case.
7. Preserve unrelated headings, tables, task IDs, version history, examples, and decisions.
8. When finishing a CACHE-01 documentation phase, audit claims against code and focused tests first, then update README, update the Roadmap documentation checkboxes, update the existing release's CHANGELOG section, and only afterward run final verification and complete the final-review checklist. Inspect current-state Roadmap prose as well as checklist boxes: stale file sizes, backend descriptions, or test counts are documentation defects even when implementation is correct. Keep the parent milestone open until every acceptance criterion and required checklist phase is verified; when closing it, mark final-review items first, add one Done-table entry, remove the completed active backlog block, and verify the milestone is not duplicated.
9. Distinguish migration recovery states in user-facing documentation: malformed or non-object JSON is quarantined, while valid JSON with unsupported nested bucket shapes remains in place and unmarked for recovery. Do not collapse those behaviors into one generic "preserved" claim.
10. When delegating a bynat task, replace concrete placeholder tokens such as angle-bracket path or identifier examples with literal wording before dispatch; the delegation interface treats angle-bracket markers as unresolved templates.
11. If behavior changes, update tests first or alongside the implementation and determine whether README, changelog, and roadmap updates are actually required.
12. If behavior is user-visible, record it in the appropriate changelog category, update the current release overview to summarize the release's complete Added, Fixed, and Changed content, and keep README behavior accurate.
13. If work is planned rather than implemented, record it only in the roadmap with concrete dependencies and completion criteria.
14. Verify every documentation claim against current code and tests. Treat a roadmap checkbox as a completion gate: mark it only after the scoped code and focused tests have been inspected and passed. Do not mark a concurrency claim from a sequential test when the acceptance criterion calls for multiprocessing; record that gap explicitly and leave later test-phase checkboxes unchanged. For final closure, map each original acceptance criterion to named implementation and test evidence rather than relying on aggregate counts; distinguish tested failure simulation from untested hard-kill durability, and report non-blocking limitations without overstating guarantees.
15. For testing-policy or engineering-standard documents, separate verified current state from proposed target state in the wording and headings. Define the scope of each generic invariant before applying it: frame-to-frame transformations, reports, loaders, writers, and cache operations have different return/index/mutation contracts, and a rule written for one must not silently cover the others. Re-check every normative example against the implementation and documented public contract, including no-op behavior, warning semantics, optional-dependency caching, DataFrame edge cases, subclass preservation, public signatures, variadic `**kwargs` behavior, argument validation, and CI selectors; a comprehensive policy is defective if its required example cannot pass against the documented contract. Probe both forms of reflective APIs where relevant: `inspect.signature(Class.method)` is unbound and includes `self`, while `inspect.signature(instance.method)` is bound and removes it. Inspect every `**kwargs` seam explicitly because obsolete or internal keywords may be swallowed instead of rejected. Describe provider-specific caching behavior separately when `None`, falsy values, exceptions, or misses have different semantics. Distinguish pytest marker selection from the tool it supports: document an execution path for every excluded marker, and give mutation engines their own complete invocation with required config/session arguments, schedule, gate status, and survivor-triage policy. If the target standard intentionally exceeds current implementation behavior, label the gap and put its resolution in the adoption roadmap instead of presenting the target as verified current behavior. Label future files, profiles, markers, coverage configuration, and gates as targets until they exist, and run a second focused review after correcting implementation-specific findings.
16. For test-suite architecture decisions, identify the constitution's genuinely mandatory structural rules before comparing models; do not infer a prohibition on nested directories or a required flat layout from marker guidance, examples, or a prior target proposal. Evaluate genuine flat, module-, test-type-, layered-, feature/domain-, and hybrid models against the same long-term criteria (ownership, cohesion, separation of concerns, coupling, discoverability, scalability, change locality, shared infrastructure, independence, tooling, maintenance cost, consistency, and constitution compliance); reject a model that only wins on migration convenience or circular compliance with its own proposed tree. Put the full architecture analysis, target tree, mapping, size budgets, and phased migration plan directly in `docs/TESTING_STANDARDS.md` when that is the requested authority; do not create a separate report or appendix. Distinguish verified current layout from future target layout in headings and normative wording; a target tree is not evidence that migration occurred. If the user later changes the architecture or scope, discard the superseded target and re-read the authoritative document before editing rather than combining incompatible designs. After implementation, re-check the exact wording for unsupported mandatory claims and numeric inconsistencies, then rerun scope, diff, collection, and focused documentation checks. When the target is hierarchical, keep directory ownership primary, keep test-type markers orthogonal, and place property tests beside the module or cross-cutting responsibility they verify rather than creating a marker-shaped directory by default. Treat pytest configuration, Hypothesis profiles, global autouse fixtures, and nested discovery settings as future targets unless the repository actually contains them.
17. Treat delegated reports as unverified until the supervisor checks the actual working tree and artifact: a report that claims completion after an interrupted or blocked tool call is not evidence. Confirm `git status`, changed paths, the relevant file contents, and the required validation output yourself; preserve the exact scope when the task is documentation-only. Recompute repository counts with a reproducible command instead of trusting a prior document: distinguish test-module lines from `tests/*.py` totals, function definitions from collected cases, and current measurements from projected post-split counts.
17. Apply the test-file size rule to every proposed target file, including files that are already oversized. Do not preserve an oversized file as a "coherent" exception or label the split a future maintenance item while claiming the target is compliant. Derive explicit target budgets from the current test responsibilities, split both current violators, and verify the largest target remains below the constitutional limit.
18. Build a complete current-to-target mapping before approving an architecture: include every test module, test-level responsibility for split files, `conftest.py`, helpers, fixtures, test data, tools, benchmarks, CI, and configuration coupling. Verify structural constraints from actual imports, path resolution, pytest collection, and hardcoded tool paths; distinguish genuine architectural requirements from temporary migration dependencies. Do not centralize a helper merely because two files use it: require distinct-domain reuse and a maintainability benefit, otherwise keep it local or module-scoped. Keep every support item on one destination throughout the target tree, mapping tables, routing details, and migration steps. For benchmarks importing test modules, prefer extracting reference implementations into benchmark support code over adding nested test directories to `sys.path`; document that extraction as a future migration dependency when implementation is out of scope.
19. Before finalizing a documentation-only architecture change, verify the exact repository counts and scope from the checkout, re-read the complete architecture section after editing, search the whole document for superseded paths and contradictory destinations, run `git diff --check`, confirm only the explicitly permitted documentation paths changed, remove any unrequested artifact, and run collection plus the narrowest relevant documentation/contract test. Verify both present and absent named files when the mapping depends on them; do not infer that a similarly named helper/test exists. Do not trust a subagent's reported count or status without re-checking it; stale line counts and omitted artifact cleanup are documentation defects.

20. Run the repository's established checks when implementation changes are authorized: pytest, compileall, Ruff, and relevant extras tests.
20. Report modified files, verification results, and remaining inconsistencies without claiming work that was not performed.
21. For release preparation, audit the authoritative version source before editing: in this repository it is `pyproject.toml`; update only demonstrably stale README and Roadmap current-state references, preserve historical version rows, and do not hand-edit generated `dist/` or `*.egg-info` artifacts. Confirm the existing changelog covers completed user-visible work without claiming backlog items, then validate the parsed metadata and built artifact before accepting the version step.

## Uncommitted-Work Audit and Recovery

Use when asked to audit everything in the working tree, recover tasks that were interrupted or redirected, or decide whether the accumulated uncommitted changes are acceptable. Load `references/work-completion-audit.md` for the recipe: reconstruct the task history first, inventory the tree against the last commit, map each requirement to a named test, re-read the normative documents for wording a mid-edit correction left stale, probe behavior independently instead of trusting the suite, repair only confirmed defects, and report an explicit acceptance decision with limitations named rather than folded into "complete".

## Test-Suite Quality Improvement Workflow

Use this workflow for test-suite quality, deduplication, coverage, discovery, CI, or performance work after architecture migration. Load `references/test-suite-quality.md` for the reusable audit matrix and command recipes.

1. Establish a read-only baseline before editing: read the complete testing standard, pytest configuration, CI workflows, production package, current test tree, tools, benchmarks, and the prior architecture-review report. Record files, line counts, collected cases, definitions, parametrization, skips, xfails, markers, full-suite results, lint, wheel verification, benchmark behavior, and current CI commands.
2. Run the baseline audit yourself before implementation; do not delegate it. Then delegate one bounded non-overlapping improvement batch at a time. Keep the supervising agent responsible for diff review, integration, and acceptance; never treat a subagent report as evidence until the working tree and commands are independently checked.
3. For each test file above the investigation threshold, classify responsibilities before splitting. Split only at meaningful ownership boundaries; retain cohesive files when a split would create trivial fragments. Apply the 200-line ceiling (`BYNAT-ARCH-4`) to every resulting file, and do not create a cross-module file that exists only because several modules share one feature.
4. Audit duplication across helpers, fixtures, data builders, assertions, patch setup, and expensive preparation. Extract only genuinely reusable infrastructure into the owning module/topic or `tests/shared/` when distinct-domain reuse is proven. Never reuse one test module from another as a helper and never delete independent public-entry-point coverage merely because assertions look alike.
5. Build a production-to-test coverage matrix and a before/after inventory. Explain every missing, added, skipped, xfailed, deselected, or split case; a green aggregate suite does not prove discovery integrity. Maintain the matrix in `docs/TEST_COVERAGE_MATRIX.md`; validate it read-only by checking every cited `tests/...::...` node against `pytest --collect-only`, every §5/§6 requirement ID against `docs/TESTING_STANDARDS.md`, and every cited production path against the tree.
6. Verify CI commands and marker semantics against the actual tree. Preserve all seven constitutional markers, including `network`, even when a marker currently selects zero tests; do not add live-network tests or silently change CI filters.
7. After each batch, inspect actual scope, run focused tests, collection, Ruff, and relevant line-size checks. After integration, run the full suite, marker selections, optional/extras workflows, documentation drift, compileall, wheel verification, benchmarks, and an independent final review. Measure performance changes under consistent conditions and do not optimize by weakening isolation or coverage. When adding contract tests, treat the resulting increases in collected cases, definitions, and assertions as intentional inventory changes and update every current-count reference before accepting the batch.

Do not classify quality work as complete from an audit report alone. The acceptance gate is repository evidence: focused and full execution, reconciled inventories, correct CI/tool paths, and an independent review with no unresolved valid findings.

When an established findings list is supplied, fix it directly. Do not restart the audit, re-derive the findings, or write another planning report; re-validate each finding against the current code and repair it.

## Test-Suite Architecture Migration Workflow

For the ordered migration procedure and verification gates, load `references/test-suite-migration.md`. Keep the always-on rules below; use the reference for implementation batches and path/tooling reconciliation.

Use this sequence when implementing a documented bynat test-suite architecture:

1. Read the complete authoritative testing standard, then inventory every current test module, test function, helper, fixture, constant, marker, skip, xfail, support-tool import, benchmark dependency, hardcoded path, and pytest configuration before moving anything. Record source-to-destination ownership for split files, not only a directory tree.
2. Correct only confirmed documentation defects that directly affect migration semantics before using the plan. Validate path calculations from the actual target file location; for `tests/cross_cutting/contracts/test_doc_drift.py`, `Path(__file__).resolve().parents[3]` is the repository root, while `parents[2]` is `tests/`.
3. Migrate one bounded plan step at a time through the configured subagent workflow. Keep each dispatch limited to non-overlapping files, inspect the actual diff and target contents, run focused tests, collection, Ruff, and the applicable line-size check, then accept the batch before starting the next.
4. Preserve test behavior structurally: move or extract existing bodies with minimal import/path edits, keep multiprocessing workers module-level, preserve fixture scope, marker assignments including `network`, strict xfails, conditional skips, parametrization, and test names, and compare pre/post inventories rather than relying on a passing aggregate suite.
5. Keep `tests/conftest.py` as the suite-wide scope and preserve existing path setup. Do not create `tests/shared/` or promote helpers unless distinct architectural domains actually reuse them; same-domain reuse belongs in a module-local helper or `conftest.py`.
6. Reconcile migration-dependent tooling in the same bounded step when required by the documented plan: update hardcoded manifests and the code that resolves those manifest paths, keep `tools/sync_docs.py` integration intact, and extract benchmark reference implementations before removing benchmark imports from relocated test modules. When targets become nested, verify the consumer uses the full relative path rather than only `Path(relative).name`; a correct manifest with basename-only resolution silently points at the wrong checkout file. Do not add nested test paths as a permanent workaround.
7. Treat a failed, interrupted, or loop-cut subagent report as potentially partial filesystem work: inspect `git status`, changed paths, and target contents before retrying, then verify the actual tree instead of reverting or duplicating the claimed changes. This prevents a discarded report from causing a second extraction over files that already landed.
8. After all batches, run full collection, the complete supported suite, marker-specific selections, extras/optional checks, wheel verification, benchmark imports/execution, line-size validation, and an independent architectural review. Recompute counts and inspect `git status`/diff scope before reporting completion.

**Migration pitfalls:**

- Do not treat a report saying "implemented" as evidence; verify changed paths, file contents, counts, and command output because delegated workers can be stale or incomplete.
- Do not classify a test as cross-cutting merely because it imports or calls another module; ownership follows the primary contract being verified, otherwise module boundaries become meaningless.
- Do not preserve an oversized target file as an exception; split every actual resulting test file below the repository limit and verify the largest file directly.
- Do not leave a documented non-authorization clause unchanged after the user authorizes implementation if it still claims the migration is prohibited; reconcile only the directly affected architecture wording so the standard and repository state agree.
- Do not report projected counts as current facts; distinguish current collection from post-split projections and account for intentional test-definition/case changes explicitly.

## Conflict Handling

When an explicit user request conflicts with an existing convention, identify the conflict and follow the explicit request only when its intended compatibility impact is clear. Ask for clarification before consequential changes when the request is materially ambiguous. Do not override repository conventions merely because another style is more conventional elsewhere.

## Scope Preservation

For a narrowly scoped update, leave unrelated documentation sections, task IDs, milestone order, release history, public examples, import guidance, and implementation behavior untouched. Do not redesign the documentation system or introduce new categories, headings, abstractions, or mandatory dependencies without explicit authorization.

Do not run installers or package managers (`uv`, `npm`, `pip`, `npx`) inside the repository root: they create untracked `.venv`/`node_modules` and dirty the working tree. Install into a scratch directory outside the repository, and ask before installing any third-party CLI or package needed to unblock a task.

## Retention Limit

Load this skill whenever you work in the bynat repository. If your agent cannot load it, re-inspect the repository's authoritative files before editing and do not rely on memory alone.
