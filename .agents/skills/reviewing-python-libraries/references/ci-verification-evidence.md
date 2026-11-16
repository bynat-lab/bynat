# CI Verification Evidence

## GitHub Actions evidence (public repos, no token)

- List runs: `GET https://api.github.com/repos/{owner}/{repo}/actions/runs?per_page=100` — record `id`, `head_sha`, `event`, `status`, `conclusion`.
- Job detail: `GET .../actions/runs/{run_id}/jobs?per_page=100` — record each job name (matrix legs appear as `job (os, python)`), its `conclusion`, and per-step conclusions. Skipped steps reveal conditional legs.
- Workflow files on a branch: `GET .../contents/.github/workflows?ref={branch}`.
- Parse with `python -c` + `json` (or `jq`); do not eyeball the payload. Unauthenticated calls are rate-limited, so batch and cache responses.

**Default-branch caveat.** The workflows API and `.../workflows/{file}/runs` reflect the repository's default branch. A workflow file added on a feature branch does not appear and has no runs, and `on: schedule` workflows only ever run on the default branch. "No workflow entry / no runs" for a branch-local workflow is expected and is not evidence that the workflow is broken — reproduce it locally and report the default-branch limitation explicitly.

## Full mutation campaign (Cosmic Ray)

- Invoke the console scripts `cosmic-ray` / `cr-report`. `python -m cosmic_ray` fails: the package has no `__main__`.
- Use the repository's own `cosmic-ray.toml`; do not create a temporary reduced session or a representative mutant subset.
- Count configured work items before executing: `cosmic-ray init <config> <session>`, then query the session database. Tables: `work_items(job_id)`, `mutation_specs(module_path, operator_name, ..., job_id)`, `work_results(worker_outcome, test_outcome, ..., job_id)`. Per-module counts: `SELECT module_path, COUNT(*) FROM mutation_specs GROUP BY module_path`.
- Execute with `cosmic-ray exec <config> <session>`; it resumes unfinished work items, so re-run it after an interruption rather than restarting the campaign.
- The default `local` distributor is sequential and `exec` exposes no parallelism flag: a campaign of ~10^3 work items is a long-running job. Launch it in the background, monitor the process to completion, and record wall-clock duration.
- Generate the report only after completion: `cr-report <session>`. A report generated from a partially completed session is not a result.
- Reconcile the counts: completed = killed + survived + timeout + error/invalid/other, and must equal the configured total. Report overall and per-module scores.
- Triage survivors in their source context: distinguish missing test coverage from genuinely equivalent mutations. Do not edit tests or implementation, shrink scope, or weaken the per-item timeout to raise the score.

### Reading `cr-report` output

`cr-report <session>` prints `total jobs`, `complete: N (X%)`, and `surviving mutants: M (Y%)`. `is_killed` is `test_outcome != 'survived'`, so timeouts and incompetent mutants count as killed; a timeout is identifiable by `output = 'timeout'` (the per-item test command was killed at the timeout limit). Per-module score = killed / total work items for that module. A repository's own mutation-score formula may subtract verified equivalent mutants; state which formula was used.

### Windows interpreter resolution for tool-driven test commands

Tools that launch a test command through `subprocess` with a bare `python` (Cosmic Ray's `test-command`, tox, coverage plugins) resolve that name differently from the activating shell:

- `shutil.which("python")` and `python` typed in the shell resolve through `PATH` to the venv.
- `subprocess.Popen(["python", ...])` on Windows searches the application directory first, which for a venv is the base interpreter's directory (the venv `python.exe` re-execs the base). The child runs the base interpreter and dies with `No module named pytest`.

Probe it instead of trusting `which`:

```python
import ctypes, shutil, subprocess, sys
buf = ctypes.create_unicode_buffer(260)
ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 260)
print(buf.value, sys.executable, shutil.which("python"))
p = subprocess.Popen(["python", "-c", "import sys; print(sys.executable)"], stdout=subprocess.PIPE)
print(p.communicate()[0])
```

If the child resolves to the base interpreter, run the campaign with a config whose test command quotes the absolute venv interpreter — Cosmic Ray splits the command with `shlex.split`, so a path containing spaces must be quoted:

```toml
test-command = "\"C:/path/to/.venv/Scripts/python.exe\" -m pytest ..."
```

Before a long run, prove the adapted config is scope-identical to the repository config: initialize a session from each and compare total `work_items`, per-module `mutation_specs` counts, and the operator distribution. Report the adaptation explicitly; it changes only the interpreter path, not the modules, test directories, marker filter, or timeout.

### Concurrency and interruption

- `cosmic-ray exec` reads `pending_work_items` once as a snapshot. Two `exec` processes on the same session each process the full snapshot — concurrent runs duplicate work rather than parallelize. The `local` distributor is sequential; the `http` distributor parallelizes, but its workers share the checkout's source files, so use it only with one source copy per worker.
- Killing `exec` mid-item leaves the mutation applied to the source file. Restore with `git checkout -- <module>`, confirm `git status` is clean, then restart; `exec` resumes the remaining items.
- Sanity-check a small probe (a handful of work items) before the full campaign. A fraction of a second per item with empty `output` means the test command failed to launch (wrong interpreter, bad path), not that the mutants were killed; a real run emits pytest output and takes seconds per item.
- A concurrent suite on the same host can push bounded-join concurrency tests (`process.join(20)`) past their limit and produce false failures. Re-run the timing-sensitive suite in isolation before reporting it as broken, and record both the loaded and isolated runs.

## Evidence table template

| Check | Command / job | Env + Python | Exit / conclusion | Counts | Log location |
|---|---|---|---|---|---|
