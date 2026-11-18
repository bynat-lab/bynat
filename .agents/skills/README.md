# Shared Agent Skills

Reusable skills for working on `bynat`. They are stored in this repository so any
coding agent can use them without a shared local configuration, agent profile,
or credentials.

## How to use a skill

1. Scan the tables below and pick the skill whose description matches your task.
2. Read that skill's `SKILL.md` in full before you start.
3. Follow any supporting files it references (`references/`, `scripts/`,
   `templates/`, `agents/`) — they live beside it in the same directory.
4. Treat the repository itself as the source of truth. If a skill and the code
   disagree, follow the code and correct the documentation.

Skills are plain Markdown plus optional scripts. Nothing here depends on a
specific home directory, machine path, or secret. A few workflow skills contain
illustrative examples that name a particular agent's delegation tool; treat
those as patterns and substitute your own harness's equivalent.

## Project-specific skills

| Skill | Entry point | Purpose |
| --- | --- | --- |
| bynat-documentation-conventions | [SKILL.md](bynat-documentation-conventions/SKILL.md) | Repository conventions for `docs/ROADMAP.md`, `CHANGELOG.md`, and `README.md`; Python and test conventions; documentation change procedures; docstring audit; test-suite quality and architecture-migration workflows; graph refresh. |
| bynat-readme-writing | [SKILL.md](bynat-readme-writing/SKILL.md) | README voice, section structure, where new content belongs, repetition rules, code accuracy, and minimal-change maintenance. |

## Python library engineering

| Skill | Entry point | Purpose | Prerequisites |
| --- | --- | --- | --- |
| python-project-structure | [SKILL.md](python-project-structure/SKILL.md) | Module organization, `__all__`, public API design, flat vs nested layouts. | None |
| testing-python-libraries | [SKILL.md](testing-python-libraries/SKILL.md) | pytest suite design, fixtures, parametrization, mocking, Hypothesis property-based tests, CI configuration. | `uv`, `pytest`, `pytest-cov`, `pytest-socket`, `hypothesis` |
| documenting-python-libraries | [SKILL.md](documenting-python-libraries/SKILL.md) | Google-style docstrings, Sphinx/autodoc/autosummary, MyST, tutorials, ReadTheDocs deployment. | `sphinx`, `furo`, `myst-parser`, `sphinx-copybutton` |
| reviewing-python-libraries | [SKILL.md](reviewing-python-libraries/SKILL.md) | Release readiness, old-vs-new regression audits, mutation/in-place contract audits, test-suite integrity audits, CI evidence levels, structured review report. | `git`, `uv`, `pytest`, `coverage`, `bandit`, `pip-audit`, `detect-secrets`, `twine`, `mypy`, `ruff` |
| packaging-python-libraries | [SKILL.md](packaging-python-libraries/SKILL.md) | `pyproject.toml`, build backends, wheel verification, PyPI trusted publishing, conda-forge. | `uv`, `twine`, `setuptools` or `hatchling`, `grayskull` |
| setting-up-python-libraries | [SKILL.md](setting-up-python-libraries/SKILL.md) | Scaffold a new library: src layout, uv, ruff, pytest, mypy, pre-commit, GitHub Actions, Makefile. | `uv`, `ruff`, `pytest`, `pre-commit`, `make` |
| codebase-inspection | [SKILL.md](codebase-inspection/SKILL.md) | Lines of code, language breakdown, and code-vs-comment ratios with `pygount`. | `pygount` |
| python-package-release | [SKILL.md](python-package-release/SKILL.md) | Offline, verified release preparation: metadata audit, README alignment, dependency check, build verification. | `git`, `python`; `python -m build` or `twine` (optional) |
| release-management | [SKILL.md](release-management/SKILL.md) | Semantic versioning, changelog maintenance, deprecation and migration guides, canonical tag-triggered PyPI publish workflow. | `git`, `uv`, `python -m build` or `twine`; GitHub Actions for the publish workflow |
| improving-python-code-quality | [SKILL.md](improving-python-code-quality/SKILL.md) | Ruff linting, mypy type checking, Pythonic idioms, refactoring. | `ruff`, `mypy` |
| api-design | [SKILL.md](api-design/SKILL.md) | API design principles, public re-exports, API evolution and deprecation, error handling. | None |

