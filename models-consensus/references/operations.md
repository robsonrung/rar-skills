# Operations Reference

Operational detail for models-consensus: startup selection templates, interactive question mechanics, cost governance, crash recovery, response schema validation, artifact policy, runner launch policy, input format, the `clarify` and `decider_context` flags, the moderator time budget, and the handoff rules. Read the relevant section when its trigger in SKILL.md fires. This file is mode-agnostic — per-mode pipelines live in [poll-protocol.md](poll-protocol.md), SKILL.md (`debate`), and [personas.md](personas.md).

## Startup Selection Templates

Question templates for preflight step 0 (seat selection). Ask via the Interactive Questions protocol; prefer one multi-select question over a series of yes/no prompts. Skipped entirely under `--auto`.

**The picker must list every roster seat the probe reports as a candidate.** A seat missing from the picker can never be chosen, so build the option list from the probe output against `_shared/references/model-roster.md` — never from a hand-remembered subset. Use seat names, not pinned model ids.

**Multi-select template** (preferred; include `All available (Recommended)` plus every detected candidate seat, omitting only seats absent from `candidate_seats`):

```text
Which models to use?
[ ] All available (Recommended)
[ ] Claude Opus (native, else claude-runner)
[ ] Claude Sonnet (native, else claude-runner)
[ ] Codex (native on a Codex host, else codex-runner)
[ ] Gemini (gemini-runner / agy)
[ ] Grok (grok-runner)
[ ] Kimi (kimi-runner / cline)
[ ] GLM (glm-runner / cline)
```

If the probe also reports backup seats from the roster (`qwen`, `gemma`, `minimax`) or the secondary `codex-code` seat as available, append them as options in the same list — the rule is one option per available roster seat, no exceptions.

**Small single-choice menu** (when the host tool cannot multi-select):
1. `All available (Recommended)`
2. `Core seats only`
3. `Specify seats manually`

If the user chooses manual selection, ask one concise follow-up listing the detected seat IDs and accept a comma-separated subset. Use an interactive follow-up question when the host supports one; use a plain-text seat-picking follow-up only when needed.

**Plain-text template** (last resort, when no interactive selection tool is available):

```text
Which models to use?
Detected seats: <comma-separated seat IDs>
Reply with a comma-separated subset or 'all'.
```

Set `selection_source=plain_text_manual` when this fallback branch is used, and wait for user input.

## Interactive Question Mechanics

Preferred host mappings:
- Claude Code: `AskUserQuestion`
- Codex: `request_user_input` when the current mode exposes it
- any other host: the equivalent native interactive question/input tool, if available
- only if none of the above are available: a concise plain-text question with 2-3 options

Rules:
- Never choose plain text just because an interactive tool is less convenient.
- If only one question fits per interactive call, use repeated interactive calls rather than switching to plain text.
- When the host supports multiple questions in one call, batch related questions together to reduce back-and-forth.

## Cost Governance

Multi-model councils can be expensive. Enforce cost transparency before launching seats.

**Pre-flight cost estimate:**
- After seat selection, estimate total token volume: `(selected_seats.count) × (avg_input_tokens + avg_output_tokens)`.
- Use rough defaults: ~4k input tokens per seat (brief + context), ~2k output tokens per seat.
- Warn the user when >4 seats are selected in non-auto mode: "Council will invoke N models, roughly X tokens total across providers. Proceed?"

**Token budgets:**
- Cap per-seat output at ~4k tokens for moderation feasibility.
- If shared brief + context files exceed ~8k tokens per seat, truncate or summarize context files before the round.
- Prefer concise briefs over verbatim file dumps.

**Cost-conscious defaults:**
- In non-`--auto` runs, make "Core seats only" the recommended startup choice rather than "all available."
- When `--auto` selects 5+ seats, emit a cost warning before the first round.
- Track cumulative token usage across rounds in state for post-council reporting, but only from runners that actually emitted `usage` (see [runner-invocations.md](runner-invocations.md) — do not assume the field exists). The ceiling that always holds is the round count in `attempts.round` against `ceilings.max_iterations`, because it is counted here rather than reported by the provider.

## Crash Recovery and State Resumption

Council state is resumable — **the ledger, not the transcript**. Treat `.ai-workflow/consensus/{session_id}.json` as the source of truth for progress.

State follows `_shared/references/run-state-contract.md`; council-specific keys (stances, seat outputs, digests, convergence, independence accounting) sit alongside the contract's own. `status` takes exactly the contract's values: `running`, `awaiting_human`, `complete`, `failed`, `ceiling_hit`, `cancelled` — the resume test below is a lookup against that set, not an inference.

