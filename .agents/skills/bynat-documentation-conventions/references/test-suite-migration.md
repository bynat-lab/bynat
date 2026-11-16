# Test-Suite Architecture Migration

Use this reference when implementing a documented bynat test-suite architecture. It is a structural migration: preserve behavior, ownership, and execution policy while changing paths.

## Procedure

1. Read the complete authoritative testing standard, especially the target layout, ownership rules, markers, fixtures, configuration, and migration plan.
2. Inventory every current test module, function, helper, fixture, constant, marker, skip, strict xfail, support-tool import, benchmark dependency, hardcoded path, and pytest configuration. Record source-to-destination ownership for split files.
3. Correct only confirmed documentation defects that directly affect migration semantics. Validate target-path calculations from the target file itself; for `tests/cross_cutting/contracts/test_doc_drift.py`, repository root resolution is `Path(__file__).resolve().parents[3]`.
4. Dispatch one bounded implementation batch at a time through the configured subagent workflow. Keep batches non-overlapping. After each batch, inspect `git status`, the actual diff, target contents, focused tests, collection, Ruff, and target line counts before accepting it.
5. Preserve structure and behavior: use moves or source extraction with minimal import changes; keep multiprocessing workers module-level; preserve fixture scope, test names, parametrization, markers including `network`, conditional skips, and strict `xfail(strict=True)` cases.
6. Keep `tests/conftest.py` suite-wide. Do not create `tests/shared/` or promote helpers unless distinct architectural domains actually reuse them; same-domain helpers stay local or module-scoped.
7. Update migration-dependent tooling in the same bounded step. When a manifest gains nested paths, update both the manifest values and the resolver to use the full relative path rather than `Path(relative).name`. Preserve `tools/sync_docs.py`; extract benchmark reference implementations before removing benchmark imports from relocated test modules.
8. When a subagent fails, is interrupted, or enters a repetition loop, assume partial filesystem changes may have landed. Inspect the tree before retrying; never duplicate an extraction or trust the report over actual files.
9. After all batches, run full collection, the complete supported suite, marker-specific selections, extras/optional checks, wheel verification, benchmark imports/execution, line-size validation, and an independent architecture review. Recompute current versus projected counts and inspect final scope.

## Gates

- Every original file and test responsibility has one destination or an explicit retention reason.
- No resulting test file exceeds the repository limit.
- Current collection, definition counts, assertions, parametrized cases, skips, and strict xfails reconcile with the migration plan; intentional additions are explained separately.
- No stale source paths remain in active tooling, manifests, imports, or discovery rules.
- A passing aggregate suite is insufficient: compare inventories and run the tools that consume relocated paths.

## Common pitfalls

- Do not classify a test as cross-cutting merely because it imports or calls another module; ownership follows the primary contract.
- Do not preserve an oversized file as an exception.
- Do not leave a non-authorization clause unchanged after implementation is authorized if it still claims migration is prohibited; reconcile only the directly affected architecture wording.
- Do not treat a delegated completion report as evidence until the working tree and commands are independently verified.
