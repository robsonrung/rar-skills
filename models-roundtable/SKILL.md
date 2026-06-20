---
name: models-roundtable
description: Answer a task by polling several models blind, then reconciling them into one consensus answer. Fan the RAW prompt out to five seats (Codex, Gemini, Kimi, Opus 4.8, Sonnet 4.6) with no orchestrator analysis so the seats stay unbiased; a dedicated organizer maps the answers into a five-dimension structured analysis (consensus, contradictions, partial coverage, unique insights, blind spots), one bounded gap-repair round closes the open points, two judges (Opus + Codex subagents) validate the still-open ones, and a dedicated synthesizer writes the final consensus answer. Read-only — produces a consensus answer + report, not code. Use when you want a higher-confidence answer/decision/analysis than one model gives, a multi-model second opinion, or to reconcile differing model answers. Distinct from models-consensus (stance/role-driven rounds) and council (single blind round, Codex decides).
---

# Models Round Table

Answer one task with several models instead of one. Each model answers the **raw prompt blind** — you, the orchestrator, add no analysis, framing, or preferred answer before they respond, so the seats stay independent and unbiased. Then a dedicated **organizer** maps the answers into a five-dimension structured analysis, one bounded **gap-repair round** closes the open points, **two judges** validate the still-open ones, and a dedicated **synthesizer** writes the single consensus answer. The deliverable is that consensus answer plus a report of how it was reached.

The pipeline is shaped by where multi-model gains actually come from: the **synthesis step is the dominant lever** (it is given to a real model, not hand-stitched by the orchestrator), and **model diversity is the secondary lever** (kept as the default, but not mandatory).

Read-only: seats, organizer, judges, and synthesizer answer and analyze; they do not modify the repo. (Turning a consensus into code is the job of `feature-models-roundtable` / `implement-and-review`.)

## Hard Rules

1. **You are the moderator, not a seat.** Add no analysis, hints, or preferred answer before the seats respond — the opening fan-out must be blind so none of your bias leaks in. Never count your own answer as a vote. You do **not** write the consensus answer either — a synthesizer model does; you validate it against the record.
2. **Read-only — no mutation.** Seats, organizer, judges, and synthesizer produce answers/opinions only; they never edit files, run mutating commands, or implement anything. Read-only *information* tools (web search/fetch, repo reads) are allowed **only** under an explicit shared tool profile (see Preflight) — never write/exec tools, never by default.
3. **Blind opening.** Every seat gets the raw prompt (plus read-only repo context only when the task is about this repo), no peer answers, no "right" answer.
4. **Bounded reconciliation.** At most one gap-repair round, then a two-judge panel, then your final call. Do not loop indefinitely.
5. **Identical conditions across seats.** Every active seat in a run gets the **same** tool profile, the same read-only sources, and the same budget. Uneven tool access biases the panel.
6. **Never fabricate a seat, judge, or diversity.** Missing CLI/tool → drop the seat, lower confidence, and say so. Pass `--disable-fallback` to every runner so none silently borrows another provider. Duplicate (self-paired) seats must be **labeled** as same-model samples and must lower **diversity confidence** — never report them as genuine model diversity.

## Seats

Five default seats. Launch each by its preferred path for the current host; fall back only when the native path is unavailable.

| Seat | Claude Code host (primary) | Fallback |
|------|----------------------------|----------|
| Opus 4.8 | native `Agent` subagent, `model: "opus"` | `claude-runner --model claude-opus-4-8` |
| Sonnet 4.6 | native `Agent` subagent, `model: "sonnet"` | `claude-runner --model claude-sonnet-4-6` |
| Codex | `codex-runner` (`--effort high`) | native `spawn_agent` on a Codex host |
| Gemini | `gemini-runner` (Antigravity `agy`) | — (skip if `agy` missing) |
| Kimi | `kimi-runner --model kimi-code/kimi-for-coding` | — (skip if `kimi-cli` missing) |

**Quorum:** proceed only with **≥3 seats**.

**Heterogeneity is the default.** Distinct models are the panel's primary differentiator. **Self-pairing** (running the same model more than once as independent labeled samples — e.g. `opus#1`, `opus#2`) is allowed two ways: as an **auto-fallback** when fewer than the quorum of distinct CLIs is available, and as a user-selectable **preset** even when distinct models exist (multiple independent samples + synthesis help even without diversity). In both cases label the duplicates and lower **diversity confidence** (tracked separately from answer confidence); never present duplicates as diverse models.

Exact commands + the output envelope are in [references/runner-invocations.md](references/runner-invocations.md).

## Organizer & Synthesizer

- **Organizer (Phase 2).** A fresh read-only model (default Opus 4.8, or the strongest available) reads **all** seat answers and emits a five-dimension structured analysis — the substrate everything downstream consumes.
- **Synthesizer (Phase 5).** A fresh read-only model (default Opus 4.8) writes the final consensus answer grounded in the record (organizer analysis + locked agreements + resolved/open points + every seat answer). The orchestrator validates it against the record and assembles the report — it does **not** write the answer prose itself.

Both are user-selectable and **recorded in the report**. Keep them as separate contexts from the seats and judges.

