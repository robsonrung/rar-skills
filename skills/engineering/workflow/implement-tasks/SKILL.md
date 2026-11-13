---
name: implement-tasks
description: Execute an approved task queue with exact model approval, dependency scheduling, and integration review. Use when the user asks to implement approved tasks; implement-and-review handles each task.
disable-model-invocation: true
---

# Implement Tasks

Turn an approved queue into one verified change. Be a **thin conductor**: you own the model plan, scheduling, write ownership, dependency release, integration, and delivery. `implement-and-review` owns everything inside a task: its roles and contexts, review cycles, isolation, the implementer's brief, and evidence. Do not restate or override those rules here.

The input is the approved PRD and `tasks.md` from `to-tasks` under `.ai-workflow/work/<feature>/`, laid out as `shared/references/work-state.md` describes. A bare plan goes to `to-prd` and `to-tasks` first. One bounded task with a complete acceptance contract and no open product, security, contract, data, or dependency decision goes straight to `implement-and-review`.

## Plan

1. Read `tasks.md` and each task's `brief.md`. An open decision, missing access, a dependency cycle, or two tasks owning the same path without a merge plan blocks the affected tasks.
2. Pick the review mode. A new feature queue uses feature mode: mark tasks `critical` when they carry high risk or a shared contract, and defer the rest to one final review. Otherwise use task mode, where every task gets its own reviewer. An existing approved plan keeps its mode and routes.
3. Resolve each task's route with `python3 shared/scripts/model_routing.py resolve <route> --provider <host> [--risk high]`, giving `--risk high` only for a task that touches the invariants `policy.high_risk_triggers` names, never for a sensitive feature label. Add the integration or final reviewer, whose model differs from every author's. Read `.rar-skills/config.local.yaml` once, if present, as advisory input while forming the plan (`shared/references/local-config.md`); never reread it after approval.
4. Show the plan: for each task its roles with model, effort, and host route; the integration or final reviewer; the concurrency cap; the review-cycle limit; and the total call ceiling. Ask: **"Approve this plan, or specify changes."** A request to use defaults and run approves the unchanged resolved plan. Task approval, `--auto`, a saved preference, or silence is not model approval. When the user wants one decision for queue and models, show both together; the single response approves both.
5. Write the approved plan to the top of `tasks.md` with the user's response and the time. It is fixed from then on. A change to any model, effort, role, host route, or limit needs the affected rows approved again. An unavailable route blocks its own tasks; never swap in another model.

## Run

Keep **the ledger, not the transcript**: `tasks.md` plus the task reports are the ledger. Update a task's row before dispatch and after its result, and resume from them.

Each wave:

1. Take the `pending` tasks whose dependencies are released, up to the approved cap (default three). Without worktree isolation, run one writer at a time.
2. Enforce write ownership. Tasks that share a file, migration, interface, or security surface run one after another unless an approved merge plan names the overlap. A task stays owner of its paths until it is integrated.
3. Run each ready task through `implement-and-review` with the inherited approved routes and its `critical` or deferred class. **Hand off the path, not the payload**: the task folder, base revision, routes, and report path, never pasted bodies (`shared/references/handoff-contract.md`).
4. Integrate in dependency order. Release a dependent only on captured checks of the current combined source, never on a worker's success label: in task mode when the dependency is `accepted`, in feature mode when it is `implemented` and its checks pass on the combined source.

Use one persistent integration context, separate from every task role. A blocked task blocks its descendants, not unrelated work. Pause only the affected task when new evidence raises a material product, security, data-ownership, or irreversible-action decision; settle implementation facts from the repository.

## Finish

In feature mode, run the final feature review in `implement-and-review`'s `Feature policy` section; only that review accepts the tasks. In task mode, run `full-review` once on the combined change through the integration route, covering seams, shared contracts, migration order, and gaps in the task reviews. Either way, capture acceptance on the combined state. Reuse a task's evidence only while `capture_check.py stale` reports it current. Open P2 findings or skipped required checks keep the queue incomplete.

Deliver the verified local diff by default. Commit, push, or open a pull request (`open-pr`) only with explicit authorization; a configured remote grants none. Preserve unrelated changes and user-owned tasks, branches, and worktrees. Never start `models-consensus` on your own.

## Report

Write `report.md` in the feature folder and lead with the outcome: `complete`, `partial`, `blocked`, or `ceiling_hit`, with the local diff or the authorized delivery link. Then:

1. Each task's ID, status, dependencies, integration result, and acceptance evidence.
2. Roles with model, effort, host route, and the model each call reported.
3. Review scope, reviewed revision, and findings applied.
4. Residual findings not applied: ID, severity, path, evidence, impact, why not applied, and next action. A blocking finding keeps its task blocked. File tracker tickets only when authorized; a failed filing keeps the local record.
5. Assumptions, blocked decisions, and the next action.

The queue is complete only when every task is accepted, final acceptance passes, and no blocking finding remains. Use `capture-learning` for a reusable finding or `session-handoff` when work must resume.
