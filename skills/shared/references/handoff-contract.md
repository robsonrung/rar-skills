# Handoff Contract

Use this contract for an actual delegated step. A method or read-only lens applied
in the assigned role records its findings in the caller's existing artifact;
it needs no worker handoff. `implement-tasks`, `dynamic-harness`, and other
orchestration skills use this contract for their dispatched roles.

`run-state-contract.md` governs what a run records. This contract governs what it
passes. A delegated step writes a report and its entry in the existing run state.

## The rule

**Hand off the path, not the payload.**

An orchestrator that pastes a step's output into the next step's brief has re-absorbed everything delegation just bought. Inputs are file paths. Outputs are file paths. The only content that crosses back into the orchestrator's context is a short envelope naming those paths and the verdict.

This keeps each handoff bounded and recoverable:

1. The orchestrator's context grows by a fixed small amount per step, not by the size of the step's work.
2. Any step's reasoning survives a compaction, a crash, or a fresh thread, because it was written to disk rather than spoken into the transcript.
3. A worker reads the required sources by path and locator from a compact brief with no parent conversation history.

## The three artifacts

All three live in the run's own directory, beside its `run-state.json`:

```
<working-dir>/.ai-workflow/<skill>/<run-id>/[<unit-id>/]
  <NN>-<step>.brief.md     ← the orchestrator writes, the worker reads
  <NN>-<step>.report.md    ← the worker writes, the orchestrator cites
  run-state.json
```

`<unit-id>` is the per-slice / per-workstream namespace when a run has more than one (omit it when it does not). `<NN>` is the step's ordinal, so the directory listing reads in execution order.

### 1. Brief from orchestrator to worker

Keep the brief to one screen when possible. Include:

| Field | Content |
| --- | --- |
| `run_id` | The run this step belongs to |
| `run_state` | Path to `run-state.json` |
| `step` | `<NN>-<step>`, the same string the report and envelope use |
| Goal | What this step must produce, in one or two sentences |
| Inputs | Prior report, spec, slice contract, and diff paths with required sections or locators and source revisions. Reuse settled decision sources. |
| Constraints and non-goals | What the worker must not do (write scope, files it may not touch, decisions already made elsewhere) |
| Deliverable | The report doc's path, and the skill the worker invokes to produce it |
| Required verification | The commands whose output must appear under `Evidence` |
| Escalation | Return unresolved decisions to the orchestrator, which obtains any required user decision. Only an explicit user request can start `models-consensus`. |
| Model approval | Exact approved snapshot, route and scope fingerprints, model/runner/effort, controls, and allowed fallback. Nested skills consume it without re-resolution or new workers. |
| Budget | Remaining call and time limits plus the reserved call ID in the existing ledger. |
| Output contract | The envelope shape below, stated verbatim |

A brief that quotes a prior report's body instead of citing its path has broken the contract, whatever else it gets right.

For iterative work, pass the recorded task and role context ID as well as the
next input paths. Follow [host-model-execution.md](host-model-execution.md): start
each independent role in its own context, then reuse that role for later turns.
An implementer, reviewer, or interview respondent must not inherit another role's
private history. Keep artifacts even when native session reuse succeeds; they
support recovery if the session is lost.

### 2. Report from worker to disk

The worker writes it before returning. Seven fixed sections, in this order, present even when empty:

```markdown
# <NN>-<step>: <run-id>[/<unit-id>]

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

The sections are fixed so the _next_ brief can cite a heading (`…/04-implement.report.md#inputs-for-the-next-step`) rather than the whole file. That citation is what keeps the next worker's read small too.

### 3. Envelope from worker to orchestrator

The worker's final message, and the only thing that enters the orchestrator's context. Keep it under 15 lines:

```json
{
  "step": "05-verify",
  "unit": "T3",
  "status": "complete",
  "verdict": "pass",
  "report": ".ai-workflow/impl-review/20260731T0912Z-a3f9/T3/report.md",
  "artifacts": [
    ".ai-workflow/impl-review/20260731T0912Z-a3f9/T3/full-review.json"
  ],
  "next_inputs": ["2 residual findings, none blocking"],
  "blockers": []
}
```

`status` uses the run-state vocabulary (`complete`, `failed`, `ceiling_hit`, `awaiting_human`);
`verdict` uses the step's own. Reserve a call before one output-contract repair.
If its envelope is still unparseable, record `failed` and preserve the raw result.

## Orchestrator obligations

1. **Write the brief and reserve the call before dispatch.** Bind the selected snapshot, source revisions, write scope, and remaining budget. Recovery uses the same ledger and ceilings.
2. **Read the envelope, not the report.** Read report details when needed for routing, integration, or a conflict decision.
3. **Record both paths** in the run state's `steps` entry, so a resumed run recovers the reasoning and not just the phase.
4. **Reuse only current, complete evidence.** A report path is not a completion signal. Check its status, acceptance evidence, input scope, and output revision before releasing dependent work. Recheck changed inputs or integration results; do not repeat valid work without a reason.
5. **Degrade honestly.** With no subagent tool available, use inline execution only if it is an approved route. Otherwise obtain approval for the route change. Keep the brief and report, and state that no worker was spawned. The file-based handoff is the part that survives; the isolation is the part that is host-dependent.

## Verification with the fresh-reader test

Apply the **cold-start test** when handoff recovery is evaluated: can a fresh
reader perform the next step from the report and its named sources? Fix missing
next-step inputs. A dispatched evaluation needs an approved route and reserved
budget; adopting this contract alone does not authorize it.
