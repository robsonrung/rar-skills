---
name: ship
description: Conduct a complete feature pipeline from idea to PR — interactive framing, specification, and task planning up front, then autonomous design-gated, test-driven, reviewed delivery per task. Use when the user says ship this, ship it, run the full pipeline, build this feature end to end, take this from idea to PR, or wants autonomous execution after an approved plan. Do not use for single small edits, pure reviews, or pure diagnosis — invoke the specific skill instead.
---

# Ship

Run a feature through three interactive phases and four autonomous phases. All human judgment is collected before the approval gate; after it, escalate to multi-model consensus instead of asking the user. This skill contains no phase knowledge of its own — every behavior is a referenced skill.

## Model routing

Before phase 0, interpret whether the invocation semantically assigns a pipeline stage to a specific model or harness ("plan with X, implement with Y"). This is meaning, not keyword matching — a model named inside feature content, quoted material, or a filename is not an assignment. Resolve each directive into a per-stage carrier:

- **Scoped** ("plan with X", "Y for implementation") binds to the named stage; multiple scoped directives resolve independently.
- **Unscoped** ("use X", "with Y") binds to the **implementation stage only** — never broaden it to planning or every stage — and the binding is disclosed in the opening line ("Routing implementation to X; planning stays on the session model.").
- **Strength** is inferred from the instruction's meaning, not a keyword: "use X for implementation" is prefer-strength (fall back with prominent disclosure when unavailable); "only use X" is require-strength (an unavailable route blocks that stage — no prompt, no silent fallback).

Sanitize every routing directive out of the feature request before it enters phases 0–2 or any review input — carriers are stage-scoped routing authority, never product content.

## Local-only mode

Run `git remote` once at the start of the run. No remote flips the whole run local-only: make every commit the phases call for, but skip every push, PR create/edit, and CI attempt — zero retries, no hunting for a remote. A missing remote is a terminal state, not an error. In local-only mode do not invoke `open-pr`; phase 6 ends at the local commits, the committed residual-findings record, and the handoff note.

## Pipeline

| Phase | Mode | Invoke |
|---|---|---|
| 0. Frame | interactive, optional | `brainstorm` (fuzzy idea); `prototype` (design unknown only running code can settle) |
| 1. Specify | interactive | `grill-with-docs` then `to-spec`; high-stakes or contested: `collaborative_discovery` then `collaborative_specification`. Run the `security-gate` spec-time checklist during the interview; `to-spec` records the answers as the PRD's Security Decisions and names the test seams, so Phase 2 can lift both. |
| 2. Plan | interactive — last human gate | `to-tasks` (default) or `collaborative_task_design` (needs per-task test plans), then apply the `to-tasks` Slice Contract to its output. User approves the breakdown. |
| 3. Design gate | autonomous, per task | `coding-design-plan`, then `design-gate` with the slice's lens flags |
| 4. Implement | autonomous, per task | `tdd` + `safe-incremental-coding` with `coding-implementation-guard` active; `safe-incremental-coding` builds a characterization-test net first when touching untested legacy code; `diagnose` for bugs found mid-work. Panel-gated alternative when an audit trail of multi-model participation is required: `collaborative_delivery`. |
| 5. Verify | autonomous | ordered, fail-fast: run the acceptance contract → `full-review` (deep security pass when flagged by `security-gate`) → `coding-review-simplify` → `verify`. Failures loop to phase 4 via `diagnose`. |
| 6. Deliver | autonomous | commit, make unapplied review findings durable per `references/residual-findings.md`, open PR (skipped in local-only mode), move the issue's triage label, write a `summarize` handoff note. The human merges. |

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

## Evidence gate

When phase 4 reports a behavior change without coherent verification evidence — which existing tests were inspected, which tests were added or run, and what they proved — re-invoke the implementation stage exactly once in recovery mode: same slice, same scope, reconcile the evidence from the already-implemented work **without reimplementing**. If the second return still lacks coherent evidence, hard-block the slice: never proceed to verify or deliver on unverified behavior; record it with the blocked slices in the final report.

## Residual findings

Phase 5 review findings that are not applied must become durable before the slice is done. Follow `references/residual-findings.md`: file tracker tickets through the detected sink (availability probed once per run and cached; structured `{filed, failed, no_sink}` return), always commit the `docs/residual-review-findings/<branch-or-head-sha>.md` record, and back-fill the PR URL into filed tickets best-effort. Residuals are **never** tracked as a PR-body ledger — the PR contract's decision log carries assumptions, not review residuals.

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
6. Do not retry pushes or PR actions in local-only mode — one `git remote` check decides the whole run.
7. Do not let a routing directive leak into spec, plan, or review inputs — sanitize it out before phase 0.

---
*Model-routing, local-only, evidence-gate, and residual-durability contracts adapted from Every's compound-engineering-plugin (`lfg`).*
