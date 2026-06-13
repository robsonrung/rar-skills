# Worktrees & Integration

How the orchestrator isolates the two tracks, integrates them, and cleans up. The orchestrator owns the worktree lifecycle so every seat (native subagents and CLI runners) can target a known path. `<id>` = session id, `<base>` = commit recorded at preflight.

## Table of Contents

1. [Setup](#setup)
2. [During the tracks](#during-the-tracks)
3. [Integration](#integration)
4. [Verification](#verification)
5. [Cleanup](#cleanup)
6. [Sequential fallback (no git)](#sequential-fallback-no-git)

## Setup

Record the base and create one worktree+branch per non-empty track, off `<base>`. Put worktrees in a writable location **outside** the main tree to avoid nesting surprises (here, a sibling `.worktrees/` dir).

```bash
base=$(git rev-parse HEAD)
root=$(git rev-parse --show-toplevel)
wt_dir="$root/../.worktrees/impl-review-<id>"
git worktree add -b impl/frontend-<id> "$wt_dir/frontend" "$base"   # only if FE track is non-empty
git worktree add -b impl/backend-<id>  "$wt_dir/backend"  "$base"   # only if BE track is non-empty
```

Use `$wt_dir/frontend` as `<wt-fe>` and `$wt_dir/backend` as `<wt-be>` in the seat commands. If the repo has uncommitted changes at start, ask the user whether to stash/commit them first — worktrees branch from a clean `<base>`.

## During the tracks

Each implementer commits on its own branch inside its worktree. Diffs for review are always `git -C <worktree> diff <base>..HEAD`. The tracks never touch each other's worktree, so they run fully in parallel without clobbering.

## Integration

After both tracks are approved (or escalated), integrate into a fresh branch off `<base>`:

```bash
git switch -c impl/integration-<id> "$base"
git merge --no-ff impl/backend-<id>   -m "integrate backend (<id>)"
git merge --no-ff impl/frontend-<id>  -m "integrate frontend (<id>)"
```

Phase 0's disjoint file scopes should make this conflict-free. If a conflict appears (a shared file slipped through), resolve it yourself using both diffs — preserve each track's intent and the shared contracts — then commit. Do the joint review & simplify pass on this integration branch.

## Verification

Run the project's detected commands (from preflight) on the integration branch; they must pass before reporting done, and again after the joint simplify pass:

```bash
git -C "$root" switch impl/integration-<id>
<detected test command>      # e.g. npm test, pytest, make test, cargo test
<detected build command>     # e.g. npm run build
```

If red, route the failure to the responsible track (FE → `SendMessage` the Opus subagent; BE → Codex `--resume`), have it fix on its branch, re-merge, re-test — bounded to 3 integration-fix cycles, then escalate. If no test/build command exists, report that verification could not run.

## Cleanup

Do **not** delete worktrees or branches, push, or open a PR unless the user asks — leave the integration branch for them to inspect or land. Report the integration branch name and the worktree paths. When the user is done, worktrees are removed with:

```bash
git worktree remove "$wt_dir/frontend"
git worktree remove "$wt_dir/backend"
git worktree prune
```

## Sequential fallback (no git)

When the project is not a git repo (or the user declines worktrees), run **sequentially in the working tree** — no isolation, no merge:

1. Backend track end-to-end: Codex implements in the working dir → Opus reviews → fix loop (≤3).
2. Then frontend track end-to-end: Opus subagent implements in the working dir → Kimi reviews → fix loop (≤3).
3. Run verification on the working tree; bounded fix loop if red.
4. Joint Opus+Codex review & simplify on the cumulative diff (`git diff` if available, else the orchestrator's record of changed files); apply; re-verify.

Running backend first lets the frontend build against settled backend contracts. Note in the report that isolation was unavailable, so the tracks were serialized.
