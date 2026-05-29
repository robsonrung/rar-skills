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

This skill delegates to `qwen-runner`, so it has the same execution and data sharing model as the Qwen wrapper. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected GLM provider. Approval mode defaults to `default`; pass `--approval-mode yolo` only for a user approved unattended run.


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
python3 .agents/skills/glm-runner/scripts/run_glm.py "your prompt here"
```

## Supported Options

The GLM runner inherits the verified Qwen runner options:
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
python3 .agents/skills/glm-runner/scripts/run_glm.py "Summarize the core module architecture"
python3 .agents/skills/glm-runner/scripts/run_glm.py --prompt-file /tmp/review.md --role codereviewer --model glm-5.1
python3 .agents/skills/glm-runner/scripts/run_glm.py "Read-only analysis" --restrict-tools --no-session-persistence --json
```

## Behavior
## Runtime Compatibility
Requirement: optional fallback policy and provenance requirements.
Never claim GLM participation when fallback provider produced output.
Output must include fallback_reason and effective_model.

1. Delegates to the shared `qwen-runner` implementation with runner identity set to `glm`.
2. Uses `stream-json` as the default native Qwen output format.
3. Never falls back to another provider. A failing GLM smoke test should block the seat.
4. Preserves the shared wrapper envelope so councils can compare GLM output with other runners consistently.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Qwen CLI not found |
| -3 | Invalid input or unexpected error |

## Gotchas

- `--bare` and `--safe` are compatibility flags here; they do not switch the transport away from Qwen CLI.
- `--output-schema` is prompt-enforced, not natively validated by Qwen CLI.
