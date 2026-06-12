---
name: glm-runner
description: Execute prompts using GLM models through Qwen Code CLI in headless mode. Use when users explicitly request GLM execution, when a workflow needs a GLM seat, or when a cross-runner workflow selects GLM as a complementary provider.
---

# GLM Runner

Execute prompts against GLM models through the shared Qwen CLI wrapper. This keeps GLM seats headless and JSON-stream friendly without relying on Claude CLI transport.

## Default Model

- `glm-5.1`

Pass `--model` if you need a different GLM model that is available to the local `qwen` CLI account.

## Prerequisites

- `qwen` installed and in `PATH`
- `qwen auth` configured for the GLM models you intend to use

## Security Model

This skill delegates to `qwen-runner`, so it has the same execution and data sharing model as the Qwen wrapper. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected GLM provider. Analysis roles (every role except `implementer`) default to restricted mode (read-only overlay plus plan approval mode); pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.


## Output Envelope

The wrapper `--json` envelope always contains these top-level keys:
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
python3 .agents/skills/glm-runner/scripts/run_glm.py "your prompt here"
```

## Supported Options and Roles

The GLM runner inherits the verified Qwen runner options (including `--ephemeral`, an alias for `--no-session-persistence`). Options, roles, return codes, and wrapper-envelope semantics are identical to `qwen-runner` — read the qwen-runner skill's `SKILL.md` when you need flag or role details beyond the examples below, or run `run_glm.py --help`.

## Examples

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "Summarize the core module architecture"
python3 .agents/skills/glm-runner/scripts/run_glm.py --prompt-file /tmp/review.md --role codereviewer --model glm-5.1
python3 .agents/skills/glm-runner/scripts/run_glm.py "Read-only analysis" --restrict-tools --no-session-persistence --json
```

## Behavior

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `glm`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. A failing GLM smoke test should block the seat.
4. Preserves the shared wrapper envelope so councils can compare GLM output with other runners consistently.
5. Never claims GLM participation when a fallback provider produced output.
6. Always includes `fallback_reason` and `effective_model` in `--json` output.

## Gotchas

- `--bare` and `--safe` are compatibility flags here; they do not switch the transport away from Qwen CLI.
