---
name: implement-tasks
description: Execute an approved task queue through implement-and-review, integrate dependencies, and verify the result. Step 4 after interview-me, to-prd, and to-tasks. Present exact implementation and review models, effort levels, and task assignments for user approval before dispatch. Use when the user asks to implement the tasks or build an approved feature. A single task uses the same model approval and then implement-and-review. Commit, push, and PR creation require user authorization.
disable-model-invocation: true
---

# Implement Tasks

Turn an approved queue into a verified change. Be a **thin conductor**: own model selection, scheduling, integration, and the final result. `implement-and-review` owns each task's design check, implementation, focused review, and acceptance evidence.

Sequence: inspect the queue → approve models → build ready tasks → integrate and verify → review cross-task seams → deliver within the user's authorization.

## 1. Prepare the execution plan

1. Read the queue under `.ai-workflow/work/<feature-slug>/tasks/`, its `tasks-draft.md`, and its PRD. Verify that both approval records are present and still describe the queue; drafts cannot start implementation. For a bare plan, obtain an approved PRD through `to-prd`, then use `to-tasks`. For one complete task, keep the model approval below and skip graph scheduling.
2. Check stable task IDs, missing dependencies, cycles, acceptance commands, HITL decisions, and write conflicts. Resolve facts from the project before asking for a decision. Do not launch a task with unresolved requirements or missing access.
3. Read `shared/references/workflow-stage-routing.md`. Reuse earlier decisions and lens findings. Each worker uses `coding-design-plan` to apply inherited gate constraints. Call `design-gate` again only when new evidence changes the design surface; do not repeat an earlier architecture study.
4. Resolve roles through `shared/references/task-shaped-model-routing.md` and `shared/references/model-roster.md`. If `.rar-skills/config.local.yaml` exists, read its advisory `seats` and `models` only while forming this preview, as `shared/references/local-config.md` defines. Validate every value against the roster and runner, let direct user instructions win, and never reread it after approval. Check installed runners and model catalogs without starting model jobs. Select the strongest known suitable model for each implementation and review role, then the lowest sufficient supported effort. Separate task-fit recommendations from measured benchmark results.
5. Inspect git state and preserve unrelated edits. Record the base revision, acceptance commands, available runners, concurrency, and delivery authorization. Use isolated worktrees when commits and integration are authorized. Otherwise use one sequential writer in the working tree.
6. Save the human preview as `model-plan.md` and progress as `run-state.json`. Create the executable `routing-plan.json` only after approval. Keep these files under `.ai-workflow/impl-review/<session_id>/`. Use `shared/references/implementation-routing-plan.schema.json` for routing and `shared/references/run-state-contract.md` for progress. Include the PRD and every executable task in `scope.inputs` with their canonical `content_sha256`; bind each route to its task through `input_path`. Use the shared normalization rule so task status updates preserve approval, while changes to scope or acceptance invalidate it.

Resolve `shared/` from the installed skill library as the `shared` skill describes. Resolve worker skills from their loaded locations; never assume a `.agents/skills` installation path.

## 2. Approve models before dispatch

Show this table with real resolved values, grouped only when tasks use the same route:

| Tasks or scope | Role | Model and runner | Effort | Model receipt | Reason |
| --- | --- | --- | --- | --- | --- |
| Task IDs | Implementation | Exact model ID and runner | Supported level | Required or unverified allowed | Task-specific fit |
| Same IDs | Independent review | Exact model ID and runner | Supported level | Required or unverified allowed | Main risk to inspect |
| Integration seams | Final review | Exact models and runners | Supported levels | Required or unverified allowed | Cross-task coverage |

Also show the coordinator model, concurrency cap, review/fix limit, and proposed fallbacks. Use an independent review context; prefer another model family when it meets the quality requirement. Include design-lens workers and specialist reviewers that will run, so no hidden panel follows approval. Represent these as reviewer routes with clear scope and track names. Give review-only passes their own scope IDs, so they do not appear as build tracks; name the integration scope explicitly. The coordinator is recorded in the human preview and run state.

Explain any receipt limit in plain terms: the runner may confirm the configured model without proving which model served the request. Record `model_verification: allow_unverified` only when the user approves that limit; otherwise use `required`. Show runtime-controlled effort as such, without inventing a fixed level.

