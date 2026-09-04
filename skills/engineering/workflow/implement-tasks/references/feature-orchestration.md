# Feature Orchestration

How the orchestrator schedules the task DAG, runs each task through `implement-and-review`, integrates in dependency order, and runs the feature-wide review. `<id>` = session id, `<base>` = feature base recorded at preflight, `<T>` = task id (e.g. `T1`).

## Table of Contents

1. [Integration branch](#integration-branch)
2. [Worker thread lifecycle](#worker-thread-lifecycle)
3. [Per-task build via implement-and-review](#per-task-build-via-implement-and-review)
4. [Scheduling & parallelism (DAG)](#scheduling--parallelism-dag)
5. [Integrate a finished task](#integrate-a-finished-task)
6. [Feature-wide review](#feature-wide-review)
7. [Fallbacks](#fallbacks)

## Integration branch

Create it once, off `<base>`:

```bash
base=$(git rev-parse HEAD)
root=$(git rev-parse --show-toplevel)
git branch impl/feature-<id> "$base"
```

`impl/feature-<id>` is the **current integration head** — each task branches off it (not stale `<base>`) so later tasks build on already-integrated work.

## Worker thread lifecycle

Every task runs in a **new** worker context that exists for that task alone. The orchestrator thread never builds a task and never reuses a worker. Four moments: name the orchestrator, open a worker, give it a goal, close it.

### 0. The orchestrator thread — once per run

Before the first worker: rename this thread `ORCHESTRATOR · implement-tasks · <feature-slug>` and pin it, so the conductor is unmistakable in a sidebar full of workers. Codex / ChatGPT app: the thread's rename and pin controls. Host without an agent-reachable control: put the request in the Phase 0 approval message (it is the last human gate anyway). Record `threads.orchestrator = { name, id }` in the run state; a resumed run restores the name before scheduling.

### 1. Open a worker

| Host | How | Registry `host` |
| --- | --- | --- |
| Claude Code | `Agent` tool, `subagent_type: general-purpose`, fresh context (no fork) | `claude-code` |
| Codex / ChatGPT desktop app | **New thread** (never a fork of the orchestrator), same repo, named `<T> · <feature-slug> · implement-and-review` | `codex-app` |
| cmux fleet (`peer-sessions`) | one new terminal per task, same name | `cmux` |
| none of the above | inline, sequential, stated as such in the report | `inline` |

Write `threads.workers[<T>] = { host, id, name, goal, opened_at }` to the run state **before** sending anything to the worker, so a crash between open and goal leaves a record to close.

### 2. Send the `/goal`, then the brief

The goal is the first message, on its own. It is a done-condition — every clause verifiable from disk or the shell — followed by the standing "keep going" instruction. Fill this template from the task file and the run state:

```text
/goal Task <T> — <title> — is done when ALL of these hold:
1. `implement-and-review` for <path to task file> has written its envelope to
   .ai-workflow/impl-review/<id>/<T>/report.md with status `complete`
   (a recorded `failed` or `ceiling_hit` also ends the goal — never a silent stop).
2. On branch impl/<T>-backend-<id> (and impl/<T>-frontend-<id> if present) these exit 0:
   <acceptance command 1>
   <acceptance command 2>
3. The report's `## Evidence` section is non-empty and lists the tests inspected, added, and run.
4. Nothing outside the task's write scope changed: `git diff --stat <head>..HEAD` touches only <allowed paths>.
Keep working until every clause holds or the 3-cycle review cap is hit. Then return the
envelope (≤15 lines, handoff-contract shape) and stop. Do not start any other task.
```

Rules for the goal:

- Name commands verbatim; "tests pass" is not a clause, `npm test -- --run src/auth` is.
- One task per goal. A goal that lists two tasks is two workers.
- If a clause cannot be written because the task file lacks an acceptance command, the task is under-specified — route it back to `to-tasks`; do not launch a worker on a vague goal.
- `/goal` exists on both hosts: Claude Code ("Set a goal Claude checks before stopping") and the Codex / ChatGPT app (the `goals` feature). Send it as the worker's first message on either. When a worker is a native `Agent` subagent that cannot receive a slash command, put the same text at the top of its first message under the heading `GOAL (checked before stopping)` — the contract is identical, only the delivery differs.

The **brief** (handoff-contract shape, paths only) is the second message. Goal = when to stop; brief = what to do.

Codex CLI fallback when the desktop UI is not reachable from the agent: start the worker as a named interactive session and feed it with

```bash
codex queue --thread "<T> · <feature-slug> · implement-and-review" --message "$(cat <goal-file>)"
codex queue --thread "<T> · <feature-slug> · implement-and-review" --message "$(cat <brief-file>)"
```

### 3. Wait on the envelope

`python3 $L poll --session-id <id> --slice <T> --wait`, or watch the report path. Read the envelope; open the report body only to route a failure or reconcile two tasks.

### 4. Close the worker

As soon as the envelope is recorded in `steps` and `threads.workers[<T>].closed_at`:

1. Append `side_effects` key `archive:<T>`.
2. Codex / ChatGPT app: **archive the thread in the UI**. Fallback: `codex archive "<T> · <feature-slug> · implement-and-review"`. Never `codex delete` — deletion is destructive and stays with the human.
3. Claude Code: the subagent has returned; nothing to archive. cmux: `peer-sessions` teardown for that terminal only.

Archive `failed` and `ceiling_hit` workers too; their report is the durable artifact. On resume, a worker with `opened_at` but no `closed_at` and no `archive:<T>` key is the one to poll or re-dispatch; one with the key is done even if the UI still shows it.

The orchestrator thread is never archived by this skill and keeps its pin and name through delivery.

## Per-task build via implement-and-review

Each task is built by `implement-and-review` **inside its own worker** (opened per [Worker thread lifecycle](#worker-thread-lifecycle)), isolated with a per-task `--slice`. The commands below are what the worker runs; the orchestrator never runs them in its own thread. Reuse that skill's launcher so you don't reimplement its FE/BE flow:

```bash
L=.agents/skills/implement-and-review/scripts/launch.py
head=$(git rev-parse impl/feature-<id>)
# fire the task's FE/BE seats in an isolated, namespaced worktree set off the integration head
python3 $L launch --session-id <id> --slice <T> --base "$head" \
  --fe-brief <dir>/<T>-fe.md --be-brief <dir>/<T>-be.md
python3 $L poll --session-id <id> --slice <T> --wait
```

Then drive that task through `implement-and-review`'s cross-review + fix loop and its per-task integration/acceptance (Phases 2–4 of that skill), scoped to this task's worktrees. Build each task's FE/BE briefs from the `to-tasks` task — its description, type, acceptance, gates, expected review focus, rollback note, and shared contracts — embedding the methodology snippets `implement-and-review` specifies (including its Slice Contract snippet).

A single-track task (pure-FE or pure-BE) uses `--no-backend` / `--no-frontend`.

## Scheduling & parallelism (DAG)

1. Build the graph from each task's `blocked_by`.
2. A task is **ready** when every blocker is integrated. Launch ready tasks **concurrently up to the cap** (default 3) — open a fresh worker per task, send its `/goal` then its brief, and let the worker fire the build (above) with its own `--slice <T>`; backend and standard frontend Codex jobs run as background jobs, while a task classified `visual_creative` may use an Opus frontend subagent.
3. HITL tasks first, attended — never pass `--auto` to a HITL task's `implement-and-review`; its human decision is recorded in that task's `gates` before it proceeds. AFK tasks run unattended.
4. When a task integrates, recompute readiness and pull the next ready tasks into flight.
5. An **escalated** task (its `implement-and-review` hit the 3-cycle cap) blocks only its dependents; keep building independents.

Two ready tasks that are likely to touch the same files should be serialized — give one a `blocked_by` on the other.

## Integrate a finished task

When a task's build is approved and passes **its acceptance contract**, merge it into the feature branch in dependency order:

```bash
git switch impl/feature-<id>
git merge --no-ff impl/<T>-backend-<id>   -m "<T>: backend"
git merge --no-ff impl/<T>-frontend-<id>  -m "<T>: frontend"
# run the task's acceptance commands on the feature branch — must pass
```

Resolve any conflict using both diffs (disjoint scopes make this rare). Red acceptance → route back to the task's `implement-and-review` (FE `SendMessage` / BE `--resume`), re-merge, re-test. Then unblock dependents.

## Feature-wide review

After all tasks integrate, run `full-review` on `impl/feature-<id>` (diff vs `<base>`), focused on cross-task seams; `security_focus=true` if any task was security-sensitive. Apply findings via the owning task's implementer, then re-run the full verification commands — must be **green**.

## Fallbacks

- **Not a git repo:** no worktrees/parallelism — run tasks sequentially in the working tree via `implement-and-review`'s no-git fallback, in dependency order.
- **Tight seats/cost:** cap = 1 (sequential tasks), still namespaced per task.
- **Cleanup:** do not remove worktrees/branches, push, or PR unless asked; `launch.py cleanup --session-id <id> --slice <T>` removes a task's worktrees when the user is done.
- **Worker threads are the exception to "leave it":** archive each worker thread as soon as its envelope is recorded (see [Close the worker](#4-close-the-worker)). Archiving is reversible (`codex unarchive`); deleting is not and is never done by this skill.
