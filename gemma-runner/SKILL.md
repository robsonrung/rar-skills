---
name: gemma-runner
description: Execute prompts as the Gemma seat through the Pi CLI on OpenRouter, with google/gemma-4-31b-it pinned per invocation. Use when users explicitly request Gemma execution, when a workflow needs a Gemma seat, or when a cross-runner workflow wants a Gemma-backed perspective without leaving the current workspace.
---

# Gemma Runner

Execute prompts as the Gemma seat through the shared `pi-runner` implementation. This replaces the previous Cline-backed shim — `--provider openrouter --model google/gemma-4-31b-it` is pinned on every invocation, so the seat no longer depends on whichever provider Cline's mutable state happens to point at; the model that answers is always the forwarded Gemma model, served via OpenRouter.

## Default Model

- `google/gemma-4-31b-it`, pinned as `--provider openrouter --model google/gemma-4-31b-it` on every run. Override with `--model` to point the Gemma seat at a different OpenRouter model id.

## Prerequisites

- `pi` CLI installed and in `PATH` (`npm install -g @mariozechner/pi-coding-agent`)
- `OPENROUTER_API_KEY` in the environment (or an OpenRouter credential in Pi's auth store)

## Security Model

This skill delegates to `pi-runner`, so it has the same execution and data sharing model as the Pi wrapper — see `../pi-runner/SKILL.md`. Runs are hermetic (no extensions, skills, or AGENTS.md/CLAUDE.md discovery). Analysis roles (every role except `implementer`) default to read-only mode (only Pi's file-reading tool enabled). Pass `--allow-write` to opt out, or `--no-tools` to block tools entirely.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read [`shared/references/runner-common.md`](../shared/references/runner-common.md) for the shared flags, envelope keys, return codes, and the seat-fidelity rule. The envelope is produced by `pi-runner/scripts/run_pi.py` with `runner=gemma`, `effective_runner=pi`, `effective_provider=google` (inferred from the `google/...` model id); `native_provider=openrouter` is the serving gateway.

## Usage

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Summarize the core module architecture"
python3 .agents/skills/gemma-runner/scripts/run_gemma.py --prompt-file /tmp/review.md --role synthesizer
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/gemma-runner/scripts/run_gemma.py "Answer from the brief only" --no-tools --json
```

## Behavior

1. Delegates to the shared `pi-runner` implementation with runner identity set to `gemma` (the envelope reports `runner=gemma`, `effective_runner=pi`).
2. Pins `--provider openrouter --model google/gemma-4-31b-it` on every call, so the Gemma seat is the model that actually answers — there is no mutable provider state that can silently reroute it.
3. Never falls back to another provider. A missing CLI blocks the seat explicitly (`status: seat_unavailable`, `return_code -2`); missing credentials report `status: auth_missing` with `auth_ok: false` — this is **seat fidelity**, the same invariant every runner upholds: never substitute another model's answer for the Gemma seat.
4. Preserves the shared wrapper envelope so councils can compare Gemma output with other runners consistently.

## Migration Note

The Cline-backed shim is no longer used by this skill — it now depends solely on `pi` and `OPENROUTER_API_KEY`. Minimax remains delegated to `cline-runner` and is unaffected. If other tooling still shells out to `cline` directly, that is also unaffected by this change.

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat (Codex UI display metadata and default prompt); do not remove it.
