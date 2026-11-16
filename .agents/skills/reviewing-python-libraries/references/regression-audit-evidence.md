# Regression Audit Evidence Matrix

## Required run matrix

| Run | Import proof | What it establishes | What it does not establish |
|---|---|---|---|
| Old tests → old artifact | `sys.executable`, `package.__file__` | Baseline suite health | New behavior correctness |
| New tests → new artifact | Same proof | New implementation's tested contract | Strict backward compatibility |
| Old tests → new artifact | Same proof, external copied tests | Compatibility of covered old behavior | Features absent from old tests |

Keep copied tests outside both worktrees and hash them before execution.

## Failure classification

1. **Intentional change:** issue acceptance criteria or documented migration contract explicitly changes behavior and new tests verify the replacement.
2. **Confirmed regression:** old contract remains applicable, the new runtime violates it, and a focused reproduction is independent of the new implementation's expected output.
3. **Test incompatibility:** the test patches an old private seam, exact module identity, or object identity that the documented migration intentionally changed.
4. **Environment/setup issue:** import, dependency, or working-directory setup is wrong; fix the harness before interpreting test results.
5. **Unresolved:** evidence cannot distinguish the classifications; propose the smallest targeted test or contract decision.

## Evidence hierarchy

Prefer, in order:

1. Runtime reproduction with independently reasoned expected behavior.
2. Existing test output with verified import path and command/exit code.
3. Issue acceptance criteria and public documentation.
4. Tracked source inspection and diff evidence.
5. Coverage or test counts as investigation guidance only.

Do not mark an issue verified from source inspection alone when an acceptance criterion requires runtime behavior.

## Compatibility checklist

Check changed:

- imports and legacy shims;
- signatures, defaults, and keyword-only parameters;
- return types and object identity;
- mutation and `inplace` behavior;
- exceptions and warnings;
- ordering and determinism;
- provider/mock seams;
- cache persistence, migration, deletion, and concurrency policy;
- optional dependencies and skipped branches;
- documentation/version consistency.

## Coverage and benchmark pitfalls

- Run coverage with an explicit checkout source root; installed-package coverage can report test files instead of production files.
- Preserve malformed or stale runs, label them invalid/superseded, and do not average them into valid results.
- Require output equivalence before timing old/new implementations.
- Match repetitions for both sides and report medians/dispersion; fastest-of-three versus one run is only directional evidence.
- Treat optional-dependency skips as unverified branches, not passes.
