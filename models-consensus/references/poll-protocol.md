# Poll Mode Protocol

Full protocol for `mode: poll` — blind poll + model-written reconciliation. Read-only, zero user interaction, deterministic termination: this is the mode pipelines call. Seat launch commands live in [runner-invocations.md](runner-invocations.md); this file holds the pipeline, the dedicated roles (organizer, judges, synthesizer), presets, and the report.

The pipeline is shaped by where multi-model gains actually come from: the **synthesis step is the dominant lever** (it is given to a real model, not hand-stitched by the orchestrator), and **model diversity is the secondary lever** (the default, but not mandatory).

## Hard rules

1. **The orchestrator is the moderator, not a seat.** Add no analysis, hints, or preferred answer before the seats respond — the opening fan-out must be blind so no orchestrator bias leaks in. Never count an orchestrator answer as a vote. The orchestrator does not write the consensus answer either — the synthesizer model does; the orchestrator validates it against the record.
2. **Read-only — no mutation.** Seats, organizer, judges, and synthesizer produce answers and opinions only; they never edit files, run mutating commands, or implement anything. Read-only *information* tools (web search/fetch, repo reads) are allowed only under an explicit shared tool profile — never write/exec tools, never by default.
3. **Blind opening.** Every seat gets the raw prompt (plus read-only repo context only when the task is about this repo), no peer answers, no "right" answer.
4. **Bounded reconciliation.** At most one gap-repair round, then a two-judge panel, then the orchestrator's final call. Never loop.
5. **Identical conditions across seats.** Same tool profile, same read-only sources, same budget for every active seat.
6. **Never fabricate a seat, judge, or diversity.** Missing CLI → drop the seat, lower confidence, say so. `--disable-fallback` on every runner. Duplicate (self-paired) seats are labeled same-model samples and lower **diversity confidence** — never reported as genuine model diversity.

## Seats

Seven core seats — opus, sonnet, codex, gemini, grok, kimi, glm — plus three optional roster seats — `qwen`, `gemma`, `muse` — that the preflight probe also checks. The optional seats join the fan-out only when the probe reports them available **and** the seat selection includes them: "Core seats only" excludes them, "All available" includes them, and a manual pick names them. They never join a fan-out silently (the probe keeps them `tier: backup`, so a bare probe without `--seat` flags cannot enlarge one). All seats launch by each seat's preferred path for the current host (native where available, runner otherwise). Seat → model ids, transports, and CLI dependencies: `shared/references/model-roster.md`; commands: [runner-invocations.md](runner-invocations.md). Poll seats take **no `--role` and no stance** — they answer the raw prompt.

**Quorum:** ≥ 3 seats. Below 3 distinct seats, first try self-pairing (below); if still short, degrade the whole run to `personas` mode on the strongest available model per SKILL.md.

**Self-pairing.** Running the same model more than once as independent labeled samples (`opus#1`, `opus#2`) is allowed two ways: auto-fallback to reach quorum, and a user-selectable preset even when distinct models exist (independent samples + synthesis help even without diversity). Launch duplicates with distinct labels in `--metadata-json` and distinct `--output-file`s; vary the brief trivially per sample (e.g. a `SAMPLE: n` line). Mark every duplicate `is_duplicate: true` in the seat table and lower diversity confidence; never present duplicates as diverse models.

**Shared-provider caveat.** The Opus and Sonnet seats are distinct models from one provider — count them as two seats but note the shared-provider caveat in diversity confidence (a milder drag than self-pairing). Same for any other pair of seats resolving to one provider.

## Presets

- `quality` (default) — all available distinct seats, strongest organizer/synthesizer, two judges.
- `budget` — ~3 cheap seats (e.g. glm + gemini + kimi; `gemma` and `qwen` are the two cheapest roster seats and are natural budget picks) + organizer + synthesizer; lighter synthesizer acceptable; note the lower confidence band. A cheap diverse panel can rival a single frontier model at materially lower cost.
- `research` — the `quality` panel + the `research_read_only` tool profile; require each seat to report `sources_used[]` and `failed_lookups[]`.

Record the run config (preset, tool profile, organizer/synthesizer/judge models) and the seat table in state before Phase 1. In `--auto`, the preset defaults to `quality` without asking.

## Dedicated roles

- **Organizer (Phase 2).** A fresh read-only model reads ALL seat answers and emits the five-dimension structured analysis — the substrate everything downstream consumes. In `quality` and `research`, default to the Opus seat model on every host: use a native subagent with `mode: "plan"` when available, otherwise `claude-runner --model opus --effort high`. In `budget`, use the Codex seat model. Fall back to the strongest available seat model.
- **Judges (Phase 4).** Two fresh read-only judges — default the Opus and Codex seat models — validate and challenge the organizer's analysis on the surviving open points (they consume it; they do not re-derive it).
- **Synthesizer (Phase 5).** A fresh read-only model writes the final consensus answer grounded in the record. Use the same preset-specific defaults as the organizer.

