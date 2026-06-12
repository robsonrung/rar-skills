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

- `qwen` installed and in `PATH`
- `qwen auth` configured for the Minimax models you intend to use

## Security Model

This skill delegates to `qwen-runner`, so it has the same execution and data sharing model as the Qwen wrapper. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected Minimax provider. Analysis roles (every role except `implementer`) default to restricted mode (read-only overlay plus plan approval mode); pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.


## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read the qwen-runner skill's SKILL.md (`../qwen-runner/SKILL.md`) when you need flag or envelope details. The envelope is produced by `qwen-runner/scripts/run_qwen.py`.

## Usage

```bash
python3 .agents/skills/minimax-runner/scripts/run_minimax.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/minimax-runner/scripts/run_minimax.py "Stress-test this implementation idea"
python3 .agents/skills/minimax-runner/scripts/run_minimax.py --prompt-file /tmp/review.md --role challenger
python3 .agents/skills/minimax-runner/scripts/run_minimax.py "Return JSON only" --output-format json --json
```

## Behavior

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `minimax`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. If the run fails (non-zero `return_code` or `auth_ok=false` in the envelope), treat the Minimax seat as blocked and report it unavailable so councils can account for the missing seat — never substitute another provider.
4. Preserves the shared wrapper envelope so councils can compare Minimax output with other runners consistently.
