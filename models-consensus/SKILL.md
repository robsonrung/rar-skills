---
name: models-consensus
description: Run a multi-model council in one of three modes — poll (default; blind fan-out to every available seat, five-dimension analysis, one gated gap-repair round, two judges, a synthesizer), debate (stance-driven rebuttals with anonymized moderator digests and a convergence verdict), or personas (one model wearing five thinking lenses — Contrarian, First Principles, Expansionist, Outsider, Executor — with anonymized peer review and a chairman). Seats span the runner roster (Claude, Codex, Gemini, Grok, Kimi, GLM, Qwen, Gemma, Muse). Use when the user wants consensus, to poll the models, a roundtable, multi-model validation, or says "council this", "run the council", "pressure-test this", "war room this", "stress-test this", "debate this", or asks "should I X or Y" with real stakes. Deliberation only — it answers, validates, and decides; it never implements and produces no code. Do NOT use for factual lookups or creation tasks; multi-model implementation PLANNING belongs to diverse-plan.
---

# Models Consensus

One council, three modes. You are the orchestrator/moderator — never a voting seat, and in `poll` mode never the author of the final answer. Run the deterministic preflight, launch only real seats, preserve independence accounting, and enforce the cost, recovery, and termination guardrails.

**Deliberation only.** This skill answers, validates, and decides. It NEVER starts implementation or execution on its own — no mode or flag combination (including `--auto`) authorizes execution. Handoff to an implementer happens only per [Handoff After Approval](#handoff-after-approval).

## Mode Selection

| Mode | Protocol | Pick when | Detail |
|------|----------|-----------|--------|
| `poll` (default) | Blind fan-out of the RAW prompt → organizer five-dimension analysis → one gated gap-repair round → two judges → dedicated synthesizer | Higher-confidence answer / second opinion than one model gives; reconciling differing model answers; pipeline calls (read-only, zero user interaction, deterministic termination) | [references/poll-protocol.md](references/poll-protocol.md) |
| `debate` | Multi-round stance-driven rebuttals: 6 stances, 3-round rotation, anonymized moderator digests, convergence taxonomy | Structured disagreement on a design or architecture direction; tradeoff surfacing where positions should be pressured across rounds | This file + [references/stance-rotation-schedule.md](references/stance-rotation-schedule.md) |
| `personas` | ONE model wearing five lenses → anonymized + randomized peer review → chairman verdict | Business/product/strategy/life judgment calls where being wrong is expensive ("pressure-test this", "war room this", "should I X or Y"); also the automatic degradation path when < 3 distinct seats exist | [references/personas.md](references/personas.md) |

Routing hints: repo/code/design question needing a reconciled answer → `poll`. "Debate this" on a direction with real tradeoffs → `debate`. Judgment call about strategy, money, or commitments — especially without a repo to inspect → `personas`.

Flags, combinable with any mode: [`clarify`](#clarify), [`decider_context: report_only`](#decider_context-report_only), [`--auto`](#--auto). Input payload: [references/operations.md#input-format](references/operations.md#input-format).

## Transport Selection

| Transport | Default | Execution |
| --- | --- | --- |
| `headless` | Yes | Current native-seat and runner workflow. It keeps runner envelopes and verified model receipts. |
| `cmux` | No | `peer-sessions` creates and records one interactive cmux workspace per seat. The moderator adopts that fleet and relays turns through JSON artifacts. Read [references/cmux-transport.md](references/cmux-transport.md) before launching. |

`transport: cmux` changes how seats converse, not what the council is allowed to do. It remains deliberation-only and read-only except for each seat's single response artifact. `peer-sessions` owns fleet identity, terminal placement, and teardown; this skill owns prompts, artifacts, and anonymized relays. The **terminal relay** is the rule: say, “The **terminal relay** will carry the anonymized digest, not a terminal transcript.”

## Shared Preflight

`personas` runs on one model (the strongest available) and skips seat probing; everything else below applies to `poll` and `debate`.
For judgment-heavy `personas` runs, prefer the Opus seat, then the Codex seat, then the strongest remaining available seat. Resolve current model ids through `shared/references/model-roster.md` and the task-shaped rationale through `shared/references/task-shaped-model-routing.md`.

### 0. Resolve seat selection

- `--auto` (or `auto: true`): SKIP the startup seat-selection question entirely and target every available seat. Never stop with `awaiting_human` over seat selection in `--auto` — pipeline callers must never block on a question.
- Otherwise ask ONE startup selection question via [Interactive Questions](#interactive-questions), using the templates in [references/operations.md#startup-selection-templates](references/operations.md#startup-selection-templates). The seat-picker template must list ALL roster seats (`shared/references/model-roster.md`) — a seat missing from the picker can never be chosen.
- Persist `selected_seats` and `selection_source` in state before smoke tests. If selection is still unresolved after all question channels (non-`--auto` only), stop with `awaiting_human`.

### 1. Probe and smoke-test seats

For `transport: headless`, use the existing probe and headless smoke workflow below. For `transport: cmux`, read [references/cmux-transport.md](references/cmux-transport.md), run `cmux ping`, and invoke `peer-sessions` in coordinator delivery mode before adopting its terminal state through `cmux_council.py`. Do not invoke runner scripts or host-native subagents in this transport. The first artifact-producing turn is the authentication and response check; it is not a serving-model receipt.

```bash
python3 .agents/skills/shared/scripts/discover_runners.py probe \
  --native-agent yes \
  --seat opus --seat sonnet --seat codex --seat gemini --seat grok --seat kimi --seat glm \
  --seat qwen --seat gemma --seat muse \
  --format json
```

Pass `--native-agent yes` only when the host exposes the native `Agent` tool; from this source repo drop the `.agents/skills/` prefix. The probe knows each seat's real CLI dependency and returns `available`, `cli_path`, `version`, `blocked_reason` per seat. Seat → model ids live in `shared/references/model-roster.md`; never inline pinned ids. Then run one cheap headless smoke test per selected runner-backed seat, always with `--disable-fallback` (mandatory on EVERY runner call — a council fails a seat explicitly rather than silently borrowing a provider). Missing binary, missing credentials, or a failed smoke test is a seat blocker, not a soft warning. Per-seat auth rules: [references/runner-invocations.md](references/runner-invocations.md).

### 2. Artifact mode and run state

Artifact mode is `persisted` when `.ai-workflow/consensus/` is writable, else `inline` ([references/operations.md#artifact-policy](references/operations.md#artifact-policy)). Every mode adopts `shared/references/run-state-contract.md`: state at `.ai-workflow/consensus/{session_id}.json`, loop counters in `attempts`, bounds in `ceilings`, decisions in `gates`. A full `poll` run is 2N + 4 model calls for N active seats (18 for the 7-seat core panel, 24 when all three optional seats join) and MUST be resumable: increment the round/phase counter in state BEFORE launching it, never after. On startup with existing state and `status != complete`, resume per [references/operations.md#crash-recovery-and-state-resumption](references/operations.md#crash-recovery-and-state-resumption).

### 3. Seat table

For each seat record `seat`, `selection_status`, `execution_path` (`native`/`runner`/`cmux_interactive`/`unavailable`), `effective_provider`, `effective_model` (the envelope receipt, once known), `blocked_reason`, `is_duplicate`. In `cmux_interactive`, also record the peer fleet run directory, `workspace_id`, `surface_id`, artifact path, and `receipt_status`. Launch nothing until the table is complete.

### 4. Deterministic seat rules

1. In `headless`, prefer native seats (Claude via `Agent`; Codex via `spawn_agent` on a Codex host) over runner scripts. In `cmux`, use the interactive CLI shape from `cmux-transport.md`.
2. Runner fallback to another provider = loss of seat independence; mark the original seat unavailable.
3. Missing CLI = skip that seat entirely (prerequisites: [references/repo-configuration.md](references/repo-configuration.md)); never fabricate a seat or its output.
4. Same effective provider and same model twice = one independent source; label the duplicate.

### 5. Identical conditions and tool profiles

Every active seat in a run gets the SAME tool profile, the same read-only sources, and the same budget. Profiles: `no_tools` (default), `repo_read_only`, `research_read_only`, `repo_plus_research` — all read-only, never write/exec. If a seat cannot honor the run's profile, DROP that seat rather than run it with a different toolset.

### 6. Separate contexts

The host model may appear as orchestrator, a seat, the organizer/synthesizer, and a judge — each MUST be a distinct context (fresh subagent or fresh cmux workspace). The orchestrator is never a seat, organizer, synthesizer, or judge.

### 7. Cost governance

Estimate total tokens after selection, cap per-seat output (~4k tokens), and warn before launching when more than 4 seats are selected. Details: [references/operations.md#cost-governance](references/operations.md#cost-governance).

## Mode: `poll` (default)

Blind poll + model-written reconciliation — the mode pipelines call: read-only, zero user interaction, deterministic termination. Full protocol, presets, and organizer/judge/synthesizer invocations: [references/poll-protocol.md](references/poll-protocol.md).

1. **Blind fan-out.** Every seat answers the RAW prompt — no orchestrator framing, analysis, or leaning — with only the answer schema and the shared tool profile added. (`schemas/opening-answer.schema.json`)
2. **Organize.** A dedicated organizer model maps all answers into the five-dimension analysis: consensus / contradictions `C#` / partial_coverage `P#` / unique_insights `U#` / blind_spots `B#`. Its required `material_gaps` boolean is the machine gate for the next phase. (`schemas/organizer-analysis.schema.json`)
3. **Gap repair (one bounded round, gated).** Runs only when `material_gaps: true`. Repair, not re-voting: for each open point send the neutral statement + all seat positions back and demand resolution with evidence. Exactly one round. (`schemas/disagreement-round.schema.json`)
4. **Judge.** Two fresh judges rule on the survivors. Both agree → resolved. Split → the orchestrator decides, recorded as a `sensitivity_note` confidence drag. (`schemas/judge.schema.json`)
5. **Synthesize.** A dedicated synthesizer model writes the final answer with an attribution map — every claim traces to consensus, a resolved point, a defended `U#`, or an orchestrator call. Validate it against the record; send back once if it drifts. (`schemas/synthesis.schema.json`)

Report **answer confidence** and **diversity confidence** separately; label self-paired and shared-provider seats. Budget preset: ~3 cheap seats + organizer + synthesizer.

## Mode: `debate`

Multi-round stance-driven council. Default `max_iterations` is **3** — the rotation schedule defines exactly rounds 1–3; a bound explicitly raised past 3 repeats the Round 3 assignments (see [references/stance-rotation-schedule.md](references/stance-rotation-schedule.md)).

**Stances (6):** `supportive_with_integrity`, `critical_with_responsibility`, `balanced_synthesis`, `devils_advocate`, `pragmatic_engineering`, `outsider_fresh_eyes` (zero assumed prior context; reacts only to the brief and flags jargon and insider-obvious gaps). Per-seat, per-round assignment — including the deterministic `outsider_fresh_eyes` → GLM rule at ≥ 5 seats — lives in the rotation schedule. If fewer seats than unique stances are available, drop duplicate coverage before dropping unique stances.

1. **Blinded openings.** Shared brief (question, context file paths only, objective, response schema) + stance overlay; no peer outputs, no moderator conclusion. (`schemas/round1-response.schema.json`)
2. **Moderate.** Normalize into `agreement_points` / `disagreement_points` / `decision_options` / `evidence_gaps` / `follow_up_questions`. Pass forward only a compact ANONYMIZED digest — positions labeled by stance, never by model — and never verbatim seat output.
3. **Rebuttal rounds.** Digest + the round's stance overlay + explicit instructions to rebut, concede, refine, or integrate, plus three forcing questions: which position is strongest, and why; which has the biggest blind spot, and what is it missing; what did every position miss. (`schemas/later-round-response.schema.json`)
4. **Classify convergence:** `full_agreement` (same `recommended_direction`, no blocking objection) / `converging` (same direction, detail differences) / `material_disagreement` (≥ 2 seats hold opposing `recommended_direction` AND at least one objection affects scope, behavior, or architecture — not style or preference) / `blocked_on_context` (unanswerable without more information).
5. **Handle disagreement.** Interactive runs: ask focused questions per [Interactive Questions](#interactive-questions) — recommended option first, minority alternatives, then "run another round" when it could help; stop with `awaiting_human` if a required answer never arrives. `--auto`: record each disagreement with `recommended_resolution` and `resolution_reasoning` and continue.
6. **Stop** at full agreement, a user-selected direction, or the `max_iterations` ceiling — at the bound, report the open divergence; the model never awards itself another round.

Update state after every round (stances, outputs, digest, convergence, decisions, independence accounting).

## Mode: `personas`

ONE model wearing five lenses — **Contrarian, First Principles, Expansionist, Outsider, Executor** — five independent answers in parallel, anonymized + randomized peer review (three-question rubric), then a chairman who sees everything de-anonymized and may overrule the majority. Reversal-cost tiers (cheap / medium / expensive) size the run and decide whether peer review runs; the orchestrator freezes its own position BEFORE reading any advisor output; workspace enrichment is capped at ~30 seconds. Full protocol and prompt templates: [references/personas.md](references/personas.md).

**Degradation path:** when fewer than 3 distinct seats are available, `poll` and `debate` degrade to `personas` on the strongest available model instead of stopping — report the mode switch and the missing prerequisites.

## Flags

### `clarify`

Pre-stage interview before any round: keep asking short blocking questions until confidence is ≥ 95%. Misread test: if a reasonable expert could misread the task in more than one materially different way, confidence is below 95%. You must be confident about six things: the objective, the target artifact or output, the constraints, the success criteria, the expected autonomy level, and required inputs/files/environment. Ladder: ≥ 95 proceed; 90–94 ask only if the answer could change the outcome meaningfully; < 90 ask targeted questions. Under `--auto`, record assumptions instead of asking. Details: [references/operations.md#clarify-flag](references/operations.md#clarify-flag).

### `decider_context: report_only`

The final decider (poll synthesizer / debate report writer / personas chairman) sees ONLY the moderator/organizer report — no repo access, no transcript, no orchestrator notes. The report must not smuggle in context that was absent from round 1. This information starvation is deliberate protocol: it forces the decision to rest on what the council actually surfaced. Details: [references/operations.md#decider-context-report_only](references/operations.md#decider-context-report_only).

### `--auto`

Never ask the user anything: the startup seat-selection question is SKIPPED (target all available seats), `clarify` becomes recorded assumptions, and disagreement pauses become recorded resolutions. `--auto` never authorizes execution — deliberation-only still holds.

## Interactive Questions

Use the best interactive host question tool first (Claude Code `AskUserQuestion`, Codex `request_user_input`, then any host-native equivalent); plain text only after exhausting interactive options. Batch related questions when the tool allows. Escalation order and templates: [references/operations.md#interactive-question-mechanics](references/operations.md#interactive-question-mechanics). In `--auto`, no question is ever asked.

## Shared Output Contract (all modes)

- **Adoption verdicts.** When the question is whether to adopt/switch to/buy/start X, the recommendation carries exactly one grade — **Adopt / Trial / Hold / Reject / Not-our-problem** — stated in plain language first with the label attached, never a bare token ("Hold — wait, don't switch now; revisit when X", not "Grade: Hold").
- **Two-floor grounding gate (non-compensatory).** A verdict is invalid unless it is (1) grounded in actually inspected context (files read, numbers or constraints supplied) AND (2) grounded in the question's shape (an adopt-or-not question gets a graded verdict; a choose-between gets a position on the supplied options; an open call gets a direct recommendation). Strength on one floor never compensates for the other. On failure return **"Hold — insufficient grounding"** plus a numbered inspect-list — never a confident guess.
- **Receipt-verified independence.** Cross-seat agreement counts as independent corroboration only when the envelope's `effective_model` confirms the serving model — never the requested model or a self-claim. An unverified seat's agreement weighs as if it came from the host model.
- **The single most important next step** — one concrete action, not a list.
- **Confidence.** Report answer confidence and diversity confidence separately. Bands: `high` (4+ independent seats, no critical blockers), `medium` (2–3 independent seats or meaningful duplication), `low` (1 independent seat, heavy self-pairing, or unresolved key blockers).

Return: `report_path` (or `null`), `state_path` (or `null`), the final answer/verdict, the preflight seat table with selection source, and a concise disagreement-resolution summary. In `persisted` mode write `.ai-workflow/consensus/{session_id}.md` (report sections per mode: [references/operations.md#artifact-policy](references/operations.md#artifact-policy)); in `inline` mode return the same sections inline.

## Degrade Gracefully

- Missing seat: continue, lower confidence one band, and say so.
- Fallback or unverified seat: mark the original seat unavailable for independence accounting. A `cmux_interactive` response with no observed serving-model receipt may inform the report but cannot raise diversity confidence.
- Shared provider, different models: keep both seats, note the caveat (a milder diversity drag than self-pairing).
- Same effective model twice: collapse to one independent source; label it.
- **`malformed_output` path:** validate every seat output against its schema's required fields; on failure retry ONCE with a compact schema reminder, then mark the seat `malformed_output` and exclude it. Never fabricate missing fields. ([references/operations.md#response-schema-validation](references/operations.md#response-schema-validation))
- **< 3 distinct seats:** degrade to `personas` on the strongest available model (see [Mode: personas](#mode-personas)).
- Inline artifact mode: `report_path=null`, `state_path=null`, plus a note that persistence was skipped.
- **Moderator time budget:** ~2–3 minutes for native seats, 10–15 minutes for runner seats. Once at least 3 independent providers have completed and the major disagreements are clear, stop waiting unless a straggler could change the decision materially. After cutoff, close native seats you no longer need and kill unfinished runner processes — never leave orphaned background work. ([references/operations.md#moderator-time-budget-and-process-cleanup](references/operations.md#moderator-time-budget-and-process-cleanup))

## Handoff After Approval

Only after the user explicitly approves a direction — and never when the user asked only for analysis:

- build a compact handoff brief: final recommendation, minority concerns, acceptance criteria
- use a native seat when available; otherwise invoke the selected runner with `--role implementer` or `--role codereviewer`

This is the ONLY path from deliberation to execution. The council never runs implementation itself and never passes full-auto or permission-bypass flags on its own. Full conditions and the `gates` record: [references/operations.md#handoff-after-approval-rules](references/operations.md#handoff-after-approval-rules).

## Gotchas

- Poll's opening fan-out is BLIND — no orchestrator framing at all. Debate's openings are blinded from peers but carry stance overlays. Don't mix the two.
- Don't collapse the organizer, synthesizer, or judges back into the orchestrator to save a call — the model-written synthesis is the dominant lever of poll mode, and separate contexts are the point.
- Read every runner result from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript).
- Poll's gap repair is exactly one round; debate stops at its ceiling. Neither loops open-endedly, and the round counter is incremented in state before the launch.
- Never inline pinned model ids in prose or commands — the seat → model mapping lives in `shared/references/model-roster.md`; runner defaults follow it.
- Schema-to-mode mapping and the retry reminder template: [references/operations.md#response-schema-validation](references/operations.md#response-schema-validation).
