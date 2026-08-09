---
name: gemma-runner
description: Execute prompts using Google Gemma models through Cline CLI in headless mode. Use when users explicitly request Gemma execution, when a workflow needs a Gemma seat, or when a cross-runner workflow wants a Gemma-backed perspective.
---

# Gemma Runner

Execute prompts against Gemma models through the shared Qwen shim, which delegates to `cline-runner`. This skill gives councils and scripted workflows a Google-backed seat in headless mode.

## Default Model

- `google/gemma-4-31b-it`

Pass `--model` if you want to target another Gemma model exposed by the selected Cline provider.

## Prerequisites

- `cline` installed and in `PATH`
- A Cline provider authenticated through `cline auth` that can resolve `google/gemma-4-31b-it`

## Security Model

This skill delegates through `qwen-runner` to `cline-runner`, so it has the Cline execution and data sharing model. Prompt text, prompt files, session files, metadata, and any files Cline reads during the run may be sent to the selected Gemma provider. Analysis roles default to native `--auto-approve false`; pass `--allow-write` to opt out.


## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read the qwen-runner skill's SKILL.md (`../qwen-runner/SKILL.md`) when you need flag or envelope details. The envelope is produced by `qwen-runner/scripts/run_qwen.py`.

## Usage

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Summarize the core module architecture"
python3 .agents/skills/gemma-runner/scripts/run_gemma.py --prompt-file /tmp/review.md --role synthesizer
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Return JSON only" --output-format stream-json --json
```

## Behavior

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `gemma`.
2. Uses the Cline NDJSON stream as the default output format.
3. Never falls back to another provider. If `cline` is missing, the envelope carries `status: seat_unavailable` and return code `-2`. A model or provider failure returns `-3`. In both cases `runner` stays `gemma` and a failing smoke test blocks the seat.
4. Preserves the shared wrapper envelope so councils can compare Gemma output with other runners consistently.

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat (Codex UI display metadata and default prompt); do not remove it.
