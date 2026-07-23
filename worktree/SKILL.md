---
name: worktree
description: "Set up an isolated git worktree — create a fresh branch for new work, or attach a worktree to an existing branch, PR, or commit to work on it in isolation. Use when the user asks to set up a git worktree, isolate work on a branch/PR/commit, or attach a worktree to an existing PR. Detects existing isolation first and prefers the harness-native worktree tool. Not for implement-and-review, which owns its own two-track worktree flow internally."
---

# Worktree Isolation

Ensure the current work happens in an isolated workspace, without disturbing the user's main checkout. Most coding harnesses now create a worktree by default at session start, so the common case is that **isolation already exists** — detect that first and do not create a redundant one.

Order of operations: **detect existing isolation -> prefer the harness-native worktree tool -> fall back to plain git.** Never create a worktree the harness cannot see.

**Two modes, set by the caller's need:**

- **New work (default).** No specific ref named — create a fresh branch from a base (trunk).
- **Isolate an existing ref.** The caller names a ref to work on in isolation — a PR head, an existing branch, or a commit. Attach the worktree to that ref instead of creating a new branch. One hard git rule governs this mode: **a branch can be checked out in only one worktree at a time.** If the named ref is already checked out somewhere (most commonly because it is the current branch in the primary checkout), do **not** create a second worktree for it — report that it is already checked out at `<path>` and let the caller act (work there in place; or, only if a clean separate tree is essential, create a *detached* worktree at the same commit). Never put one branch in two worktrees.

The steps below (detect -> native tool -> git fallback) apply to both modes; the mode only changes what gets checked out and is reported back to the caller.

## Step 0: Detect existing isolation

Before creating anything, check whether the current directory is already a linked worktree. Compare the **resolved absolute** git dir against the **resolved absolute** common git dir — resolve each to an absolute path first and compare those, not the raw `git rev-parse` output. Git mixes absolute and relative forms depending on the current directory (from a subdirectory of a normal checkout, `--git-dir` comes back absolute while `--git-common-dir` may be relative), so a raw string compare yields a false "already isolated":

```bash
git rev-parse --absolute-git-dir                     # absolute git dir for this worktree
(cd "$(git rev-parse --git-common-dir)" && pwd -P)   # absolute shared (common) git dir
```

If the two absolute paths are **equal**, this is a normal checkout — continue to Step 1.

If they **differ**, you are in a linked worktree *or* a submodule. Distinguish them:

```bash
git rev-parse --show-superproject-working-tree
```

- **Non-empty** output -> you are in a submodule; treat it as a normal checkout and continue to Step 1.
- **Empty** output -> you are **already in an isolated worktree**. Report the worktree path (`git rev-parse --show-toplevel`) and current branch. Do not create another worktree — a worktree-from-worktree lands in the wrong tree and is invisible to the harness that made the current one. Then **work in place**: in new-work mode, continue here; in isolate-an-existing-ref mode, check that ref out here (unless it is already the current branch) rather than nesting a worktree.

## Step 1: Prefer the harness-native worktree tool

If the harness provides a native worktree primitive, use it and stop. In Claude Code that is the **EnterWorktree** tool; other harnesses may expose a `/worktree` command or a `--worktree` flag. Native tools place, track, and clean up the worktree so the harness can manage it. A behind-the-back `git worktree add` creates phantom state the harness cannot see, navigate to, or clean up.

## Step 2: Git fallback

Only when there is no native tool **and** Step 0 found no existing isolation.

1. **Run from the repo root.** The `.worktrees/` and `.gitignore` paths below are repo-root-relative, but the skill runs from the user's current directory, which may be a subdirectory — so move to the root first: `cd "$(git rev-parse --show-toplevel)"`. Without this, `.worktrees/<branch>` and the `.gitignore` edit would land in the subdirectory (e.g. `src/.worktrees/...`, `src/.gitignore`) instead of at the repo root.
2. Choose a meaningful branch name from the work description (e.g. `feat/login`, `fix/email-validation`) — avoid opaque auto-generated names. Pick a base branch (default: origin's default branch, else `main`).
3. **Ensure `.worktrees/` is gitignored before creating anything**, so worktree contents are never committed: check `git check-ignore -q .worktrees/` — **with the trailing slash**, so an existing directory-only `.worktrees/` rule is honored even before the directory exists (`git check-ignore .worktrees` without the slash would miss it and dirty a correctly-configured repo). If it is not ignored, add a `.worktrees/` line to `.gitignore`.
4. Best-effort refresh the base branch without disturbing the current checkout: `git fetch origin <from-branch>`. This is **non-fatal** — if it errors (no `origin` remote, a differently-named remote, or a local-only branch), do not abort; continue to the next step and use the local ref.
5. Create the worktree — the command depends on the mode:
   - **New work:** `git worktree add -b <branch-name> .worktrees/<branch-name> origin/<from-branch>` (use the local `<from-branch>` ref if `origin/<from-branch>` does not exist). This creates a new branch from the base.
   - **Isolate an existing ref:** attach to the ref instead of branching — for an existing branch or tag, `git worktree add .worktrees/<slug> <target-ref>`. For a **PR**, check it out **on a local branch** (never a detached `FETCH_HEAD` — that orphans the fix loop's commits instead of updating the PR): `git fetch origin pull/<n>/head:pr-<n>` then `git worktree add .worktrees/pr-<n> pr-<n>`. (To get push-tracking back to the PR instead, create the worktree detached first — `git worktree add --detach .worktrees/pr-<n>` — then `cd` in and run `gh pr checkout <n>`, which is fork-safe and also works for PRs from forks.) If git reports the ref is already checked out elsewhere, follow the already-checked-out rule under **Two modes** — do not force a second worktree.
6. Switch into it: `cd .worktrees/<branch-name>` (or `.worktrees/<slug>`).

If `git worktree add` fails with a sandbox or permission error, the requested isolation could not be created. This needs a **blocking** user decision before touching the current checkout — do not silently continue there (the user chose isolation specifically to avoid it). Report the failure and ask via the harness's blocking question tool — in Claude Code, `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded) — offering options such as "work in the current checkout" vs "stop and resolve the permission issue". If no blocking tool exists in the harness or the call errors, present the numbered options in chat and wait for the reply; never skip the confirmation. Only work in the current checkout on explicit confirmation, and do not retry alternative paths automatically.

## Other worktree operations

Use `git` directly — no wrapper is needed:

```bash
git worktree list                          # list worktrees
git worktree remove .worktrees/<branch>    # remove a worktree
cd .worktrees/<branch>                     # switch to a worktree
cd "$(git rev-parse --show-toplevel)"      # return to the current checkout root
```

## When to create a worktree

Create one (Step 1/2) only when you are **not** already isolated and you need a separate workspace:

- Reviewing or fixing a PR while keeping the current checkout free for other work
- Running multiple features in parallel without branch-switching overhead

Do not create a worktree for single-task work that can happen on a branch in the current checkout — and never when Step 0 shows you are already in one.

## Troubleshooting

**"Worktree already exists"**: the path is in use. Switch to it (`cd .worktrees/<branch>`) or remove it (`git worktree remove .worktrees/<branch>`) before recreating.

**"Cannot remove worktree: it is the current worktree"**: `cd` out of the worktree first, then `git worktree remove`.

---

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
