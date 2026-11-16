---
name: python-package-release
description: "Prepare Python packages for offline, verified release."
version: 0.1.0
author: bynat
license: MIT
platforms: [linux, macos, windows]
---

# Python Package Release Skill

Prepare a Python package for a documented, dependency-correct release without changing its implementation unless the user explicitly allows it. This skill covers source inspection, README accuracy, dependency configuration, offline packaging checks, and release-blocker reporting.

## When to Use

- Use when a user asks to prepare, audit, or verify a Python package for PyPI or another package index.
- Use when README/API documentation and `pyproject.toml` or `setup.py` must be aligned with the actual source.
- Do not use for publishing, release creation, or CI changes unless the user explicitly asks for those actions.

## Prerequisites

- Work from the actual repository root, not merely the session working directory.
- Read repository instructions and inspect `git status` before editing.
- Work offline when the request requires it; do not install packages or query indexes to resolve uncertainty.
- For substantive edits, implement through a subagent where your harness supports it, then independently inspect, test, and review the result.

## Procedure

1. **Locate and establish scope.** Confirm the repository root with `git status` and `git ls-files`. If the session directory is not the requested project, search nearby paths for the actual `pyproject.toml`, `README.md`, package directory, and `.git`. Record the target root before reading or editing. Completion criterion: the target is a git repository and the changed-file scope is explicit.

2. **Read the package completely enough to document behavior.** Read `README.md`, packaging metadata, ignore rules, package initializers, every source module, and available tests. Extract public classes, functions, constructors, signatures, defaults, return behavior, side effects, and exceptions from the implementation rather than names alone. Completion criterion: every README example and API entry can be traced to a real symbol.

3. **Audit imports and dependency boundaries.** Separate standard-library imports from third-party imports. Treat imports executed at module import time as mandatory, even when only one method uses the dependency. Inspect local `setup.py`, `*.egg-info`, sibling packages, and local metadata before mapping an import name to a distribution name. Declare a dependency only when its distribution identity is supported locally; otherwise record the uncertainty explicitly. Inspect dynamic database drivers, spaCy models, and network-backed services separately because they are runtime requirements for specific features, not necessarily package dependencies. See `references/dependency-audit.md`.

4. **Refactor optional integrations defensively.** If a dependency is moved from module scope to a method-local import, search the entire module for every symbol supplied by the removed import and bind each one locally. Preserve existing early returns before importing the optional package, because a new import can turn a documented no-op into an unexpected `ImportError`. Add tests for the feature's success path, missing-dependency path, and relevant early-return path; broad exception handlers can otherwise hide stale references and produce incorrect results.

5. **Determine the supported Python floor from syntax and imports.** Preserve an existing requirement unless the source proves it is too low; for example, `typing.Self` requires Python 3.11. Do not raise the floor based on installed-environment versions or guesswork.

5. **Write the README from verified behavior.** Treat `README.md` as production documentation for package users, not as an audit log. Keep it concise and release-ready: installation, Python requirement, declared dependencies, separate sections for each public subpackage, practical examples, API parameters, limitations, and license. Avoid internal verification notes, agent reports, temporary troubleshooting details, badges, marketing claims, unverifiable links, invented APIs, benchmark claims, and compatibility promises. Put maintainer-only findings and unresolved release checks in the final report instead of the README.

**Align every release-facing document with the target release before editing it.** When the work is the first change being prepared for a new release, create a new top version section in `CHANGELOG.md` using the existing structure and place new entries there; do not append them to the previous release section. Apply the same target-version discipline to completed entries in `docs/ROADMAP.md` and current API notes in `README.md`; never label new work with an older release merely because that section is already present. Preserve historical sections and unrelated roadmap rows unchanged. Read each saved document back and verify the exact new heading/entry text exists before reporting success. Treat the target release version and package metadata version as separate decisions: update `pyproject.toml` only when explicitly requested, and never claim a release occurred merely because a changelog section was prepared.

7. **Update metadata with minimal scope.** Preserve package name, version, build backend, discovery rules, valid metadata, and implementation files. Put mandatory runtime requirements under `[project].dependencies`; use optional dependencies only for features that can genuinely be absent while the package still imports and works. Keep development/test tools out of runtime dependencies. Ensure the discovery pattern includes every public subpackage.

