---
name: glm-runner
description: Execute prompts using GLM models through Qwen Code CLI in headless mode. Use when users explicitly request GLM execution, when a workflow needs a GLM seat, or when a cross-runner workflow selects GLM as a complementary provider.
---

# GLM Runner

Execute prompts against GLM models through the shared Qwen CLI wrapper. This keeps GLM seats headless and JSON-stream friendly without relying on Claude CLI transport.

## Default Model

- `z-ai/glm-5.2`

This matches the GLM provider configured in the local `qwen` CLI account. Pass `--model` to target another GLM model exposed by your `qwen` configuration.

## Prerequisites

- `qwen` installed and in `PATH`
- A GLM provider configured in the qwen CLI — a `modelProviders` entry in `~/.qwen/settings.json` (with its API key env var set) or credentials supplied via `--openai-api-key` / `--auth-type`. The legacy `qwen auth` subcommand has been removed.

## Security Model

This skill delegates to `qwen-runner`, so it has the same execution and data sharing model as the Qwen wrapper. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected GLM provider. Analysis roles (every role except `implementer`) default to restricted mode (read-only overlay plus plan approval mode); pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.


## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read the qwen-runner skill's SKILL.md (`../qwen-runner/SKILL.md`) when you need flag or envelope details. The envelope is produced by `qwen-runner/scripts/run_qwen.py`.

## Usage

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "Summarize the core module architecture"
python3 .agents/skills/glm-runner/scripts/run_glm.py --prompt-file /tmp/review.md --role codereviewer --model z-ai/glm-5.2
python3 .agents/skills/glm-runner/scripts/run_glm.py "Read-only analysis" --restrict-tools --no-session-persistence --json
```

## Behavior

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `glm`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. If the run fails (non-zero `return_code` or `auth_ok=false` in the envelope), treat the GLM seat as blocked and report it unavailable so councils can account for the missing seat — never substitute another provider.
4. Preserves the shared wrapper envelope so councils can compare GLM output with other runners consistently.
