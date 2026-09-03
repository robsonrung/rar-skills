---
name: verify-changes
description: "Run a target repository's own deterministic verification checks — install, build, typecheck, lint, test — by discovering its command surface (package.json scripts and packageManager, Makefile, justfile, Cargo, Go, Gradle/Maven, pyproject) instead of assuming a toolchain, scoped to the workspaces a diff touches when the repo supports it. Emits a machine-readable checks[] result plus a human pass/fail table; only captured command results count as evidence — narrative doesn't. Use when the user asks to verify this branch, run the repo's checks, or prove the build and tests pass, and as review-gate's verification phase in mode:pipeline. It never fixes anything: failures route to diagnose, it never modifies tests to make verification pass, and it never touches lockfiles or CI config. Not for launching the app interactively (run) or browser testing (browser-smoke)."
---

# Verify Changes

Produce hard evidence that a change passes the repository's own gates. This skill is a deterministic evidence producer: it discovers the repo's command surface, runs the checks in a fixed order, and reports captured results. It never judges code and never fixes anything — a failing check is a finding for `diagnose`, not a repair job for this skill.

## Modes

- **Manual (default):** interactive. You may ask which checks matter when the repo's surface is ambiguous, and you present the human table as the primary output.
- **Pipeline (`mode:pipeline`):** invoked by an automated caller — in this repo that is `review-gate`'s Phase 2. Never ask a question. Return only the structured result (the `checks[]` JSON per `references/checks-schema.json`) plus the one-line verdict. An ambiguous surface is resolved by the discovery precedence below, not by asking.

## Workflow

### 1. Discover the command surface

Follow `references/command-discovery.md`. In brief:

1. Detect every build system present (a monorepo may have more than one).
2. Prefer the repo's own named scripts (`typecheck`, `lint`, `test`, `build`, `check`) over reconstructed tool invocations — the repo's aliases carry its flags and environment.
3. Use CI config (`.github/workflows/`, `.gitlab-ci.yml`, etc.) as a **read-only oracle** for which commands the repo itself treats as gating. Never edit CI; read it to learn what "green" means here.
4. Record the discovered surface in `commandSurface` with its `source` (`scripts`, `makefile`, `ci`, or `reconstructed`).

### 2. Scope to the diff

Compute the workspaces/packages the diff touches (`git diff --name-only <base>...HEAD` mapped onto workspace roots). When the repo has a native scoping mechanism, use it — `npm --workspace` / `pnpm --filter` / `yarn workspace`, `turbo run --filter`, `nx affected`, per-crate `cargo -p`, per-module Go package paths. When it doesn't, run whole-repo and record `workspacesScoped.supported: false`. Resolve the base branch from `origin/HEAD`, then `gh repo view --json defaultBranchRef`, then `main` — never hardcode it.

### 3. Execute

Run in canonical order: **install → build → typecheck → lint → test**.

- Skip a rung only when the repo has no such command; record it as `not-applicable`, never omit it.
- A rung you deliberately chose not to run (e.g. caller passed a subset) is `skipped` with a note — a check that is absent from the report reads as "covered", and it wasn't.
- Capture each command's exit code, duration, and output tail to files under `${TMPDIR:-/tmp}/verify-changes-$(date +%s)` — never into the project tree.
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
- The working tree must be byte-identical after the run, apart from build artifacts and caches the repo's own commands produce. Verify with `git status --porcelain` and record `treeClean`.

## Gotchas

1. A dirty working tree is run as-is and noted in the report — never stash, reset, or `git clean`.
2. Monorepos with multiple build systems get each surface run and reported; don't pick a favourite.
3. Install steps honour the repo's own lockfile-respecting command (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) when one exists; the lockfile itself is never modified.
4. Long output goes to the evidence dir; the report carries the tail, not the transcript.