## Judges (2)

Two judges — **Opus + Codex**, fresh read-only subagents — **validate and challenge** the organizer's analysis on the disagreements that survive the gap-repair round (they consume that analysis; they do not originate it). They see the open points + every seat's final position + the organizer's structured analysis, and rule on each, flagging judge-sensitivity.

Opus appears four ways (orchestrator, a seat, the organizer/synthesizer, a judge) — all **separate contexts**. A judge must be a different subagent than the Opus seat; the orchestrator is never a seat, organizer, synthesizer, or judge.

## Preflight

1. **Host & seats.** Detect the `Agent` tool (native Opus/Sonnet). Check `codex`, `agy` (Gemini), `kimi-cli` in `PATH`; mark missing seats `unavailable`. Enforce the ≥3 quorum, auto-engaging self-pairing only if needed to reach it.
2. **Preset.** Pick a preset (default `quality`); it bundles panel size, whether self-pairing is on, tool profile, per-seat budget, judge count, and synthesizer strength:
   - `quality` — all available distinct seats, strongest organizer/synthesizer, two judges.
   - `budget` — cheaper panel (e.g. Gemini + Kimi + one Claude), lighter synthesizer; note the lower confidence band. A cheaper diverse panel can still rival a single frontier model at materially lower cost.
   - `research` — `quality` panel + the `research_read_only` tool profile (below).
3. **Tool profile (identical for all seats).** Default `no_tools`. Choose by task type and apply the **same** profile + budget to every seat:
   - `no_tools` — default; best for repo/code decisions and self-contained reasoning.
   - `repo_read_only` — read the working repo (no web).
   - `research_read_only` — web search/fetch only (no repo); for research/multi-source/current-facts tasks. Require each seat to report sources used and failed lookups.
   - `repo_plus_research` — both, read-only.
   Never grant write/exec (e.g. bash mutation) — that violates Rule 2.
4. **Repo grounding (optional).** Only if the task is about this repo: collect `CONTEXT.md`/ADRs and the relevant files to pass as **read-only context** so seats use the project's vocabulary. For a general (non-repo) task, skip this.
5. **Artifact mode.** `persisted` when `.ai-workflow/` is writable → `.ai-workflow/roundtable/<session_id>/`; else `inline` (return paths `null`).
6. **Session id.** Short stable id (e.g. `roundtable-<slug>`); use it for the artifact dir and filenames.

Record a run config (preset, tool profile, organizer model, synthesizer model, judge models) and a seat table (`seat`, `execution_path`, `status`, `blocked_reason`, `is_duplicate`) before Phase 1.

## Phase 1 — Blind Fan-out

Launch all available seats **concurrently** (runner Bash calls + the Opus/Sonnet `Agent` calls in one message). Each seat gets the **raw prompt**, the answer schema, and the **same** tool profile — nothing else from you.

Conform to [schemas/opening-answer.schema.json](schemas/opening-answer.schema.json): `answer`, `key_points`, `assumptions`, `confidence` (plus `sources_used` / `failed_lookups` when a research profile is active).

Opening seat prompt shape:

```text
Answer the following task as well as you can. Be concrete and self-contained.
You cannot see other models' answers.

TASK:
<raw prompt verbatim>

CONTEXT (read-only, only if provided): <paths / glossary>
TOOLS (read-only, only if a profile is active): <web_search/web_fetch and/or repo reads>; report sources used and failed lookups.

Return ONLY JSON: {answer, key_points[], assumptions[], confidence[, sources_used[], failed_lookups[]]}
```

Collect each seat's `agent_message` from its `--output-file` (not raw stdout). Validate; on malformed output retry once with a schema reminder, then drop the seat. A transient runner failure (`success=false` with no output file) may be **retried once sequentially** before dropping.

## Phase 2 — Organize: Structured Analysis

Hand the **organizer** every seat's answer and have it emit the five-dimension analysis — this is the load-bearing artifact, so it is produced by a model, not improvised by you.

Conform to [schemas/organizer-analysis.schema.json](schemas/organizer-analysis.schema.json):
- **consensus** — points all/most seats share (higher-confidence; lock them).
- **contradictions** — points where seats materially conflict in conclusion/approach/key claim (id `C1`, `C2`, …), with each seat's position.
- **partial_coverage** — points only some seats addressed (id `P1`, …).
- **unique_insights** — valuable points raised by a single seat that no one contradicted (id `U1`, …) — additive material the binary agree/disagree split used to discard.
- **blind_spots** — necessary aspects of the task **no** seat addressed (id `B1`, …).

`agreements` and `disagreements` are **derived** views of this analysis, not the whole output. Keep a compact digest; never paste full answers forward. **Gate the next round here:** if the analysis surfaces no material contradictions, blind spots, or contested unique insights (only trivial/wording differences), **skip Phase 3** and go straight to judging/synthesis.

## Phase 3 — Gap-Repair Round (one round, skippable)

Run only when Phase 2 found material gaps. This is **targeted repair, not re-voting**: for each open `C#`/`B#`/`U#`, send the neutral statement + every seat's position back to all seats and ask each to resolve the contradiction, fill the blind spot, or defend/refute the unique insight — with evidence. One round only.