**Resume handshake:**
- At preflight, check if `state_path` exists and `status != complete`.
- If resuming, load prior round outputs, seat assignments, and moderator digests from state.
- Set `resumed_from` to the previous state's `last_completed_round`.
- Skip to the next uncompleted round; do not re-run completed rounds.
- A question already answered in `gates` is **already decided** — resume without re-asking the user.

**Bounded rounds:** `max_iterations` lives in `ceilings`, and the round number lives in `attempts.round`. Increment it in state *before* launching the round, not after — a council that crashes mid-round has still spent that round. At the bound, stop and report the open divergence: **the model never decides the retry**, and it does not decide to award itself another round either.

**Orphaned process cleanup:**
- When resuming, identify any runner PIDs or background tasks from the prior session and terminate them before launching new seats.
- For `transport: cmux`, retain the recorded workspace and surface IDs for recovery, but do not close a workspace automatically. Closing a user-visible workspace needs explicit user direction; mark it stale and start a fresh workspace only when the user authorizes it.
- In `inline` mode, recovery is limited to what fits in the current context; persist key digests to state when possible.

**State update cadence:**
- In `persisted` mode, write state after every iteration.
- In `inline` mode, still build the same state structure in memory so it can be returned or persisted if the mode changes.

## Response Schema Validation

Validate every model output before accepting it into the digest/analysis. Outputs ARE schema-validated against the bundled schemas below.

### Schema → mode and stage

| Schema file (`models-consensus/schemas/`) | Mode | Stage / producer |
|---|---|---|
| `opening-answer.schema.json` | `poll` | Phase 1 — every seat's blind answer to the raw prompt |
| `organizer-analysis.schema.json` | `poll` | Phase 2 — the organizer's five-dimension analysis (its `material_gaps` boolean gates Phase 3) |
| `disagreement-round.schema.json` | `poll` | Phase 3 — each seat's one bounded gap-repair response |
| `judge.schema.json` | `poll` | Phase 4 — each of the two judges' verdicts on the still-open points |
| `synthesis.schema.json` | `poll` | Phase 5 — the synthesizer's consensus answer + attribution map |
| `round1-response.schema.json` | `debate` | Round 1 — each seat's blinded, stance-carrying opening |
| `later-round-response.schema.json` | `debate` | Rounds 2..N — each seat's rebuttal/refinement after the anonymized digest |
| — | `personas` | No JSON schemas: advisors, reviewers, and the chairman return prose in the fixed section structure of [personas.md](personas.md) |

