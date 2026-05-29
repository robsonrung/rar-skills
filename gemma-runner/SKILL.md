---
name: gemma-runner
description: Execute prompts using Google Gemma models through Qwen Code CLI in headless mode. Use when users explicitly request Gemma execution, when a workflow needs a Gemma seat, or when a cross-runner workflow wants a Gemma-backed perspective without leaving the current workspace.
---

# Gemma Runner

Execute prompts against Gemma models through the shared Qwen CLI wrapper. This skill gives councils and scripted workflows a Google-backed seat that still runs locally in headless mode.

## Default Model

- `google/gemma-4-31b-it`

Pass `--model` if you want to target another Gemma model exposed by the local `qwen` CLI account.

## Prerequisites

- `qwen` installed and in `PATH`
- `qwen auth` configured for the Gemma models you intend to use

## Security Model

This skill delegates to `qwen-runner`, so it has the same execution and data sharing model as the Qwen wrapper. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected Gemma provider. Approval mode defaults to `default`.


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

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "your prompt here"
```

## Supported Options

The Gemma runner inherits the verified Qwen runner options:
- `--timeout`
- `--working-dir`
- `--json`
- `--prompt-file` (repeatable)
- `--model`
- `--output-format`
- `--input-format`
- `--approval-mode`
- `--sandbox`
- `--safe`
- `--bare`
- `--no-session-persistence`
- `--restrict-tools`
- `--role`
- `--session-file`
- `--metadata-json`
- `--output-schema`
- `--disable-fallback`
- `--output-file`

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
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Summarize the core module architecture"
python3 .agents/skills/gemma-runner/scripts/run_gemma.py --prompt-file /tmp/review.md --role synthesizer
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Return JSON only" --output-format json --json
```

## Behavior
## Runtime Compatibility
Define optional fallback policy when qwen/gemma auth unavailable.
If fallback occurs, keep runner=gemma and set effective_runner to actual provider.
If fallback disabled, return seat_unavailable envelope.

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `gemma`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. A failing Gemma smoke test should block the seat.
4. Preserves the shared wrapper envelope so councils can compare Gemma output with other runners consistently.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Qwen CLI not found |
| -3 | Invalid input or unexpected error |

## Gotchas

- `--bare` and `--safe` are compatibility flags here; they do not change the Qwen CLI transport.
- `--output-schema` is prompt-enforced, not natively validated by Qwen CLI.