Conform to [schemas/disagreement-round.schema.json](schemas/disagreement-round.schema.json): `item_responses` (`point_id`, `position`, `agree`, `reasoning`, `evidence`, `uncertainty`, `changes_answer`), `confidence`.

Re-moderate via the organizer: any point the seats now converge on becomes consensus. Carry only the still-open points (+ the organizer analysis) to the judges.

## Phase 4 — Judge Panel (Opus + Codex)

Spawn two fresh read-only judge subagents — **Opus** and **Codex** — on the still-open points. Each judge sees the open points, every seat's final position, and the **organizer's structured analysis**, and **validates/challenges** it (it does not re-derive the analysis from scratch). Each rules on each point and flags judge-sensitivity.

Conform to [schemas/judge.schema.json](schemas/judge.schema.json): `verdicts` (`point_id`, `ruling`, `rationale`, `confidence`, `sensitivity_note`).

A point is **resolved** when both judges rule the same way. Adopt that ruling. If a central claim's resolution hinges on judge choice (or a low-capacity judge decided it), record that as **confidence drag** via `sensitivity_note`.

## Phase 5 — Synthesis, Final Call & Report

1. **Final call.** For points the **two judges still split on**, you (orchestrator) make the final call and state the reasoning.
2. **Synthesize.** Hand the **synthesizer** the full record — organizer analysis, locked consensus, resolved/open points with their rulings, all seat answers — and have it write the consensus answer + confidence rationale, conforming to [schemas/synthesis.schema.json](schemas/synthesis.schema.json) (`consensus_answer`, `attribution_map`, `confidence_rationale`, `confidence`). **Validate** the synthesis against the record (every claim must trace to consensus, a resolved point, a defended unique insight, or your final call); send back once if it drifts.
3. **Report.** Assemble the result inline, and write `.ai-workflow/roundtable/<session_id>/report.md` (persisted mode):

   1. **Task** — the original prompt and run status (`consensus` / `judge-resolved` / `orchestrator-decided`).
   2. **Run config** — preset, tool profile, organizer/synthesizer/judge models, **diversity confidence** (lowered if self-paired).
   3. **Seats & judges** — who participated (mark duplicates); any unavailable/malformed, with reasons.
   4. **Consensus answer** — the synthesizer's single answer (the deliverable).
   5. **Agreements** — locked consensus.
   6. **How disagreements resolved** — per point: positions → gap-repair outcome → judge rulings → final call (note which were decided by judges vs. the orchestrator).
   7. **Blind spots & partial coverage** — what no seat (or only some) addressed, from the organizer analysis.
   8. **Attribution map** — each major claim in the consensus answer → its source (consensus / unique insight U# / judge resolution / orchestrator call).
   9. **Confidence** — `high` (≥4 distinct seats, mostly agreement or clean judge resolution), `medium` (some orchestrator-decided points, a missing seat, or a self-paired panel), `low` (quorum barely met, heavy self-pairing, or key points decided with low confidence). Report **answer confidence** and **diversity confidence** separately.
   10. **Open caveats** — anything decided with low confidence or worth the user confirming, plus judge-sensitivity flags.

## Output Contract

Return:
1. `report_path` (or `null`)
2. the **consensus answer** (from the synthesizer)
3. the run config + seat/judge table (who → status, duplicates marked)
4. a concise "how disagreements resolved" summary, including any judge-sensitivity / diversity-confidence caveats

## Degrade Gracefully

- **< 3 distinct seats:** auto-engage self-pairing to reach quorum (labeled, diversity confidence lowered); if still < 3 total, stop and report which prerequisites are missing rather than running a thin table.
- **A seat fails/malformed:** retry once (sequentially for a transient runner `-3`); then drop it, continue, lower confidence one band.
- **Organizer or synthesizer unavailable:** fall back to the strongest available seat model for that role; if none, the orchestrator may perform the role manually but must flag it as a confidence drag in the report.
- **A judge unavailable** (e.g., no `codex`): run with the one available judge + the orchestrator's final call, and note the reduced panel.
- **Inline artifact mode:** return `report_path=null` and keep the digest in memory.

## Gotchas

- The opening fan-out is **blind** — do not prepend your own analysis, summary, or leaning; that is the whole point of the unbiased seats.
- Don't collapse organizer/synthesizer/judge back into the orchestrator to save a call — that re-introduces the orchestrator-stitched synthesis this pipeline removes, and you don't write the answer yourself (Hard Rule 1).
- Keep the Opus contexts separate: Opus seat ≠ Opus organizer/synthesizer ≠ Opus judge ≠ orchestrator. A judge must be a fresh subagent.
- Read each seat/judge result from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript).
- **Identical tool profile for every seat** — never give one seat tools another lacks. Never enable write/exec tools; never trust Fusion-style research numbers for code/long-horizon tasks (keep `no_tools` the default there).
- One gap-repair round, then judges, then your call — don't turn it into an open-ended debate (that's `models-consensus`).
- Read-only throughout. To build from the consensus, hand off to `feature-models-roundtable` / `implement-and-review`.
