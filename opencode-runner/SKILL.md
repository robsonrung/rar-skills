---
name: opencode-runner
description: Execute prompts using OpenCode CLI in headless mode from the current workspace. Use when users explicitly request OpenCode execution, when a workflow needs an OpenCode CLI run inside this repository, or when a cross-runner workflow selects OpenCode as the preferred model. Triggers on mentions of OpenCode, opencode run, OpenCode CLI, or OpenCode headless mode.
---

# OpenCode Runner

Execute prompts via OpenCode CLI headless mode (`opencode run`) with XML-tagged role overlays,
streaming output, session continuation, and file attachment support.

OpenCode provides access to 75+ LLM providers (Anthropic, OpenAI, Google, Groq, AWS Bedrock, Azure,
OpenRouter, etc.) through a unified CLI interface.

## Sandbox Safety

**Agent Safehouse (OS-level):** When [Agent Safehouse](https://agent-safehouse.dev/) (`safehouse` binary) is installed,
the runner automatically wraps the subprocess with a macOS kernel-level sandbox that restricts
filesystem writes to the working directory.

Install: `brew install eugene1g/safehouse/agent-safehouse`

To opt out: pass `--no-safehouse`. To fail closed when Safehouse is unavailable, pass `--require-safehouse`.

## Security Model

This skill invokes the local OpenCode CLI from the current machine. Prompt text, prompt files, session files, metadata, attached files, and any files OpenCode reads during the run may be sent to the selected provider. OpenCode headless mode may run tool calls without interactive permission prompts. Use Safehouse for a filesystem boundary, prefer `--require-safehouse` for sensitive work, and use `--no-safehouse` only when the user accepts the local execution risk.

## Runtime Compatibility
Requirement: provider-auth preflight before execution.
If selected provider model is unauthorized, stop with blocked_reason=missing_provider_auth.
Make Safehouse optional and platform-guarded.
Output must include provider/model provenance envelope.

1. Try executing via `opencode` CLI in headless mode (preferred).
2. If the CLI is not available (script returns code `-2`), stop with a clear prerequisite message.


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
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "your prompt here"
```

For repository-aware tasks, prefer `--working-dir` set to the repository root.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Output script result in JSON envelope | False |
| `--model`, `-m` | Model in `provider/model` format (e.g., `openrouter/anthropic/claude-sonnet-4.6`) | CLI default |
| `--stream` | Stream JSON events to stderr in real-time (forces `--format json`) | False |
| `--prompt-file` | Read the prompt from a file | None |
| `--role` | Apply a role overlay (see Roles section) | None |
| `--session-file` | Append prior debate or workflow context for continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--continue`, `-c` | Continue the last session | False |
| `--session`, `-s` | Resume a specific session by ID | None |
| `--file`, `-f` | File(s) to attach to message (repeatable) | None |
| `--title` | Title for the session | None |
| `--agent` | Agent to use | None |
| `--no-safehouse` | Skip safehouse OS-level sandboxing even when installed | False |
| `--require-safehouse` | Fail unless Agent Safehouse is available for this run | False |

## Model Format

OpenCode uses `provider/model` notation. Common models:

| Provider | Model Examples |
|----------|---------------|
| Anthropic via OpenRouter | `openrouter/anthropic/claude-sonnet-4.6`, `openrouter/anthropic/claude-opus-4.7` |
| OpenAI | `openai/gpt-5.4`, `openai/gpt-5.4-mini`, `openai/gpt-5.3-codex` |
| Google | `google/gemini-2.5-pro`, `google/gemini-2.5-flash` |
| Kimi For Coding | `kimi-for-coding/k2p6` |
| Z.AI | `alibaba-cn/glm-5.1` |
| Minimax | `alibaba-cn/MiniMax/MiniMax-M2.7` |

## Roles

Roles inject XML-tagged prompt blocks that give OpenCode a durable identity and structured
constraints. When a role is active, the user prompt is also wrapped in `<task>` tags.

| Role | Purpose |
|------|---------|
| `planner` | Break work into phases with risks, dependencies, and exit criteria |
| `codereviewer` | Evidence-based review with P1-P4 severity ratings |
| `implementer` | Forward-progress coding with completeness contracts and verification loops |
| `synthesizer` | Reconcile competing proposals into an actionable recommendation |
| `challenger` | Devil's advocate — stress-test the emerging consensus |
| `researcher` | Thorough investigation with citation rules and fact/inference distinction |

## Examples

```bash
# Basic prompt
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "create a python script that lists files"

# With specific model
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "explain this code" \
  --model "openrouter/anthropic/claude-sonnet-4.6"

# With timeout and working directory
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "add unit tests for the core module" \
  --working-dir "$PWD/backend" --timeout 3600

# Use OpenAI model
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "review this architecture" \
  --model "openai/gpt-5.4"

# Use Google model
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "analyze the codebase" \
  --model "google/gemini-2.5-pro"

# Stream output in real-time
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "refactor the auth module" --stream

# JSON output for council integration
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "summarize the repo" --json

# Role overlay for code review
python3 .agents/skills/opencode-runner/scripts/run_opencode.py --prompt-file /tmp/review.md --role codereviewer

# Adversarial review
python3 .agents/skills/opencode-runner/scripts/run_opencode.py --prompt-file /tmp/diff.md --role challenger

# Research with citations
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "how does the permission system work in this repo" \
  --role researcher --working-dir "$PWD"

# Attach files to the prompt
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "review these files" \
  --file src/main.ts --file src/utils.ts

# Continue the last session
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "now add tests for the edge cases" --continue

# Resume a specific session
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "continue review" --session "abc-123"

# Session continuation with prior context
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "Implement the accepted recommendation" \
  --role implementer --session-file .ai-workflow/consensus/feature-x.md
```

## Behavior

1. Runs `opencode run "<prompt>"` through the local runner script.
2. OpenCode headless mode may execute tool calls without interactive permission prompts. The wrapper records whether Safehouse was active, missing, or disabled.
3. Supports XML-tagged role specialization so consensus and review workflows can give OpenCode a durable seat identity.
4. Supports continuation by appending prior round or report context from `--session-file` wrapped in context.
5. Supports native session continuation via `--continue` (most recent) or `--session <id>` (specific session).
6. Prefers `--prompt-file` for long prompts to avoid shell quoting issues.
7. When `--format json` is used (via `--json` or `--stream`), parses the JSON output and extracts `agent_message` and `usage` into the result envelope.
8. When `--stream` is used, forces JSON format and reads stdout line-by-line, printing formatted events to stderr in real-time.
9. Returns a consistent JSON envelope including runner identity and execution diagnostics.

## Output Formats

### Default (text)

Plain text output — OpenCode's response is printed to stdout.

### JSON (`--json`)

Returns a JSON envelope with:
- `agent_message`: The model's response text
- `usage`: Token usage statistics (if available)
- `events`: Raw JSON events from the CLI

## Session Management

```bash
# Continue the most recent conversation
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "follow up question" --continue

# Resume a specific session by ID
python3 .agents/skills/opencode-runner/scripts/run_opencode.py "continue review" --session "session-id"
```

This is complementary to `--session-file`, which appends prior context from a file into the prompt.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | OpenCode CLI not found |
| -3 | Unexpected error |

## Gotchas

- **Headless execution**: OpenCode headless mode may run tool calls without permission prompts. There is no native `--safe` equivalent, so use Agent Safehouse when a filesystem boundary matters.
- **Model format**: Always use `provider/model` format (e.g., `openrouter/anthropic/claude-sonnet-4.6`), not just the model name.
- **No native effort control**: OpenCode does not have a built-in `--effort` flag. Reasoning effort depends on the provider/model chosen.
- **File attachments**: Use `--file` (repeatable) to attach files to the prompt context. OpenCode also supports `@filename` syntax in prompts.
- **Auth via env vars**: Configure API keys via environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, etc.
- **Config file**: Settings in `~/.opencode.json` or `./.opencode.json` (project-local).
- **No bidirectional streaming**: `opencode run` is one-shot. Use `--continue`/`--session` for multi-turn conversations.

## Prerequisites

- **CLI**: OpenCode CLI installed and in PATH. Install via:
  - `brew install opencode-ai/tap/opencode`
  - `go install github.com/opencode-ai/opencode@latest`
- **API keys**: At least one provider API key set in environment (e.g., `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
