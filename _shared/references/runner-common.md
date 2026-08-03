# Runner Common Reference

Canonical, agent-facing rules shared by every runner skill: `claude-runner`, `codex-runner`, `gemini-runner`, `grok-runner`, `qwen-runner`, `cline-runner`, `dcode-runner`, plus the cline-backed `kimi`/`glm` shims and the qwen-backed `gemma`/`minimax` shims. Each runner's SKILL.md points here for these shared blocks and keeps inline only its genuine deltas. Seat → model ids live in [model-roster.md](model-roster.md); seat availability comes from `_shared/scripts/discover_runners.py`.

## Seat fidelity

**Seat fidelity** — a seat's output is only ever that seat's, or the seat is reported absent (labeled via `fallback_from`).

This is the core invariant every runner upholds. A runner never silently substitutes another model's answer for the seat the caller asked for. When the requested CLI is missing, blocked, or fails, the runner either:

- routes to an explicit fallback runner and labels the substitution on the envelope (`fallback_from`, `fallback_reason`), so the caller always knows which seat actually answered; or
- reports the seat as unavailable (`success: false`, typically `status: seat_unavailable` with `return_code -2`) so councils and orchestrators account for the missing seat.

This is the one place the fallback split is defined; nothing else restates it.

| Runner | On a missing / failing CLI |
|---|---|
| `claude` | falls back → `codex` |
| `codex` | falls back → `claude` |
| `gemini` | falls back → `qwen`, `kimi`, `codex`, `claude` (in that order) |
| `dcode` | falls back → `claude`, `codex`, `qwen`, `kimi` (in that order) |
| `grok`, `qwen`, `cline`, `kimi`, `glm`, `gemma`, `minimax` | **block-and-report** — never substitutes |

A fallback is always labeled (`fallback_from`, `fallback_reason`), and every fallback chain passes `--disable-fallback` to the runner it delegates to so chains cannot loop. Either way the seat's identity is never faked.

## Output envelope (required keys)

All `--json` responses conform to `_shared/runner-envelope.schema.json` (bundled in this repo; installed at `.agents/skills/_shared/runner-envelope.schema.json`).

Required top-level keys, always emitted on every exit path:

- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok` (auth preflight result: `true` on a successful run; `null` when auth was never exercised — missing CLI, invalid input, or a failure before auth; `false` only when an authentication failure was actually detected)
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

## Guardrails (opt-in command guard)

Runner skills launch CLI seats headless with auto-approve flags — the guard puts a floor under that. `_shared/hooks/` ships a denylist of catastrophic commands (`dangerous-patterns.txt`), a shared PreToolUse guard script (`deny-dangerous.sh`), and its test suite (`test-guard.sh`). The guard blocks only irreversible damage (rm on /|~, raw-disk writes, sudo rm, fork bombs, curl|sh, remote-history rewrites, gh repo delete, token exfil); recoverable commands stay allowed. It is a seatbelt against accidents, not a sandbox against a malicious agent — keep sandboxing and permission modes on regardless.

**Install is opt-in and user-driven; no skill ever wires it automatically.** Copy the two files to `~/.agents/hooks/` (or point configs at the repo checkout) and register the script per CLI:

- **Claude Code** — `~/.claude/settings.json`, `PreToolUse` hook with matcher `Bash` running the script (exit 2 blocks). Merge into any existing `hooks` object, never overwrite.
- **Codex CLI** — `~/.codex/hooks.json`, same `PreToolUse`/`Bash` shape. Gotcha: Codex pins hook-entry trust by hash — after editing the hook ENTRY (not the patterns file), re-trust via `/hooks` in Codex or it silently skips the guard.
- **Cline-backed seats (cline, kimi, glm) and qwen-backed seats** — no user-global PreToolUse hook system as of 2026-08; their floor is the sandbox/approval mode each runner script already sets. Note the gap rather than pretending coverage.

Use absolute paths in configs (`~` expansion is inconsistent across hosts). After ANY pattern change run `test-guard.sh` (must end `failed: 0`). Known false-positive class: a harmless command whose argument text contains a dangerous-looking string can be blocked — put the text in a file and reference it.

## Background jobs

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs with the shared CLI (used by every runner skill):

```bash
python3 .agents/skills/_shared/scripts/runner_jobs.py list [--runner <name>]
python3 .agents/skills/_shared/scripts/runner_jobs.py status [job-id]
python3 .agents/skills/_shared/scripts/runner_jobs.py result [job-id]
python3 .agents/skills/_shared/scripts/runner_jobs.py cancel [job-id]
```

`job-id` defaults to the most recent job. All subcommands accept `--working-dir` and `--json`. `status` reports `running`, `completed`, `failed`, `cancelled`, or `died` plus a log tail; `result` prints the stored `agent_message` (or the full envelope with `--json`) and the session id for follow-up resumes; `cancel` terminates the job's process group.
