---
name: implement-and-review
description: Implement and review one approved coding task through exact model routes and persistent role contexts. Use for a scoped task with an acceptance contract; use implement-tasks to coordinate a queue.
---

# Implement And Review

Build one approved task to its **acceptance contract**, or complete its bound feature review. A worker result is integration evidence. The parent alone accepts tasks after the applicable gate passes.

## Authority and common rules

An implementation request authorizes in-scope edits, stated verification, and reversible isolation. Commit, push, merge, pull request, deployment, external messages, and destructive cleanup need explicit authority. Reuse existing authorization. Ask only for a material unresolved scope, cost, or authority decision.

For worker dispatch, obtain or reuse one approved snapshot through `shared/references/model-preview.md`. Model and effort defaults come only from `shared/model-routing.json`. Dispatch, repairs, and resumes retain the exact route, provider controls, tools, privacy, source bindings, budget, fallback triggers, and call, time, concurrency, and recovery limits. A missing required capability blocks that route. Never call `models-consensus` here.

Use separate persistent contexts for each task, track, and role. Reviewers use a different model and a separate context from every author in their scope. Native handoffs require `parent_history: none`. Keep native contexts in `native_contexts[route_id]` and runner sessions in `runner_contexts[route_id]`. Reconcile pending calls before retry or reconstruction. Context loss preserves counters and routes.

The launcher validates approved input hashes before writes or dispatch. It includes the full contract for first calls and reconstruction, and validates continuation proof before selecting the smaller full or compact input. Derived notes cannot change acceptance. Its complete rendered input limit is 24,000 UTF-8 bytes; a larger approved `context_budget` needs a reason. Read `shared/references/context-packets.md` when preparing or recovering a packet.

## Select one path

Use the approved policy, not a prose label. Without a bound `review_policy`, keep task mode. Existing plans and snapshots remain unchanged. A standalone small change uses task mode when its complete contract leaves no product, data, security, public contract, or dependency decision unresolved.

Read only the selected row and its triggered references. Section pointers mean the named section, not the whole manual. Retain already loaded rules without rereading them.

| Current work | Load |
| --- | --- |
| Implement a feature task classified `deferred` | [task-implementation.md](references/task-implementation.md), then [deferred-task.md](references/deferred-task.md). |
| Implement a critical feature task or a standalone/legacy task | [task-implementation.md](references/task-implementation.md), then [task-review.md](references/task-review.md) when implementation evidence is ready. |
| Review a completed critical or standalone task | [task-review.md](references/task-review.md). |
| Complete combined feature review under a bound policy | [final-feature-review.md](references/final-feature-review.md). |
| Repair, recheck, or recover a selected path | Keep that path; load `Continue the same role` in [runner-invocations.md](references/runner-invocations.md#continue-the-same-role), plus `shared/references/incremental-review.md` for a reviewer recheck or prose addendum. |

For a new route selection, load the routing schema, `shared/references/task-shaped-model-routing.md`, and `shared/references/host-model-execution.md`. For runner execution, read only [Runner policy and receipts](references/runner-invocations.md#runner-policy-and-receipts). For native execution, read only [Native receipts](references/runner-invocations.md#native-receipts). For job inspection or authorized cleanup, read its `Poll and cleanup` section. A handoff or successful poll proves execution status only.

## Output contract

Return `status`, `acceptance`, `routes_used`, `review`, `changed_paths`, and `next_action`. Include required behavior and captured results, exact approved route IDs and effective receipts, applied or declined findings with evidence, and unresolved risks. Use `implemented` for provisional feature tasks; otherwise `complete`, `failed`, `ceiling_hit`, or `awaiting_human`. Critical task review readiness does not accept the feature. Name any pending final gate.

Write the task report under `.ai-workflow/impl-review/<session-id>/<task-id>/report.md` when available. Link snapshots, original captures, review records and verifier results where applicable, role contexts, reconstruction, changed paths, and remaining risks. Retain role contexts until fixes, rechecks, and evidence obligations finish. Return only a necessary decision, parent integration, or separately authorized delivery as `next_action`.
