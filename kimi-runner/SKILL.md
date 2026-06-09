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

This skill invokes the local Kimi CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Kimi reads during the run may be sent to Moonshot according to the local Kimi configuration. Use `--restrict-tools` for review seats; it adds a read-only overlay to the prompt, so treat it as a prompt level constraint rather than a hard sandbox.


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
- `--restrict-tools`
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
6. Preserves Kimi's resume hint lines in raw `stdout`, while also extracting `assistant_message` and `native_result` when the native stream is parseable.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Kimi CLI not found |
| -3 | Invalid input or unexpected error |

## Gotchas

- Kimi print mode still emits a resume hint after the final answer. The wrapper keeps raw output and also extracts the assistant message separately when possible.
- `--output-schema` is prompt-enforced, not validated by a native Kimi schema flag.
- `--restrict-tools` is a prompt overlay, not a sandbox — see Security Model.
