# Accessor `inplace` Contract

Use when changing `df.bynat` mutation behavior, adding an in-place capable accessor
method, or regenerating `bynat/_accessors/dataframe.pyi`.

## Contract

- `inplace: bool = False` is declared at the SAME parameter kind and positional index as the
  corresponding `BaseData` method. It is positional-or-keyword for most methods, and
  keyword-only only where the shared function's variadic positional parameter leaves no free
  positional slot (`reorder_columns`, `extract_keywords`, `handle_outliers`, `drop_outliers`,
  `fill_missing`, `fill_missing_from`, `impute_by_language`, `fill_missing_coordinates`,
  `convert_to_usd`, `extract_entities_nlp`). A blanket keyword-only flag silently changes the
  calling convention relative to `BaseData` and breaks parity.
- Default (`inplace=False`): return the shared function's result; `self._obj` is untouched,
  including when the shared function raises, so validation failures never mutate.
- `inplace=True`: call the shared function first, then `self._obj._update_inplace(result)`,
  then return `None`.
- Conditional return: `handle_outliers`, `drop_outliers`, `fill_missing`, and
  `fill_missing_from` mutate AND return the hierarchical statistics `DataFrame` instead of
  `None` when `get_hierarchical_stats=True`. Mirror `BaseData._finish_with_stats`; do not
  collapse this into a universal "returns None" rule.
- Excluded methods keep raising `TypeError` for `inplace=`: `get_hierarchical_stats`,
  `profile`, `save_to_json`, `save_to_sql`, `clear_cache_for_column`, `with_cache`.
  `view` has no accessor equivalent.
- `_update_inplace` preserves `id(frame)` and every caller reference. Verify on pandas 2.x
  and 3.x, including shape, column, and index changes. It also preserves `BaseData`
  metadata: an in-place accessor call on a `BaseData` frame keeps the same
  `cache_manager` and `_metadata`, so cache sharing across derived frames survives.
  Verify that explicitly when the wrapped frame is a `BaseData` subclass.

## Implementation seam

- Factories in `bynat/_accessors/_binding.py`: `_frame_method(func, *, inplace=False, stats=False,
  inplace_before=None)` and `_cached_frame_method(func, *, inplace=False, inplace_before=None)`.
  Methods that must not accept `inplace` keep the defaults, so the flag still raises
  `TypeError`. `inplace_before` names the parameter `inplace` precedes when `BaseData`
  interleaves it rather than appending it.
- `kwargs.pop('inplace', False)` must happen inside the wrapper before the shared call.
  Never let it reach `**target_cols_and_keywords`, `**target_cols_and_indices`,
  `**target_cols_and_substrings`, `melt_transform_pivot`'s `**kwargs`, or
  `**target_cols_and_json_keys` — each of those absorbs it as data.
- Binding: the wrapper is `def method(self, *args, **kwargs)`, and `__signature__` is
  introspection-only, so a positional flag never reaches `kwargs`. Compute `keyword_only` and
  the positional `index` once, when the factory runs. If `inplace` is keyword-only, pop it
  from `kwargs`; otherwise, when `len(args) > index`, take `flag = args[index]` and REMOVE
  that element, leaving every later argument in place:
  `args = args[:index] + args[index + 1 :]`; otherwise pop it from `kwargs`. Skipping this
  makes every positional call fail (or silently fall through to the copy path).
