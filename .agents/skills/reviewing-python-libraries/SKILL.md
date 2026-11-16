---
name: reviewing-python-libraries
description: Use when auditing a Python library or comparing releases. Review code, tests, APIs, packaging, static quality, and evidence.
author: wdm0006 (based on Will McGinnis's Guide to Developing High-Quality Python Libraries)
license: MIT
---

# Python Library Review

## When to Use

Use this skill for release-readiness reviews, old-vs-new regression audits, package-quality assessments, CI/test-infrastructure verification, and evidence consolidation after testing. Keep the review read-only unless the user explicitly requests fixes.

## Quick Health Check (5 min)

```bash
git clone https://github.com/user/package && cd package
head -50 pyproject.toml                     # Modern config?
ls tests/ && uv run pytest --collect-only   # Tests exist?
uv run pytest --cov=package | tail -20      # Coverage?
uvx bandit -r src/                          # Security?
```

## Review Dimensions

| Area | Check For |
|------|-----------|
| Structure | src/ layout, py.typed marker |
| Packaging | pyproject.toml (not setup.py) |
| Code | Type hints, docstrings, no anti-patterns |
| Tests | 80%+ coverage, edge cases |
| Security | No secrets, input validation, pip-audit clean |
| Docs | README, API docs, changelog |
| API | Consistent naming, sensible defaults |
| CI/CD | Tests on PR, multi-Python, security scans |

## Old-vs-New Regression Audit Workflow

1. **Freeze the evidence boundary.** Record absolute worktree paths, commits, branch/detached state, and porcelain status before reading results; compare tracked Git content only, because caches, wheels, `build/`, pyc files, and generated metadata pollute directory diffs.
2. **Build the baseline matrix.** Run the old suite on the old installed artifact, the new suite on the new installed artifact, and an external immutable copy of the old tests against the new installed artifact. Print `sys.executable` and `package.__file__` immediately before each run; a test command from a repository directory can silently import the wrong checkout.
3. **Read issue requirements before judging behavior.** Retrieve the full issue body and acceptance criteria, map each criterion to implementation, tests, and runtime evidence, and classify each issue as `Verified`, `Partially Verified`, `Failed`, or `Blocked`; never infer requirements from titles or commit messages.
4. **Classify compatibility failures against contracts.** Separate intentional API-transition changes from regressions using documented behavior and issue criteria. Treat changed object identity, `__module__`, exception behavior, provider seams, defaults, mutation, ordering, and cache conflict semantics as public compatibility questions, not incidental test failures.
5. **Review test quality, not just counts.** Inspect modified/deleted assertions, skips, optional-dependency branches, independently reasoned expected values, negative/error paths, real multiprocess behavior, and whether mocks exercise the new seam. Coverage directs investigation; it does not prove correctness.
6. **Separate correctness from performance.** Require deterministic identical inputs and output-equivalence assertions before timing. Record repetitions, warm-up, medians, variability, and whether old/new timing procedures match; fastest-of-three current versus one legacy timing is directional evidence only.
7. **Separate package-source coverage from test-file coverage.** Run source-directed coverage against each checkout with an explicit source root and preserve invalid/superseded attempts as invalid evidence rather than blending percentages.
8. **Consolidate without overwriting raw evidence.** Inventory actual artifacts, mark stale or invalid outputs as superseded, and write a separate evidence-review report. Prefer a short follow-up test that resolves one unanswered contract over rerunning an entire suite.

Use `references/regression-audit-evidence.md` for the detailed evidence matrix and failure-classification checklist.

## CI Verification Evidence

Use when verifying CI/test-infrastructure claims: workflow separation, job gates, marker selection, coverage/mutation configuration. Four levels are distinct — accept only the highest the criterion requires:

| Level | Example | What it proves |
|---|---|---|
| Configuration inspection | reading a workflow or `cosmic-ray.toml` | what is configured; never that it ran |
| Collection | `pytest --collect-only`, `cosmic-ray init` | discoverability and configured work-item count |
| Partial execution | one job, one marker, a 3-mutant probe | a command works; not the gate |
| Complete execution | every configured job/leg/work item reaches a final state | the criterion |

- Derive commands from the current workflow text in the working tree; do not reuse a prior report's command list.
- Reproduce in an environment matching the workflow's Python version; the ambient interpreter is not a substitute.
- Prefer real CI runs as evidence when available; a configured workflow is not execution evidence.
- Record per check: exact command/job, environment + Python version, exit code or job conclusion, test counts, and log location.
- A workflow that has never run is `Not verified`, not passing and not broken.
- A mutation campaign rewrites source files in place. Run it exclusively — never alongside another test run, coverage run, or wheel build against the same checkout; a parallel pytest can import a mutated module and produce false results. This includes delegated subagents: do not dispatch another suite against the same checkout while the campaign runs.
- On Windows a venv's `python.exe` re-execs the base interpreter, so a child process launched with a bare `python` resolves to the base interpreter and misses the project's dependencies; `shutil.which("python")` disagrees with what `subprocess` actually launches. Probe a small run before a long campaign and put an absolute interpreter path in the tool's test command.
- A timing-sensitive suite (bounded `process.join(n)`, wall-clock budgets) can fail under CPU contention from a concurrent run. Re-run it in isolation before classifying the failure; a green isolated rerun means the earlier red was load, not a defect. Record both runs.

See `references/ci-verification-evidence.md` for the GitHub Actions API recipe and the full Cosmic Ray campaign procedure.

## Red Flags 🚩

- No tests
- No type hints
- setup.py only (no pyproject.toml)
- Pinned exact versions for all deps
- No LICENSE file
- Last commit > 1 year ago

## Green Flags ✅

- Active maintenance (recent commits)
- High test coverage (>85%)
- Comprehensive CI/CD
- Type hints throughout
- Clear documentation
- Semantic versioning

## Report Template

```markdown
# Library Review: [package]

**Rating:** [Excellent/Good/Needs Work/Significant Issues]

## Strengths
- [Strength 1]

## Areas for Improvement
- [Issue 1] - Severity: High/Medium/Low

## Category Scores
| Category | Score |
|----------|-------|
| Structure | ⭐⭐⭐⭐⭐ |
| Testing | ⭐⭐⭐☆☆ |
| Security | ⭐⭐⭐⭐☆ |

## Recommendations
1. [High priority action]
2. [Medium priority action]
```

For detailed checklists, see:
- **[CHECKLIST.md](CHECKLIST.md)** - Full review checklist
- **[REPORT_TEMPLATE.md](REPORT_TEMPLATE.md)** - Complete report template

## Best Practices Checklist

```
Essential:
- [ ] pyproject.toml valid
- [ ] Tests exist and pass
- [ ] README has install/usage
- [ ] LICENSE present
- [ ] No hardcoded secrets

Important:
- [ ] Type hints on public API
- [ ] CI runs tests on PRs
- [ ] Coverage > 85%
- [ ] Changelog maintained

Recommended:
- [ ] src/ layout
- [ ] py.typed marker
- [ ] Security scanning in CI
- [ ] Contributing guide
```

## Learn More

This skill is based on the [Guide to Developing High-Quality Python Libraries](https://mcginniscommawill.com/guides/python-library-development/) by [Will McGinnis](https://mcginniscommawill.com/). The review criteria in this skill draw from all posts in the guide — see the [full guide](https://mcginniscommawill.com/guides/python-library-development/) for detailed quality criteria across every dimension of library development.
