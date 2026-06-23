---
name: ship
description: Conduct a complete feature pipeline from idea to PR — interactive framing, specification, and task planning up front, then autonomous design-gated, test-driven, reviewed delivery per task. Use when the user says ship this, ship it, run the full pipeline, build this feature end to end, take this from idea to PR, or wants autonomous execution after an approved plan. Do not use for single small edits, pure reviews, or pure diagnosis — invoke the specific skill instead.
---

# Ship

Run a feature through three interactive phases and four autonomous phases. All human judgment is collected before the approval gate; after it, escalate to multi-model consensus instead of asking the user. This skill contains no phase knowledge of its own — every behavior is a referenced skill.

## Pipeline

| Phase | Mode | Invoke |
|---|---|---|
| 0. Frame | interactive, optional | `brainstorm` (fuzzy idea); `prototype` (design unknown only running code can settle) |
| 1. Specify | interactive | `grill-with-docs` then `to-spec`; high-stakes or contested: `collaborative_discovery` then `collaborative_specification`. Run the `security-gate` spec-time checklist during the interview. |
| 2. Plan | interactive — last human gate | `to-tasks` (default) or `collaborative_task_design` (needs per-task test plans), then apply the `to-tasks` Slice Contract to its output. User approves the breakdown. |
| 3. Design gate | autonomous, per task | `coding-design-plan`, then `design-gate` with the slice's lens flags |
| 4. Implement | autonomous, per task | `tdd` + `safe-incremental-coding` with `coding-implementation-guard` active; `safe-incremental-coding` builds a characterization-test net first when touching untested legacy code; `diagnose` for bugs found mid-work |
| 5. Verify | autonomous | ordered, fail-fast: run the acceptance contract → `full-review` (deep security pass when flagged by `security-gate`) → `coding-review-simplify` → `verify`. Failures loop to phase 4 via `diagnose`. |
| 6. Deliver | autonomous | commit, open PR, move the issue's triage label, write a `summarize` handoff note. The human merges. |

Skip phases 0–1 when the input is already a PRD or approved spec; skip to phase 3 when approved slices already exist.

## Slice Contract

The Slice Contract — machine-checkable `acceptance` commands plus `gates` flags for `design-gate` and `security-gate`, HITL/AFK classification with HITL scheduled first, and the `ready-for-agent` / `TASKS.md` work queue — is defined in `to-tasks`. Phase 2 must produce slices carrying it; phases 3–6 consume it.

## Autonomous loop

For each ready slice, in dependency order:

1. Create an isolated worktree for the slice.
2. Run phases 3–6.
3. On completion, pick up the next ready slice. Independent slices may run in parallel worktrees.
4. On a blocked slice (escalation ladder exhausted at a hard-stop), record why, skip it, continue with unblocked slices, and list all blocked slices in the final report.

For long-running slices, preserve context with `codex-mission-control` or `handoff` rather than degrading in a bloated context window.

## Escalation ladder (replaces mid-flight questions)

When an autonomous phase hits a contested or irreversible decision:

1. Run `models-consensus` (or the lighter `council` with `--auto` — never plain `council`, whose default mode interviews the user) — multi-model deliberation substitutes for the user.
2. Still unresolved: pick the most reversible default, record assumption + rationale in a decision log carried into the PR body, proceed.
3. Hard-stop and wait for the human only for destructive or irreversible operations (data deletion, force-push, external publication, irreversible migration against real data).

## PR contract

The PR body must contain: acceptance evidence (commands run, output), design-gate verdicts, review summary, decision log with flagged assumptions, and remaining risks. Report outcomes faithfully — failed or skipped checks are stated, never smoothed over.

## Gotchas

1. Do not collapse phases to save time; the gates are the quality mechanism.
2. Do not ask the user anything after the phase 2 approval gate except at a hard-stop.
3. Do not write phase behavior here or inline — invoke the referenced skill so knowledge stays in one place.
4. Do not start phase 4 on a slice whose blockers are incomplete.
5. Do not mark a slice done without its acceptance commands passing in the worktree.