8. **Run deterministic offline checks.** Use `terminal` for `python -m compileall`, the available test runner, TOML parsing, static API-name checks, and a focused smoke test for dependency-light functionality. Try `python -m build` only if the module is available. If it is unavailable but `uv` is available, use `uv build --offline` as a local alternative; never let the fallback contact an index. Use `python -m twine check dist/*` only when Twine is already available. Completion criterion: each attempted check has an actual exit result recorded. For optional extras, distinguish metadata/import verification, missing-dependency behavior, and successful feature execution; an import alone does not verify the feature.

9. **Inspect built artifacts.** Rebuild from the current source rather than trusting pre-existing `dist/` or ignored `*.egg-info/` output. Inspect wheel and sdist file lists and metadata to verify both public subpackages are included and `Requires-Dist` matches the intended dependency configuration. A successful build alone does not prove package contents are correct.

10. **Review scope and release blockers.** Run `git diff --check`, inspect `git diff --name-only` plus untracked files, and confirm only permitted files changed. For substantive implementation changes, obtain an independent review after implementation and rerun the affected tests after every correction. Separate user-provided evidence from checks you personally executed, especially when a user supplies a prepared virtual environment. If that environment lacks the test runner, run a focused assertion script there rather than claiming a pytest result. Report unavailable tools as unavailable, not as passed. Distinguish documentation/configuration improvements from blockers such as an unresolved external dependency, an absolute import that excludes bundled code, an unverified distribution-name mapping, or an untestable optional model/service.

11. **When the release task includes an implementation refactor, establish a behavior baseline before optimizing.** Record the focused and full test results, add regression tests for the requested new behavior and boundary inputs, and compare the refactored output against the prior algorithm on deterministic fixtures before declaring semantic preservation. For grouped data code, test duplicate grouping labels and target/group-column overlap explicitly; pandas often raises late during `reset_index()` or `melt()`, so normalize redundant grouping labels or reject conflicting roles before expensive aggregation.

12. **Smoke-test the exact built artifact outside the repository.** Select wheel and sdist paths matching the current version in `pyproject.toml` rather than taking the first `dist/*` match, because stale artifacts can coexist. Install the local wheel with `python -m pip install --no-deps --target <scratch> dist/<exact-wheel>` and run the import/usage probe from a scratch working directory so the source checkout cannot shadow the installed package.

## Verification Checklist

- [ ] Target repository and branch confirmed.
- [ ] README, metadata, package initializers, all source modules, and tests inspected.
- [ ] Public API entries and examples match real source symbols.
- [ ] Standard-library and third-party imports distinguished.
- [ ] Distribution names supported by local metadata or uncertainty reported.
- [ ] Mandatory runtime dependencies declared; optional and development dependencies separated.
- [ ] Python floor justified by source compatibility.
- [ ] Both public subpackages present in package discovery and built artifacts.
- [ ] Compilation, tests, smoke checks, build, and metadata checks reported with actual results.
- [ ] No network access, package installation, publishing, or CI changes occurred unless explicitly requested.
- [ ] Final scope and unresolved release blockers verified.

## Pitfalls

- **Do not trust the session working directory.** A nearby package can look plausible while being a different project; establish the git root and tracked files first.
- **Do not equate an import name with a distribution name.** Names such as `ahocorasick` may map to a different installable distribution; use local metadata or report uncertainty rather than guessing.
- **Do not omit a top-level local-package import from dependency analysis.** An absolute import such as `from Caching import CacheManager` is still a mandatory runtime dependency when the source executes it during module import.
- **Do not hide an implementation release blocker because the task forbids source changes.** Preserve scope, document the caveat, and state whether installation or subpackage import can fail.
- **Do not call a no-tests result a passing test run.** Report that no tests were collected and rely on separate smoke and packaging checks.
- **Do not trust stale generated metadata or artifacts.** Treat `pyproject.toml` and current source as authoritative, rebuild from them, and leave ignored `dist/`, `build/`, and `*.egg-info/` output out of the source-change assessment.
- **Do not claim a package is ready solely because a build completed.** Inspect wheel/sdist contents and metadata, then verify the exact changed-file scope.
- **Do not stop after adding lazy imports.** Search for every removed module-level symbol and test both a real successful path and the missing-dependency path; swallowed `NameError` exceptions can silently corrupt feature decisions.
- **Do not call an optional extra verified from installation alone.** Exercise at least one deterministic public feature in the environment where the extra is installed, because an import proves the distribution mapping but not the package's actual input/output behavior.
- **Do not put audit state in the production README.** Move offline verification gaps, agent findings, and temporary build-tool notes to the final report, because published documentation should describe user-facing behavior rather than the review process.

## References

- Dependency decisions and import-to-distribution audit: `references/dependency-audit.md`.
