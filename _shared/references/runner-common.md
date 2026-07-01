# Runner Common Reference

Canonical, agent-facing rules shared by every runner skill (claude, codex, gemini, qwen, the cline-backed kimi/glm shims, and the qwen-backed gemma/minimax shims). Each runner's SKILL.md points here for these four blocks and keeps inline only its genuine deltas.

## Seat fidelity

**Seat fidelity** — a seat's output is only ever that seat's, or the seat is reported absent (labeled via `fallback_from`).

This is the core invariant every runner upholds. A runner never silently substitutes another model's answer for the seat the caller asked for. When the requested CLI is missing, blocked, or fails, the runner either:

- routes to an explicit fallback runner and labels the substitution on the envelope (`fallback_from`, `fallback_reason`), so the caller always knows which seat actually answered; or
- reports the seat as unavailable (`success: false`, typically `status: seat_unavailable` with `return_code -2`) so councils and orchestrators account for the missing seat.

Runners that never fall back (kimi, qwen, and the qwen-backed shims) only ever block-and-report; runners with a fallback chain (claude, codex, gemini) may substitute, but only when labeled. Either way the seat's identity is never faked.

## Output envelope (required keys)

All `--json` responses conform to `_shared/runner-envelope.schema.json` (bundled in this repo; installed at `.agents/skills/_shared/runner-envelope.schema.json`).

Required top-level keys, always emitted on every exit path:

- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok` (auth preflight result)
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `stdout`, `stderr`, and execution metadata. The clean final answer is exposed as `agent_message` — orchestrators should read that field instead of parsing `stdout`. Individual runners extend this contract with their own keys (e.g. `session_id`, `status`, `fallback_from`, `fallback_attempts`); see each runner's SKILL.md for its extensions.

## Roles

Supported roles:

- `planner`
- `codereviewer`
- `implementer`
- `synthesizer`
- `adversarial`
- `challenger`
- `researcher`

Every role except `implementer` is an analysis seat and defaults to read-only mode (the exact enforcement — Claude planning mode, Codex read-only sandbox, qwen `--approval-mode plan`, or a prompt-level overlay — is runner-specific). Pass `--allow-write` when an analysis role legitimately needs to write.

## Presenting results

- Prefer `agent_message` over `stdout`; the raw payload is for debugging.
- For reviews, keep findings ordered by severity and preserve file paths and line numbers exactly as reported.
- Preserve evidence boundaries: if the model marked something as an inference or open question, keep that distinction.
- Never auto-apply review findings; present them and ask which to fix.
- If a run fails, report the failure with the most actionable stderr lines — do not silently substitute another model's answer (seat fidelity). Any fallback run is always labeled via `fallback_from`/`fallback_reason`.

## Background jobs

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs with the shared CLI (used by every runner skill):

```bash
python3 .agents/skills/_shared/scripts/runner_jobs.py list [--runner <name>]
python3 .agents/skills/_shared/scripts/runner_jobs.py status [job-id]
python3 .agents/skills/_shared/scripts/runner_jobs.py result [job-id]
python3 .agents/skills/_shared/scripts/runner_jobs.py cancel [job-id]
```

`job-id` defaults to the most recent job. All subcommands accept `--working-dir` and `--json`. `status` reports `running`, `completed`, `failed`, `cancelled`, or `died` plus a log tail; `result` prints the stored `agent_message` (or the full envelope with `--json`) and the session id for follow-up resumes; `cancel` terminates the job's process group.
