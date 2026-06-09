---
name: models-consensus
description: Orchestrate a multi-model council across Claude Opus 4.7, Claude Sonnet 4.6, Codex, Gemini, Gemma, GLM, Kimi, and Minimax-backed seats using stance-driven rounds, blinded opening analyses, moderated rebuttals, and a final decision report. Use when a repository decision benefits from structured disagreement, tradeoff surfacing, or deliberate synthesis instead of a single-model answer. Also use when the user asks for multi-model validation, consensus review, or wants multiple AI perspectives on a design or architecture decision.
---

# Models Consensus

Moderate a council of native seats and local runner skills. Do not act as one of the voting seats. The moderator's job is to run a deterministic preflight, launch only real seats, preserve independence accounting, surface disagreements that actually change scope or behavior, and enforce cost and recovery guardrails.

## Seat Discovery

Detect available seats from host-native tools and installed CLI runners. See [references/repo-configuration.md](references/repo-configuration.md) for the repository-specific seat catalog, default models, and CLI prerequisites. Adapt `RUNNER_BASE_PATH` when using this skill in another repository.

Do not claim a seat participated unless the preflight confirms a real execution path for it.

## Host Tool Compatibility

Council logic is host-agnostic, but concrete tools differ by platform. See [references/runner-invocations.md](references/runner-invocations.md) for the full host capability mapping and native vs. runner launch patterns. Branch all seat launch instructions by host capability.

