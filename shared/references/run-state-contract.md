# Run State Contract

Canonical, agent-facing rules for the durable run state shared by every long-running orchestration skill (`ship`, `implement-and-review`, `implement-feature`, `dynamic-harness`, `models-consensus`). Each skill's SKILL.md points here and keeps inline only its own field names and ceilings.

A long run's progress lives in **the ledger, not the transcript**. Anything the run must know after a crash, a compaction, or a restart is written to this file; anything held only in the message history is lost with it.

## Location

```
<working-dir>/.ai-workflow/<skill>/<run-id>/run-state.json
```

Same tree as the existing `.ai-workflow/runner-jobs/`, `.ai-workflow/consensus/`, and `.ai-workflow/roundtable/` layouts (gitignored). `<run-id>` is unique per run — a UTC timestamp plus a short random suffix. Never reuse a fixed path across runs: a single fixed path turns two concurrent runs into one corrupted run.

This is the path for a skill adopting the contract fresh. A skill that already has an established state location keeps it (`models-consensus` stays at `.ai-workflow/consensus/{session_id}.json`, `implement-and-review` extends its `launch-manifest.json`) — what this contract fixes is the *shape and the rules*, not the filename. Two state files for one run is worse than one file in an unusual place.

## Shape

```json
{
  "run_id": "20260728T1402Z-auth-slice-a3f9",
  "skill": "implement-and-review",
  "status": "running",
  "phase": "backend_review",
  "started_at": "2026-07-28T14:02:11Z",
  "updated_at": "2026-07-28T14:37:52Z",
  "attempts":     { "backend_fix_cycle": 2 },
  "ceilings":     { "max_cycles": 3, "max_agents": 12, "deadline": "2026-07-28T16:00:00Z" },
  "gates":        [ { "gate": "phase0_plan_approval", "decision": "approved", "decided_at": "2026-07-28T14:04:00Z" } ],
  "side_effects": [ { "key": "pr:feat-auth", "done_at": "2026-07-28T15:10:03Z" } ],
  "steps":        [ { "step": "backend_review", "result": "ok", "artifact": ".ai-workflow/impl-review/a3f9/be-review-2.json" } ]
}
```

`status` is one of: `running`, `awaiting_human`, `complete`, `failed`, `ceiling_hit`, `cancelled`. These are the only values; a resume protocol that branches on `status` branches on this set.

Extra skill-specific keys are fine. The eight above are the contract.

## The rules

### Attempts — the model never decides the retry

Every bounded loop keeps its count in `attempts` under a name matching the loop.

1. Read `attempts.<loop>` before the attempt. Absent means `0`.
2. Increment and write it back **before** the attempt, never after. A crash mid-attempt still counts as an attempt; counting afterwards makes a crashing step retry forever.
3. Compare against the matching entry in `ceilings` before starting. At or over the bound, take the escalation route — do not start the attempt and do not re-reason about whether the bound applies.

A bound stated only in prose is not a bound. If nothing outside the model counts the attempts, the loop is unbounded regardless of what the prose says.

### Termination — three exits

Every run declares **three exits** and records which one it took in `status`:

- **success** → `complete`
- **retries exhausted** → `failed`, with the exhausted loop named in the final report
- **hard ceiling** → `ceiling_hit`, with the ceiling named

A ceiling lives in `ceilings` and is counted without the model's cooperation — cycles, dispatched agents, a wall-clock deadline. When a run can consume many agents, long commands, paid APIs, or production data, ask the user for the bound and record the answer as a gate.

### Gates — an approval that survives a restart

A human decision recorded only in conversation is gone after a restart: the run either re-asks (annoying) or proceeds as if approved (dangerous). Append to `gates` when the user decides, then set `status` back to `running`.

While waiting, `status` is `awaiting_human`. On resume, a gate already present in `gates` is **already decided** — do not re-ask. A gate absent from `gates` was never granted, whatever the transcript appears to say.

### Side effects — decide, then execute

Separate the decision from the act. Deciding is safe to replay; acting is not.

Before any write outside the run — a commit, a merge, a PR, a ticket, a message, a deploy — append its stable key to `side_effects`, then perform it. At the top of any step that could replay, check `side_effects` for the key and skip if present. Write the key first: a crash lands between the record and the effect either way, and recording first means the replay skips rather than duplicates.

Stable keys are derived from the work, not from a counter: `pr:<branch>`, `commit:<slice-id>`, `ticket:<finding-id>`.

### Steps — the replay trace

Append one entry per completed step: the step name, its result, and the path to its artifact. This is what answers "what ran, in what order, and where is the output" after the run is over. Append; never rewrite history.

A step that was **delegated** records its `brief` and `report` paths alongside `result` (shapes in `handoff-contract.md`), so a resumed run recovers the step's reasoning and not only its name. Those two paths are also the completion signal: a step whose report exists is done, and is re-dispatched only when its `result` says it failed.

### Cadence

Write after every step boundary, every attempt increment, every gate decision, and every side-effect key. Update `updated_at` on each write.

## Resume

At the start of a run, if a `run-state.json` exists for the target run id with `status` not `complete`:

1. Load it. Do not restart from the beginning.
2. Resume at `phase`, with `attempts` intact — a crash does not reset a counter.
3. Skip every step already in `steps` and every effect already in `side_effects`.
4. Treat every gate in `gates` as already decided.

## Verification — the crash-resume test

A resume path that was never exercised does not work. Once per skill that adopts this contract, kill a run mid-flight, restart it, and assert three things: it resumes at the right `phase`, `attempts` survived, and no entry in `side_effects` executed twice. This is a required check, not an optional one.
