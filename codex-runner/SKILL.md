---
name: codex-runner
description: Execute prompts using Codex CLI in non-interactive exec mode. Use when users explicitly request Codex execution, when a workflow needs a Codex CLI run inside this repository, or when a cross-runner workflow selects Codex as the preferred model and native Codex subagents are unavailable.
---

# Codex Runner

Execute prompts via Codex CLI `exec` mode with role overlays and continuation support.

## Runtime Compatibility
Requirement: fallback chain beyond Claude-only behavior.
Probe order: codex -> qwen -> kimi -> gemini -> claude.
Output must include provider switch reason and keep runner provenance fields mandatory.
If --disable-fallback: return non-zero with prerequisites.

1. Check whether `codex` CLI is available.
2. If available, execute this skill normally.
3. If unavailable and `claude` is available, route to `$claude-runner` as fallback and report the provider switch.
4. If neither is available, stop with a clear prerequisite message.

## Security Model

This skill invokes the local Codex CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Codex reads during the run may be sent to OpenAI according to the local Codex CLI configuration. The wrapper no longer passes `--full-auto` by default. Use `--restrict-tools` for read only review seats, and use `--full-auto` only for a user approved unattended run.


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
python3 .agents/skills/codex-runner/scripts/run_codex.py "your prompt here"
```

For repository-aware tasks, prefer `--working-dir` set to the repository root so Codex picks up the applicable local instructions.

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
python3 .agents/skills/codex-runner/scripts/run_codex.py "Explain this module"
python3 .agents/skills/codex-runner/scripts/run_codex.py "Review the staged diff" --role codereviewer --restrict-tools
python3 .agents/skills/codex-runner/scripts/run_codex.py --prompt-file /tmp/review.md --role challenger --ephemeral
python3 .agents/skills/codex-runner/scripts/run_codex.py "Return JSON matching the schema" --output-schema /tmp/schema.json
python3 .agents/skills/codex-runner/scripts/run_codex.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
```

## Behavior

1. Executes `codex exec`.
2. Uses Codex CLI defaults when no explicit sandbox is requested. Pass `--full-auto` only after explicit user approval.
3. Maps `--restrict-tools` to `--sandbox read-only`.
4. Passes through `--ephemeral` and `--output-schema`.
5. Supports role overlays, `--prompt-file`, and `--session-file` continuation.
6. Returns a runner envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, `effective_runner`, and execution metadata.
7. When Codex CLI is invoked with `--json`, the native Codex JSONL event stream remains in `stdout`; the wrapper does not re-shape it.

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
