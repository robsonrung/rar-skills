---
name: worktree
description: Set up an isolated git worktree for new work or an existing ref. Use when the user requests isolation or an implementation plan requires separate workspaces; reuse suitable existing isolation.
---

# Worktree Isolation

Put the work in an isolated workspace without disturbing the user's checkout. Reuse existing isolation first, then the harness's native worktree tool, then plain git, so every worktree you create is one the harness can see.

Two modes:

- **New work** (default): a fresh branch from the base branch.
- **Existing ref**: the caller names a PR, branch, tag, or commit, and the worktree attaches to it. Git checks a branch out in one worktree at a time. If the ref is already checked out, often in the primary checkout, report where and let the caller choose between working there and a detached worktree at the same commit.

## 1. Detect existing isolation

```bash
git rev-parse --absolute-git-dir
(cd "$(git rev-parse --git-common-dir)" && pwd -P)
```

Compare these two absolute paths. Raw `git rev-parse` output mixes relative and absolute forms and can give a false match.

- Equal: a normal checkout. Go to step 2.
- Different: run `git rev-parse --show-superproject-working-tree`. Non-empty output means a submodule; treat it as a normal checkout. Empty output means you are already in a linked worktree. Report its path and branch and work in place, checking the requested ref out here in existing-ref mode. A worktree created from inside a worktree lands in the wrong tree and is invisible to the harness.

## 2. Native tool

If the harness has a worktree tool, use it and stop: Claude Code's `EnterWorktree`, a `/worktree` command, or a `--worktree` flag. The harness then tracks and cleans up what it created.

## 3. Git fallback

1. `cd "$(git rev-parse --show-toplevel)"` so `.worktrees/` and the `.gitignore` edit land at the repo root.
2. Name the branch after the work, such as `feat/login` or `fix/email-validation`. The base is origin's default branch, else `main`.
3. Run `git check-ignore -q .worktrees/`. Keep the trailing slash: it matches a directory-only rule before the directory exists. If the path is not ignored, add `.worktrees/` to `.gitignore`.
4. Run `git fetch origin <base>`. A failure is fine; use the local ref.
5. Create the worktree:
   - New work: `git worktree add -b <branch> .worktrees/<branch> origin/<base>`, or the local `<base>` when `origin/<base>` is missing.
   - Branch or tag: `git worktree add .worktrees/<slug> <ref>`.
   - PR: check it out on a local branch, since a detached `FETCH_HEAD` orphans new commits. Run `git fetch origin pull/<n>/head:pr-<n>`, then `git worktree add .worktrees/pr-<n> pr-<n>`. For push tracking, including PRs from forks, run `git worktree add --detach .worktrees/pr-<n>`, then `gh pr checkout <n>` inside it.
6. `cd` into the new worktree.

On a sandbox or permission error, request permission through the host and retry with the same ref. If isolation stays blocked, report it; work in the user's checkout only after they say yes.

## Cleanup

Remove a worktree only when the user asks: `cd` out of it, then run `git worktree remove .worktrees/<branch>`.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
