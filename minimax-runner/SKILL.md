---
name: minimax-runner
description: Execute prompts using Minimax models through Qwen Code CLI in headless mode. Use when users explicitly request Minimax execution, when a workflow needs a Minimax seat, or when a cross-runner workflow wants a Minimax-backed perspective without leaving the current workspace.
---

# Minimax Runner

Execute prompts against Minimax models through the shared Qwen CLI wrapper. This skill adds a Minimax-backed seat for councils and scripted workflows while keeping execution headless and stream-friendly.

## Default Model

- `minimax/minimax-m2.7`

Pass `--model` if you want to target another Minimax model exposed by the local `qwen` CLI account.

## Prerequisites
Requirement: qwen/minimax auth smoke test and explicit blocked response.
Differentiate missing_binary vs auth_failed vs timeout in return semantics.
Output must include effective_provider metadata even in non-fallback mode.
Document council seat accounting behavior.

- `qwen` installed and in `PATH`
- `qwen auth` configured for the Minimax models you intend to use


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
python3 .agents/skills/minimax-runner/scripts/run_minimax.py "your prompt here"
```

## Supported Options

The Minimax runner inherits the verified Qwen runner options:
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
python3 .agents/skills/minimax-runner/scripts/run_minimax.py "Stress-test this implementation idea"
python3 .agents/skills/minimax-runner/scripts/run_minimax.py --prompt-file /tmp/review.md --role challenger
python3 .agents/skills/minimax-runner/scripts/run_minimax.py "Return JSON only" --output-format json --json
```

## Behavior

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `minimax`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. A failing Minimax smoke test should block the seat.
4. Preserves the shared wrapper envelope so councils can compare Minimax output with other runners consistently.

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
