# Handoff Contract

What crosses between an orchestrator and a worker it dispatches. Where the files live is in [work-state.md](work-state.md). A method or lens applied in the current role needs no handoff.

## The rule

**Hand off the path, not the payload.** Inputs are file paths, outputs are file paths, and only a short envelope naming those paths and the verdict crosses back into the orchestrator's context. An orchestrator that pastes a step's output into the next brief re-absorbs everything delegation bought. Written to disk, a step's reasoning also survives a compaction, a crash, or a fresh thread.

## Brief

Send what the step needs, not a summary of the parent conversation. Keep it to about a screen:

- the goal, in one or two sentences;
- inputs as paths with section locators: the task's `brief.md`, the PRD, prior reports, the diff;
- the base revision, write scope, files not to touch, and decisions already made;
- the deliverable: the report path, and the checks whose captured output must appear under Evidence;
- the approved route;
- escalation: unresolved decisions return to the orchestrator, and only the user can start `models-consensus`;
- the envelope shape below.

Keep each complete worker input under **24,000 UTF-8 bytes**; when it is over, link evidence or split independent work, never cut acceptance rules. `shared/scripts/context_packet.py measure --input <file>` checks the size. Each independent role starts with no parent history; repairs and rechecks go to the same role context with only the changed facts and finding IDs.

## Report

The worker writes it before returning, with these sections in this order, present even when empty:

1. `## Verdict`: one line in the step's own vocabulary.
2. `## What ran`: skill, roles, models requested and reported, mode.
3. `## Evidence`: the captured evidence files and their results.
4. `## Decisions & assumptions`: every call taken without asking, with its reason.
5. `## Findings not applied`: what was raised and not acted on, and why.
6. `## Inputs for the next step`: facts written to be lifted, not re-derived.
7. `## Artifacts`: paths to everything else produced.

## Envelope

The worker's final message, under 15 lines, and the only thing that enters the orchestrator's context:

```json
{"task": "T3", "status": "implemented", "verdict": "ready",
 "report": ".ai-workflow/work/auth/T3-session-expiry/report.md",
 "next_inputs": ["2 residual findings, none blocking"], "blockers": []}
```

`status` uses the work-state vocabulary; `verdict` uses the step's own. Open the report only when routing, integration, or a conflict needs it. A report is evidence, not completion: check its status and captured evidence before releasing dependent work.

## Fresh-reader test

Apply the **fresh-reader test** (the **cold-start test**) when checking recovery: can a reader with no history do the next step from the report and its named sources alone? Fix whatever input is missing.
