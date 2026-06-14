# Worktrees & Integration (one task)

How the orchestrator isolates the two tracks of **one task**, integrates them, and cleans up. The orchestrator owns the worktree lifecycle so every seat (native subagents and CLI runners) can target a known path. `<id>` = session id, `<base>` = the head this task builds on. (When `implement-feature` drives this skill per task, it passes a per-task `--slice` namespace and a `<base>` = the feature's current integration head — see that skill's reference.)

## Table of Contents

1. [Setup](#setup)
2. [During the tracks](#during-the-tracks)
3. [Integration](#integration)
4. [Verification](#verification)
5. [Cleanup](#cleanup)
6. [Sequential fallback (no git)](#sequential-fallback-no-git)

## Setup

Create one worktree+branch per non-empty track, off `<base>`, outside the main tree (a sibling `.worktrees/` dir). `<S>` is the optional slice/task namespace (omit for a standalone single task):

```bash
base=$(git rev-parse HEAD)       # or the base implement-feature assigned
root=$(git rev-parse --show-toplevel)
wt="$root/../.worktrees/impl-review-<id>${S:+/$S}"
git worktree add -b "impl/${S:+$S-}frontend-<id>" "$wt/frontend" "$base"   # if FE work
git worktree add -b "impl/${S:+$S-}backend-<id>"  "$wt/backend"  "$base"   # if BE work
```

The launcher does this for you (`launch.py launch --session-id <id> [--slice <S>] …`; see runner-invocations). If the repo has uncommitted (tracked) changes at start, ask the user to stash/commit first.

## During the tracks

Each implementer commits on its own branch inside its worktree. Review diffs are `git -C <wt/track> diff <base>..HEAD`. The two tracks use disjoint file scopes, so they run fully in parallel without clobbering.

## Integration

After both tracks are approved (or escalated), merge into an integration branch off `<base>`:

```bash
git switch -c impl/integration-<id>${S:+-$S} "$base"
git merge --no-ff impl/${S:+$S-}backend-<id>   -m "${S:+$S: }backend"
git merge --no-ff impl/${S:+$S-}frontend-<id>  -m "${S:+$S: }frontend"
```

Disjoint scopes should make this clean; resolve any conflict using both diffs (preserve each track's intent and the shared contracts). Run the final full-review on this integration branch.

## Verification

Run the project's detected commands on the integration branch; they must pass before done, and again after applying full-review findings:

```bash
git -C "$root" switch impl/integration-<id>${S:+-$S}
<detected test command>      # e.g. npm test, pytest, make test, cargo test
<detected build command>     # e.g. npm run build
```

Red → route to the responsible track (FE → `SendMessage`; BE → Codex `--resume`), fix, re-merge, re-test (≤3), then escalate. No test/build command → report that verification could not run.

## Cleanup

Do **not** delete worktrees/branches, push, or open a PR unless asked — leave the integration branch for the user to inspect or land. Report the branch name and worktree paths. The launcher's `cleanup` removes the session's worktrees; otherwise `git worktree remove <path>` then `git worktree prune`.

## Sequential fallback (no git)

When the project is not a git repo (or worktrees are declined), run the tracks **sequentially in the working tree** — no isolation, no merge: backend track end-to-end (Codex implements → Opus reviews → fix ≤3), then frontend (Opus subagent implements → Kimi reviews → fix ≤3) so the FE builds against settled backend contracts; verification on the working tree; full-review against the local diff. Note in the report that isolation was unavailable.
