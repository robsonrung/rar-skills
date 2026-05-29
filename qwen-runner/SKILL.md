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

This skill invokes the local Qwen CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected provider behind the local Qwen account. Approval mode defaults to `default`.


## Output Envelope

All `--json` responses must conform to `.agents/skills/_shared/runner-envelope.schema.json`.
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
Normalize script invocation from repo root (ROOT=$(git rev-parse --show-toplevel || pwd)).
Requirement: standardized seat_unavailable envelope when qwen/auth missing.
Keep no-silent-provider-switch rule explicit.
Separate return codes for missing binary vs auth failure.

```bash
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "your prompt here"
```

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

`--safe`, `--bare`, and `--disable-fallback` are accepted for cross-runner compatibility. Qwen-backed runners do not fall back to another provider.

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
| -3 | Invalid input or unexpected error |

## Gotchas

- `--output-schema` is enforced by prompt instructions, not by a native Qwen schema flag.
- `--restrict-tools` adds a read-only overlay to the prompt; it is not a hard tool sandbox.
- Use the runner's `--json` flag when a workflow needs the wrapper envelope on stdout.