- Never extract the flag by truncating with `args = args[:index]`. Truncation discards the
  arguments that legitimately follow `inplace` (for example
  `translate_conditional_column`'s `random_state`), and it silently swallows surplus
  positional arguments that the shared function would reject: the accessor then mutates and
  returns `None` where `BaseData` raises `TypeError`. Argument validation is part of the
  public contract, so an accept/reject divergence between the two APIs is a defect.
- Do not replace `_update_inplace` with per-method column assignment; it is the same
  primitive `BaseData` uses and the only way to change shape/columns/index in place.
- mypy: `# type: ignore[operator]` on the `_update_inplace` call. pandas-stubs does not
  declare the attribute, so mypy resolves it through `DataFrame.__getattr__` to
  `Series[Any]`. `warn_unused_ignores = true`, so suppress nothing else.

## Insertion rule (runtime and stub)

Given the shared function's parameters with the leading frame and `cache_manager` removed:

1. If an explicit anchor names the parameter `inplace` precedes (only
   `translate_conditional_column`, anchored before `random_state`, because `BaseData` orders
   it `..., save_every=1000, inplace=False, random_state=0, provider=None`), insert there as
   POSITIONAL_OR_KEYWORD.
2. Else find the first parameter whose kind is KEYWORD_ONLY, VAR_POSITIONAL, or VAR_KEYWORD.
   - If that parameter is VAR_POSITIONAL, there is no free positional slot: `inplace` becomes
     KEYWORD_ONLY and is inserted immediately AFTER the `*args` (the start of the keyword-only
     block).
   - Otherwise insert POSITIONAL_OR_KEYWORD at that index — the end of the positional block,
     before the keyword-only block or `**kwargs`.

`inspect.Signature.replace` raises `ValueError: wrong parameter order: keyword-only parameter
before variadic positional parameter` if the keyword-only form is inserted AT the `*args`
index instead of after it.

Simulate the rule in a scratch script against the real `BaseData` signatures and assert
parameter kind AND positional index for every affected method before dispatching the
implementation. `inspect.signature(Class.method)` is unbound and includes `self`; strip it
before comparing indices, or every row will look off by one.

## Stub regeneration

`bynat/_accessors/dataframe.pyi` is generated — never hand-edit it. `tools/sync_docs.py`
matches class-body assignments whose value calls a name in `METHOD_FACTORIES`, resolves
the wrapped shared function through `__wrapped__`, and rebuilds the signature from the
shared module's source. A runtime-only wrapper parameter therefore requires extending
`_stub_function` to insert at the same index and with the same kind as the runtime rule:
`args.kwonlyargs.insert(0, ...)` plus a matching `args.kw_defaults` entry for the variadic
case, or an insertion into the positional block at the end for the other cases. A defaulted
positional insertion needs a matching `ast.Constant(False)` in `args.defaults` at
`index - pad`, where `pad = len(args.args) - len(args.defaults)`; inserting before a required
parameter is impossible because Python defaults are right-aligned. Widen the return
annotation for non-stats methods, and pass the anchor out of the factory call in
`render_stub` as `inplace_before`. Run `python tools/sync_docs.py`, then confirm with
`--check`.
`tests/cross_cutting/contracts/test_doc_drift.py` enforces the stub and pins exact
accessor parameter-key lists, so any signature change breaks it until those expected
lists are updated.

## Tests

- Accessor mutation behavior is cross-cutting: `tests/cross_cutting/accessor/`.
- Cover both paths for every eligible method; assert `id(frame)` is unchanged and that
  an independent second reference observes the mutation.
- Cover positional binding, not only keyword binding: for every method whose `BaseData`
  counterpart accepts `inplace` positionally, call the accessor with the flag in that position
  and assert it mutates; for keyword-only methods assert a positional flag is rejected. Also pin
  `inspect.signature` kind and positional index against `BaseData` so the stub, the runtime
  wrapper, and the class cannot drift apart again.
- Probe positional parity past the happy path. For any wrapper that extracts a positional
  control flag, compare the accessor and `BaseData` on exact, surplus, and
  following-parameter positional calls and require identical accept/reject outcomes (same
  return category or same exception type). A green happy-path test hides a silent
  argument-drop, and the divergence only appears on calls nobody wrote a test for.
- When a test asserts an input object is unmutated, pass the SAME object into the call and
  assert on that object. Building the input from a factory inside the argument helper, so
  the call and the pre-call snapshot each call `factory()`, asserts on a lookalike that was
  never passed: the test stays green even when the callee mutates its argument. This bites
  `fill_missing_from` reference-dataset checks and every "source unchanged" assertion.
- PD-01 regressions: `extract_keywords`, `split_list_objects`, `truncate_after_substring`,
  `melt_transform_pivot`, and `extract_entities_nlp` must treat `inplace` as the control
  flag and still accept their legitimate variadic keywords.
- Class/accessor parity belongs in `tests/cross_cutting/accessor/test_parity.py`; the two
  ownership models must not be required to share object identity.
- Enrichment paths need offline provider/spaCy fakes. Put them in the owning domain's
  `tests/modules/enrichment/helpers.py` when the test lives in that domain, and define them
  locally when the test is cross-cutting; never import one `test_*.py` module from another
  (`BYNAT-ARCH-6`).

## Documentation parity

Changing this contract makes `docs/TESTING_STANDARDS.md` wrong, not just the README. Reconcile
the normative accessor rules (`S-1`, `S-4`, `ML-1`, `ML-2`, `ML-3`) and the Phase 0 adoption
table entry that counts the pinned `xfail` tests, and remove or rewrite the strict `xfail`
markers that asserted the accessor rejects `inplace` — a stale strict `xfail` whose body now
fails for a different reason still reports XFAIL and hides the contract change. The
constitution's documentation-parity rule requires test and policy to be reconciled in the
same change. Check `docs/ROADMAP.md` public-API policy statements for contradictory claims.

## Verification

- Lint the directories you changed with the repository's CI scope
  (`ruff check bynat tests benchmarks`; add `tools` when it changed); a bare
  `ruff check ./` also lints vendored agent-skill scripts under `.agents/` and
  fails outside the package.
- CI installs the latest pandas, so a green CI run does not by itself cover the oldest
  supported pandas major; run the suite and a runtime probe on that version too
  (`id(frame)`, an independent second reference, shape/column/index changes), not only
  through the latest-version suite.
- `tools/sync_docs.py` writes the `.pyi` with LF while `core.autocrlf=true` makes the
  other working files CRLF. `git diff` normalizes, so the warning is not a whole-file
  change; do not hand-convert line endings and do not hand-edit the generated file.
