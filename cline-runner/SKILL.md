---
name: cline-runner
description: Execute prompts using Cline CLI in headless print mode with NDJSON streaming output by default. Use when users explicitly request Cline execution, when a workflow needs a Cline-backed seat with an arbitrary provider/model pair (Anthropic, OpenAI, Z.AI, OpenRouter, etc.), or when a cross-runner workflow selects Cline as the preferred model.
---

# Cline Runner

Execute prompts through the local `cline` CLI in one-shot headless mode. Cline is provider-agnostic — unlike single-vendor runners, `--model` takes any `provider/model` pair the local `cline auth` has configured, so this is the runner to reach for when the caller needs to pick the exact model per run.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas are inline below.

## Default Model

None forced. Cline uses whichever `provider/model` the local `cline auth` last configured (inspect with `cline config` interactively, or `cat ~/.cline/data/settings/providers.json`). Pass `--model provider/model-id` to pick a specific model for a run — e.g. `--model anthropic/claude-sonnet-4-5`, `--model openai/gpt-5.1`, `--model zai/glm-5.2`. Pass `--provider` to select an authenticated provider id (`cline`, `cline-pass`, or whatever `cline auth` set up) independently of the model string.

## Security Model

This skill invokes the local Cline CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Cline reads or writes during the run may be sent to the configured provider. Cline's native `--auto-approve false` is a **real enforcement boundary**, not a prompt overlay: with it set, tool calls fail cleanly with an explicit approval error instead of running (verified — the model receives `"Tool approval requires an interactive session, but this session is non-interactive."` and continues without ever touching the filesystem). Analysis roles (every role except `implementer`) default to `--auto-approve false`; pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role.

**`--model` mutates the user's persisted Cline config.** Passing `--model` (even an invalid one) rewrites the selected provider's `model` field in `~/.cline/data/settings/providers.json` as a side effect — the *next interactive* `cline` session on this machine will pick up whatever model this runner last requested. For automated/scripted runs where that persistence is unwanted, pass `--data-dir <path>` to isolate state into a scratch directory instead of touching `~/.cline`.

## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Cline-specific extensions: `agent_message` (the final answer text, extracted from the terminal `run_result` event, or trimmed stdout in `text` mode), `finish_reason` (Cline's native `completed`/`error`/etc.), `native_model_id`/`native_provider` (the model that actually answered, read back from the stream — useful when `--model` was omitted), `native_return_code` (the raw process exit code before return-code normalization), and `session_id` (recovered from `cline history`, not from the stream itself — see Gotchas).

## Usage

