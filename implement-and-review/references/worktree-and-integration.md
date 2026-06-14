# Worktrees, Slices & Integration

How the orchestrator isolates slices and tracks, schedules parallel slices, integrates in dependency order, and cleans up. The orchestrator owns the worktree lifecycle so every seat (native subagents and CLI runners) can target a known path. `<id>` = session id, `<S>` = slice id (e.g. `S1`), `<base>` = commit recorded at preflight.

## Table of Contents

1. [Layout & naming](#layout--naming)
2. [The integration branch](#the-integration-branch)
3. [Per-slice setup](#per-slice-setup)
4. [Scheduling & parallelism (DAG)](#scheduling--parallelism-dag)
5. [Slice integration + acceptance](#slice-integration--acceptance)
6. [Final verification](#final-verification)
7. [Cleanup](#cleanup)
8. [Fallbacks (single slice / no git)](#fallbacks-single-slice--no-git)

## Layout & naming

Two levels of isolation: a worktree per **slice**, and within it a worktree per **track**. Keep them outside the main tree (a sibling `.worktrees/` dir).

```
<root>/../.worktrees/impl-review-<id>/
  <S1>/frontend   branch impl/<S1>-frontend-<id>
  <S1>/backend    branch impl/<S1>-backend-<id>
  <S2>/frontend   ...
```

A slice may be single-track (only `frontend` or only `backend`). The integration branch `impl/integration-<id>` accumulates merged slices in dependency order.

## The integration branch

Create it once, off `<base>`:

```bash
base=$(git rev-parse HEAD)
root=$(git rev-parse --show-toplevel)
git branch impl/integration-<id> "$base"
```

This branch is the **current integration head** — new slices branch off it (not stale `<base>`) so later slices build on already-integrated work. If the repo has uncommitted (tracked) changes at start, ask the user to stash/commit first.

## Per-slice setup

When a slice becomes ready (all `blocked_by` integrated), create its track worktrees off the **current** `impl/integration-<id>` head:

```bash
head=$(git rev-parse impl/integration-<id>)
wt="$root/../.worktrees/impl-review-<id>/<S>"
git worktree add -b impl/<S>-frontend-<id> "$wt/frontend" "$head"   # if slice has FE work
git worktree add -b impl/<S>-backend-<id>  "$wt/backend"  "$head"   # if slice has BE work
```

The launcher does this for you: `launch.py launch --session-id <id> --slice <S> ...` (see runner-invocations). Within a slice the two tracks use **disjoint file scopes**, so they run fully in parallel without clobbering. Review diffs are always `git -C <wt/track> diff <head>..HEAD`.

## Scheduling & parallelism (DAG)

1. Build the dependency graph from each slice's `blocked_by`.
2. A slice is **ready** when every blocker is integrated. Launch ready slices **concurrently up to the concurrency cap** (default 3 in flight); each runs the full per-slice build in its own worktrees.
3. When a slice integrates, recompute readiness and pull the next ready slices into flight.
4. **HITL** slices first (cluster human touchpoints early); **AFK** slices unattended.
5. An **escalated** slice (3-cycle cap) blocks only its dependents — independent slices keep going. Record it.

Because ready slices branch off the moving integration head, two in-flight slices that don't depend on each other still won't see each other's commits until each integrates — that's fine for disjoint work; if two ready slices are likely to touch the same files, serialize them (mark one `blocked_by` the other).

## Slice integration + acceptance

When a slice's tracks are approved (or the slice is escalated with usable work):

```bash
git switch impl/integration-<id>
git merge --no-ff impl/<S>-backend-<id>   -m "<S>: backend"
git merge --no-ff impl/<S>-frontend-<id>  -m "<S>: frontend"
```

Resolve any conflict using both diffs (preserve each track's intent and the shared contracts). Then run the slice's **acceptance contract** on the integration branch:

```bash
git -C "$root" switch impl/integration-<id>
<slice acceptance commands>     # the exact commands to-tasks recorded for this slice
```

Plus its `gates`: if `security: deep`, run `full-review security_focus=true` scoped to this slice now. Red → bounded slice-fix loop (≤3): route to the responsible track, re-merge, re-test. Green → mark the slice **done**, unblock dependents.

## Final verification

After all slices are integrated, on `impl/integration-<id>` run the project's full detected commands; they must pass before reporting done, and again after applying full-review findings:

```bash
git -C "$root" switch impl/integration-<id>
<detected test command>      # e.g. npm test, pytest, make test, cargo test
<detected build command>     # e.g. npm run build
```

## Cleanup

Do **not** delete worktrees/branches, push, or open a PR unless asked — leave `impl/integration-<id>` for the user to inspect or land. Report the branch name and worktree paths. The launcher's `cleanup --session-id <id>` removes the session's worktrees; otherwise:

```bash
git worktree remove "$root/../.worktrees/impl-review-<id>/<S>/frontend"
git worktree remove "$root/../.worktrees/impl-review-<id>/<S>/backend"
git worktree prune
```

## Fallbacks (single slice / no git)

- **Single implicit slice** (small change / no breakdown): skip the DAG — one slice, FE/BE tracks off `<base>`, integrate once, run the change's tests as acceptance, then the final full-review.
- **Not a git repo (or worktrees declined):** run **sequentially in the working tree**, no isolation, no parallelism — backend track end-to-end, then frontend (so the FE builds against settled backend contracts), per slice in dependency order; verification on the working tree; full-review against the local diff. Note in the report that isolation was unavailable.
- **Tight seats/cost:** lower the concurrency cap toward 1 (sequential slices) while keeping per-slice worktrees.
