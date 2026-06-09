# Operations Reference

Cost governance and crash recovery procedures. Read the relevant section when its trigger in SKILL.md fires.

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
