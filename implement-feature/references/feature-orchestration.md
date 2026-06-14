# Feature Orchestration

How the orchestrator schedules the task DAG, runs each task through `implement-and-review`, integrates in dependency order, and runs the feature-wide review. `<id>` = session id, `<base>` = feature base recorded at preflight, `<T>` = task id (e.g. `T1`).

## Table of Contents

1. [Integration branch](#integration-branch)
2. [Per-task build via implement-and-review](#per-task-build-via-implement-and-review)
3. [Scheduling & parallelism (DAG)](#scheduling--parallelism-dag)
4. [Integrate a finished task](#integrate-a-finished-task)
5. [Feature-wide review](#feature-wide-review)
6. [Fallbacks](#fallbacks)

## Integration branch

Create it once, off `<base>`:

```bash
base=$(git rev-parse HEAD)
root=$(git rev-parse --show-toplevel)
git branch impl/feature-<id> "$base"
```

`impl/feature-<id>` is the **current integration head** — each task branches off it (not stale `<base>`) so later tasks build on already-integrated work.

## Per-task build via implement-and-review

Each task is built by `implement-and-review`, isolated with a per-task `--slice`. Reuse that skill's launcher so you don't reimplement its FE/BE flow:

```bash
L=.agents/skills/implement-and-review/scripts/launch.py
head=$(git rev-parse impl/feature-<id>)
# fire the task's FE/BE seats in an isolated, namespaced worktree set off the integration head
python3 $L launch --session-id <id> --slice <T> --base "$head" \
  --fe-brief <dir>/<T>-fe.md --be-brief <dir>/<T>-be.md
python3 $L poll --session-id <id> --slice <T> --wait
```

Then drive that task through `implement-and-review`'s cross-review + fix loop and its per-task integration/acceptance (Phases 2–4 of that skill), scoped to this task's worktrees. Build each task's FE/BE briefs from the `to-tasks` task (its description + acceptance + gates + shared contracts), embedding the methodology snippets `implement-and-review` specifies.

A single-track task (pure-FE or pure-BE) uses `--no-backend` / `--no-frontend`.

## Scheduling & parallelism (DAG)

1. Build the graph from each task's `blocked_by`.
2. A task is **ready** when every blocker is integrated. Launch ready tasks **concurrently up to the cap** (default 3) — fire each task's build (above) with its own `--slice <T>`; their Codex BE jobs run as background jobs and their Opus FE subagents run concurrently.
3. HITL tasks first; AFK unattended.
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
