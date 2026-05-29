---
name: gemini-runner
description: Execute prompts using Antigravity CLI (`agy`) headless print mode for a Gemini/Google seat. Use when users request Gemini execution, Antigravity CLI execution, or when a consensus workflow needs a Gemini seat and local `agy` is installed.
---

# Gemini Runner

Execute prompts via Antigravity CLI (`agy`) headless print mode with role overlays and continuation support.

## Runtime Compatibility
Requirement: full fallback order including qwen and kimi seats.
Standardize envelope fields: runner, effective_runner, fallback_reason, auth_ok.
Keep disable-fallback strict and explicit.
Document seat-unavailable behavior for councils.

1. Check whether Antigravity CLI (`agy`) is available.
2. If available, run this skill.
3. If unavailable, route through the fallback order `$qwen-runner`, `$kimi-runner`, `$codex-runner`, then `$claude-runner`, and report the fallback.
4. Never claim the Gemini/Google seat participated when a fallback provider produced the output.

## Security Model

This skill invokes the local Antigravity CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Antigravity reads during the run may be sent to the configured Google model. Permission checks stay enabled through the local Antigravity configuration.


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
| `--model`, `-m` | Compatibility metadata label. `agy` uses its configured model from `/model` or settings. | `agy-configured-model` |
| `--output-format`, `-o` | Response format hint: `text`, `json`, or `stream-json`. `agy` print mode has no output-format launch flag. | `text` |
| `--prompt-file` | Read the prompt from a file | None |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior workflow context for continuation | None |
| `--agy-continue` | Resume the most recent Antigravity CLI conversation with native `agy --continue` | False |
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
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Continue the previous analysis" --agy-continue
```

## Behavior

1. Executes `agy [--continue] --print-timeout <Ns> --print "<prompt>"`.
2. Does not request a permission bypass.
3. Supports role overlays, `--prompt-file`, `--session-file` prompt context, and `--agy-continue` native Antigravity conversation continuation.
4. Returns a runner envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, `effective_runner`, and execution metadata.
5. Keeps `runner=gemini` for workflow compatibility and sets `effective_runner=agy` when Antigravity CLI produced the output.
6. Does not pass unsupported Gemini CLI flags such as `--model`, `--output-format`, `--thinking-budget`, or a read-only convenience mode to `agy`.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1+ | Antigravity CLI (`agy`) error (passthrough) |
| -1 | Timeout expired |
| -2 | Antigravity CLI (`agy`) not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Antigravity CLI (`agy`) installed and available in PATH
- Authentication configured for Antigravity CLI
- Model selection configured in `agy` via `/model` or `~/.gemini/antigravity-cli/settings.json` when a specific model is required
