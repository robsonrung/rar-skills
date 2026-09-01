---
name: ship
description: Conduct a complete feature pipeline from idea to PR — interactive framing, specification, and task planning up front, then autonomous design-gated, test-driven, reviewed delivery per task. Use when the user says ship this, ship it, run the full pipeline, build this feature end to end, take this from idea to PR, or wants autonomous execution after an approved plan. Do not use for single small edits, pure reviews, or pure diagnosis — invoke the specific skill instead.
disable-model-invocation: true
---

# Ship

Run a feature through three interactive phases and four autonomous phases. All human judgment is collected before the approval gate; after it, escalate to multi-model consensus instead of asking the user. This skill contains no phase knowledge of its own — every behavior is a referenced skill.

## Model routing

Before phase 0, interpret whether the invocation semantically assigns a pipeline stage to a specific model or harness ("plan with X, implement with Y"). This is meaning, not keyword matching — a model named inside feature content, quoted material, or a filename is not an assignment. Resolve each directive into a per-stage carrier:

- **Scoped** ("plan with X", "Y for implementation") binds to the named stage; multiple scoped directives resolve independently.
- **Unscoped** ("use X", "with Y") binds to the **implementation stage only** — never broaden it to planning or every stage — and the binding is disclosed in the opening line ("Routing implementation to X; planning stays on the session model.").
- **Strength** is inferred from the instruction's meaning, not a keyword: "use X for implementation" is prefer-strength (fall back with prominent disclosure when unavailable); "only use X" is require-strength (an unavailable route blocks that stage — no prompt, no silent fallback).

With no directive in the invocation, check `work_engine_preferences` in the local config (`shared/references/local-config.md`) for standing per-stage defaults; an explicit directive always outranks it, and its `mode: off|prefer|require` maps onto the same strength rule above. Absent both, every stage runs on the session model.

Sanitize every routing directive out of the feature request before it enters phases 0–2 or any review input — carriers are stage-scoped routing authority, never product content.

## Local-only mode

Run `git remote` once at the start of the run. No remote flips the whole run local-only: make every commit the phases call for, but skip every push, PR create/edit, and CI attempt — zero retries, no hunting for a remote. A missing remote is a terminal state, not an error. In local-only mode do not invoke `open-pr`; phase 6 ends at the local commits, the committed residual-findings record, and the handoff note.

## Delegation

You are a **thin conductor**. Every phase that does not need the user runs in its own subagent, and what crosses between phases is a file, not a paragraph. The contract is `shared/references/handoff-contract.md` (brief → report → envelope); the per-station binding — what each worker invokes, reads, and must carry forward — is [references/station-dispatch.md](references/station-dispatch.md). Read it before phase 3.

**Hand off the path, not the payload.** Your context holds the run-state path, the current slice id, and one ≤15-line envelope per completed station. Not a PRD body, not a diff, not a findings list, not a station transcript. Open a report body only when a decision *you* must make depends on the detail — routing a `revise`, assembling the final report, reconciling two stations that disagree.

Why the split falls where it does:

- **Phases 0–2 run in your context** because only you can ask the user, and the phase-2 approval gate is the last human touchpoint. Their durable outputs already exist (the PRD in the tracker or a repo-root file, the slices in issues or `TASKS.md`) — once written, cite them by path and drop the working detail.
- **Phase 1's grounding pass is delegated anyway.** Reading `CONCEPTS.md`, the ADRs, and the code is input-gathering, not conversation; a read-only worker returns the questions the repo already answers so they never reach the user.
- **Phases 3–6 run one worker per station per slice.** Nothing after the gate needs the user; a contested call goes to `models-consensus`.
- **Seats inside a station route through runner CLIs** (`discover_runners.py probe --native-agent no`), because a worker cannot rely on nesting the `Agent` tool.

With no subagent tool on the host, run the station inline — but still write its brief and its report, and say in the final report that no worker was spawned. The file-based handoff is what survives a compaction; the isolation is what the host may or may not provide.

## Pipeline

