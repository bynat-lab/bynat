# Refreshing the bynat Graphify graph

Use when a task asks to refresh `graphify-out/` after repository changes. The artifacts are tracked in git, so a refresh is a normal repository change; the graph represents structure, not behavior.

## Artifacts and their roles

| File | Role |
| --- | --- |
| `graph.json` | Nodes, edges, communities, source files/locations |
| `.graphify_analysis.json` | Communities, cohesion, hubs, surprises, review questions |
| `.graphify_labels.json` / `.sig` | Node id-to-label map and its signature |
| `manifest.json` | Per-file mtime + AST hash used to detect changes |
| `graph.html` | Interactive visualization |
| `GRAPH_REPORT.md` | Human summary; carries the persistent brand/refresh instructions |
| `build_graph_html.js` | Custom builder hook; re-applies brand theme and report section |

`GRAPH_REPORT.md` records the commit it was built from; compare that to `git rev-parse HEAD` before assuming staleness.

## Documented workflow

Run from the repository root with the `graphify` CLI:

```bash
graphify update .
graphify cluster-only      # optional: recompute communities only
graphify export html       # optional: regenerate the HTML view
```

The exporter auto-detects and runs `graphify-out/build_graph_html.js` via Node.js on `update`/`export html`. If `graph.html` or `GRAPH_REPORT.md` is ever overwritten, `node graphify-out/build_graph_html.js` restores the brand theme and report instructions.

The Graphify CLI is user-installed. Do not install it (or any substitute) unprompted; if it is missing, report the exact blocker and stop.

## Refresh procedure

1. Snapshot the current `graphify-out/` to a scratch directory outside the repository and record `git rev-parse HEAD` plus the report's built-from commit.
2. Run `graphify update .` from the repository root.
3. Compare old vs new: `manifest.json` for changed/deleted files, `graph.json` for added/removed nodes and edges and community assignments, `.graphify_analysis.json` for cohesion/hub/question changes, and `GRAPH_REPORT.md` summary counts.
4. Report actual differences only. A parameter-signature or behavior-only change usually produces no structural graph difference; do not manufacture one. Any real difference may reflect commits between the report's built-from commit and current `HEAD`, not the change being tested.

## Constraints

- Never hand-edit Graphify artifacts to fabricate a difference.
- Do not claim the graph was refreshed when the CLI could not run; state the blocker.
- Keep generated artifacts consistent with the repository: do not commit a graph built from a different checkout.
