---
name: dynamic-harness
description: Plan and run a bounded worker fleet for a complex task. Use when the user explicitly requests delegation, parallel work, a tournament, or a managed mission.
disable-model-invocation: true
---

# Dynamic Harness

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Use this skill for work that benefits from explicit delegation. It is not the default for a normal task. The **smallest coherent shape** is one local worker or one bounded check; add agents only when independent work reduces time or improves evidence.

## Outcome

Deliver a verified result with clear ownership, evidence, and a stop condition. For work that spans a context window, a restart, or several batches, keep a durable ledger.

## Choose the Pattern

| Need | Pattern |
| --- | --- |
| Choose the right route or specialist | Classify and act |
| Inspect independent files, claims, or hypotheses | Fan out and synthesize |
| Challenge a high-impact result | Adversarial verification |
| Generate options then rank them | Generate and filter or tournament |
| Search an unknown amount of work | Loop until done |

Use one pattern unless a dependency requires two. Keep the main agent on the critical path while independent workers run.

## Prepare the Brief

Before delegation, write a short brief with the objective, success criteria, selected pattern, worker scopes, verification method, stop condition, ceiling, and output path. Give each worker:

```text
Role:
Scope:
Goal:
Allowed actions:
Write scope:
Evidence required:
Done condition:
```

Workers receive only the context they need. Assign disjoint write scopes for code changes. Use a worktree when parallel edits or an experiment could collide. Keep untrusted content away from privileged actions.

## Run the Work

1. Resolve models with `shared/references/task-shaped-model-routing.md` and native delegation with `shared/references/host-model-execution.md`. Prefer native tools for supported host models and external runners for other selected routes. If no route can meet an exact model assignment, report the affected route; serial local work cannot stand in for a different approved model.
2. Start only independent workers. Use a verifier for high-impact outputs and give it the evidence and rubric, not the worker's conclusion.
3. Inspect every worker result and changed path before integration. Mark each material claim `verified`, `refuted`, or `unresolved`.
4. Keep external side effects and destructive operations in the main workstream unless the user has authorized them.
5. Synthesize evidence, preserve material dissent, and run the nearest safe verification command after code changes.

## Loops and Budgets

Before a repeated batch, define **three exits**: a success signal, an escalation condition, and a hard ceiling on batches and workers. Record the counters before each batch. **The model never decides the retry**.

Default scale is one to three workers for a quick check, then a representative slice before expanding. Ask for a budget only when the requested work can materially consume paid services, production access, or a large fleet.

## Manager Mode

Use manager mode only for a long mission with several workstreams or a likely restart. The manager owns routing, integration, and the final report. Workers own exploration and bounded implementation.

Create a mission directory before the first worker. Set `SKILL_DIR` to the absolute directory containing this file in the same shell call:

```bash
SKILL_DIR="<absolute path of this dynamic-harness directory>"; python3 "$SKILL_DIR/scripts/start_mission.py" --title "short task title"
```

Keep the brief, worker reports, and `run-state.json` under that mission directory. Progress lives in **the ledger, not the transcript**. On resume, read the run state and keep completed steps and side effects **already decided**. Reconcile pending calls and reuse the recorded context for further turns of the same role. Close only confirmed unused workers owned by this run; dispatch only remaining work.

If the host cannot create a separate thread, write a handoff file and its seed prompt. Do not claim that a thread exists. Hand off the path, not the payload.

## Report

Report the selected pattern, worker count and scopes, verified outcome, evidence, unresolved risks, and any ledger or handoff path. A mission report also names its identifier and remaining worker state.
