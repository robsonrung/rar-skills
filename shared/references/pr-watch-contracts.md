# PR-watch contracts (for the future `watch-pr` skill)

Contract-level material salvaged ahead of the deferred `pr-snapshot` engine (see the plan's Deferred engines gates: CI coverage, named owner, fork-vs-sync drift plan, demonstrated need). A future `watch-pr` skill implements against these contracts; the debugging skills already speak the return vocabulary below.

## Delegate return contract (CI-failure delegate)

A watch loop delegates CI failures to the debugging skill in pipeline mode and parses exactly this status vocabulary (must stay identical to systematic-debugging's pipeline-mode return — do not invent new states):

```json
{
  "status": "fixed-and-pushed | diagnosed-no-fix | flaky-infra | needs-human",
  "summary": "<one line>",
  "root_cause": "<causal chain, brief>",
  "changed_files": ["..."],
  "head_sha": "<sha after push, when fixed-and-pushed>",
  "residuals": [ { "title": "...", "decision_context": "...", "thread": "<url|null>" } ]
}
```

## Watch-loop state contract (essentials)

- **Detector, not agent:** a cheap deterministic background change-detector polls (fetch→diff on an interval, no agent tokens) and emits one wake line only on actionable change (unresolved threads, failed CI, branch currency) or a stop condition (terminal / blocked / needs-human / merge-ready-after-settle / max-runtime / superseded). The agent backgrounds the detector and waits with the harness's background-and-wake capability (Claude Code: background Bash + Monitor) — the loop stays in-session so mid-run decisions (declined nits, user steering) survive.
- **State path:** `<scratch-root>/watch-pr/<host>-<owner>-<repo>-<pr>/state.json` — the `<host>` segment is load-bearing (GitHub Enterprise: two PRs sharing `owner/repo#N` on different hosts must not share state). One writer under a file lock.
- **Idempotent ticks:** claim→act→confirm dedup so a crashed tick never double-acts; after any mutation, re-snapshot at the start of the next tick, not mid-tick.
- **Watcher ownership:** latest-valid-watcher-wins with a generation counter carried on wakes and snapshots; a stale wake is discarded against a fresh snapshot.
- **Settle window:** merge-ready is declared only after a quiet settle period (~5 min default), not on the first green poll.
- **Trajectory facts (deterministic, never labeled by the watcher):** `recurring_checks`/`check_recur_max` (failed → cleared → failed again on a *new* head; same-head flapping excluded), `unresolved_trend` + `new_threads_this_tick`, `stream_alternations` (ci↔review bouncing), `heads_since_progress`. The *leaf* (debug/resolve delegate) judges convergence from these; the anti-cry-wolf line: progressive failure migration (A fixed → B appears once → done) is ordinary repair — keep fixing; oscillation (the same check returns after a fix aimed at it, defects cycle, fix size grows superlinearly) is non-convergence — park with a decision_context.
- **Success means:** every check terminal and none failing (at least one observed — an empty rollup is "CI hasn't started", not success), actionable backlog empty, mergeability certain and clean. Budget defaults: ~3 CI fix rounds per head-lineage, overall time cap; on exhaust, still-red checks become residuals.

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
