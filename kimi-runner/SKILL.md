---
name: kimi-runner
description: Execute prompts as the Kimi seat through the Pi CLI on OpenRouter, with Moonshot's flagship Kimi K3 model pinned per invocation (moonshotai/kimi-k3) — strong long-horizon coding, large-codebase understanding, 1M-token context, always-on thinking. Use when users explicitly request Kimi execution, when a workflow needs a Kimi-backed seat, or when a cross-runner workflow wants a Moonshot Kimi perspective without leaving the current workspace.
---

# Kimi Runner

Execute prompts as the Kimi seat through the shared `pi-runner` implementation. This replaces the previous Cline-backed shim — `--provider openrouter --model moonshotai/kimi-k3` is pinned on every invocation, so the seat no longer depends on whichever provider Cline's mutable state happens to point at; the model that answers is always the forwarded Moonshot model, served via OpenRouter.

## Default Model

- `moonshotai/kimi-k3` — Moonshot's flagship **Kimi K3** seat (long-horizon coding, large-codebase understanding, 1M-token context, always-on thinking), pinned as `--provider openrouter --model moonshotai/kimi-k3` on every run. There is a single K3 id — no `-code`/`-thinking` variants. Override with `--model` to point the Kimi seat at a different OpenRouter model id.

## Prerequisites

- `pi` CLI installed and in `PATH` (`npm install -g @mariozechner/pi-coding-agent`)
- `OPENROUTER_API_KEY` in the environment (or an OpenRouter credential in Pi's auth store)

## Security Model

This skill delegates to `pi-runner`, so it has the same execution and data sharing model as the Pi wrapper — see `../pi-runner/SKILL.md`. Runs are hermetic (no extensions, skills, or AGENTS.md/CLAUDE.md discovery). Analysis roles (every role except `implementer`) default to read-only mode (only Pi's file-reading tool enabled). Pass `--allow-write` to opt out, or `--no-tools` to block tools entirely.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read [`shared/references/runner-common.md`](../shared/references/runner-common.md) for the shared flags, envelope keys, return codes, and the seat-fidelity rule. The envelope is produced by `pi-runner/scripts/run_pi.py` with `runner=kimi`, `effective_runner=pi`, `effective_provider=moonshotai` (inferred from the `moonshotai/...` model id); `native_provider=openrouter` is the serving gateway.

## Usage

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Summarize the core module architecture"
python3 .agents/skills/kimi-runner/scripts/run_kimi.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Answer from the brief only" --no-tools --json
```

## Behavior

1. Delegates to the shared `pi-runner` implementation with runner identity set to `kimi` (the envelope reports `runner=kimi`, `effective_runner=pi`).
2. Pins `--provider openrouter --model moonshotai/kimi-k3` on every call, so the Kimi seat is the model that actually answers — there is no mutable provider state that can silently reroute it.
3. Never falls back to another provider. A missing CLI blocks the seat explicitly (`status: seat_unavailable`, `return_code -2`); missing credentials report `status: auth_missing` with `auth_ok: false` — this is **seat fidelity**, the same invariant every runner upholds: never substitute another model's answer for the Kimi seat.
4. Preserves the shared wrapper envelope so councils can compare Kimi output with other runners consistently.

## Migration Note

The Cline-backed shim (and its `--lane kimi` isolated-auth workflow) is no longer used by this skill — it now depends solely on `pi` and `OPENROUTER_API_KEY`. The earlier dedicated `kimi-cli` binary is likewise not invoked. If other tooling still shells out to `cline` or `kimi-cli` directly, that is unaffected by this change.
