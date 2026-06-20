# Operations Reference

Operational detail for models-consensus: cost governance, crash recovery, response schema validation, artifact policy, runner launch policy, input format, and mode behavior. Read the relevant section when its trigger in SKILL.md fires.

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
- Track cumulative token usage across rounds in state for post-council reporting.

## Crash Recovery and State Resumption

Council state is resumable. Treat `.ai-workflow/consensus/{session_id}.json` as the source of truth for progress.

**Resume handshake:**
- At preflight, check if `state_path` exists and `status != complete`.
- If resuming, load prior round outputs, seat assignments, and moderator digests from state.
- Set `resumed_from` to the previous state's `last_completed_round`.
- Skip to the next uncompleted round; do not re-run completed rounds.

**Orphaned process cleanup:**
- When resuming, identify any runner PIDs or background tasks from the prior session and terminate them before launching new seats.
- In `inline` mode, recovery is limited to what fits in the current context; persist key digests to state when possible.

**State update cadence:**
- In `persisted` mode, write state after every iteration.
- In `inline` mode, still build the same state structure in memory so it can be returned or persisted if the mode changes.

## Response Schema Validation

Validate seat outputs before accepting them into the moderator digest. Seat outputs ARE schema-validated against the field lists below.

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

## Artifact Policy

Determine artifact mode in preflight, then apply the per-mode behaviors here.

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

Launch seats using native host tools when available; fall back to runner scripts only when native paths are unavailable. See [runner-invocations.md](runner-invocations.md) for complete invocation patterns, auth rules, and the runner output contract.

Runner seats invoke local CLIs and may send prompt context, selected files, and runner metadata to their configured providers. Prefer `--restrict-tools` for review and planning seats. Do not pass permission bypass or full auto flags unless the user has explicitly approved unattended write capable execution for that run.

Key flags for every runner-backed seat:
- `--disable-fallback` (mandatory)
- `--timeout 900`
- `--json` for wrapper envelope
- `--output-file` for persisted artifacts

In `inline` mode, combine stance and brief into a single positional prompt. In `persisted` mode, use `--prompt-file` flags when the runner supports them.

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

Startup seat selection is governed by preflight step 0 in SKILL.md (the single normative rule). Mode only affects later pausing:

- `interactive`: pause later only when disagreement is material or preference-sensitive.
- `autonomous`: run the rounds without further pauses and return recommendations and reasoning.