## Development workflow

| Skill | Entry point | Purpose |
| --- | --- | --- |
| systematic-debugging | [SKILL.md](systematic-debugging/SKILL.md) | Four-phase root-cause debugging: reproduce, find the pattern, test a hypothesis, fix with a regression test. |
| test-driven-development | [SKILL.md](test-driven-development/SKILL.md) | RED-GREEN-REFACTOR discipline and common testing anti-patterns. |
| requesting-code-review | [SKILL.md](requesting-code-review/SKILL.md) | Pre-commit gate: static security scan, baseline-aware tests and lint, independent reviewer, auto-fix loop. |
| simplify-code | [SKILL.md](simplify-code/SKILL.md) | Parallel multi-angle cleanup review of recent changes, then apply what is worth applying. |
| spike | [SKILL.md](spike/SKILL.md) | Throwaway feasibility experiments and head-to-head approach comparisons before committing to a build. |
| handoff | [SKILL.md](handoff/SKILL.md) | Write a compact, redaction-aware handoff document for a fresh agent. |

## Dependencies and loading order

Load the skill that matches the task; most are standalone. These internal
references exist, and every one resolves inside `.agents/skills/`:

| From | Internal dependency | Nature |
| --- | --- | --- |
| packaging-python-libraries | `setting-up-python-libraries/PYPROJECT.md` | File link |
| packaging-python-libraries | `release-management/AUTOMATION.md` | File link |
| testing-python-libraries | `setting-up-python-libraries/CI.md` | File link |
| setting-up-python-libraries | `improving-python-code-quality` | Named reference |
| setting-up-python-libraries | `release-management` (`managing-python-releases`) | Named reference |
| release-management | `AUTOMATION.md`, `MIGRATION.md`, `scripts/bump_version.py` | Own files |
| improving-python-code-quality | `RUFF_CONFIG.md`, `MYPY_CONFIG.md`, `TYPE_PATTERNS.md` | Own files |
| release-management | `api-design` | Named reference (deprecation scope) |
| api-design | `release-management/MIGRATION.md` | File link |
| api-design | `improving-python-code-quality` | Named reference |
| api-design | `PATTERNS.md`, `EVOLUTION.md` | Own files |
| requesting-code-review | `test-driven-development` | Named reference |
| simplify-code | `requesting-code-review` | Named reference |
| systematic-debugging | `test-driven-development` | Named reference |
| bynat-documentation-conventions | `references/accessor-inplace.md`, `references/docstring-audit.md`, `references/graphify-refresh.md`, `references/work-completion-audit.md`, `scripts/verify_docs_only.py` | Own files |
| reviewing-python-libraries | `references/mutation-contract-audit.md`, `references/test-suite-integrity-audit.md`, `scripts/reconcile_pytest_counts.py` | Own files |

When several apply, load upstream first: `setting-up-python-libraries`, then
`improving-python-code-quality` / `testing-python-libraries` /
`packaging-python-libraries`, then `release-management` and `api-design`. The
workflow skills (`systematic-debugging`, `test-driven-development`,
`requesting-code-review`, `simplify-code`, `spike`, `handoff`) are independent.

A few skills name complementary skills that are deliberately outside this
bundle: `subagent-driven-development` (Claude Code/superpowers orchestration),
`github` (Hermes-adapted gh CLI workflow), `plan`, and `gsd-spike`. None is
invoked by a procedure step; the naming skills remain usable without them.

## Notes

- Supporting files stay inside their own skill directory; a few skills additionally link into sibling skills' files (see the dependency table above).
- Licensing and attribution are documented per source in [LICENSE.md](LICENSE.md). Six upstream sources are covered: `wdm0006/python-skills`, `obra/superpowers`, `NousResearch/hermes-agent`, `gsd-build/get-shit-done`, `wshobson/agents`, and `mattpocock/skills`. The remaining three skills are original `bynat` work under the repository licence.
- Author and licence fields from the original skills are preserved in each
  `SKILL.md`.
