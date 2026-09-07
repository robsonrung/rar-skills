---
name: verify-changes
description: "Run a repository's deterministic checks from its own command surface. Use when the user asks to verify a branch, run repository checks, or prove that build and tests pass. It captures command evidence, does not repair code, and does not replace browser testing."
---

# Verify Changes

Produce hard evidence that a change passes the repository's own gates. This skill is a deterministic evidence producer: it discovers the repo's command surface, runs the checks in a fixed order, and reports captured results. It never judges code and never fixes anything — a failing check is a finding for `diagnose`, not a repair job for this skill.

## Modes

1. **Manual (default):** run every discovered gate and present the human table. Ask only when the user explicitly limits the check set.
2. **Pipeline (`mode:pipeline`):** a non-interactive caller. Never ask a question. Return the structured result from `references/checks-schema.json` and one verdict. Resolve an ambiguous surface with the discovery precedence.

## Workflow

### 1. Discover the command surface

Follow `references/command-discovery.md`. In brief:

1. Detect every build system present (a monorepo may have more than one).
2. Prefer the repo's own named scripts (`typecheck`, `lint`, `test`, `build`, `check`) over reconstructed tool invocations — the repo's aliases carry its flags and environment.
3. Use CI config (`.github/workflows/`, `.gitlab-ci.yml`, etc.) as a **read-only oracle** for which commands the repo itself treats as gating. Never edit CI; read it to learn what "green" means here.
4. Record the discovered surface in `commandSurface` with its `source` (`scripts`, `makefile`, `ci`, or `reconstructed`).

### 2. Scope to the diff

Compute the workspaces/packages the branch diff touches. For the current worktree, include staged and unstaged changes. When the repo has a native scoping mechanism, use it. Otherwise run the whole repo and record `workspacesScoped.supported: false`. Resolve the base branch from `origin/HEAD`, then code-host metadata, then `main`.

### 3. Execute

Run in canonical order: **install → build → typecheck → lint → test**.

- Skip a rung only when the repo has no such command; record it as `not-applicable`, never omit it.
- A rung you deliberately chose not to run (e.g. caller passed a subset) is `skipped` with a note — a check that is absent from the report reads as "covered", and it wasn't.
- Capture each command's exit code, duration, and output tail in a temporary directory outside the project.
- Apply a per-check timeout ceiling (default 15 minutes; callers may override). A timed-out check is recorded with `result: timeout` and counts as a failure.

### 4. Report

Emit:

1. The machine result validated against `references/checks-schema.json`.
2. A human table: one row per check with command, result, and duration.
3. A one-line verdict: `PASS` (every executed check passed), `FAIL` (any `fail`/`timeout`), or `SKIP` (nothing was executed — a run that verified nothing is never reported as a pass).

## Evidence rules

- **Only captured command results count as evidence — narrative doesn't.** Writing "tests pass" proves nothing; the captured command, exit code, and duration are the result, and prose that disagrees with them is discarded.
- Never claim a check ran that you did not run.
- Never modify tests, source, lockfiles, or CI config to make a check pass. Fixing anything is out of scope; report the failure and stop.
- Capture the tracked working-tree baseline before the run and compare it after the run. `treeClean` reports whether the tree is clean after the run. `treeChanged` reports whether verification added tracked changes relative to the baseline. Do not make the tree clean by stashing, resetting, or cleaning it.

## Gotchas

1. A dirty working tree is run as-is and recorded as the baseline. Never stash, reset, or `git clean`.
2. Monorepos with multiple build systems get each surface run and reported; don't pick a favourite.
3. Install steps honour the repo's own lockfile-respecting command (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) when one exists; the lockfile itself is never modified.
4. Long output goes to the evidence dir; the report carries the tail, not the transcript.
