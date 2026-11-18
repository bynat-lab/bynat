# Uncommitted-Work Audit and Recovery

Use when asked to audit everything in the working tree, recover interrupted or redirected
tasks, or decide whether the accumulated uncommitted changes are acceptable. The goal is a
verdict backed by repository evidence, not a summary of what was attempted.

## 1. Reconstruct the task history first

Read the attachments and prior instructions before touching the tree; they are the
authoritative task text. Build a table of every task, every follow-up that modified or
expanded it, and every item that was deferred, interrupted, or superseded. Label each row
Completed / Partially completed / Interrupted / Intentionally deferred / Superseded. Do not
invent tasks, and do not silently treat an earlier task as finished because a later prompt
redirected attention.

## 2. Inventory against the last commit

```bash
git status --short                 # includes renames as R and untracked as ??
git ls-files --others --exclude-standard
git diff --stat -M                 # -M so renames are not counted as add+delete
git diff -M -- <path>              # per-file content of a moved or edited file
```

Group the inventory by production code, tooling, documentation, tests, and artifacts. Count
renames separately from modifications. A file listed as `R` with no content change is a
pure move; `RM` means the move also edited content, so read it. Check for stray leftovers
from interrupted operations: cache directories, scratch files, `.orig`/`.rej`, duplicated
old filenames still present next to their replacements.

## 3. Trace requirements to evidence

For each requirement, name the implementing symbol/file and the test that proves it. A
requirement with no named test is unverified, however green the suite is. Recompute counts
with a reproducible command rather than trusting a prior report or document.

## 4. Re-read normative documents end to end

A rule rewritten after user pushback often leaves a stale heading, a stale table-of-contents
anchor, or a stale example elsewhere in the same document. Grep the whole repository for the
superseded wording and for pre-move paths, including generated or tracked artifacts and
tooling manifests. Search the production package for statements the change made false.

## 5. Probe behavior independently

Do not accept the test suite as the only evidence. Build a scratch probe outside the repo that
compares the two APIs or two dependency versions on the edge calls, and require identical
outcomes. Edge calls that no test covers are where silent argument capture, silent
argument-drop, and accept/reject divergence survive. Run the probe on every interpreter that
carries the relevant dependency versions.

## 6. Repair, then verify

Repair only confirmed defects. Do not expand the audit into a general quality or
architecture refactor the request excluded. After repairing, re-run the focused tests, the
full suite on each available dependency version, lint, typing, the docs-drift check, and
`git diff --check`; confirm the out-of-scope artifacts and the changelog were not touched.

## 7. Report

History table, change inventory, requirement-to-evidence matrix, confirmed incomplete work,
repairs performed, remaining issues, final repository state with exact command output, and
an explicit acceptance decision. Name limitations individually rather than folding them into
"complete"; a documented limitation is not automatically an accepted requirement, and an
out-of-scope item is not a blocker.
