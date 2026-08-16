---
name: qwen-runner
description: Execute prompts as the Qwen seat through the Pi CLI on OpenRouter, with Qwen3.8 Max pinned per invocation (qwen/qwen3.8-27b, 1M-token context). Use when users explicitly request Qwen execution, when a workflow needs an independent Qwen seat, or when a cross-runner workflow wants a Qwen-backed perspective without leaving the current workspace.
---

# Qwen Runner

Execute prompts as the Qwen seat through the shared `pi-runner` implementation. This replaces the previous Cline-backed shim — `--provider openrouter --model qwen/qwen3.8-27b` is pinned on every invocation, so the seat no longer depends on whichever provider Cline's mutable state happens to point at; the model that answers is always the forwarded Qwen model, served via OpenRouter.

## Default Model

- `qwen/qwen3.8-27b` — **Qwen3.8 Max** (1M-token context in the OpenRouter catalog), pinned as `--provider openrouter --model qwen/qwen3.8-27b` on every run. Override with `--model` to point the Qwen seat at a different OpenRouter model id.

## Prerequisites

- `pi` CLI installed and in `PATH` (`npm install -g @mariozechner/pi-coding-agent`)
- `OPENROUTER_API_KEY` in the environment (or an OpenRouter credential in Pi's auth store)

## Security Model

This skill delegates to `pi-runner`, so it has the same execution and data sharing model as the Pi wrapper — see `../pi-runner/SKILL.md`. Runs are hermetic (no extensions, skills, or AGENTS.md/CLAUDE.md discovery). Analysis roles (every role except `implementer`) default to read-only mode (only Pi's file-reading tool enabled). Pass `--allow-write` to opt out, or `--no-tools` to block tools entirely.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read [`_shared/references/runner-common.md`](../_shared/references/runner-common.md) for the shared flags, envelope keys, return codes, and the seat-fidelity rule. The envelope is produced by `pi-runner/scripts/run_pi.py` with `runner=qwen`, `effective_runner=pi`, `effective_provider=qwen` (inferred from the `qwen/...` model id); `native_provider=openrouter` is the serving gateway.

## Usage

```bash
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "your prompt here"
```

Paths use the installed `.agents/skills/` layout. From this source repository, invoke `qwen-runner/scripts/run_qwen.py`.

## Examples

```bash
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Explain the core module architecture"
python3 .agents/skills/qwen-runner/scripts/run_qwen.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Apply the accepted fix" --role implementer
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Answer from the brief only" --no-tools --json
```

## Behavior

1. Delegates to the shared `pi-runner` implementation with runner identity set to `qwen` (the envelope reports `runner=qwen`, `effective_runner=pi`).
2. Pins `--provider openrouter --model qwen/qwen3.8-27b` on every call, so the Qwen seat is the model that actually answers — there is no mutable provider state that can silently reroute it.
3. Never falls back to another provider. A missing CLI blocks the seat explicitly (`status: seat_unavailable`, `return_code -2`); missing credentials report `status: auth_missing` with `auth_ok: false` — this is **seat fidelity**, the same invariant every runner upholds: never substitute another model's answer for the Qwen seat.
4. Preserves the shared wrapper envelope so councils can compare Qwen output with other runners consistently.

## Migration Note

The Cline-backed shim is no longer used by this skill — it now depends solely on `pi` and `OPENROUTER_API_KEY`. Gemma and Minimax, which previously reused this wrapper's Cline-backed `main()`, now delegate to `cline-runner` directly and are unaffected. If other tooling still shells out to `cline` directly, that is also unaffected by this change.
