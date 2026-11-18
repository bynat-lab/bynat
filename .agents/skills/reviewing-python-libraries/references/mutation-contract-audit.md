# Mutation / In-Place Contract Audit

Use when auditing whether a library's public transformation API should keep, gain, or drop an `inplace` (or otherwise mutating) mode, and whether an existing mutating implementation is correct. Typical for pandas-DataFrame subclasses, ORM wrappers, and collection-like classes.

## 1. Freeze the evidence boundary

- Record absolute repo path, branch, commit, `git status --porcelain` (must be clean), package version (`pyproject.toml` / `__init__`), and the exact interpreter and framework versions (`sys.executable`, `pandas.__version__`).
- Re-check porcelain at the end and remove any artifact your own commands created (`.pytest_cache`, `.venv`, `__pycache__`).
- Never run `uv run` inside the audited repository: it creates `.venv`/`uv.lock` and dirties the tree. Use an existing interpreter by absolute path, or set `PYTHONPATH`.

## 2. Inventory

- List only methods **defined by the library**. Inherited framework methods (pandas `drop`, `fillna`, `sort_values`, ...) are a separate surface: count them separately and record that they keep framework semantics.
- Include constructors, special methods, and public properties, but mark them as non-transformations.
- Per method record: file:line, delegated implementation file:line, decorators, current mutating parameter, actual return type in each mode, and defined-vs-inherited.
- Separate value/column/row transformers from read-only analysis, external I/O, and helpers.

## 3. Source checklist per method

- Locate the real mutation: `self[...] = ...`, `_update_inplace`, `self._mgr`, or construction of a new object.
- Trace decorators that rewrite signatures or return values.
- Object identity: does the mutating mode keep the same instance (`id`) and the same subclass type?
- Attached state: metadata lists (`_metadata`), `__finalize__`, cache/state managers. Confirm they survive the mutation.
- Return contract in both modes, including early exits and "extra result" modes (for example statistics returned alongside the frame).
- Failure safety: is the full result computed before the mutation is committed? Check invalid arguments, external/API failures, and partial writes.
- Subclass behavior: does mutating mode preserve `JsonFile`/`CsvFile`-style subclasses?
- Compare docs and tests against the observed contract; never trust names or docstrings.

## 4. Runtime verification recipe

- Put the probe script in a scratch directory outside the repo; never write into the audited tree.
- For each method assert: new/default mode returns a new object of the same class, original unchanged, attached state shared; mutating mode returns the documented value (usually `None`), `id` unchanged, type unchanged, state identity unchanged, data equal to the copy result.
- Inject fake providers/seams for external calls; never touch the network.
- Run on at least the minimum and latest supported framework versions; framework internals change between them.
- Exercise real transformations, not only early exits: actual column drops/renames, row explosions, reshapes, outlier removal, reference-dataset imputation.
- Verify failure paths: invalid arguments must raise before mutation; provider failures must not partially mutate the frame.

## 5. Decision labels

- **KEEP**: existing mutating support is appropriate and correct.
- **ADD**: should support it but does not.
- **DO NOT ADD**: should not expose it (read-only analysis, external I/O, helpers).
- **FIX**: exposes it but behavior or contract is wrong.
- **INVESTIGATE**: a specific unresolved technical question blocks the decision.

## 6. Pitfalls

- **Private mutation hooks drift.** `pandas.DataFrame._update_inplace` is private, and its signature and body changed between pandas 2 and 3. Inspect `inspect.getsource` on every runtime; do not assume the mechanism is stable. Prefer the framework's own commit path, but pin it with a compatibility test.
- **`**kwargs` silently absorbs flags.** A variadic method (`**target_cols`, `**kwargs`) swallows an unexpected `inplace=True` and either ignores it or creates a column named `inplace`. Probe the exact call shape; passing a tuple as one positional argument hides the bug.
- **Injecting a flag into a wrapper's positional slot drops surplus arguments.** When a decorator synthesizes a signature by inserting a parameter (`inplace`) at a fixed index into `*args`, the extraction must remove only that one element: `args = args[:position] + args[position + 1 :]`. Writing `args = args[:position]` truncates, so every positional argument *after* the injected one is silently discarded and the wrapper accepts calls the wrapped API correctly rejects with `TypeError`. Truncation also mis-binds trailing parameters: with `inplace` before `random_state`, a 9-positional call meant as `random_state=42` is read as `inplace=42`. Probe surplus positionals and trailing positional parameters against the class API, not only the flag's own position.
- **Docstrings copied from shared functions omit subclass-only parameters.** When a class method reuses a shared docstring, class-only flags (`inplace`, `cache_manager`) are undocumented in hover/reference text even though the signature exposes them.
- **Framework string dtype changes break masked string concatenation.** Patterns like `series.loc[mask] += ", " + other[mask]` can raise on Arrow-backed string dtypes (pandas 3) even when `mask` is all False, because the empty selection has a null/Arrow dtype. Test on the newest supported framework.
- **Inherited methods bypass the library's contract.** A subclass inherits framework `inplace` methods that return the framework's value (pandas 3 `fillna(inplace=True)` returns the frame, while a `_finish`-style helper returns `None`). Document the divergence; do not count them as library implementations.
- **Missing optional dev dependencies block collection.** A test module importing `hypothesis` (or another dev extra) fails collection and can abort the whole suite. Exclude that file and record the environment gap; do not install into the user's environment during a read-only audit.
- **Test runs leave artifacts.** Use `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`; delete `.pytest_cache` afterward. Check porcelain again before reporting.

## 7. Report shape

1. Inventory: class, method, file:line, current support, actual return, defined-vs-inherited.
2. Decision table with per-method evidence and reasoning.
3. ADD/FIX analysis: current behavior, proposed behavior in both modes, identity, memory, failure safety, return contract, implementation locations.
4. DO-NOT-ADD analysis, one method at a time.
5. Verified bugs and inconsistencies, each labeled confirmed vs uncertain.
6. Counts, prioritized changes, proposed contract, and decisions requiring maintainer judgment.