```bash
python3 .agents/skills/cline-runner/scripts/run_cline.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. When running from this source repo, skills live at the repo root, so invoke `cline-runner/scripts/run_cline.py` instead.

## Supported Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Maximum execution time in seconds; also passed to native `--timeout` (minus a 5s margin) so Cline self-terminates cleanly first | `3600` |
| `--working-dir`, `-w` | Working directory for execution | Current dir |
| `--json`, `-j` | Output wrapper results in JSON format | `False` |
| `--prompt-file` | Read prompt content from a file; repeatable | None |
| `--model`, `-m` | Cline model id, `provider/model` form | Locally configured default |
| `--provider`, `-P` | Cline provider id (native `-P`) | Locally configured default |
| `--output-format`, `-o` | `text` or `stream-json` (native `--json` on/off) | `stream-json` |
| `--thinking` | Reasoning effort: `none\|low\|medium\|high\|xhigh` | Provider default |
| `--session` | Resume a specific Cline session by id (native `--id`) | None |
| `--worktree` | Auto-create a detached git worktree under `~/.cline/worktrees/` and run there (native `--worktree`) | `False` |
| `--data-dir` | Isolated local state directory (native `--data-dir`) — use for automated runs to avoid mutating `~/.cline` | None |
| `--config` | Configuration directory (native `--config`) | None |
| `--system` | Override the default Cline system prompt (native `--system`) | None |
| `--restrict-tools` | Force native `--auto-approve false` | `True` for analysis roles |
| `--allow-write` | Opt an analysis role out of the `--auto-approve false` restriction | `False` |
| `--background` | Run as a tracked background job and return a job id immediately | `False` |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior workflow context from a file | None |
| `--metadata-json` | JSON string to embed as execution metadata | None |
| `--output-schema` | Path to a JSON Schema file for the final response shape (prompt-enforced) | None |
| `--ephemeral`, `--no-session-persistence`, `--safe`, `--bare`, `--disable-fallback` | Accepted for cross-runner parity; no effect on Cline CLI | `False` |
| `--output-file` | Write the wrapper JSON result to this file atomically | None |

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Cline, analysis roles default to native `--auto-approve false`, a real enforcement boundary (see Security Model); pass `--allow-write` to opt out.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `../_shared/references/runner-common.md`.

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure) live in `../_shared/references/runner-common.md`.

## Examples

```bash
python3 .agents/skills/cline-runner/scripts/run_cline.py "Summarize the core module architecture"
python3 .agents/skills/cline-runner/scripts/run_cline.py "Explain this module" --model anthropic/claude-sonnet-4-5
python3 .agents/skills/cline-runner/scripts/run_cline.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/cline-runner/scripts/run_cline.py "Implement the accepted fix" --role implementer --model openai/gpt-5.1
python3 .agents/skills/cline-runner/scripts/run_cline.py "Resume and continue" --session 1782865158637_s2n62
python3 .agents/skills/cline-runner/scripts/run_cline.py "Run this in CI" --model zai/glm-5.2 --data-dir /tmp/cline-ci-state
```

## Behavior

1. Runs `cline <prompt> --cwd <dir> --auto-approve <bool>` directly for non-interactive execution.
2. Defaults to native `--json` (NDJSON event stream) so callers can consume streaming output; the wrapper parses the terminal `run_result` line for the final text, `finishReason`, and resolved model.
3. Returns a wrapper envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, `effective_runner`.
4. Keeps native Cline output in `stdout`; the wrapper `--json` flag only controls the outer envelope.
5. Never falls back to another provider. Missing CLI or auth failures block the seat explicitly.
6. Trusts the process exit code for `success`, but overrides to failure if the stream's `finishReason` disagrees (e.g. a native agent error reported with an unexpectedly clean exit), so `success` is never self-contradictory with `finish_reason`.
7. `session_id` is recovered with a best-effort `cline history --json` lookup by working directory and start time immediately after the run, since Cline's own stream never reports one.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Cline CLI not found |
| -3 | Invalid input, native agent error (non-`completed` `finishReason`), or unexpected error |

## Gotchas

- **`--model` persists globally.** See Security Model — every `--model` invocation rewrites `~/.cline/data/settings/providers.json` for the requested provider, including on a failed run with an invalid model string. Use `--data-dir` for automated runs to avoid surprising the user's next interactive `cline` session.
- **No session id in the stream.** Cline's `--json` output never includes a `sessionId`/`session_id` field (the `agentId`/`taskId` in `hook_event` lines are different, per-run identifiers, not the resumable session id). The wrapper cross-references `cline history --json` by cwd + start time; this is best-effort and can miss under heavy concurrent use of the same working directory.
- **`--auto-approve false` fails tool calls, it doesn't skip them.** The model sees an explicit approval error and keeps reasoning — expect it to explain what it couldn't do rather than silently omitting the attempt. This is a real boundary (verified: no hang, no silent bypass), stronger than the prompt-only overlays other runners rely on.
- **`--output-schema` is prompt-enforced**, not validated by a native Cline schema flag.
- Cline's non-JSON native error lines (e.g. `hook dispatch failed: ...`) can appear on stderr even for a run whose `agent_message` and `finishReason` are otherwise fine — treat `success`/`finish_reason` as authoritative over stray stderr noise.

## Prerequisites

- `cline` CLI installed and in `PATH` (`npm install -g cline`)
- At least one provider authenticated via `cline auth`

This is **seat fidelity** for a no-fallback runner: if `cline` is missing or auth fails, the seat is blocked and reported absent, never substituted by another model. The envelope returns `success=false` with remediation guidance in `stderr`. A missing CLI maps to `return_code=-2` and `status=seat_unavailable`; auth or model failures surface as Cline's own nonzero exit with `finish_reason` set to the native reason — treat any `success=false` as a blocked seat.
