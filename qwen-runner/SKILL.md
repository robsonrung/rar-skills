---
name: qwen-runner
description: Execute prompts using Qwen Code CLI in headless mode with JSON-stream output by default. Use when users explicitly request Qwen execution, when a workflow needs a verified Qwen-backed seat, or when another runner skill should reuse the shared Qwen CLI wrapper.
---

# Qwen Runner

Execute prompts through the local `qwen` CLI in one-shot headless mode. Prefer this skill for automation, councils, and scripted validation where structured stream output is helpful.

## Prerequisites

- `qwen` installed and in `PATH`
- `qwen auth` configured for the models you want to call

## Security Model

This skill invokes the local Qwen CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected provider behind the local Qwen account. Analysis roles (every role except `implementer`) default to restricted mode: a read-only prompt overlay plus `--approval-mode plan`; pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.


## Output Envelope

All `--json` responses must conform to `.agents/skills/_shared/runner-envelope.schema.json` (an install-time path; the schema is not bundled in this repo, so the required-keys list below is the operative contract).
Required top-level keys:
- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok`
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `agent_message` (the clean final answer extracted from the native result event, or trimmed stdout in `text` mode) and `session_id` when the native stream reports one. Orchestrators should read `agent_message` instead of parsing `stdout`.

## Usage

Invoke the script from the repository root:

```bash
ROOT=$(git rev-parse --show-toplevel || pwd)
python3 "$ROOT/.agents/skills/qwen-runner/scripts/run_qwen.py" "your prompt here"
```

Paths use the installed `.agents/skills/` layout; when running from this source repo, skills live at the repo root, so invoke `qwen-runner/scripts/run_qwen.py` instead.

## Supported Options

- `--timeout`
- `--working-dir`
- `--json`
- `--prompt-file` (repeatable)
- `--model`
- `--output-format` with default `stream-json`
- `--input-format`
- `--approval-mode` with default `default`
- `--sandbox`
- `--restrict-tools` (default for analysis roles)
- `--allow-write` (opt an analysis role out of restricted mode)
- `--background` (tracked background job; manage with `_shared/scripts/runner_jobs.py`)
- `--role`
- `--session-file`
- `--metadata-json`
- `--output-schema`
- `--ephemeral`
- `--no-session-persistence`
- `--safe`
- `--bare`
- `--disable-fallback`
- `--output-file`

`--safe`, `--bare`, and `--disable-fallback` are accepted for cross-runner compatibility (see Behavior item 5 for the no-fallback rule). Run the script with `--help` for per-flag docs.

## Roles

Supported roles:
- `planner`
- `codereviewer`
- `implementer`
- `synthesizer`
- `adversarial`
- `challenger`
- `researcher`

## Examples

```bash
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Explain the core module architecture"
python3 .agents/skills/qwen-runner/scripts/run_qwen.py --prompt-file /tmp/stance.md --prompt-file /tmp/brief.md --role codereviewer --restrict-tools
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Return JSON matching the schema" --output-schema /tmp/schema.json --json
```

## Behavior

1. Runs the local `qwen` CLI directly with `--channel CI` for headless execution.
2. Defaults to `--output-format stream-json` so automation can consume the native event stream.
3. Returns a wrapper envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, and `effective_runner`.
4. Keeps the native Qwen JSON or JSONL output in `stdout`; the wrapper `--json` flag only controls the outer envelope.
5. Never falls back to another provider. Missing CLI or auth failures block the seat explicitly.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Qwen CLI not found |
| -3 | Invalid input, native API/auth error, or unexpected error |

On `-2` the envelope also carries `status: seat_unavailable`. There is no separate return code for auth failures: native API/auth errors are folded into `-3`, the `[API Error: ...]` text is appended to `stderr`, and `auth_ok` stays `null` in that case (only `-2` sets it to `false`).

## Background Jobs

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs (`list`/`status`/`result`/`cancel`) with `python3 .agents/skills/_shared/scripts/runner_jobs.py`. This also applies to the gemma/glm/minimax shims, which tag jobs with their own runner name.

## Presenting Results

- Prefer `agent_message` over `stdout`; the raw stream is for debugging.
- For reviews, keep findings ordered by severity and preserve file paths and line numbers exactly as reported.
- Preserve evidence boundaries: if the model marked something as an inference or open question, keep that distinction.
- Never auto-apply review findings; present them and ask which to fix.
- If a run fails, report the failure with the most actionable stderr lines — do not silently substitute another model's answer.

## Gotchas

- `--output-schema` is enforced by prompt instructions, not by a native Qwen schema flag. A ready-made review schema (verdict/findings/next_steps) is bundled at `codex-runner/schemas/review-output.schema.json` and works with any runner.
- `--restrict-tools` adds a read-only overlay to the prompt and switches headless approval mode to `plan`; it is not a hard tool sandbox.
- Use the runner's `--json` flag when a workflow needs the wrapper envelope on stdout.
- Chat recording is always disabled (the wrapper always passes `--chat-recording=false`); `--ephemeral` and `--no-session-persistence` are compatibility no-ops.
