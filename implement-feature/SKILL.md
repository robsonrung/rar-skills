---
name: implement-feature
description: Build a whole feature by breaking a plan into tasks and running implement-and-review on each. Given a plan or feature, decompose it into tracer-bullet vertical-slice tasks (via the to-tasks skill — acceptance contracts + gate flags + dependencies), then execute the task DAG (independent tasks in parallel) by running implement-and-review for each per-task FE/BE cross-reviewed TDD build, integrate tasks in dependency order with per-task acceptance, and finish with a feature-wide full-review, leaving tests/build green. Opus orchestrates the breakdown, scheduling, integration, and final review; per-task building is implement-and-review's job. Use to ship/build a multi-task feature end-to-end. For a single scoped task call implement-and-review directly. Distinct from models-roundtable (answer only), feature-models-roundtable (multi-model consensus, then this), and ship (single-model pipeline).
---

# Implement Feature

High-level build orchestrator: turn a plan into a working, reviewed feature by **decomposing it into tasks and delegating each to `implement-and-review`**. You (the main agent, Opus 4.8) own the breakdown, the dependency DAG and scheduling, cross-task integration, and the feature-wide final review. Per-task building — the FE/BE split, cross-model review, and TDD — is `implement-and-review`'s job. **Call it; don't reimplement it.**

Pipeline: **plan → `to-tasks` (vertical slices) → `implement-and-review` per task (parallel where independent) → integrate in dependency order → feature-wide `full-review` → green.**

The detailed scheduling/integration commands are in [references/feature-orchestration.md](references/feature-orchestration.md); read it before Phase 1.

## Hard Rules

1. **Decompose with `to-tasks`.** Break the plan into tracer-bullet vertical-slice tasks, each with a machine-checkable acceptance contract, gate flags (lenses + `security`), and `blocked_by` deps. (`to-tasks` is preferred over `to-issues` for autonomous execution.)
2. **Tasks are the unit of value and parallelism.** Independent tasks run in parallel; dependent ones wait on their blockers.
3. **Delegate each task to `implement-and-review`.** Don't duplicate its FE/BE/TDD/cross-review logic — hand it the task, a per-task `--slice` namespace, and the base to build on.
4. **Writes are gated.** No code until the user approves the breakdown (skip only with `--auto`).
5. **Integrate in dependency order.** Each task must pass its acceptance contract before its dependents start.
6. **Feature-wide final review.** After all tasks integrate, run `full-review` across the whole feature (focused on cross-task seams; per-task review already happened), apply findings, leave green.
7. **Bounded + escalate.** A task whose `implement-and-review` hits its 3-cycle cap is escalated; it blocks only its dependents — independent tasks keep going.
8. **Never fabricate a seat; degrade** per [Degrade Gracefully](#degrade-gracefully).

## Preflight

1. **Host & git.** Worktrees (and thus parallel tasks) need git; no git → sequential fallback.
2. **Seats.** Use the shared probe to verify both runners up front so tasks don't all fail: `python3 .agents/skills/_shared/scripts/discover_runners.py probe --native-agent yes --seat codex --seat kimi --seat opus --format json`. Each task's `implement-and-review` needs `codex` and `kimi` available; the native `Agent` tool (`opus.execution_path: agent_native`) handles Opus seats.
3. **Verification commands.** Detect the project's feature-wide test/build commands. `to-tasks` acceptance contracts must use commands that exist.
4. **Concurrency cap.** Default **3 tasks in flight** (each runs a full FE+BE build); lower it when seats/cost are tight.
5. **Base & artifacts.** Record `HEAD` as the feature `<base>`; create the feature integration branch; use `.ai-workflow/impl-review/<session_id>/` for the breakdown, per-task subdirs, and the report.

## Phase 0 — Plan & Decompose (gate)

1. **Intake the plan.** Sources: a plan/spec the user gives; an existing `TASKS.md` or tracker issues; or a `models-roundtable` consensus report (passed as `--from-roundtable <path>`, e.g. by `feature-models-roundtable` — take its *Consensus answer* as the plan and resolve its *Open caveats* with the user first).
2. **Decompose** with `to-tasks` → vertical-slice tasks with acceptance, gates, and deps. If the work is genuinely a single task, **skip `to-tasks` and just call `implement-and-review`** (then stop).
3. **Present** the task list (titles, deps, acceptance, gates, HITL/AFK) + the verification commands. **Get approval before any code is written**, unless `--auto`.

## Phase 1 — Schedule & Build the DAG

Build the dependency graph from `blocked_by`. Then:
- Schedule **HITL** tasks first; run **AFK** tasks unattended.
- Run all currently-unblocked tasks **concurrently, up to the cap**, each by running **`implement-and-review` for that task** — pass the task brief, a per-task `--slice <task>` namespace, and `--base` = the **current feature integration head** (so each task builds on already-integrated work). See [references/feature-orchestration.md](references/feature-orchestration.md).
- As each task's build finishes and passes **its acceptance contract**, integrate it into the feature integration branch in dependency order, recompute readiness, and pull the next ready tasks into flight.
- Continue until every task is done or escalated. An escalated task blocks only its dependents.
- Report progress (done / in flight / blocked); never silently drop a task.

## Phase 2 — Feature-wide Final Review

After all tasks are integrated, run **`full-review`** across the whole feature (diff vs the feature `<base>`), focused on **cross-task integration and seams** and anything the per-task reviews could not see. `security_focus=true` if any task was security-sensitive. Apply findings (route each to the owning task's implementer via `implement-and-review`, or a scoped fix), then re-verify the full suite **green**.

## Phase 3 — Report

Deliver inline and write `.ai-workflow/impl-review/<session_id>/report.md`:
1. **Feature** and final status (`done` / `partial` / `escalated`).
2. **Tasks** — a table: task, deps, status, acceptance result, review cycles, which ran in parallel.
3. **Integration** — order merged, conflicts resolved.
4. **Feature-wide full-review** — verdict, findings by severity, what was fixed, deferrals.
5. **Verification** — commands + results (green/red).
6. **Branch/worktrees** — the feature integration branch and how to inspect/land it. Do not push, PR, or delete worktrees unless asked.
7. **Escalations** — any task stopped at its build's 3-cycle cap, with open findings.

## Degrade Gracefully

- **Not a git repo:** run tasks **sequentially** in the working tree (each via `implement-and-review`'s no-git fallback), no parallelism.
- **Few seats / tight cost:** lower the cap toward 1 (sequential tasks).
- **Single task:** skip the DAG — just call `implement-and-review` and report its result.
- **A task escalates:** keep building independents; surface the escalation in the report.

## Gotchas

- **Don't reimplement `implement-and-review`.** This skill is breakdown + DAG + cross-task integration + feature-wide review only.
- Each task builds on the **current integration head** (`--base`), not the stale feature base, so later tasks see earlier work; respect `blocked_by`, and serialize tasks likely to touch the same files (add a `blocked_by`).
- Per-task reviews already ran inside each `implement-and-review`; the feature-wide `full-review` targets the **seams** so you don't pay to re-review every task in full.
- **Vertical vs horizontal:** `to-tasks` tasks are vertical (all layers); `implement-and-review` splits each task horizontally (FE/BE). The task is the outer unit; the FE/BE split is inside each task.
- Keep state in the orchestrator — track the DAG and integration head; read each task's compact report, not full transcripts.
