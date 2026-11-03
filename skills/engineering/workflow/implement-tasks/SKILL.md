---
name: implement-tasks
description: Execute an approved task queue with exact model approval, dependency scheduling, and integration review. Use when the user asks to implement approved tasks; implement-and-review handles each task.
disable-model-invocation: true
---

# Implement Tasks

Turn an approved queue into one verified change. Be a **thin conductor**: you own the model plan, scheduling, write ownership, dependency release, integration, and delivery. `implement-and-review` owns everything inside a task: its roles and contexts, review cycles, isolation, the implementer's brief, and evidence. Do not restate or override those rules here.

The input is the approved PRD and canonical queue from `to-tasks` under `.ai-workflow/work/<feature-slug>/`. A bare plan goes to `to-prd` and `to-tasks` first. One bounded task with a complete acceptance contract and no open product, security, contract, data, or dependency decision goes straight to `implement-and-review`.

## Plan

1. Check the queue with `shared/scripts/task_queue.py approval-inputs` and each task's gates with `shared/scripts/gate_contract.py`, as [references/queue-controller.md](references/queue-controller.md) describes. Open requirements, missing access, or unowned write paths block the affected tasks.
2. Pick the review mode. A new feature queue binds one `review_policy` in both `queue.json` and the routing plan, per `shared/references/feature-review.md`; check it with `shared/scripts/feature_review.py validate`. Routine tasks are then deferred to one final feature review, and critical ones keep a task reviewer. Without a policy, every task gets its own reviewer. An existing approved plan keeps its mode and routes.
3. Resolve the routes. Give each task its route, risk, and a `risk_reason` drawn from the invariants it touches, not a sensitive feature label, and run `python3 shared/scripts/model_routing.py resolve-batch --tasks <tasks.json> [--review-mode feature]`. Add the integration or final reviewer, whose model differs from every author's. Read `.rar-skills/config.local.yaml` once, if present, as advisory input while forming the plan (`shared/references/local-config.md`); never reread it after approval.
4. Show the plan: for each task its roles with model, effort, and host route; the integration or final reviewer; the concurrency cap; the review-cycle limit; and the total call ceiling. Ask: **"Approve this plan, or specify changes."** A request to use defaults and run approves the unchanged resolved plan. Task approval, `--auto`, a saved preference, or silence is not model approval. When the user wants one decision for queue and models, show both together and record the single response as two gates, `task_queue_approval` and `model_plan_approval`.
5. Save the approved plan as `routing-plan.json` with the response reference and time, and check it with `shared/scripts/routing_plan.py digests` (schema: `shared/references/implementation-routing-plan.schema.json`). Approval is reused on resume while scope and routes are unchanged; a new context ID needs none.

A change to any model, effort, role, transport, or limit needs the affected rows approved again. An unavailable route blocks its own tasks; never swap in another model.

## Run

Keep **the ledger, not the transcript**: `routing-plan.json` and `run-state.json` under `.ai-workflow/impl-review/<session>/`, per `shared/references/run-state-contract.md`. Reserve every call with `shared/scripts/run_state.py reserve` before dispatch and record it with `complete` after; a native role's receipt comes from `shared/scripts/native_completion.py`.

Each wave:

1. Run `task_queue.py schedule` and take only its `ready` tasks, up to the approved cap (default three). Without worktree isolation, run one writer at a time.
2. Enforce write ownership. Tasks that share a file, migration, interface, or security surface run one after another unless an approved merge plan names the overlap. A task with a pending call or unfinished integration keeps its paths.
3. Run each ready task through `implement-and-review` with the inherited approved routes and policy class. **Hand off the path, not the payload**: the task contract path, scope, base revision, routes, and report path, never pasted bodies (`shared/references/handoff-contract.md`).
4. Integrate in dependency order. Release a dependent only on integration evidence for the current combined source, never on a worker's success label, as [references/feature-orchestration.md](references/feature-orchestration.md) describes.

Use one persistent integration context, separate from every task role. A failed task blocks its descendants, not unrelated work. Pause only the affected task when new evidence raises a material product, security, data-ownership, or irreversible-action decision; settle implementation facts from the repository.

## Finish

With a feature policy, run the final feature review in `implement-and-review`'s `Feature policy` section; only that gate accepts the tasks. Without one, run `full-review` once on the combined change through the integration route, covering seams, shared contracts, migration order, and gaps in the task reviews. Either way, capture acceptance on the combined state, reusing a task result only while its code, dependencies, environment, and contract still match, and require `shared/scripts/review_evidence.py verify` to return `ready` (`shared/references/review-evidence.md`). Open P2 findings or skipped required checks keep the queue incomplete.

Deliver the verified local diff by default. Commit, push, or open a pull request (`open-pr`) only with explicit authorization; a configured remote grants none. Preserve unrelated changes and user-owned tasks, branches, and worktrees. Never start `models-consensus` on your own.

## Report

Write `report.md` in the run directory and lead with the outcome: `complete`, `partial`, `failed`, or `ceiling_hit`, with the local diff or the authorized delivery link. Then:

1. Each task's ID, status, dependencies, integration result, and acceptance evidence.
2. Roles with model, effort, host route, and whether the serving model was verified.
3. Review scope, reviewed revision, and findings applied.
4. Residual findings not applied: ID, severity, path, evidence, impact, why not applied, and next action. A blocking finding keeps its task blocked. File tracker tickets only when authorized; a failed filing keeps the local record.
5. Assumptions, blocked decisions, and the next action.

The queue is complete only when every task is accepted, final acceptance passes, and no blocking finding remains. Use `capture-learning` for a reusable finding or `session-handoff` when work must resume.
