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

This skill delegates to `qwen-runner`, so it has the same execution and data sharing model as the Qwen wrapper. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected Gemma provider. Analysis roles (every role except `implementer`) default to restricted mode (read-only overlay plus plan approval mode); pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.


## Output Envelope

All `--json` responses use the shared runner envelope inherited from `qwen-runner`. The envelope is expected to conform to `.agents/skills/_shared/runner-envelope.schema.json`; when that schema file is absent, the inline key list below is authoritative.
Required top-level keys:
- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok`
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `agent_message` (the clean final answer) and `session_id` when the native stream reports one — see the qwen-runner SKILL.md for details.

## Usage

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "your prompt here"
```

## Options, Roles, and Return Codes

Options, roles, and return codes are inherited from `qwen-runner` — read the qwen-runner skill's SKILL.md when you need flag details. Every flag the Qwen wrapper accepts, including `--ephemeral`, works here unchanged.

## Examples

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Summarize the core module architecture"
python3 .agents/skills/gemma-runner/scripts/run_gemma.py --prompt-file /tmp/review.md --role synthesizer
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Return JSON only" --output-format json --json
```

## Behavior

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `gemma`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. If the `qwen` CLI is missing, the envelope carries `status: seat_unavailable` (return code `-2`); Gemma auth failures fold into return code `-3` with the native `[API Error: ...]` text in `stderr`. In both cases `runner` stays `gemma`, the envelope still carries the `fallback_reason` key, and a failing Gemma smoke test should block the seat.
4. Preserves the shared wrapper envelope so councils can compare Gemma output with other runners consistently.

## Gotchas

- `--bare` and `--safe` are compatibility flags here; they do not change the Qwen CLI transport.
- `--output-schema` is prompt-enforced, not natively validated by Qwen CLI.

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat (Codex UI display metadata and default prompt); do not remove it.
