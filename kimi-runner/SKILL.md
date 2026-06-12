---
name: kimi-runner
description: Execute prompts using Kimi CLI in headless mode with stream-json output by default. Use when users explicitly request Kimi execution, when a workflow needs a Kimi-backed seat, or when a cross-runner workflow wants a Moonshot Kimi perspective without leaving the current workspace.
---

# Kimi Runner

Execute prompts through the local `kimi-cli` in one-shot headless mode. Prefer this skill for councils, scripted validation, and Kimi-specific runs where stream-friendly output and a consistent runner envelope matter.

## Default Model

- `kimi-code/kimi-for-coding`

This matches the locally configured coding model in `~/.kimi/config.toml`. Pass `--model` if you need a different Kimi model exposed by the local CLI.

## Prerequisites

- `kimi-cli` installed and in `PATH`
- Authentication configured via `kimi-cli login`

If `kimi-cli` is missing or auth fails, the seat is blocked, never substituted: the envelope returns `success=false` with remediation guidance in `stderr`. A missing CLI maps to `return_code=-2` and `status=seat_unavailable`; auth failures surface as kimi-cli's native nonzero exit code with `auth_ok` unset — treat any `success=false` as a blocked seat.

## Security Model

This skill invokes the local Kimi CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Kimi reads during the run may be sent to Moonshot according to the local Kimi configuration. Analysis roles (every role except `implementer`) default to a read-only overlay on the prompt; pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role. The overlay is a prompt level constraint rather than a hard sandbox.


## Output Envelope

All `--json` responses must conform to the shared runner envelope contract (`.agents/skills/_shared/runner-envelope.schema.json`, provided by the skills install root; if that file is absent, the key list below is authoritative).
Required top-level keys:
- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok`
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `agent_message` (the clean final assistant answer — same value as the legacy `assistant_message` field, or trimmed stdout in `text` mode) and `session_id` when the native stream reports one. Orchestrators should read `agent_message` instead of parsing `stdout`.

## Usage

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "your prompt here"
```

## Supported Options

The Kimi runner supports these verified options:
- `--timeout`
- `--working-dir`
- `--json`
- `--prompt-file` (repeatable)
- `--model`
- `--output-format` with default `stream-json`
- `--thinking`
- `--no-thinking`
- `--continue`
- `--session`
- `--restrict-tools` (default for analysis roles)
- `--allow-write` (opt an analysis role out of the read-only overlay)
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

`--ephemeral`, `--no-session-persistence`, `--safe`, `--bare`, and `--disable-fallback` are accepted for cross-runner compatibility. They do not currently change Kimi CLI behavior; in particular, `--no-session-persistence` is inert because the current Kimi CLI still records resumable session metadata in print mode.

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

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs (`list`/`status`/`result`/`cancel`) with `python3 .agents/skills/_shared/scripts/runner_jobs.py`.

## Presenting Results

- Prefer `agent_message` over `stdout`; the raw stream is for debugging.
- For reviews, keep findings ordered by severity and preserve file paths and line numbers exactly as reported.
- Preserve evidence boundaries: if the model marked something as an inference or open question, keep that distinction.
- Never auto-apply review findings; present them and ask which to fix.
- If a run fails, report the failure with the most actionable stderr lines — do not silently substitute another model's answer.

## Examples

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Summarize the core module architecture"
python3 .agents/skills/kimi-runner/scripts/run_kimi.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/kimi-runner/scripts/run_kimi.py --prompt-file /tmp/stance.md --prompt-file /tmp/brief.md --output-format stream-json --json
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Return JSON only" --output-schema /tmp/schema.json --json
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Continue the last Kimi session in this repo" --continue
```

## Behavior

1. Runs `kimi-cli --print` directly for non-interactive execution.
2. Defaults to `--output-format stream-json` so councils and scripts can consume native event output.
3. Returns a wrapper envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, and `effective_runner`.
4. Keeps native Kimi output in `stdout`; the wrapper `--json` flag only controls the outer envelope.
5. Never falls back to another provider. Missing CLI or auth failures block the seat explicitly.
6. Preserves Kimi's resume hint lines in raw `stdout`, while also extracting `agent_message` (alias `assistant_message`), `session_id`, and `native_result` when the native stream is parseable.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Kimi CLI not found |
| -3 | Invalid input or unexpected error |

## Gotchas

- Kimi print mode still emits a resume hint after the final answer. The wrapper keeps raw output and also extracts the assistant message separately when possible.
- `--output-schema` is prompt-enforced, not validated by a native Kimi schema flag. A ready-made review schema (verdict/findings/next_steps) is bundled at `codex-runner/schemas/review-output.schema.json` and works with any runner.
- `--restrict-tools` is a prompt overlay, not a sandbox — see Security Model.