Pass the matching schema via `--output-schema` to seats that accept it — Codex and Grok validate it natively (`grok-runner` forwards it to grok's own `--json-schema`); Cline-backed seats accept the flag but enforce it by prompt. Gemini and Claude seats have no schema flag; for them (and as a backstop for everyone) the brief's trailing `Return ONLY JSON …` line holds the shape, and the moderator validates against the field lists below.

**`poll` required fields** (top level, per schema): opening answer — `answer`, `key_points`, `assumptions`, `confidence` (plus `sources_used` / `failed_lookups` under a research profile); organizer analysis — `consensus`, `contradictions`, `partial_coverage`, `unique_insights`, `blind_spots`, `material_gaps`; gap-repair — `item_responses`, `confidence`; judge — `verdicts`; synthesis — `consensus_answer`, `attribution_map`, `confidence_rationale`, `confidence`.

**`debate` Round 1 required fields:**
- `stance`
- `position_summary`
- `key_arguments`
- `risks_or_limits`
- `recommended_direction`
- `confidence`
- `questions_for_the_council`

**`debate` later-round required fields:**
- `updated_position`
- `what_changed`
- `points_conceded`
- `remaining_objections`
- `best_next_step`
- `confidence`

**Validation behavior (the `malformed_output` path):**
- If a response is missing required fields, retry once with a compact schema reminder prepended to the prompt.
- If the retry also fails, mark the seat as `malformed_output`, exclude it from the digest, and degrade gracefully.
- Do not fabricate missing fields from the seat's partial output.

**Schema reminder template** (prepend to prompts when retrying):
```text
Respond in JSON with exactly these top-level keys: [list keys].
No markdown fencing. No extra commentary outside the JSON object.
```

## Artifact Policy

Determine artifact mode in preflight, then apply the per-mode behaviors here.

When artifact mode is `persisted`, use:
- state: `.ai-workflow/consensus/{session_id}.json`
- report: `.ai-workflow/consensus/{session_id}.md`
- per-round outputs: `.ai-workflow/consensus/{session_id}-round-{n}-{seat}-output.json`
- optional prompt files only when the selected runner requires them
- prefer runner-level `--output-file` writes over shell redirection so incomplete seats do not leave misleading zero-byte artifacts
- for `transport: cmux`, use the same per-round output path as the terminal's only permitted write, then read it with `scripts/cmux_council.py collect`

When artifact mode is `inline`:
- do not create temp prompt files; build prompts in memory
- do not require `.ai-workflow/consensus/`
- return the final report and state inline, with `report_path` and `state_path` set to `null`
- keep round digests and moderator digests in memory

### Report sections per mode

The report is the same document in both artifact modes — written to `.ai-workflow/consensus/{session_id}.md` when `persisted`, returned inline otherwise. Its sections depend on the mode:

- **`poll`** — the ten numbered sections in [poll-protocol.md](poll-protocol.md#phase-5--synthesis-final-call-report): Task / Run config / Seats and judges / Consensus answer / Agreements / How disagreements resolved / Blind spots and partial coverage / Attribution map / Confidence / Open caveats.
- **`debate`** — Task and clarified brief / Run config and seat table (with stance assignments per round) / Round-by-round digests (anonymized as they were passed forward) / Agreement points / Disagreement points with each side's strongest case / Convergence classification and its evidence / Decision options with the recommended direction / Evidence gaps and follow-up questions / Independence accounting (`effective_model` per seat, duplicates and shared providers labeled) / Confidence (answer and diversity, separately) / Open divergence if the run stopped at the `max_iterations` ceiling.
- **`personas`** — the fixed verdict structure in [personas.md](personas.md#step-5--present-the-verdict): Where the Council Agrees / Where the Council Clashes / Blind Spots the Council Caught / The Recommendation / The One Thing to Do First / Reversal Trigger (medium and expensive tiers only), plus the reversal-cost tier, whether peer review ran, and the mode-switch note when `personas` was reached by degradation.

Every mode additionally honors the shared output contract in SKILL.md (adoption grade, two-floor grounding gate, receipt-verified independence, the single next step, both confidence numbers).

## Runner Launch Policy

This section applies to `transport: headless`. For interactive terminals, read [cmux-transport.md](cmux-transport.md) instead.

Launch seats using native host tools when available; fall back to runner scripts only when native paths are unavailable. See [runner-invocations.md](runner-invocations.md) for complete invocation patterns, auth rules, and the runner output contract.

Runner seats invoke local CLIs and may send prompt context, selected files, and runner metadata to their configured providers. Pass `--restrict-tools` to every council seat — they are all analysis seats. Do not pass permission bypass or full auto flags unless the user has explicitly approved unattended write capable execution for that run.

Key flags for every runner-backed seat:
- `--disable-fallback` (mandatory)
- `--timeout 900` for `debate` rounds carrying a digest; `--timeout 600` is ample for a single `poll` answering pass
- `--json` for wrapper envelope
- `--output-file` for persisted artifacts
- `--output-schema <stage schema>` where the runner accepts one ([Schema → mode and stage](#schema--mode-and-stage))

`debate` seats also carry a `--role` and a stance in `--metadata-json`; `poll` seats carry **neither** (they answer the raw prompt) — see [runner-invocations.md#poll-mode-deltas](runner-invocations.md#poll-mode-deltas).

In `inline` mode, combine the overlay and brief into a single positional prompt. In `persisted` mode, use `--prompt-file` flags when the runner supports them.

## Input Format

Expected input payload:
- `question`: required
- `mode`: optional council mode — `poll` (default), `debate`, or `personas` (SKILL.md, Mode Selection)
- `context_files`: optional list of repo-relative or absolute file paths
- `max_iterations`: optional, default `3` (the `debate` rotation schedule defines exactly rounds 1–3; `poll` is fixed at one gap-repair round and ignores this)
- `session_id`: required unique identifier
- `auto`: optional boolean, default `false`
- `clarify`: optional boolean, default `false` (see [Clarify Flag](#clarify-flag))
- `decider_context`: optional, `full` (default) or `report_only` (see [Decider Context: report_only](#decider-context-report_only))
- `interaction_mode`: optional, `interactive` (default) or `autonomous`
- `preset`: optional `poll` preset — `quality` (default), `budget`, `research` ([poll-protocol.md](poll-protocol.md#presets))

Free-form shortcuts:
- `--auto` is equivalent to `auto=true`
- `clarify` as a bare word is equivalent to `clarify=true`

`mode` selects the council protocol; `interaction_mode` only controls pausing. Never conflate the two.

## Interaction Mode Behavior

Startup seat selection is governed by preflight step 0 in SKILL.md (the single normative rule). `interaction_mode` only affects later pausing:

- `interactive`: pause later only when disagreement is material or preference-sensitive.
- `autonomous`: run the rounds without further pauses and return recommendations and reasoning.

`--auto` implies `autonomous` and additionally suppresses the startup seat-selection question and the `clarify` interview.

## Clarify Flag

A pre-stage interview that runs **before any round of any mode**, when `clarify` is set. Keep asking short blocking questions until confidence is ≥ 95%, then build one clarified prompt and hand only that to the council.

**Misread test:** if a reasonable expert could misread the task in more than one materially different way, confidence is below 95%.

Be confident about six things:
1. the actual objective
2. the target artifact or output
3. the important constraints
4. the success criteria
5. the autonomy level expected
6. any required inputs, files, or environment assumptions

**Decision ladder:**
- `>= 95` — proceed without more user input
- `90–94` — ask only if the missing information could change the outcome in a meaningful way
- `< 90` — ask targeted questions

Rules:
- Ask **only blocking** questions. Do not interview for preferences that cannot change the outcome.
- Ask one short question at a time unless an interactive multiple-choice UI is available and materially faster (see [Interactive Question Mechanics](#interactive-question-mechanics)).
- Never leak the interview transcript into the council: the seats receive the **clarified prompt only** — no interview notes, no orchestrator analysis, no preferred answer. In `poll` this is mandatory (the fan-out is blind).
- Be conservative about false confidence: 95% means you would be comfortable acting without reinterpretation.
- Under `--auto`, skip the interview entirely, **record the assumptions** you are making in state and in the report, and continue. Never block a pipeline caller on a clarify question.
- If a required answer never arrives through any question channel, stop with `awaiting_human` (non-`--auto` only).

## Decider Context: report_only

The final decider — `poll` synthesizer, `debate` report writer, `personas` chairman — sees **ONLY** the moderator/organizer report. No repo access, no seat transcripts, no orchestrator notes, and in `personas` no frozen host position.

Rules:
- The report handed over must not smuggle in context that was absent from round 1. If a fact was not surfaced by the council, it does not reach the decider.
- The decider is always a **fresh context** (separate from the orchestrator, the seats, the organizer, and the judges).
- This information starvation is deliberate protocol, not a limitation: it forces the decision to rest on what the council actually surfaced, so a weak council produces a visibly weak decision instead of an orchestrator-rescued one.
- If the decider reports it cannot decide on the report alone, that is a **finding** — record it as an evidence gap and, in interactive runs, offer another round rather than quietly widening the decider's context.
- Record `decider_context` in the run config section of the report so the reader knows how the decision was constrained.

## Moderator Time Budget and Process Cleanup

The moderator waits, but never indefinitely.

- Budget ~2–3 minutes for native seats and 10–15 minutes for runner-backed seats per round.
- Once at least 3 independent providers have completed **and** the major disagreements are clear, stop waiting — unless a straggler could change the decision materially.
- After the cutoff: close native seats you no longer need and **kill unfinished runner processes**. Never leave orphaned background work behind.
- Record every cut-off seat as `unavailable` with the reason (`timeout_cutoff`), and lower confidence one band exactly as for any missing seat — a cut seat is a missing seat, not a silent omission.
- On resume, terminate any runner PIDs or background jobs recorded from the prior session before launching new seats (see [Crash Recovery and State Resumption](#crash-recovery-and-state-resumption)); background runner jobs are managed with `_shared/scripts/runner_jobs.py` (`status` / `result` / `cancel`).

## Handoff After Approval Rules

Deliberation-only is absolute: no mode, preset, or flag combination (including `--auto`) authorizes execution. Handoff happens only when **all** of these hold:

1. The user explicitly approved a direction after seeing the verdict — approval by the council itself, by a seat, or by inference from silence does not count.
2. The user did not ask for analysis only. If the request was "review", "compare", or "what do you think", stop at the report.

Then, and only then:

- Build a **compact handoff brief**: the final recommendation, the minority concerns worth carrying, and the acceptance criteria. Not the full transcript.
- Prefer a native seat for the implementation; otherwise invoke the selected runner with `--role implementer` (or `--role codereviewer` for a review handoff) — the only roles that legitimately leave read-only mode.
- Never pass permission-bypass or full-auto flags on the council's own initiative; that requires the user's explicit approval for unattended write-capable execution in this run.
- Record the handoff in `gates` (what was approved, to whom it was handed, with which brief) so a resumed session does not re-hand the same work.
- The council never runs the implementation itself, and never edits files in any mode.