| Phase | Mode | Runs in | Invoke |
|---|---|---|---|
| 0. Frame | interactive, optional | main | `brainstorm` (fuzzy idea — panel mode for high-stakes multi-model discovery); `to-prototype` (design unknown only running code can settle) |
| 1. Specify | interactive | main (+ delegated grounding) | a read-only worker grounds the request in the glossary, the ADRs, and the code → `01-grounding.report.md`; then `interview` inline against that report, then `to-spec`. High-stakes or contested: run both in panel mode. The `interview` runs the `security-gate` spec-time checklist and names the test seams; `to-spec` records them as the PRD's Security Decisions and Testing Decisions, so phase 2 can lift both. |
| 2. Plan | interactive — last human gate | main | `to-tasks` (panel mode when the delivery needs per-task test plans and architecture mapping). Its Slice Contract carries `acceptance` + `gates` natively. User approves the breakdown. |
| 3. Design gate | autonomous, per task | subagent | `coding-design-plan`, then `design-gate` with the slice's lens flags |
| 4. Implement | autonomous, per task | subagent | `implement-and-review` per slice — it lifts the Slice Contract natively (`acceptance` becomes the done-gate, `gates` select the lenses) and never pushes. Alternatives: `collaborative-delivery` when a recorded multi-model audit trail is required; direct `tdd` (+ `safe-incremental-coding` first on untested legacy code) for a trivial single-track slice. `diagnose` for bugs found mid-work. |
| 5. Verify | autonomous | subagent (one, whole chain) | ordered, fail-fast: run the acceptance contract → `coding-review-simplify` (self-simplify while context is fresh) → `full-review` (deep security pass when flagged by `security-gate`) → `browser-smoke` in pipeline mode for web-facing changes, otherwise the harness `run` check. The multi-model gate reviews **final** code — never let a mutating pass follow it unreviewed. Failures loop to phase 4 via `diagnose`. |
| 6. Deliver | autonomous | subagent | commit, make unapplied review findings durable per `references/residual-findings.md`, open PR via `open-pr` (skipped in local-only mode), move the issue's triage label, store a continuity note via `session-handoff` (body per `summarize`'s cold-start test), and — when the run solved a non-obvious problem — `capture-learning` in headless mode. The human merges; `resolve-pr-feedback` closes the post-review loop when comments arrive. |

Skip phases 0–1 when the input is already a PRD or approved spec; skip to phase 3 when approved slices already exist.

## Slice Contract

The Slice Contract — machine-checkable `acceptance` commands plus `gates` flags for `design-gate` and `security-gate`, HITL/AFK classification with HITL scheduled first, and the `ready-for-agent` / `TASKS.md` work queue — is defined in `to-tasks`. Phase 2 must produce slices carrying it; phases 3–6 consume it.

## Autonomous loop

