---
name: qwen-runner
description: Execute prompts using Qwen Code CLI in headless mode with JSON-stream output by default. Use when users explicitly request Qwen execution, when a workflow needs a verified Qwen-backed seat, or when another runner skill should reuse the shared Qwen CLI wrapper.
---

# Qwen Runner

Execute prompts through the local `qwen` CLI in one-shot headless mode. Prefer this skill for automation, councils, and scripted validation where structured stream output is helpful. This is also the canonical wrapper doc the gemma/glm/minimax shims point at.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas (the qwen-specific approval-mode/wrapper detail and gotchas) are inline below.

## Prerequisites

- `qwen` installed and in `PATH`
- A model provider configured in the qwen CLI — a `modelProviders` entry in `~/.qwen/settings.json` (with its API key env var set) or credentials supplied via `--openai-api-key` / `--auth-type`. The legacy `qwen auth` subcommand has been removed.

## Security Model

This skill invokes the local Qwen CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Qwen reads during the run may be sent to the selected provider behind the local Qwen account. Analysis roles (every role except `implementer`) default to restricted mode: a read-only prompt overlay plus `--approval-mode plan`; pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.


## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Qwen-specific extensions: `agent_message` (the clean final answer extracted from the native result event, or trimmed stdout in `text` mode) and `session_id` when the native stream reports one.

## Usage

Invoke the script from the repository root:

```bash
ROOT=$(git rev-parse --show-toplevel || pwd)
python3 "$ROOT/.agents/skills/qwen-runner/scripts/run_qwen.py" "your prompt here"
```

Paths use the installed `.agents/skills/` layout; when running from this source repo, skills live at the repo root, so invoke `qwen-runner/scripts/run_qwen.py` instead.

## Supported Options

- `--timeout`
- `--working-dir`
- `--json`
- `--prompt-file` (repeatable)
- `--model`
- `--output-format` with default `stream-json`
- `--input-format`
- `--approval-mode` with default `default`; choices `plan`, `default`, `auto-edit`, `auto`, `yolo`
- `--sandbox`
- `--restrict-tools` (default for analysis roles)
- `--allow-write` (opt an analysis role out of restricted mode)
- `--background` (tracked background job; manage with `_shared/scripts/runner_jobs.py`)
- `--role`
- `--session-file`
- `--metadata-json`
- `--output-schema`
- `--ephemeral`
- `--no-session-persistence`
- `--safe`
- `--bare`
- `--disable-fallback`
- `--output-file`

`--safe`, `--bare`, and `--disable-fallback` are accepted for cross-runner compatibility (see Behavior item 5 for the no-fallback rule). Run the script with `--help` for per-flag docs.

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Qwen, analysis roles default to restricted mode: a read-only prompt overlay plus `--approval-mode plan`; pass `--allow-write` to opt out. Otherwise approval mode defaults to `default`.

## Examples

```bash
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Explain the core module architecture"
python3 .agents/skills/qwen-runner/scripts/run_qwen.py --prompt-file /tmp/stance.md --prompt-file /tmp/brief.md --role codereviewer --restrict-tools
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Return JSON matching the schema" --output-schema /tmp/schema.json --json
```

## Behavior

1. Runs the local `qwen` CLI directly with `--channel CI` for headless execution.
2. Defaults to `--output-format stream-json` so automation can consume the native event stream.
3. Returns a wrapper envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, and `effective_runner`.
4. Keeps the native Qwen JSON or JSONL output in `stdout`; the wrapper `--json` flag only controls the outer envelope.
5. Never falls back to another provider. Missing CLI or auth failures block the seat explicitly and report it absent (**seat fidelity**) — the seat is never substituted by another model.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Qwen CLI not found |
| -3 | Invalid input, native API/auth error, or unexpected error |

On `-2` the envelope also carries `status: seat_unavailable`. There is no separate return code for auth failures: native API/auth errors are folded into `-3`, the `[API Error: ...]` text is appended to `stderr`, and `auth_ok` stays `null` in that case (only `-2` sets it to `false`).

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `../_shared/references/runner-common.md`. This also applies to the gemma/glm/minimax shims, which tag jobs with their own runner name.

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure) live in `../_shared/references/runner-common.md`.

## Gotchas

- `--output-schema` is enforced natively via the qwen CLI's `--json-schema` flag (a synthetic `structured_output` tool; the session ends on the first valid call). The schema is passed as `@<path>` and is not injected into the prompt. The structured object surfaces in `native_result`; `agent_message` is its JSON serialization (parse with `json.loads` to recover the object). A ready-made review schema (verdict/findings/next_steps) is bundled at `codex-runner/schemas/review-output.schema.json` and works with any runner.
- `--output-schema` and `--restrict-tools` interact: when `--output-schema` is set, the `restrict_tools` → `plan` rewrite is skipped (plan mode can block the synthetic `structured_output` tool). For a schema run that must stay read-only, pass `--approval-mode auto` explicitly — the LLM classifier approves the structured output without auto-approving edits.
- `--approval-mode yolo` auto-approves every tool, including edits and destructive actions. Reserve for ephemeral sandboxes. `auto` is safer: an LLM classifier approves safe actions and blocks risky ones.
- `--restrict-tools` adds a read-only overlay to the prompt and switches headless approval mode to `plan`; it is not a hard tool sandbox.
- Use the runner's `--json` flag when a workflow needs the wrapper envelope on stdout.
- Chat recording is always disabled (the wrapper always passes `--chat-recording=false`); `--ephemeral` and `--no-session-persistence` are compatibility no-ops.
