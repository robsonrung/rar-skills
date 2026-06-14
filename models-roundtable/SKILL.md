---
name: models-roundtable
description: Answer a task by polling several models blind, then reconciling them into one consensus answer. Fan the RAW prompt out to five seats (Codex, Gemini, Kimi, Opus 4.8, Sonnet 4.6) with no orchestrator analysis so the seats stay unbiased; the orchestrator collects answers, separates agreements from disagreements, runs one disagreement round where each model sees the others' views and gives a final opinion, then convenes two judges (Opus + Codex subagents) on the still-open points and makes the final call. Read-only — produces a consensus answer + report, not code. Use when you want a higher-confidence answer/decision/analysis than one model gives, a multi-model second opinion, or to reconcile differing model answers. Distinct from models-consensus (stance/role-driven rounds) and council (single blind round, Codex decides).
---

# Models Round Table

Answer one task with five models instead of one. Each model answers the **raw prompt blind** — you, the orchestrator, add no analysis, framing, or preferred answer before they respond, so the seats stay independent and unbiased. Then you reconcile: separate agreement from disagreement, run one disagreement round, bring in two judges, and make the final call. The deliverable is a single consensus answer plus a report of how it was reached.

Read-only: seats and judges answer and analyze; they do not modify the repo. (Turning a consensus into code is the job of `feature-models-roundtable` / `implement-and-review`.)

## Hard Rules

1. **You are the moderator, not a seat.** Add no analysis, hints, or preferred answer before the seats respond — the opening fan-out must be blind so none of your bias leaks in. Never count your own answer as a vote.
2. **Read-only.** Seats and judges produce answers/opinions only; they do not edit files, run mutating commands, or implement anything.
3. **Blind opening.** Every seat gets the raw prompt (plus read-only repo context only when the task is about this repo), no peer answers, no "right" answer.
4. **Bounded reconciliation.** Exactly one disagreement round, then a two-judge panel, then your final call. Do not loop indefinitely.
5. **Never fabricate a seat or judge.** Missing CLI/tool → drop it, lower confidence, and say so. Pass `--disable-fallback` to every runner so none silently borrows another provider.

## Seats (5)

Launch each by its preferred path for the current host; fall back only when the native path is unavailable.

| Seat | Claude Code host (primary) | Fallback |
|------|----------------------------|----------|
| Opus 4.8 | native `Agent` subagent, `model: "opus"` | `claude-runner --model claude-opus-4-8` |
| Sonnet 4.6 | native `Agent` subagent, `model: "sonnet"` | `claude-runner --model claude-sonnet-4-6` |
| Codex | `codex-runner` (`--effort high`) | native `spawn_agent` on a Codex host |
| Gemini | `gemini-runner` (Antigravity `agy`) | — (skip if `agy` missing) |
| Kimi | `kimi-runner --model kimi-code/kimi-for-coding` | — (skip if `kimi-cli` missing) |

Quorum: proceed only with **≥3 seats**. Exact commands + the output envelope are in [references/runner-invocations.md](references/runner-invocations.md).

## Judges (2)

Two judges — **Opus + Codex**, fresh read-only subagents — rule on the disagreements that survive the disagreement round. They see only the open points and every seat's final position.

Opus appears three ways (orchestrator, a seat, a judge) — all **separate contexts**. A judge must be a different subagent than the Opus seat; the orchestrator is never a seat or a judge.

## Preflight

1. **Host & seats.** Detect the `Agent` tool (native Opus/Sonnet). Check `codex`, `agy` (Gemini), `kimi-cli` in `PATH`; mark missing seats `unavailable`. Enforce the ≥3 quorum.
2. **Repo grounding (optional).** Only if the task is about this repo: collect `CONTEXT.md`/ADRs and the relevant files to pass as **read-only context** so seats use the project's vocabulary. For a general (non-repo) task, skip this.
3. **Artifact mode.** `persisted` when `.ai-workflow/` is writable → `.ai-workflow/roundtable/<session_id>/`; else `inline` (return paths `null`).
4. **Session id.** Short stable id (e.g. `roundtable-<slug>`); use it for the artifact dir and filenames.

Record a seat table (`seat`, `execution_path`, `status`, `blocked_reason`) before Phase 1.

## Phase 1 — Blind Fan-out

