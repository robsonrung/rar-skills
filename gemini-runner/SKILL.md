---
name: gemini-runner
description: Execute prompts using Antigravity CLI (`agy`) headless print mode for a Gemini/Google seat. Use when users request Gemini execution, Antigravity CLI execution, or when a consensus workflow needs a Gemini seat and local `agy` is installed.
---

# Gemini Runner

Execute prompts via Antigravity CLI (`agy`) headless print mode with role overlays and continuation support.

## Runtime Compatibility
When `agy` is missing and fallback is disabled (or all fallbacks are unavailable), the envelope carries `status: seat_unavailable` and `return_code` -2; council orchestrators must treat that seat as absent. When a fallback runner does produce the output, unavailable fallback seats attempted before it are listed in `fallback_attempts` on the returned envelope.

1. Check whether Antigravity CLI (`agy`) is available.
2. If available, run this skill.
3. If unavailable, route through the fallback order `$qwen-runner`, `$kimi-runner`, `$codex-runner`, then `$claude-runner`, and report the fallback.
4. Never claim the Gemini/Google seat participated when a fallback provider produced the output.

## Security Model

This skill invokes the local Antigravity CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Antigravity reads during the run may be sent to the configured Google model. Permission checks stay enabled through the local Antigravity configuration. Analysis roles (every role except `implementer`) default to a read-only prompt overlay (`agy` has no sandbox flag, so this is a soft constraint); pass `--allow-write` to opt out.

## Output Envelope

All `--json` responses follow the shared runner envelope contract used by every runner skill. Required top-level keys:
- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok`
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `stdout`, `stderr`, and any execution metadata from the run, plus `agent_message` (the trimmed `agy` print-mode response — `agy` exposes no session id, so `session_id` stays null).

## Usage

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. When running from this source repo, skills live at the repo root, so invoke `gemini-runner/scripts/run_gemini.py` instead.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Maximum execution time in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current directory |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Compatibility metadata label. `agy` uses its configured model from `/model` or settings. | `agy-configured-model` |
| `--output-format`, `-o` | Response format hint: `text`, `json`, or `stream-json`. `agy` print mode has no output-format launch flag. | `text` |
| `--prompt-file` | Read the prompt from a file (repeatable; files are concatenated in order) | None |
| `--role` | Apply a role overlay | None |
| `--restrict-tools` | Add a read-only analysis overlay to the prompt | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default read-only overlay | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior workflow context for cross-runner continuation | None |
| `--agy-continue` | Resume the most recent Antigravity CLI conversation with native `agy --continue` | False |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope atomically to this path; with `--json`, stdout becomes a compact `{success, return_code, output_file}` pointer | None |

## Roles

Supported roles:
- `planner`
- `codereviewer`
- `implementer`
- `synthesizer`
- `adversarial`
- `challenger`
- `researcher`

Every role except `implementer` is an analysis seat and defaults to the read-only prompt overlay. Pass `--allow-write` when an analysis role legitimately needs to write.

## Background Jobs

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs with the shared CLI (`list`/`status`/`result`/`cancel`):

```bash
python3 .agents/skills/_shared/scripts/runner_jobs.py status [job-id]
```

## Presenting Results

- Prefer `agent_message` over `stdout`; the raw payload is for debugging.
- For reviews, keep findings ordered by severity and preserve file paths and line numbers exactly as reported.
- Preserve evidence boundaries: if the model marked something as an inference or open question, keep that distinction.
- Never auto-apply review findings; present them and ask which to fix.
- If a run fails, report the failure with the most actionable stderr lines — do not silently substitute another model's answer (fallback runs are always labeled via `fallback_from`/`fallback_reason`).

## Examples

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Explain this code"
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Analyze this file" --output-format json
python3 .agents/skills/gemini-runner/scripts/run_gemini.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Continue the previous analysis" --agy-continue
```

## Behavior

1. Executes `agy [--continue] --print-timeout <Ns> --print "<prompt>"`.
2. Does not request a permission bypass.
3. Keeps `runner=gemini` for workflow compatibility and sets `effective_runner=agy` when Antigravity CLI produced the output.
4. Does not pass unsupported Gemini CLI flags such as `--model`, `--output-format`, `--thinking-budget`, or a read-only convenience mode to `agy`.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1+ | Antigravity CLI (`agy`) error (passthrough) |
| -1 | Timeout expired |
| -2 | Antigravity CLI (`agy`) not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Antigravity CLI (`agy`) installed and available in PATH
- Authentication configured for Antigravity CLI
- Model selection configured in `agy` via `/model` or `~/.gemini/antigravity-cli/settings.json` when a specific model is required
