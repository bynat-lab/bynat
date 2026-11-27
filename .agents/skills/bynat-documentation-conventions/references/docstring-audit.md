# Docstring Audit and Standardization Recipe

Ordered procedure for auditing and standardizing docstrings in `bynat/`. Load this
when the task is a docstring audit, a documentation-accuracy pass, or a request to
make the docstrings consistent.

## 1. Inventory before editing

- Enumerate every module and every public function, method, and class with an AST
  walk; record missing docstrings and docstrings that are a single line.
- Identify the generated artifacts first: `bynat/cleaning/base.py` carries literal
  copies of the shared docstrings, and `bynat/_accessors/dataframe.pyi` carries the
  accessor signatures with the same docstrings. Both come from
  `tools/sync_docs.py`; a hand edit is overwritten on the next run.
- Make the convention explicit before changing it: parse every docstring and
  tally the `Args:`, `Returns:`, `Raises:`, `Notes:`, `Example:`, `Examples:`, and
  `Attributes:` headings, and confirm each docstring's headings appear in that
  order with no duplication.

## 2. Establish real behavior by probing

Write the probe outside the repository in a scratch directory, never inside it,
and run it with the repository's check interpreter `.venv-check/Scripts/python`
(the environment that carries pandas, NumPy, and the dev tools). Do not treat an
existing docstring as evidence.

Probe at least:

- **Mutation.** Deep-copy the input frame, call the function, assert the input is
  unchanged. A read such as `df.loc[df[col].notna(), [col]]` is not a mutation,
  and a write through `result = df.copy()` does not mutate the caller's frame.
- **`inplace`.** Return value in both modes, plus `id(frame)` after
  `inplace=True` and whether caller references observe the change.
- **Statistics combined with `inplace`.** `get_hierarchical_stats=True` together
  with `inplace=True` returns the statistics object, not `None`.
- **Validation.** For each numeric or enum parameter pass `0`, `-1`, `True`,
  `1.5`, and `"1"`; record accept versus raise and the exception type. Booleans
  are a distinct case because `bool` subclasses `int`.
- **Warnings and logs.** Capture both `warnings.catch_warnings(record=True)` and
  `logging` at `DEBUG`; a code path that only logs is invisible to
  `pytest.warns`.
- **Optional dependencies.** Determine which imports are lazy and which are
  required, and whether a missing dependency raises `ImportError` or silently
  degrades. Install fake modules in `sys.modules` when the real extra is absent,
  reusing `tests/modules/enrichment/helpers.py` rather than hand-rolling stubs.
- **Cached enrichment and NLP paths.** Point `BYNAT_CACHE_DIR` at a scratch
  directory before probing `translate_*`, `convert_to_usd`,
  `fill_missing_coordinates`, or `extract_entities_nlp`. The default
  `Settings/Cache Data/Automated/cache.sqlite3` persists across runs, and a
  cache hit returns before the fetch/model-load path, so the probe reports the
  contract as satisfied without executing it. Confirm the path really ran (a
  cold cache must reach the lazy import or provider call).
- **Early exits.** For a missing column, an empty selection, or a no-match
  substring, record whether a copy is returned or the same object.
- **Return types.** `type(result)` for every `output_type`, including `None`.
- **Text and regex edges.** Patterns without a capture group, keywords that are
  regex metacharacters, and Title-Casing of extracted values.

## 3. Edit, then regenerate

- Edit the shared functions in `columns.py`, `text.py`, `stats.py`, `profile.py`,
  `io.py`, `enrich/*.py`, `analytics/analyzer.py`, `caching/*.py`, `_common.py`,
  and `_outputs.py`.
- Run `.venv-check/Scripts/python tools/sync_docs.py` to rewrite `base.py` and
  `bynat/_accessors/dataframe.pyi`.
- Run `.venv-check/Scripts/python tools/sync_docs.py --check` as its own
  command; it exits 1 on drift and aborts an `&&` chain.

### Documenting `inplace` on a shared docstring

A bulk pass that adds "the input is never modified" to a shared docstring
silently becomes false the moment the same text is copied onto the `BaseData`
and accessor methods, which accept `inplace=True`. Apply all three parts
together, and word them so they stay true for the standalone function too:

- `Args:` — one entry, always last, scoped to the surfaces that have the
  parameter:

  ```
        inplace (bool): `BaseData` methods and the `df.bynat` accessor only; the
            standalone function has no such parameter and always returns a new
            frame. When True, the receiver is mutated in place. Defaults to
            False.
  ```

- `Returns:` — both modes and the exact value of each, distinguishing a new
  object from mutation of the receiver:

  ```
    Returns:
        With `inplace=False` (default), a new dataframe ...; the input is not
        modified. With `inplace=True`, the receiver is mutated in place and None
        is returned.
  ```

  For `handle_outliers`, `drop_outliers`, `fill_missing`, and
  `fill_missing_from`, state all four combinations: with
  `get_hierarchical_stats=True`, `inplace=False` returns `(frame, statistics)`
  and `inplace=True` returns the statistics object instead of `None`. Note that
  `fill_missing_from`'s `dataset` is never modified in either mode.

- `Notes:` — rescope the claim rather than deleting it. Replace
  "The input ``df`` is never modified." with
  "The standalone function never modifies ``df``."

Do not document `inplace` in `Returns` alone; an undocumented parameter plus a
mode-dependent return is the contradiction this pattern prevents.

## 4. Verify

```bash
./.venv-check/Scripts/python -m ruff check bynat tools tests
./.venv-check/Scripts/python tools/sync_docs.py --check
./.venv-check/Scripts/python -m mypy
./.venv-check/Scripts/python -m pytest -q
./.venv-check/Scripts/python -m pytest -m "extras or slow or mutation" -q
./.venv-check/Scripts/python -m compileall -q bynat tools
git diff --check
./.venv-check/Scripts/python .agents/skills/bynat-documentation-conventions/scripts/verify_docs_only.py .
```

## 5. Prove the change is documentation-only

`scripts/verify_docs_only.py` compares `HEAD` with the working tree after
stripping docstrings and attribute docstrings. Every modified Python file must be
reported as documentation-only; investigate any file that is not.

## 6. Re-audit after a bulk pass

A bulk documentation edit is not finished when the checks pass. Re-audit every
docstring you changed against the implementation, and specifically re-check every
function and method that carries a contract-bearing parameter (`inplace`,
mutation, copy-vs-mutate, return value, optional dependency). Verify each surface
separately — standalone function, `BaseData` method, accessor method — because a
claim true for one is often false for another. Compare `Returns:` against
`Notes:` for internal contradiction, and re-run the contract probe rather than
reasoning from the default-mode behavior.

## 7. Report

Scope inspected (modules and API elements), counts added/corrected/standardized,
the convention selected and why it fits, the behavior clarifications documented,
files changed, verification commands with their actual results, and remaining
undocumented or unverifiable behavior with `file:function` references. Do not
claim complete coverage unless every module and API element was inspected, and do
not silently leave a known inaccuracy unresolved — name it.