For any user-facing question, use the [Interactive Questions](#interactive-questions) protocol.

## Mandatory Preflight

Run preflight before building any round prompt.

### 0. Resolve seat selection mode

Before the full preflight, determine whether seat selection is automatic or user-directed. Always resolve startup seat selection before running smoke tests or launching any round.

- Accept `auto: true` in a structured payload.
- Accept `--auto` in a free-form user request as shorthand for `auto: true`.
- If `auto` or `--auto` is present, skip the startup seat-selection question and target every available seat. Only target all seats when `--auto` or `auto: true` is explicitly set; do not auto-select seats just because interactive startup questioning is unavailable.
- Otherwise, ask the user which models or CLIs to use before running smoke tests or launching any round. Never skip the startup seat-selection question in non-`--auto` runs.
- In non-`--auto` runs, if startup selection is still unresolved after the available question channels, stop with `awaiting_user_decision`.

Selection workflow:
- Do a lightweight capability discovery first: detect host-native seat support and runner binary presence only.
- Build a `candidate_seats` list from that lightweight discovery.
- Ask one startup selection question following the [Interactive Questions](#interactive-questions) protocol.
- Prefer one multi-select question when the host supports it, rather than a series of yes/no prompts. Include `All available (Recommended)` plus the detected candidate seats.
- Multi-select startup prompt template:
  `Which models to use?`
  `[ ] All available (Recommended)`
  `[ ] Claude Opus 4.7`
  `[ ] Claude Sonnet 4.6`
  `[ ] Codex`
  `[ ] Gemini`
  `[ ] Kimi`
  `[ ] Gemma`
  `[ ] GLM`
  `[ ] Minimax`
  Omit seats that are not present in `candidate_seats`.
- If the host tool only supports a small single-choice menu, ask a preset question with:
  1. `All available (Recommended)`
  2. `Core seats only`
  3. `Specify seats manually`
- If the user chooses manual selection, ask one concise follow-up question listing the detected seat IDs and accept a comma-separated subset. Use an interactive follow-up question when the host supports one; use a plain-text seat-picking follow-up only when needed.
- Plain-text startup prompt template when no interactive selection tool is available:
  `Which models to use?`
  `Detected seats: <comma-separated seat IDs>`
  `Reply with a comma-separated subset or 'all'.`
  Set `selection_source=plain_text_manual` when this fallback branch is used, and wait for user input.
- Treat `Core seats only` as the highest-diversity non-duplicate set available. See [references/repo-configuration.md](references/repo-configuration.md) for the core-seats definition.
- Persist `selected_seats` and `selection_source` in state, and emit the selected and omitted seats, before continuing to smoke tests.

### 1. Detect host-native seats

- If `Agent` exists, Claude Opus 4.7 and Claude Sonnet 4.6 use native seats.
- If `spawn_agent` and `wait_agent` exist, Codex uses a native seat.
- Otherwise, those seats may use runner scripts if the local CLI exists.

### 2. Check local runner prerequisites

Use shell commands to verify binaries, auth, and one cheap headless smoke test for every runner-backed seat you intend to launch. Only run smoke tests for seats included by `selected_seats` or by `--auto`.

Minimum checks:
- `claude` in `PATH`
- `gemini` in `PATH`
- `kimi-cli` in `PATH` when the Kimi seat is under consideration
- `qwen` in `PATH` when any Gemma, GLM, or Minimax seat is under consideration

Mandatory seat smoke tests:
- Run a minimal non-interactive invocation for every runner-backed seat with the exact model you plan to use.
- Run every runner-backed seat with `--disable-fallback`. Councils must fail a seat explicitly instead of silently borrowing another provider.
- See [references/runner-invocations.md](references/runner-invocations.md) for per-seat auth rules, including the critical Claude `--bare` rule and Qwen transport rule.

Treat missing binaries, missing credentials, or failing smoke tests as seat blockers, not soft warnings.

### 3. Determine artifact mode

Prefer persisted artifacts in `.ai-workflow/consensus/` only when writes are safe.

Set artifact mode to:
- `persisted` when `.ai-workflow/consensus/` exists or its parent is writable
- `inline` when writes are blocked, risky, or unavailable in the current mode

Apply the per-mode behaviors from [Artifact Policy](#artifact-policy).

### 4. Build a seat table

For each potential seat, record:
- `seat`
- `selection_status`: `selected`, `omitted_by_user`, or `unavailable`
- `requested_runner`
- `execution_path`: `native`, `runner`, or `unavailable`
- `effective_provider`
- `effective_model` when known
- `blocked_reason` when unavailable

Do not launch any seat until this table is complete.

## Deterministic Seat Selection

Use these rules:

1. Prefer native Claude seats over `claude-runner`.
2. Prefer native Codex seats over any CLI path.
3. On a Codex host, the Codex seat must run as a native subagent.
4. Use runner scripts only when the native seat path is unavailable.
5. Treat runner fallback to another provider as loss of seat independence.
6. If Gemini CLI is missing, skip Gemini entirely.
7. If Kimi CLI is missing, skip Kimi entirely.
8. If Qwen CLI is missing, skip Gemma, GLM, and Minimax entirely.
9. Use `GLM Critic` only after all unique-provider seats have been considered.
10. Treat Gemma, GLM, and Minimax as separate providers for diversity accounting unless the smoke test proves they resolve to the same effective provider and model.
11. Continue with the remaining seats and lower confidence; never fabricate a missing seat.

## Artifact Policy

When artifact mode is `persisted`, use:
- state: `.ai-workflow/consensus/{session_id}.json`
- report: `.ai-workflow/consensus/{session_id}.md`
- per-round outputs: `.ai-workflow/consensus/{session_id}-round-{n}-{seat}-output.json`
- optional prompt files only when the selected runner requires them
- prefer runner-level `--output-file` writes over shell redirection so incomplete seats do not leave misleading zero-byte artifacts

When artifact mode is `inline`:
- do not create temp prompt files; build prompts in memory
- do not require `.ai-workflow/consensus/`
- return the final report and state inline, with `report_path` and `state_path` set to `null`
- keep round digests and moderator digests in memory

## Runner Launch Policy

Launch seats using native host tools when available; fall back to runner scripts only when native paths are unavailable. See [references/runner-invocations.md](references/runner-invocations.md) for complete invocation patterns, auth rules, and the runner output contract.

Runner seats invoke local CLIs and may send prompt context, selected files, and runner metadata to their configured providers. Prefer `--restrict-tools` for review and planning seats. Do not pass permission bypass or full auto flags unless the user has explicitly approved unattended write capable execution for that run.

Key flags for every runner-backed seat:
- `--disable-fallback` (mandatory)
- `--timeout 900`
- `--json` for wrapper envelope
- `--output-file` for persisted artifacts

In `inline` mode, combine stance and brief into a single positional prompt. In `persisted` mode, use `--prompt-file` flags when the runner supports them.

## Cost Governance and Crash Recovery

Both procedures live in [references/operations.md](references/operations.md); read them on demand:

- When more than 4 seats are selected, read [references/operations.md#cost-governance](references/operations.md#cost-governance) before launching seats and apply its cost-transparency rules.
- At preflight, if `state_path` exists with `status != complete`, read [references/operations.md#crash-recovery-and-state-resumption](references/operations.md#crash-recovery-and-state-resumption) and resume from state instead of restarting.

## Response Schema Validation

Validate seat outputs before accepting them into the moderator digest.

**Round 1 required fields:**
- `stance`
- `position_summary`
- `key_arguments`
- `risks_or_limits`
- `recommended_direction`
- `confidence`
- `questions_for_the_council`

**Later rounds required fields:**
- `updated_position`
- `what_changed`
- `points_conceded`
- `remaining_objections`
- `best_next_step`
- `confidence`

**Validation behavior:**
- If a response is missing required fields, retry once with a compact schema reminder prepended to the prompt.
- If the retry also fails, mark the seat as `malformed_output`, exclude it from the digest, and degrade gracefully.
- Do not fabricate missing fields from the seat's partial output.

**Schema reminder template** (prepend to prompts when retrying):
```text
Respond in JSON with exactly these top-level keys: [list keys].
No markdown fencing. No extra commentary outside the JSON object.
```

## Interactive Questions

Every user-facing question must use the best available interactive host tool first, on both CLI and app surfaces. Treat plain-text questioning as a last resort only when no interactive tool is available in the current host or mode.

Questioning workflow:
1. Detect which interactive question/input tools are exposed by the current host and current mode.
2. Prefer a tool that can present structured choices or multiple short questions in one call.
3. If the first tool is unavailable, unsupported in the current mode, or errors immediately, try the next interactive tool.
4. Use concise plain-text questions only after exhausting interactive tool options.

Preferred host mappings:
- Claude Code: `AskUserQuestion`
- Codex: `request_user_input` when the current mode exposes it
- any other host: the equivalent native interactive question/input tool, if available
- only if none of the above are available: a concise plain-text question with 2-3 options

Additional rules:
- Never choose plain text just because an interactive tool is less convenient.
- If only one question fits per interactive call, use repeated interactive calls rather than switching to plain text.
- When the host supports multiple questions in one call, batch related questions together to reduce back-and-forth.

Never tell the user to reply with numbered choices when an interactive question tool exists.

Startup seat-selection question: unless `--auto` is set, the first question of the run must ask which models or CLIs to use, following the selection workflow and prompt templates in preflight step 0.

## Degrade Gracefully

Apply these rules when the council cannot run at full strength:

- Missing seat: continue and lower overall confidence one level.
- Fallback seat: mark the original seat as unavailable for independence accounting.
- Shared provider, different models: keep both seats but note the shared-provider caveat.
- Same effective provider and same model: collapse to one independent source and call out the lost diversity.
- Malformed output: retry once, then mark seat unavailable and continue.
- Inline artifact mode: return `report_path=null` and `state_path=null`, plus a note that persistence was skipped because writes were unavailable.

Use confidence bands:
- `high`: 4+ independent seats with no critical blockers
- `medium`: 2-3 independent seats, or meaningful fallback duplication
- `low`: 1 independent seat, or unresolved blockers on key disagreement points

Moderator time budget:
- Prefer a finite moderation window for opening statements. Recommended defaults: 2-3 minutes for native seats, 10-15 minutes for runner seats.
- Once at least 3 independent providers have completed and the major disagreements are already clear, stop waiting unless another seat is likely to change the decision materially.
- After moderation cutoff, close native seats you no longer need and kill unfinished runner processes so councils do not leave background work behind.

## Input Format

Expected input payload:
- `question`: required
- `context_files`: optional list of repo-relative or absolute file paths
- `max_iterations`: optional, default `4`
- `session_id`: required unique identifier
- `auto`: optional boolean, default `false`
- `mode`: optional, `interactive` (default) or `autonomous`

Free-form shortcut:
- `--auto` is equivalent to `auto=true`

## Mode Behavior

- `interactive`: ask the startup seat-selection question unless `--auto` is set, then pause later only when disagreement is material or preference-sensitive
- `autonomous`: still ask the startup seat-selection question unless `--auto` is set, then run the remaining rounds without further pauses and return recommendations and reasoning

## Council Model

Assign one stance per active seat per round. See [references/stance-rotation-schedule.md](references/stance-rotation-schedule.md) for the explicit per-seat, per-round stance mapping and fallback rules.

Available stances:
- `supportive_with_integrity`
- `critical_with_responsibility`
- `balanced_synthesis`
- `devils_advocate`
- `pragmatic_engineering`

The stance-to-runner-role mapping lives in the same reference.

If fewer seats are available than unique stances, drop duplicate coverage before dropping unique stances.

## Discussion Protocol

### 1. Build the shared brief

Always include:
- the question
- context file paths only
- the current objective
- previous round digest and user decisions when `iteration > 1`
- the required response schema

In `persisted` mode, write prompt files only for runners that need them.
In `inline` mode, keep the brief in memory and pass it directly.

### 2. Run blinded opening statements

Round 1 inputs:
- shared brief
- stance overlay
- no peer outputs
- no moderator conclusion

Required response schema: the Round 1 fields from [Response Schema Validation](#response-schema-validation).

### 3. Moderate the round

Normalize outputs into:
- `agreement_points`
- `disagreement_points`
- `decision_options`
- `evidence_gaps`
- `follow_up_questions`

Do not paste long verbatim runner output into later rounds. Pass only a compact moderator digest.

### 4. Run rebuttal and refinement rounds

Later rounds get:
- shared brief
- current stance overlay
- prior moderator digest
- explicit instructions to rebut, concede, refine, or integrate

Required response schema: the later-rounds fields from [Response Schema Validation](#response-schema-validation).

### 5. Classify convergence

Use one of:
- `full_agreement`
- `converging`
- `material_disagreement`
- `blocked_on_context`

**Heuristic definitions:**
- `full_agreement`: all selected seats share the same `recommended_direction` and no seat raises a blocking objection.
- `converging`: all seats agree on `recommended_direction` but differ on implementation details, risk weighting, or acceptance criteria.
- `material_disagreement`: ≥2 seats hold opposing `recommended_direction` values, and at least one objection affects scope, behavior, or architecture (not style or preference).
- `blocked_on_context`: seats agree that the question cannot be answered without additional information, file contents, or external validation.

Capture:
- `agreement_points`
- `disagreement_points`
- `leading_option`
- `minority_concerns`
- `open_questions`

### 6. Handle disagreement

Trigger when:
- disagreement remains material after a round
- the decision depends on priorities or preferences
- more context is required
- any recommendation would lead to code or document changes

In `interactive` mode, ask focused questions with:
1. recommended option first
2. minority alternative(s)
3. `Run another round to refine positions` when another round could help

Ask these questions using the [Interactive Questions](#interactive-questions) protocol.

If a required answer is still missing after available question channels, stop with `awaiting_user_decision`.

In `autonomous` mode:
- record each disagreement
- include `recommended_resolution`
- include `resolution_reasoning`
- continue to stop conditions

### 7. Update state

When artifact mode is `persisted`, update state after every iteration with:
- assigned stances
- seat outputs
- moderator digest
- convergence classification
- user decisions
- recommendation log
- runner execution metadata
- independence accounting

When artifact mode is `inline`, keep the same structure in memory and return it inline instead of writing it.

### 8. Stop condition

Stop when:
- full agreement is reached
- the user selects a direction in `interactive` mode
- all rounds complete in `autonomous` mode
- `max_iterations` is reached

### 9. Handoff after approval

Only after the user approves a direction:
- build a compact handoff brief
- include the final recommendation, minority concerns, and acceptance criteria
- use a native seat when available
- otherwise invoke the selected runner with `--role implementer` or `--role codereviewer`

Do not hand off automatically when the user asked only for analysis.

## Final Report

When artifact mode is `persisted`, write `.ai-workflow/consensus/{session_id}.md` with:
1. question and status
2. preflight summary, including seat selection source and selected seats
3. iteration summary
4. agreement points
5. divergence points
6. user decision summary for any non-unanimous result
7. final recommendation
8. recommended next runner and handoff goal
9. confidence assessment

When artifact mode is `inline`, return the same sections inline.

## Output Contract

Return:
1. `report_path` or `null`
2. `state_path` or `null`
3. concise inline summary
4. preflight seat table
5. selected seats and selection source

## Important Rules

1. Preflight first. Never launch seats from assumptions.
2. Unless `--auto` is set, resolve the startup seat-selection question before running smoke tests or rounds.
3. Use the same shared brief for every participant in a round; only the stance overlay changes.
4. Keep opening statements blinded from peer outputs.
5. Treat the moderator as separate from all council seats.
6. Rotate stances across iterations using [references/stance-rotation-schedule.md](references/stance-rotation-schedule.md) to reduce model-position bias.
7. Continue gracefully when one runner fails; never fabricate missing outputs.
8. In `interactive` mode, never apply recommendation-derived edits without explicit user approval.
9. Prefer continuation over repetition when moving from consensus to implementation.
