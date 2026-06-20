---
name: kimi-runner
description: Execute prompts using Kimi CLI in headless mode with stream-json output by default. Use when users explicitly request Kimi execution, when a workflow needs a Kimi-backed seat, or when a cross-runner workflow wants a Moonshot Kimi perspective without leaving the current workspace.
---

# Kimi Runner

Execute prompts through the local `kimi-cli` in one-shot headless mode. Prefer this skill for councils, scripted validation, and Kimi-specific runs where stream-friendly output and a consistent runner envelope matter.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas are inline below.

## Default Model

- `kimi-code/kimi-for-coding`

This matches the locally configured coding model in `~/.kimi/config.toml`. Pass `--model` if you need a different Kimi model exposed by the local CLI.

## Security Model

This skill invokes the local Kimi CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Kimi reads during the run may be sent to Moonshot according to the local Kimi configuration. Analysis roles (every role except `implementer`) default to a read-only overlay on the prompt; pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role. The overlay is a prompt-level constraint rather than a hard sandbox.

## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Kimi-specific extensions: `agent_message` (the clean final assistant answer — same value as the legacy `assistant_message` field, or trimmed stdout in `text` mode) and `session_id` when the native stream reports one.

## Usage

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. When running from this source repo, skills live at the repo root, so invoke `kimi-runner/scripts/run_kimi.py` instead.

## Supported Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Maximum execution time in seconds | `3600` |
| `--working-dir`, `-w` | Working directory for execution | Current dir |
| `--json`, `-j` | Output wrapper results in JSON format | `False` |
| `--prompt-file` | Read prompt content from a file; repeatable | None |
| `--model`, `-m` | Kimi model to use | `kimi-code/kimi-for-coding` |
| `--output-format`, `-o` | Kimi CLI output format: `text` or `stream-json` | `stream-json` |
| `--thinking` | Enable Kimi thinking mode explicitly | CLI default |
| `--no-thinking` | Disable Kimi thinking mode explicitly | CLI default |
| `--continue` | Resume the previous Kimi session for the working directory | `False` |
| `--session` | Resume a specific Kimi session by ID | None |
| `--restrict-tools` | Add a read-only analysis overlay to the prompt | `True` for analysis roles |
| `--allow-write` | Opt an analysis role out of the read-only overlay | `False` |
| `--background` | Run as a tracked background job and return a job id immediately | `False` |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior workflow context from a file | None |
| `--metadata-json` | JSON string to embed as execution metadata | None |
| `--output-schema` | Path to a JSON Schema file for the final response shape | None |
| `--ephemeral`, `--no-session-persistence`, `--safe`, `--bare`, `--disable-fallback` | Accepted for cross-runner parity; no effect on Kimi CLI (Kimi never falls back) | `False` |
| `--output-file` | Write the wrapper JSON result to this file atomically | None |

The parity no-op flags above are accepted so callers can use the same flag set across runner skills. They do not currently change Kimi CLI behavior; in particular, `--no-session-persistence` is inert because the current Kimi CLI still records resumable session metadata in print mode.

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Kimi, analysis roles default to a read-only prompt overlay (a prompt-level constraint, not a sandbox); pass `--allow-write` to opt out.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `../_shared/references/runner-common.md`.

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure) live in `../_shared/references/runner-common.md`.

## Examples

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Summarize the core module architecture"
python3 .agents/skills/kimi-runner/scripts/run_kimi.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/kimi-runner/scripts/run_kimi.py --prompt-file /tmp/stance.md --prompt-file /tmp/brief.md --output-format stream-json --json
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Return JSON only" --output-schema /tmp/schema.json --json
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Continue the last Kimi session in this repo" --continue
```

## Behavior

1. Runs `kimi-cli --print` directly for non-interactive execution.
2. Defaults to `--output-format stream-json` so councils and scripts can consume native event output.
3. Returns a wrapper envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, and `effective_runner`.
4. Keeps native Kimi output in `stdout`; the wrapper `--json` flag only controls the outer envelope.
5. Never falls back to another provider. Missing CLI or auth failures block the seat explicitly.
6. Preserves Kimi's resume hint lines in raw `stdout`, while also extracting `agent_message` (alias `assistant_message`), `session_id`, and `native_result` when the native stream is parseable.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Kimi CLI not found |
| -3 | Invalid input or unexpected error |

## Gotchas

- Kimi print mode still emits a resume hint after the final answer. The wrapper keeps raw output and also extracts the assistant message separately when possible.
- `--output-schema` is prompt-enforced, not validated by a native Kimi schema flag. A ready-made review schema (verdict/findings/next_steps) is bundled at `codex-runner/schemas/review-output.schema.json` and works with any runner.
- `--restrict-tools` is a prompt overlay, not a sandbox — see Security Model.

## Prerequisites

- `kimi-cli` installed and in `PATH`
- Authentication configured via `kimi-cli login`

This is **seat fidelity** for a no-fallback runner: if `kimi-cli` is missing or auth fails, the seat is blocked and reported absent, never substituted by another model. The envelope returns `success=false` with remediation guidance in `stderr`. A missing CLI maps to `return_code=-2` and `status=seat_unavailable`; auth failures surface as kimi-cli's native nonzero exit code with `auth_ok` unset — treat any `success=false` as a blocked seat.