All three are user-selectable and recorded in the report. Each is a separate context from the seats, the orchestrator, and each other (SKILL.md, Shared Preflight step 6).
Task shaped role guidance lives in `shared/references/task-shaped-model-routing.md`.

## Schemas

Every poll phase has a bundled JSON Schema in `models-consensus/schemas/`. Pass it via `--output-schema` where the runner accepts one and validate the returned object before it enters the record ([operations.md#response-schema-validation](operations.md#response-schema-validation) for the retry/`malformed_output` path and the full cross-mode mapping).

| Phase / stage | Producer | Schema | Required top-level keys |
|---|---|---|---|
| 1 — blind fan-out | every seat | [../schemas/opening-answer.schema.json](../schemas/opening-answer.schema.json) | `answer`, `key_points`, `assumptions`, `confidence` (+ `sources_used`, `failed_lookups` under a research profile) |
| 2 — organize | organizer | [../schemas/organizer-analysis.schema.json](../schemas/organizer-analysis.schema.json) | `consensus`, `contradictions`, `partial_coverage`, `unique_insights`, `blind_spots`, `material_gaps` |
| 3 — gap repair (gated, one round) | every seat | [../schemas/disagreement-round.schema.json](../schemas/disagreement-round.schema.json) | `item_responses`, `confidence` |
| 4 — judge panel | each of two judges | [../schemas/judge.schema.json](../schemas/judge.schema.json) | `verdicts` |
| 5 — synthesis | synthesizer | [../schemas/synthesis.schema.json](../schemas/synthesis.schema.json) | `consensus_answer`, `attribution_map`, `confidence_rationale`, `confidence` |

`mode: debate` uses `round1-response.schema.json` / `later-round-response.schema.json` instead; `mode: personas` uses no JSON schemas.

## Phase 1 — Blind fan-out

Launch all available seats **concurrently** (all runner Bash calls + the native `Agent` calls in one message). Each seat gets the **raw prompt**, the answer schema, and the same tool profile — nothing else.

Conform to [../schemas/opening-answer.schema.json](../schemas/opening-answer.schema.json): `answer`, `key_points`, `assumptions`, `confidence` (plus `sources_used` / `failed_lookups` under a research profile).

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

Collect each seat's `agent_message` from its `--output-file` (not raw stdout). Validate; on malformed output retry once with a schema reminder, then drop the seat. A transient runner failure (`success=false` with no output file, e.g. `return_code -3` on a busy concurrent launch) may be retried once sequentially before dropping.

**Repo grounding (optional):** only when the task is about this repo, pass `CONTEXT.md`/ADRs and the relevant files as read-only context so seats use the project's vocabulary. Skip for general tasks.

## Phase 2 — Organize: structured analysis

Hand the **organizer** every seat's answer and have it emit the five-dimension analysis — the load-bearing artifact, produced by a model, not improvised by the orchestrator.

Conform to [../schemas/organizer-analysis.schema.json](../schemas/organizer-analysis.schema.json):

- **consensus** — points all/most seats share (higher-confidence; lock them).
- **contradictions** — material conflicts in conclusion/approach/key claim (`C1`, `C2`, …), with each seat's position.
- **partial_coverage** — points only some seats addressed (`P1`, …).
- **unique_insights** — valuable points raised by a single seat that no one contradicted (`U1`, …) — additive material a binary agree/disagree split would discard.
- **blind_spots** — necessary aspects of the task NO seat addressed (`B1`, …).

`agreements`/`disagreements` are derived views of this analysis, not the whole output. Keep a compact digest; never paste full answers forward. **The machine gate:** the schema's required `material_gaps` boolean decides Phase 3 — when the organizer sets it `false` (no material contradictions, blind spots, or contested unique insights; only trivial/wording differences), skip Phase 3 and go straight to judging/synthesis.

Organizer invocation: native `Agent` (`model: "opus"`, `mode: "plan"`) when available; otherwise `claude-runner --model opus --effort high --restrict-tools --disable-fallback` for `quality` and `research`, or `codex-runner --effort high --restrict-tools --disable-fallback` for `budget`. Apply the organizer schema without a role.

## Phase 3 — Gap-repair round (one round, gated)

Runs only when `material_gaps: true`. **Targeted repair, not re-voting:** for each open `C#`/`B#`/`U#`, send the neutral statement + every seat's position back to all seats and ask each to resolve the contradiction, fill the blind spot, or defend/refute the unique insight — with evidence. Exactly one round; increment the phase counter in state before launching.

Conform to [../schemas/disagreement-round.schema.json](../schemas/disagreement-round.schema.json): `item_responses` (`point_id`, `position`, `agree`, `reasoning`, `evidence`, `uncertainty`, `changes_answer`), `confidence`.

Re-moderate via the organizer: points the seats now converge on become consensus. Carry only the still-open points (+ the organizer analysis) to the judges.

## Phase 4 — Judge panel (two judges)

Spawn two fresh read-only judges on the still-open points. Each sees the open points, every seat's final position, and the organizer's structured analysis (validating/challenging it, not re-deriving it), rules on each point, and flags judge-sensitivity.

Conform to [../schemas/judge.schema.json](../schemas/judge.schema.json): `verdicts` (`point_id`, `ruling`, `rationale`, `confidence`, `sensitivity_note`).

A point is **resolved** when both judges rule the same way — adopt that ruling. When the judges split, the orchestrator decides and records it. If a central claim's resolution hinges on judge choice (or a low-capacity judge decided it), record that as confidence drag via `sensitivity_note`.

Judge invocations: Opus judge as a fresh native `Agent` (`model: "opus"`, `mode: "plan"`; a *different* subagent than the Opus seat); Codex judge via `codex-runner --restrict-tools --effort high --disable-fallback --output-schema <judge schema>` (no `--role`).

## Phase 5 — Synthesis, final call, report

1. **Final call.** For points the two judges split on, the orchestrator makes the final call and states the reasoning — recorded as a `sensitivity_note` confidence drag on the affected claims.
2. **Synthesize.** Hand the **synthesizer** the full record — organizer analysis, locked consensus, resolved/open points with rulings, all seat answers — and have it write the consensus answer + confidence rationale, conforming to [../schemas/synthesis.schema.json](../schemas/synthesis.schema.json) (`consensus_answer`, `attribution_map`, `confidence_rationale`, `confidence`). **Validate** the synthesis against the record — every claim must trace to consensus, a resolved point, a defended unique insight, or the orchestrator's final call; send back once if it drifts. Under `decider_context: report_only`, the synthesizer receives only the organizer report and rulings — no repo, no transcript, no orchestrator notes.
3. **Report.** Assemble the result inline, and in persisted mode write `.ai-workflow/consensus/{session_id}.md`:

   1. **Task** — the original prompt and run status (`consensus` / `judge-resolved` / `orchestrator-decided`).
   2. **Run config** — preset, tool profile, organizer/synthesizer/judge models, diversity confidence (lowered if self-paired).
   3. **Seats and judges** — who participated (duplicates marked); any unavailable/malformed, with reasons.
   4. **Consensus answer** — the synthesizer's single answer (the deliverable), honoring the shared output contract (verdict vocabulary, grounding gate, single next step).
   5. **Agreements** — locked consensus.
   6. **How disagreements resolved** — per point: positions → gap-repair outcome → judge rulings → final call (which were judge-decided vs. orchestrator-decided).
   7. **Blind spots and partial coverage** — from the organizer analysis.
   8. **Attribution map** — each major claim → its source (consensus / `U#` / judge resolution / orchestrator call).
   9. **Confidence** — answer confidence and diversity confidence, reported separately, with the band rationale.
   10. **Open caveats** — low-confidence decisions, judge-sensitivity flags, anything worth the user confirming.

## Call budget and resumability

Call budget: **2N + 4 model calls** for N active seats (N fan-out + 1 organizer + up to N gap-repair calls + 2 judges + 1 synthesizer) — 18 for the 7-seat core panel, 24 when all three optional seats join. Every phase boundary and round increment is written to state BEFORE launching (run-state contract), so a crashed run resumes at the next uncompleted phase instead of re-polling.

## Degrade gracefully (poll-specific)

- **< 3 distinct seats:** auto-engage self-pairing to reach quorum (labeled, diversity confidence lowered); if still < 3 total, degrade to `personas` mode per SKILL.md.
- **A seat fails/malformed:** retry once (sequentially for a transient runner failure), then drop it, continue, lower confidence one band.
- **Organizer or synthesizer unavailable:** fall back to the strongest available seat model for that role; if none, the orchestrator may perform the role manually but MUST flag it as a confidence drag in the report.
- **A judge unavailable:** run with the one available judge + the orchestrator's final call; note the reduced panel.
- **Inline artifact mode:** `report_path=null`; keep the digest in memory.

## Gotchas

- The opening fan-out is blind — no orchestrator analysis, summary, or leaning in the seat prompts.
- Don't collapse organizer/synthesizer/judges into the orchestrator to save a call — that re-introduces the orchestrator-stitched synthesis this pipeline removes.
- Keep host-model contexts separate: seat ≠ organizer/synthesizer ≠ judge ≠ orchestrator. A judge is always a fresh subagent.
- One gap-repair round, then judges, then the final call — don't turn it into an open-ended debate (that's `mode: debate`).
- Read-only throughout. To build from the consensus, hand off per SKILL.md's Handoff After Approval (explicit, post-approval only).
