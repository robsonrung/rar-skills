# Handoff Contract

Canonical, agent-facing rules for delegating one step of a long run to a subagent or a separate thread, and for what crosses back. Used by `ship` (one station per subagent), `dynamic-harness` (manager mode workstreams), and any orchestration skill that keeps its own context thin. Each skill points here and keeps inline only its own station/workstream names.

The sibling contract is `run-state-contract.md`: that one governs what a run *records*, this one governs what a run *passes*. A step that is delegated writes both — a report doc here, and its `steps` entry there.

## The rule

**Hand off the path, not the payload.**

An orchestrator that pastes a step's output into the next step's brief has re-absorbed everything delegation just bought. Inputs are file paths. Outputs are file paths. The only content that crosses back into the orchestrator's context is a short envelope naming those paths and the verdict.

Three consequences, all load-bearing:

1. The orchestrator's context grows by a fixed small amount per step, not by the size of the step's work.
2. Any step's reasoning survives a compaction, a crash, or a fresh thread, because it was written to disk rather than spoken into the transcript.
3. A worker reads exactly the prior work it needs, named file by file, instead of inheriting a forked context full of work it does not need. Never fork a bloated orchestrator context — a clean worker seeded by a compact brief beats a fork carrying everything already spent.

## The three artifacts

All three live in the run's own directory, beside its `run-state.json`:

```
<working-dir>/.ai-workflow/<skill>/<run-id>/[<unit-id>/]
  <NN>-<step>.brief.md     ← the orchestrator writes, the worker reads
  <NN>-<step>.report.md    ← the worker writes, the orchestrator cites
  run-state.json
```

`<unit-id>` is the per-slice / per-workstream namespace when a run has more than one (omit it when it does not). `<NN>` is the step's ordinal, so the directory listing reads in execution order.

### 1. Brief — orchestrator → worker

One screen when possible. Ten fields:

| Field | Content |
|---|---|
| `run_id` | The run this step belongs to |
| `run_state` | Path to `run-state.json` |
| `step` | `<NN>-<step>` — the same string the report and envelope use |
| Goal | What this step must produce, in one or two sentences |
| Inputs | **Paths only** — prior report docs, the spec, the slice contract, the diff range. Name the section of a report when only one section is relevant. |
| Constraints and non-goals | What the worker must not do (write scope, files it may not touch, decisions already made elsewhere) |
| Deliverable | The report doc's path, and the skill the worker invokes to produce it |
| Required verification | The commands whose output must appear under `Evidence` |
| Escalation | Where an unresolvable decision goes (for the autonomous half: `models-consensus`, never the user) |
| Output contract | The envelope shape below, stated verbatim |

A brief that quotes a prior report's body instead of citing its path has broken the contract, whatever else it gets right.

### 2. Report — worker → disk

The worker writes it before returning. Seven fixed sections, in this order, present even when empty:

```markdown
# <NN>-<step> — <run-id>[/<unit-id>]

## Verdict
One line: the step's outcome in its own vocabulary (`proceed` / `revise`, `pass` / `fail`, `complete` / `blocked`).

## What ran
Which skill, which seats, which mode. Enough to tell a reader what to re-run.

## Evidence
Commands and their results. Actual output, not a claim about output.

## Decisions & assumptions
Every call taken without asking, with its rationale. This is what the PR's decision log is built from.

## Findings not applied
Anything raised and deliberately not acted on, with why. Never dropped silently.

## Inputs for the next step
The specific facts the next step needs. Written to be lifted, not re-derived.

## Artifacts
Paths to everything else this step produced.
```

The sections are fixed so the *next* brief can cite a heading (`…/04-implement.report.md#inputs-for-the-next-step`) rather than the whole file. That citation is what keeps the next worker's read small too.

### 3. Envelope — worker → orchestrator

The worker's final message, and the only thing that enters the orchestrator's context. Keep it under 15 lines:

```json
{ "step": "05-verify",
  "unit": "T3",
  "status": "complete",
  "verdict": "pass",
  "report": ".ai-workflow/ship/20260731T0912Z-a3f9/T3/05-verify.report.md",
  "artifacts": [".ai-workflow/ship/20260731T0912Z-a3f9/T3/full-review.json"],
  "next_inputs": ["2 residual findings, none blocking"],
  "blockers": [] }
```

`status` uses the run-state vocabulary (`complete`, `failed`, `ceiling_hit`, `awaiting_human`); `verdict` uses the step's own. A worker that returns prose instead of an envelope is re-prompted **once** with the output contract restated, then recorded as `failed` — an unparseable return is a step that did not report, not a step to interpret.

## Orchestrator obligations

1. **Write the brief before dispatching.** A verbal assignment leaves no artifact for a resumed run to re-dispatch from.
2. **Read the envelope, not the report.** Open a report body only when a decision the orchestrator itself must make depends on the detail — routing, integration, or a conflict between two steps. Reading every report to "stay informed" is the failure this contract exists to prevent.
3. **Record both paths** in the run state's `steps` entry, so a resumed run recovers the reasoning and not just the phase.
4. **Never re-run a step whose report exists** unless its `status` says it failed. The report is the completion signal.
5. **Degrade honestly.** With no subagent tool available, run the step inline — but still write the brief and the report, and say in the final report that no worker was spawned. The file-based handoff is the part that survives; the isolation is the part that is host-dependent.

## Verification — the fresh-reader test

Once per skill that adopts this contract: hand a report doc and nothing else to a fresh context and ask it to perform the next step. If it has to ask what happened earlier, the report's `Inputs for the next step` section is doing its job badly — fix the section, not the reader.
