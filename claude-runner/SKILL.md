---
name: claude-runner
description: Execute prompts using Claude CLI in headless print mode from the current workspace. Use when users explicitly request Claude execution, when a cross-runner workflow selects Claude as the preferred model, or when repo automation needs a Claude CLI seat alongside Codex, Gemini, GLM, or Qwen.
---

# Claude Runner

Execute prompts via Claude CLI `-p` mode with role overlays and continuation support.

## Runtime Compatibility
Fallback order: codex-runner -> qwen-runner -> kimi-runner -> gemini-runner.
Honor --disable-fallback as fail-fast.
Always emit effective_runner, effective_model, fallback_reason.
Requirement: auth preflight result field auth_ok.

1. Check whether `claude` CLI is available.
2. If available, execute this skill normally.
3. If unavailable and `codex` is available, route to `$codex-runner` as fallback and report the provider switch.
4. If neither is available, stop with a clear prerequisite message.

## Security Model

This skill invokes the local Claude CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Claude reads during the run may be sent to Anthropic according to the local Claude CLI configuration. Permission checks stay enabled. Use `--restrict-tools` for read only review seats.


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
python3 .agents/skills/claude-runner/scripts/run_claude.py "your prompt here"
```

Use `--working-dir` when the prompt depends on package-local files or generated artifacts. Use repeated `--prompt-file` flags for longer prompts or council overlays.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in a JSON envelope | False |
| `--prompt-file` | Read prompt content from a file; may be repeated | None |
| `--model`, `-m` | Claude model alias or full model name such as `claude-sonnet-4-6` or `claude-opus-4-7` | CLI default |
| `--output-format`, `-o` | Claude print-mode output format: `text`, `json`, or `stream-json` | `text` |
| `--safe` | Keep Claude permission checks enabled | True |
| `--bare` | Use Claude bare mode for faster startup and fewer implicit context sources | False |
| `--no-session-persistence` | Do not persist Claude session files to disk | False |
| `--restrict-tools` | Use Claude planning mode for read-only analysis seats | False |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior debate or workflow context for continuation | None |
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
python3 .agents/skills/claude-runner/scripts/run_claude.py "Summarize the sync service"
python3 .agents/skills/claude-runner/scripts/run_claude.py "Compare two implementation plans" --model claude-sonnet-4-6
python3 .agents/skills/claude-runner/scripts/run_claude.py --prompt-file /tmp/overlay.md --prompt-file /tmp/brief.md --role codereviewer --model claude-opus-4-7
python3 .agents/skills/claude-runner/scripts/run_claude.py "Read-only architecture review" --restrict-tools --bare --no-session-persistence
python3 .agents/skills/claude-runner/scripts/run_claude.py "Continue from the accepted report" --role implementer --session-file .ai-workflow/consensus/feature-x.md
```

## Behavior

1. Executes `claude -p` through the local runner script.
2. Keeps Claude permission checks enabled.
3. Maps `--restrict-tools` to Claude `--permission-mode plan` for read-only analysis seats.
4. Supports repeated `--prompt-file` flags, role overlays, and `--session-file` continuation.
5. Returns a runner envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, `effective_runner`, and execution metadata.
6. When `--output-format json` or `stream-json` is used, the native Claude payload stays in `stdout`; the wrapper does not re-shape it.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Claude CLI not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Claude CLI installed and in PATH
- Claude CLI authenticated
