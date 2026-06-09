---
name: codex-runner
description: Execute prompts using Codex CLI in non-interactive exec mode. Use when users explicitly request Codex execution, when a workflow needs a Codex CLI run inside this repository, or when a cross-runner workflow selects Codex as the preferred model and native Codex subagents are unavailable.
---

# Codex Runner

Execute prompts via Codex CLI `exec` mode with role overlays and continuation support.

## Runtime Compatibility

1. Check whether `codex` CLI is available.
2. If available, execute this skill normally.
3. If unavailable, the script automatically falls back to the claude-runner skill (`run_claude.py`) and reports the provider switch (`fallback_from`, `fallback_reason`); runner provenance fields stay mandatory in the envelope.
4. If `--disable-fallback` is set or no fallback runner is found, the script exits non-zero with `return_code` -2 and a clear prerequisite message.

The broader cross-runner probe chain (codex -> qwen -> kimi -> gemini -> claude) is a contract owned by the runner skills that implement it (see the claude-runner skill's SKILL.md for its own fallback order); this wrapper implements only the codex -> claude leg.

## Security Model

This skill invokes the local Codex CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Codex reads during the run may be sent to OpenAI according to the local Codex CLI configuration. The wrapper no longer passes `--full-auto` by default. Use `--restrict-tools` for read only review seats, and use `--full-auto` only for a user approved unattended run.


## Output Envelope

All `--json` responses must conform to `.agents/skills/_shared/runner-envelope.schema.json` (an install-time path; the schema is not bundled in this repo, so the required-keys list below is the operative contract).
Required top-level keys:
- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok`
- `fallback_reason`
- `success`
- `return_code`

Envelopes also include `stdout`, `stderr`, and execution metadata (command, working directory, role, sandbox, and related fields).

## Usage

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout; when running from this source repo, skills live at the repo root, so invoke `codex-runner/scripts/run_codex.py` instead.

For repository-aware tasks, prefer `--working-dir` set to the repository root so Codex picks up the applicable local instructions.

Before composing non-trivial prompts (reviews, implementations, research seats), read `references/prompting.md` for task-type XML recipes and anti-patterns.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Codex model alias | CLI default |
| `--sandbox`, `-s` | Codex sandbox mode override | CLI default |
| `--restrict-tools` | Use `--sandbox read-only` for analysis seats | False |
| `--full-auto` | Pass Codex full auto mode for an explicitly approved unattended run | False |
| `--approval-policy`, `-a` | Codex approval policy override | None |
| `--skip-git-repo-check` | Allow runs outside a Git repo | False |
| `--prompt-file` | Read the prompt from a file | None |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior workflow context for continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--ephemeral` | Run without persisting session files to disk | False |
| `--output-schema` | Path to a JSON Schema file for the final response shape | None |
| `--output-file` | Write the full wrapper JSON result atomically to this file | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |

When `--json` and `--output-file` are combined, stdout becomes a compact `{success, return_code, output_file}` summary, keeping large Codex outputs out of an orchestrating agent's context window.

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
python3 .agents/skills/codex-runner/scripts/run_codex.py "Explain this module"
python3 .agents/skills/codex-runner/scripts/run_codex.py "Review the staged diff" --role codereviewer --restrict-tools
python3 .agents/skills/codex-runner/scripts/run_codex.py --prompt-file /tmp/review.md --role challenger --ephemeral
python3 .agents/skills/codex-runner/scripts/run_codex.py "Return JSON matching the schema" --output-schema /tmp/schema.json
python3 .agents/skills/codex-runner/scripts/run_codex.py "Audit the auth module" --json --output-file /tmp/codex-audit.json
python3 .agents/skills/codex-runner/scripts/run_codex.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
```

## Behavior

1. Executes `codex exec`.
2. Supports role overlays, `--prompt-file`, and `--session-file` continuation.
3. When Codex CLI is invoked with `--json`, the native Codex JSONL event stream remains in `stdout`; the wrapper does not re-shape it.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Codex CLI not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Codex CLI installed and in PATH
- Codex CLI authenticated
