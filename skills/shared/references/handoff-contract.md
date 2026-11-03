# Handoff Contract

What a delegated step passes between the orchestrator and a worker. `implement-tasks`, `peer-sessions`, and other orchestration skills use it for dispatched roles; a method or lens applied in the current role needs no handoff. What a run records is in [run-state-contract.md](run-state-contract.md).

## The rule

**Hand off the path, not the payload.** Inputs are file paths, outputs are file paths, and only a short envelope naming those paths and the verdict crosses back into the orchestrator's context. An orchestrator that pastes a step's output into the next brief re-absorbs everything delegation bought. Written to disk, a step's reasoning also survives a compaction, a crash, or a fresh thread.

The artifacts live beside the run's `run-state.json`:

```
<working-dir>/.ai-workflow/<skill>/<run-id>/[<unit-id>/]
  <NN>-<step>.brief.md     ← the orchestrator writes, the worker reads
  <NN>-<step>.report.md    ← the worker writes, the orchestrator cites
  run-state.json
```

`<unit-id>` namespaces a slice or workstream when there is more than one; `<NN>` orders steps.

## Brief

Use **selection over compression**: send what the step needs, not a summary of the parent conversation. Keep it to about a screen:

- `run_id`, the `run-state.json` path, and the `<NN>-<step>` name;
- the goal, in one or two sentences;
- inputs as paths with section locators and source revisions: prior reports, spec, task contract, diff;
- constraints and non-goals: write scope, files not to touch, decisions already made;
- the deliverable: the report path and the skill that produces it;
- the verification commands whose output must appear under Evidence;
- the approved route and the reserved call ID;
- escalation: unresolved decisions return to the orchestrator, and only the user can start `models-consensus`;
- the envelope shape below, verbatim.

Keep each complete worker input under **24,000 UTF-8 bytes**. When it is over, shorten derived notes, link evidence, or split independent work; never cut acceptance rules. A route may raise the limit with `context_budget: {"max_bytes": 32000, "reason": "..."}`. `context_packet.py` enforces this and catches drift:

```bash
python3 <shared-dir>/scripts/context_packet.py prepare \
  --brief <brief.md> --sources <sources.json> --output <brief.md.packet.json>
python3 <shared-dir>/scripts/context_packet.py verify --packet <brief.md.packet.json>
python3 <shared-dir>/scripts/context_packet.py measure --input <complete-worker-input.md>
```

`sources.json` lists `path`, `authority` (`decision`, `evidence`, or `superseded`), and `locator`, with at least one current decision. A superseded source is history, not instruction. When a decision changes, write a new brief and packet; never overwrite old evidence. Bytes are not tokens, so don't claim token savings from them.

Each independent role starts with no parent history. Repairs and rechecks go to the same role context with only the changed facts and finding IDs; a fresh or reconstructed context gets the full contract. Context IDs live in **the ledger, not the transcript** ([host-model-execution.md](host-model-execution.md)).

## Report

The worker writes it before returning, with seven fixed sections in this order, present even when empty:

1. `## Verdict`: one line in the step's own vocabulary.
2. `## What ran`: skill, seats, mode.
3. `## Evidence`: commands and their actual output.
4. `## Decisions & assumptions`: every call taken without asking, with its reason.
5. `## Findings not applied`: what was raised and not acted on, and why.
6. `## Inputs for the next step`: facts written to be lifted, not re-derived.
7. `## Artifacts`: paths to everything else produced.

Fixed headings let the next brief cite one section (`…/04-implement.report.md#inputs-for-the-next-step`) instead of the whole file.

## Envelope

The worker's final message, under 15 lines, and the only thing that enters the orchestrator's context:

```json
{
  "step": "05-verify",
  "unit": "T3",
  "status": "complete",
  "verdict": "pass",
  "report": ".ai-workflow/impl-review/20260731T0912Z-a3f9/T3/report.md",
  "artifacts": [".ai-workflow/impl-review/20260731T0912Z-a3f9/T3/full-review.json"],
  "next_inputs": ["2 residual findings, none blocking"],
  "blockers": []
}
```

`status` uses the run-state vocabulary (`complete`, `failed`, `ceiling_hit`, `awaiting_human`); `verdict` uses the step's own. Reserve a call before one output repair; if the envelope is still unparseable, record `failed` and keep the raw result.

## Orchestrator obligations

1. Write the brief and reserve the call before dispatch.
2. Read the envelope, and open the report only when routing, integration, or a conflict needs it.
3. Record the brief and report paths in the run state's `steps` entry.
4. Treat a report as evidence, not completion: check its status, acceptance evidence, and revisions before releasing dependent work.
5. Without a subagent tool, run inline only on an approved route, keep the brief and report, and say no worker was spawned.

## Fresh-reader test

Apply the **fresh-reader test** (the **cold-start test**) when checking recovery: can a reader with no history do the next step from the report and its named sources alone? Fix whatever input is missing.