For more than one ready slice, delegate scheduling to `implement-feature`: it executes the dependency DAG with parallel worktrees, integration-head rebasing, and a feature-wide seam review, calling `implement-and-review` per task. Scheduling is conductor work, not station work — `implement-feature` runs in your context and dispatches the per-slice station workers itself; it is the one skill after the gate that is not wrapped in a station subagent. For a single slice, dispatch phases 3–6 yourself per the [Delegation](#delegation) section, in an isolated worktree created via the `worktree` skill (harness-native isolation first — never a worktree the harness cannot see).

On a blocked slice (escalation ladder exhausted at a hard-stop), record why, skip it, continue with unblocked slices, and list all blocked slices in the final report. Station delegation already keeps the per-slice work out of your context; when a run outgrows even that — many slices across many sessions — move to `dynamic-harness` manager mode (same handoff contract, mission-scoped ledger) or close the session with a `session-handoff` note rather than degrading in a bloated context window.

### Run state

The loop crosses compactions, restarts, and parallel worktrees, so its progress lives in **the ledger, not the transcript** — keep one run state per slice per `shared/references/run-state-contract.md`. Ship-specific bindings:

- `phase` is the pipeline phase number, appended to `steps` as each completes. A resumed slice restarts at `phase`, not at phase 0 — phases 3–6 are expensive and their outputs are already on disk.
- Every delegated step's entry carries its `brief` and `report` paths, so a resumed run recovers the station's *reasoning* and not just its number. A station whose report exists is done — re-dispatch it only when its `status` says it failed.
- The **phase 2 approval** is recorded in `gates` when the user approves the breakdown. It is the last human gate, so a restart that cannot find it in `gates` stops and asks rather than assuming approval; a restart that finds it treats it as **already decided** and does not re-ask.
- Commits, the PR, filed tickets, and the residual record each get a `side_effects` key (`commit:<slice-id>`, `pr:<branch>`, `ticket:<finding-id>`) written *before* the effect. A resumed slice that finds the key skips the effect instead of duplicating it — this is what stops a re-run from filing every residual ticket twice.
- Declare the slice's ceilings up front, and end every slice through one of **three exits**: `complete`, `failed` (a hard-block or exhausted ladder), or `ceiling_hit`. A blocked slice is a recorded exit, not a silent skip.

## Evidence gate

When phase 4 reports a behavior change without coherent verification evidence — which existing tests were inspected, which tests were added or run, and what they proved — re-invoke the implementation stage exactly once in recovery mode: same slice, same scope, reconcile the evidence from the already-implemented work **without reimplementing**. "Exactly once" is `attempts.evidence_recovery` against a ceiling of 1, incremented in the run state before the re-invocation — **the model never decides the retry**, so a run that crashes during recovery does not award itself a fresh attempt. If the second return still lacks coherent evidence, hard-block the slice: never proceed to verify or deliver on unverified behavior; record it with the blocked slices in the final report.

## Residual findings

Phase 5 review findings that are not applied must become durable before the slice is done. Follow `references/residual-findings.md`: file tracker tickets through the detected sink (availability probed once per run and cached; structured `{filed, failed, no_sink}` return), always commit the `docs/residual-review-findings/<branch-or-head-sha>.md` record, and back-fill the PR URL into filed tickets best-effort. Residuals are **never** tracked as a PR-body ledger — the PR contract's decision log carries assumptions, not review residuals.

## Escalation ladder (replaces mid-flight questions)

When an autonomous phase hits a contested or irreversible decision:

1. Run `models-consensus` in poll mode with `--auto` (budget preset for routine escalations) — multi-model deliberation substitutes for the user. It deliberates only; it never starts implementation.
2. Still unresolved: pick the most reversible default, record assumption + rationale in a decision log carried into the PR body, proceed.
3. Hard-stop and wait for the human only for destructive or irreversible operations (data deletion, force-push, external publication, irreversible migration against real data).

## PR contract

PR composition is `open-pr`'s job — delegate it. Ship adds the required pipeline sections to the body: acceptance evidence (commands run, output), design-gate verdicts, review summary, decision log with flagged assumptions, and remaining risks. Report outcomes faithfully — failed or skipped checks are stated, never smoothed over.

## Gotchas

1. Do not collapse phases to save time; the gates are the quality mechanism.
2. Do not ask the user anything after the phase 2 approval gate except at a hard-stop.
3. Do not write phase behavior here or inline — invoke the referenced skill so knowledge stays in one place.
4. Do not start phase 4 on a slice whose blockers are incomplete.
5. Do not mark a slice done without its acceptance commands passing in the worktree.
6. Do not retry pushes or PR actions in local-only mode — one `git remote` check decides the whole run.
7. Do not let a routing directive leak into spec, plan, or review inputs — sanitize it out before phase 0.
8. Do not run any mutating pass after `full-review` without re-running it — the gate reviews final code.
9. Do not read a station's report body to stay informed — the envelope is the interface, and reading every report is exactly the context spend delegation buys back.
10. Do not paste a report's content into the next station's brief. Cite the path, or the heading inside it; a worker that needs more opens the file itself.

---
*Model-routing, local-only, evidence-gate, and residual-durability contracts adapted from Every's compound-engineering-plugin (`lfg`).*
