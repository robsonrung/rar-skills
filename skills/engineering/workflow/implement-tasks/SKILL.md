---
name: implement-tasks
description: Execute an approved task queue with model approval, dependency scheduling, and integration review. Use when the user asks to implement approved tasks; implement-and-review handles each task.
disable-model-invocation: true
---

# Implement Tasks

Turn an approved queue into a verified change. Be a **thin conductor**: own model selection, scheduling, integration, and delivery. `implement-and-review` owns each task's implementation, focused review, and acceptance evidence.

The sequence is `interview-me` → `to-prd` → `to-tasks` → `implement-tasks`. Receive the approved PRD and task queue under `.ai-workflow/work/<feature-slug>/`. A complete single task uses the same model approval and skips graph scheduling. Missing product decisions return to the appropriate earlier stage.

## Select the current phase

| Phase | Required work and reference |
| --- | --- |
| Prepare or revise a model plan | Read [references/model-plan.md](references/model-plan.md). Validate the approved queue, dependencies, input hashes, routes, and available transports; produce the exact preview. |
| Schedule and integrate approved tasks | Read [references/feature-orchestration.md](references/feature-orchestration.md). Dispatch ready tasks, enforce write ownership, and verify the combined result before releasing dependents. |
| Verify and deliver | Read [references/completion.md](references/completion.md). Reconcile cross-task risks, capture final acceptance, and deliver within the user's authorization. |
| Resume | Compare saved scope, route approval, task inputs, and repository state before continuing the applicable phase. Reuse matching approval and evidence. |

Resolve `shared/` as the collection's `shared` skill describes and worker skills from their loaded locations. Use `shared/references/workflow-stage-routing.md` for engineering placement, `shared/references/task-shaped-model-routing.md` and `shared/references/model-roster.md` for model selection, and the shared routing schema and run-state contract for persisted state. Load these at the phase that uses them and reuse active context.

## Model approval is required

Before any worker or model job, show exact implementation and independent review models, runners, supported effort, receipt policy, task assignments, concurrency, and call limits. Include planned specialists and integration review; no hidden panel follows approval. Select the strongest known suitable model, then the lowest sufficient supported effort. Distinguish task-fit guidance from measured evidence.

Use `.rar-skills/config.local.yaml` only as advisory input while forming the preview; never reread it after approval. The approved plan is authoritative.

Ask the user to approve the concrete model plan or specify changes, then wait for the answer. Task approval, `--auto`, a default, or silence is not model approval. Reuse an explicit approval for the exact scope and routes. Save the actual response reference, timestamp, and scope/route digests in `routing-plan.json` as [the model-plan reference](references/model-plan.md) specifies.

A model, runner, role, mode, effort, or receipt-policy change requires approval of the affected rows unless that exact fallback was approved. An unavailable route blocks its own work. Never silently substitute the current model or a cheaper model. Treat configured labels and observed serving-model receipts separately; unverified execution needs the user's explicit approval of that limit.

## Execution rules

1. Apply inherited design constraints. Use `coding-design-plan` only for an unresolved implementation shape and `design-gate` only when new evidence changes the design surface. Workers select the relevant engineering practices; they do not replay every lens.
2. Use one fresh worker context per task. **Hand off the path, not the payload**: pass artifact paths and a short brief. Default to at most three tasks in flight within the approved cap; use one sequential writer without isolation. A worker tool's absence is disclosed in the preview before proposing inline execution.
3. Keep progress in **the ledger, not the transcript**. Store the preview, approved routing plan, and `run-state.json` under `.ai-workflow/impl-review/<session_id>/`. Record effects before dispatch, then confirm from actual state.
4. Keep the limit of three review/fix cycles and one evidence recovery per task. Record attempts before dispatch. Exhaustion blocks that task; independent work may continue.
5. Worker completion is not task completion. Integrate in dependency order and capture applicable acceptance on the combined state. Reuse matching evidence; rerun checks affected by code, dependency, environment, or contract changes and all checks the caller requires fresh.
6. Pause only the affected task when new evidence requires a material product, security, data ownership, architecture, or irreversible-action decision. Resolve implementation facts from the repository and record reversible assumptions within scope.

## Delivery boundary

Deliver the verified local diff by default. Reuse explicit authorization for commits, integration, push, or a PR; `open-pr` handles an authorized PR. Preserve unrelated changes. Do not create, rename, pin, archive, or remove user-owned tasks or worktrees as routine execution work.

Never invoke `models-consensus` automatically. An explicit user request for more opinions enters that workflow's own model approval; a previous council report is only an input.

Return `report.md` with task outcomes, acceptance evidence, routes and receipt limits, review scope, residual findings, and unresolved decisions as [references/completion.md](references/completion.md) defines. The queue is complete only when every task is done, final acceptance passes, and no blocking finding remains.
