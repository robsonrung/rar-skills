---
name: claude-runner
description: Execute prompts using Claude CLI in headless print mode from the current workspace. Use when users explicitly request Claude execution, when a cross-runner workflow selects Claude as the preferred model, or when repo automation needs a Claude CLI seat alongside the other runner seats.
---

# Claude Runner

Execute prompts via Claude CLI `-p` mode with role overlays and continuation support.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas are inline below.

## Runtime Compatibility
Fallback: codex-runner only (invoked with `--disable-fallback`; the chain does not continue to qwen, kimi, or gemini).
With `--disable-fallback`, fail fast with a prerequisite message instead of routing.

1. Check whether `claude` CLI is available.
2. If available, execute this skill normally.
3. If unavailable and `codex` is available, route to `$codex-runner` as fallback and report the provider switch (`fallback_from`). The fallback invocation always passes `--disable-fallback`, so the claude ⇄ codex pair can never loop.
4. If neither is available, stop with a clear prerequisite message.

This upholds **seat fidelity**: the Claude seat's output is only ever Claude's, or the seat is reported absent — a codex fallback is always labeled via `fallback_from`, never passed off as Claude.

## Security Model

This skill invokes the local Claude CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Claude reads during the run may be sent to Anthropic according to the local Claude CLI configuration. Permission checks stay enabled. Analysis roles (every role except `implementer`) default to Claude planning mode (read-only); pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role.


## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Claude-specific envelope extensions:
- `agent_message` — the clean final answer. With `--output-format json`/`stream-json` it is parsed from the result event; with `text` it is the trimmed stdout.
- `session_id` — the Claude session id (available with `--output-format json`/`stream-json`), usable for `--resume <id>` follow-ups.

## Usage

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py "your prompt here"
```

Use `--working-dir` when the prompt depends on package-local files or generated artifacts; relative `--prompt-file`/`--session-file` paths resolve against it (not the process cwd), with `~` expanded. Use repeated `--prompt-file` flags for longer prompts or council overlays. Combine `--output-file` with `--json` to write the full envelope to disk and print only a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}`, keeping large outputs out of the orchestrator's context while still showing which seat (or labeled fallback) answered.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in a JSON envelope | False |
| `--prompt-file` | Read prompt content from a file; may be repeated | None |
| `--model`, `-m` | Claude model alias or full model name such as `claude-sonnet-5-0` or `claude-opus-4-8` | CLI default |
| `--output-format`, `-o` | Claude print-mode output format: `text`, `json`, or `stream-json` | `text` |
| `--safe` | Informational no-op; permission checks are always enabled whether or not the flag is passed | True |
| `--bare` | Use Claude bare mode for faster startup and fewer implicit context sources | False |
| `--no-session-persistence` | Do not persist Claude session files to disk | False |
| `--restrict-tools` | Use Claude planning mode (read-only) | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default planning mode | False |
| `--effort`, `-e` | Claude effort level: `low`, `medium`, `high`, `xhigh`, `max` | CLI default |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Claude session by id | None |
| `--continue` | Natively resume the most recent Claude conversation in this project | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior debate or workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope to this file atomically; with `--json`, stdout becomes a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` | None |

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Claude, analysis roles default to Claude planning mode (`--permission-mode plan`); pass `--allow-write` to opt out.

## Session Continuation

- `--resume <session-id>` / `--continue` — native Claude resume. Preferred for claude -> claude continuation; the session id comes from the `session_id` envelope field of the earlier run (requires `--output-format json` or `stream-json` on that run).
- `--session-file <file>` — prepends prior workflow context as text. Use only for cross-runner handoffs where no native session exists.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list --runner claude` / `status` / `result` / `cancel`) — see `../_shared/references/runner-common.md`.

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure) live in `../_shared/references/runner-common.md`.

## Examples

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py "Summarize the sync service"
python3 .agents/skills/claude-runner/scripts/run_claude.py "Compare two implementation plans" --model claude-sonnet-5-0
python3 .agents/skills/claude-runner/scripts/run_claude.py --prompt-file /tmp/overlay.md --prompt-file /tmp/brief.md --role codereviewer --model claude-opus-4-8
python3 .agents/skills/claude-runner/scripts/run_claude.py "Read-only architecture review" --restrict-tools --bare --no-session-persistence
python3 .agents/skills/claude-runner/scripts/run_claude.py "Continue from the accepted report" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/claude-runner/scripts/run_claude.py "Deep audit of the auth module" --role codereviewer --effort xhigh --output-format json --json
python3 .agents/skills/claude-runner/scripts/run_claude.py --resume 1f2e3d4c-... "Apply the top recommendation" --role implementer --allow-write
python3 .agents/skills/claude-runner/scripts/run_claude.py "Investigate the flaky test" --output-format json --background
```

## Behavior

1. Maps `--restrict-tools` to Claude `--permission-mode plan`; analysis roles get this by default.
2. When `--output-format json` or `stream-json` is used, the native Claude payload stays in `stdout`; the wrapper does not re-shape it, but it extracts `agent_message` and `session_id` into the envelope.
3. `--resume`/`--continue` map to the native Claude CLI flags; `--effort` maps to Claude `--effort`.
4. Resolves relative `--prompt-file`/`--session-file` paths against `--working-dir` (not the process cwd), with `~` expanded.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Claude CLI not found |
| -3 | Invalid input or unexpected error |
| -4 | Bare mode without `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (bare mode disables OAuth/keychain auth) |

## Prerequisites

- Claude CLI installed and in PATH
- Claude CLI authenticated

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat; do not remove it.
