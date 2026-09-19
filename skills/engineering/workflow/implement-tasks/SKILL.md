---
name: implement-tasks
description: Execute an approved task queue with exact model approval, native-first role sessions, dependency scheduling, and integration review. Use when the user asks to implement approved tasks; implement-and-review handles each task.
disable-model-invocation: true
---

# Implement Tasks

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Turn an approved queue into a verified change. Be a **thin conductor**: own model selection, scheduling, integration, and delivery. `implement-and-review` owns each task's implementation, focused review, and acceptance evidence.

The sequence is `interview-me` → `to-prd` → `to-tasks` → `implement-tasks`. Receive the approved PRD and task queue under `.ai-workflow/work/<feature-slug>/`. A complete single task uses the same model approval and skips graph scheduling. Missing product decisions return to the appropriate earlier stage.

## Select the current phase

| Phase | Required work and reference |
| --- | --- |
| Prepare or revise a model plan | Read [references/model-plan.md](references/model-plan.md). Validate the approved queue, dependencies, input hashes, routes, native capabilities, role-session strategy, and available transports; produce the exact preview. |
| Schedule and integrate approved tasks | Read [references/feature-orchestration.md](references/feature-orchestration.md). Dispatch ready tasks, enforce write ownership, retain same-task role sessions through permitted iterations, and verify the combined result before releasing dependents. |
| Verify and deliver | Read [references/completion.md](references/completion.md). Reconcile cross-task risks, capture final acceptance, and deliver within the user's authorization. |
| Resume | Compare saved scope, route approval, task inputs, and repository state before continuing the applicable phase. Reuse matching approval and evidence. |

Resolve `shared/` as the collection's `shared` skill describes and worker skills from their loaded locations. Use `shared/references/workflow-stage-routing.md` for engineering placement, `shared/references/task-shaped-model-routing.md` and `shared/references/model-roster.md` for model selection, `shared/references/host-model-execution.md` for native-first transport and role-session reuse, and the shared routing schema and run-state contract for persisted state. Load these at the phase that uses them and reuse active context.

## Model approval is required

Before any worker or model job, show exact implementation, independent review, and integration routes. For every route, show the model, effort, native or runner transport, host capability result, role-session strategy, receipt policy, task assignment, concurrency, and call limits. Include planned specialists; no hidden panel follows approval. Resolve task fit and exact models only through the shared routing references. Distinguish task-fit guidance from measured evidence.

Use `.rar-skills/config.local.yaml` only as advisory input while forming the preview; never reread it after approval. The approved plan is authoritative.

Ask the user to approve the concrete model plan or specify changes, then wait for the answer. Task approval, `--auto`, a default, or silence is not model approval. Reuse an explicit approval for the exact scope and routes; do not ask again merely because a same-route role session is resumed or receives a newly recorded context ID. Save the actual response reference, timestamp, and scope/route digests in `routing-plan.json` as [the model-plan reference](references/model-plan.md) specifies.

A model, runner, role, mode, native transport, effort, or receipt-policy change requires approval of the affected rows unless that exact fallback was approved. An unavailable route blocks its own work. Never silently substitute the current model or a cheaper model. Treat configured labels and observed serving-model receipts separately; unverified execution needs the user's explicit approval of that limit.

## Execution rules

1. Apply inherited design constraints. Use `coding-design-plan` only for an unresolved implementation shape and `design-gate` only when new evidence changes the design surface. Workers select the relevant engineering practices; they do not replay every lens.
2. Start a fresh implementer context and a separate independent reviewer context for each task. A later task never inherits either context. Reuse the recorded implementer for that task's fixes and evidence recovery, and its reviewer for rechecks. Use a separate persistent integration context for the combined revision; it never becomes a task implementer or reviewer. **Hand off the path, not the payload**: pass artifact paths and a short brief.
3. Follow `host-model-execution.md`. When preflight proves that the active host can run the selected model, effort, isolation, and follow-up natively, use the native subagent or authorized task thread. Use a runner only for a foreign model, an explicit user-requested transport, or a native route that cannot meet the approved requirements, and disclose why in the preview. Prefer a resumable session for an iterative runner role. A missing native continuation capability is recorded; it does not authorize a transport change.
4. Keep progress in **the ledger, not the transcript**. Store the preview, approved routing plan, and `run-state.json` under `.ai-workflow/impl-review/<session_id>/`. Before dispatch, record each role's route ID, host, transport, task and role, pending call, and pending context entry. When a call returns, record its actual context or session reference, completed turn, input revision, receipt, and resume result. Record effects before dispatch, then confirm from actual state.
5. Default to at most three tasks in flight within the approved cap; use one sequential writer without isolation. A worker tool's absence is disclosed in the preview before proposing inline execution. Do not reuse a global latest-session selector while more than one role can run.
6. Keep the limit of three review/fix cycles and one evidence recovery per task. Record attempts before dispatch. Reuse the approved same-task role context during those attempts when it remains available. Exhaustion blocks that task; independent work may continue.
7. Worker completion is not task completion. Integrate in dependency order and capture applicable acceptance on the combined state. Reuse matching evidence; rerun checks affected by code, dependency, environment, or contract changes and all checks the caller requires fresh.
8. Pause only the affected task when new evidence requires a material product, security, data ownership, architecture, or irreversible-action decision. Resolve implementation facts from the repository and record reversible assumptions within scope.

## Delivery boundary

Deliver the verified local diff by default. Reuse explicit authorization for commits, integration, push, or a PR; `open-pr` handles an authorized PR. Preserve unrelated changes. Do not create, rename, pin, archive, or remove user-owned tasks as routine execution work. Task isolation follows `references/worktree-and-integration.md` from the loaded `implement-and-review` skill. Do not rename or remove user-owned worktrees without explicit authorization.

Never invoke `models-consensus` automatically. An explicit user request for more opinions enters that workflow's own model approval; a previous council report is only an input.

Return `report.md` with task outcomes, acceptance evidence, routes and receipt limits, role-session and resume records, review scope, residual findings, and unresolved decisions as [references/completion.md](references/completion.md) defines. The queue is complete only when every task is done, final acceptance passes, and no blocking finding remains.
