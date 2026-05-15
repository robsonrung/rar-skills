---
name: gemini-runner
description: Execute prompts using Gemini CLI in headless mode. Use when users request Gemini execution or when a consensus workflow needs a Gemini seat and the local Gemini CLI is installed.
---

# Gemini Runner

Execute prompts via Gemini CLI headless mode with role overlays and continuation support.

## Runtime Compatibility
Requirement: full fallback order including qwen/kimi/opencode seats.
Standardize envelope fields: runner, effective_runner, fallback_reason, auth_ok.
Keep disable-fallback strict and explicit.
Document seat-unavailable behavior for councils.

1. Check whether `gemini` CLI is available.
2. If available, run this skill.
3. If unavailable, route to `$codex-runner` or `$claude-runner` and report the fallback.
4. Never claim Gemini participated when a fallback provider produced the output.


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
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "your prompt here"
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Maximum execution time in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current directory |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Gemini model to use | `gemini-2.5-flash` |
| `--output-format`, `-o` | Gemini output format: `text`, `json`, or `stream-json` | `text` |
| `--no-yolo` | Disable auto-approval mode | False |
| `--prompt-file` | Read the prompt from a file | None |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior workflow context for continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |

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
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Explain this code"
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Analyze this file" --output-format json
python3 .agents/skills/gemini-runner/scripts/run_gemini.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
```

## Behavior

1. Executes `gemini --prompt`.
2. Adds `--yolo` by default unless `--no-yolo` is provided.
3. Supports role overlays, `--prompt-file`, and `--session-file` continuation.
4. Returns a runner envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, `effective_runner`, and execution metadata.
5. Does not expose unverified council-only flags such as `--thinking-budget` or a read-only convenience mode.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1+ | Gemini CLI error (passthrough) |
| -1 | Timeout expired |
| -2 | Gemini CLI not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Gemini CLI installed and available in PATH
- Authentication configured for Gemini CLI