Launch all available seats **concurrently** (runner Bash calls + the Opus/Sonnet `Agent` calls in one message). Each seat gets the **raw prompt** and the answer schema — nothing else from you.

Conform to [schemas/opening-answer.schema.json](schemas/opening-answer.schema.json): `answer`, `key_points`, `assumptions`, `confidence`.

Opening seat prompt shape:

```text
Answer the following task as well as you can. Be concrete and self-contained.
You cannot see other models' answers.

TASK:
<raw prompt verbatim>

CONTEXT (read-only, only if provided): <paths / glossary>

Return ONLY JSON: {answer, key_points[], assumptions[], confidence}
```

Collect each seat's `agent_message` from its `--output-file` (not raw stdout). Validate; on malformed output retry once with a schema reminder, then drop the seat.

## Phase 2 — Organize: Agreements vs. Disagreements

Normalize the answers into:
- **Agreements** — substantive points all seats' answers share (lock them).
- **Disagreements** — points where answers materially differ in conclusion, approach, or a key claim (not wording). Give each a stable id (`D1`, `D2`, …), a neutral one-line statement, and every seat's position.

Keep a compact digest; never paste full answers forward. If there are **no disagreements**, synthesize the consensus answer and go straight to the report.

## Phase 3 — Disagreement Round (one round)

For each `D#`, send the neutral statement **plus every seat's position** back to all seats and ask each for a **final opinion** — which view it now backs and why, or that it holds. One round only.

Conform to [schemas/disagreement-round.schema.json](schemas/disagreement-round.schema.json): `item_responses` (`point_id`, `position`, `agree`, `reasoning`), `confidence`.

Re-moderate: any `D#` the seats now converge on becomes an agreement. Carry only the still-open points to the judges.

## Phase 4 — Judge Panel (Opus + Codex)

Spawn two fresh read-only judge subagents — **Opus** and **Codex** — on the still-open points. Each judge sees the open `D#` set + every seat's final position and rules on each.

Conform to [schemas/judge.schema.json](schemas/judge.schema.json): `verdicts` (`point_id`, `ruling`, `rationale`, `confidence`).

A point is **resolved** when both judges rule the same way. Adopt that ruling.

## Phase 5 — Final Call & Report

For points the **two judges still split on**, you (orchestrator) make the **final call** and state the reasoning. Then assemble the result.

Deliver inline, and write `.ai-workflow/roundtable/<session_id>/report.md` (persisted mode):

1. **Task** — the original prompt and run status (`consensus` / `judge-resolved` / `orchestrator-decided`).
2. **Seats & judges** — who participated; any unavailable/malformed, with reasons.
3. **Consensus answer** — the single synthesized answer to the task (the deliverable).
4. **Agreements** — what all seats already shared.
5. **How disagreements resolved** — per `D#`: the positions → disagreement-round outcome → judge rulings → final call (note which were decided by judges vs. by the orchestrator).
6. **Confidence** — `high` (≥4 seats, mostly agreement or clean judge resolution), `medium` (some orchestrator-decided points or a missing seat), `low` (quorum barely met or key points decided with low confidence).
7. **Open caveats** — anything decided with low confidence or worth the user confirming.

## Output Contract

Return:
1. `report_path` (or `null`)
2. the **consensus answer**
3. the seat/judge table (who → status)
4. a concise "how disagreements resolved" summary

## Degrade Gracefully

- **< 3 seats:** stop and report which prerequisites are missing rather than running a thin table.
- **A seat fails/malformed:** drop it, continue, lower confidence one band.
- **A judge unavailable** (e.g., no `codex`): run with the one available judge + the orchestrator's final call, and note the reduced panel.
- **Inline artifact mode:** return `report_path=null` and keep the digest in memory.

## Gotchas

- The opening fan-out is **blind** — do not prepend your own analysis, summary, or leaning; that is the whole point of the unbiased seats.
- Opus seat ≠ Opus judge ≠ orchestrator. Keep the three Opus contexts separate; a judge must be a fresh subagent.
- Read each seat/judge result from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript).
- One disagreement round, then judges, then your call — don't turn it into an open-ended debate (that's `models-consensus`).
- Read-only throughout. To build from the consensus, hand off to `feature-models-roundtable` / `implement-and-review`.