Ask: **"Approve this model plan, including effort and receipt limits, or specify changes?"** Wait for the answer. Record the user response reference, approval time, and canonical scope and route digests in `routing-plan.json`. Save a matching `gates` entry with `gate: model_plan_approval`, `decision: approved`, and the approval time. The launcher verifies the fingerprints and input files before side effects; the host remains responsible for recording only actual user approval.

Task approval from `to-tasks` does not approve the model plan. `--auto`, a default selection, or silence cannot approve it. Reuse approval only when the user already approved this exact scope and plan in the session. Do not start implementation, reviewer, council, or model probe jobs before this gate.

Carry the approved model and effort into every worker and runner call. Check configured values and serving-model receipts against the approved receipt policy. Any change to model, runner, mode, role, effort, or receipt policy requires approval of the changed rows unless that exact fallback was already approved. A missing model or unsupported effort blocks its route. Never silently use a cheaper model or the host model instead. On resume, compare saved scope and routes before reusing approval.

## 3. Build and integrate

Read `references/feature-orchestration.md` for the worker brief and integration rules.

1. Start tasks whose dependencies passed acceptance on the integration state. Attend HITL tasks when their recorded decision is needed. Keep independent tasks moving when another task is blocked.
2. Use one fresh task context per task, with `implement-and-review`, the task path, approved route, write scope, current integration revision, and report path. **Hand off the path, not the payload**: pass artifact paths and a short brief. Do not create host goals or user-owned tasks unless requested.
3. Limit concurrency by write ownership, runner capacity, and the approved cap. Default to at most three tasks in flight; use one writer without isolation. Split frontend and backend work only when both can proceed independently against an agreed interface.
4. Require captured command results and observable behavior in each task report. Missing evidence allows one recovery pass over the existing work. Record the attempt before dispatch; a second result without evidence blocks the task.
5. Integrate authorized task commits in dependency order, or accept sequential working-tree changes. Run task acceptance on the combined result before marking it `done` or releasing dependents. Review conflict resolutions as changed code.

Progress lives in **the ledger, not the transcript**. Store worker IDs, task states, reviewed revisions, effective models, acceptance results, and attempt counts. Worker completion is not task completion until integration checks pass. Use the shared prepare/execute/confirm rule for side effects; a pending record is not proof of success.

## 4. Verify the complete change

Run the feature's acceptance commands. For several tasks, call `full-review` once on the combined change, focused on integration seams, shared contracts, migration order, and gaps in task reviews. Use the approved reviewer plan and `security_focus=true` when a task has deep security exposure.

A single task with a complete scoped review does not need a duplicate full panel. Reuse task evidence when the code and assumptions still match. After a fix, rerun affected checks and review changed paths; broaden only when the change or a failure requires it. Never weaken acceptance checks to obtain a pass.

Record unapplied findings using `references/residual-findings.md`. A blocking defect stays blocked; recording it does not complete the feature.

## 5. Deliver and report

Deliver the verified local diff by default. If the user authorized commit, push, or a PR, perform those actions; use `open-pr` for an authorized PR. A configured remote does not grant publication permission. Reuse prior authorization without asking again.

Write `report.md` in the run directory. Include:

1. Result: `complete`, `partial`, `failed`, or `ceiling_hit`; local diff or authorized delivery link.
2. Tasks: stable ID, status, dependency, integration result, and acceptance evidence.
3. Models: approved and configured models, observed serving models when available, receipt limits, effort, and approved substitutions.
4. Review: scope, reviewed revision, applied findings, residual record, and unverified checks.
5. Decisions: assumptions within scope, blocked decisions, and required next actions.

The queue is complete only when every task is done and final acceptance passes. `partial` is a report outcome; run state uses the shared status enum. Use `capture-learning` for a reusable project finding or `session-handoff` when work must resume, within the original authorization.

## Decisions and failures

1. Use the approved PRD, task contract, code, and targeted tests to resolve implementation details. Record reversible assumptions within scope.
2. If new evidence changes product behavior, security, data ownership, an accepted architecture decision, or an irreversible operation, pause the affected task for that decision. Continue independent work.
3. Never call `models-consensus` automatically. Use it only when the user asks for additional opinions, with its own model approval. An existing council report is input, not authorization for another council or code changes.
4. Keep the `implement-and-review` limit of three review/fix cycles and one evidence recovery. Exhausted attempts block that task. Model or effort escalation follows the saved approval.
5. Without a worker tool, propose sequential inline execution in the model plan and report that no worker was created. Do not rename, pin, create, or archive user-owned tasks as routine implementation work.
