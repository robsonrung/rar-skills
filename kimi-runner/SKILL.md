---
name: kimi-runner
description: Execute prompts as the Kimi seat through Cline CLI headless mode, with Moonshot's flagship Kimi K3 model actually forwarded (moonshotai/kimi-k3) — strong long-horizon coding, large-codebase understanding, 1M-token context, always-on thinking. Use when users explicitly request Kimi execution, when a workflow needs a Kimi-backed seat, or when a cross-runner workflow wants a Moonshot Kimi perspective without leaving the current workspace.
---

# Kimi Runner

Execute prompts as the Kimi seat through the shared `cline-runner` implementation. This replaces the previous dedicated `kimi-cli` integration — `--model moonshotai/kimi-k3` is now passed straight through to `cline`, which resolves it via whichever Cline provider the user has authenticated, so the Kimi seat still gets a real, forwarded Moonshot model rather than a generic default.

## Default Model

- `moonshotai/kimi-k3` — Moonshot's flagship **Kimi K3** seat (long-horizon coding, large-codebase understanding, 1M-token context, always-on thinking), forwarded to `cline` as `--model moonshotai/kimi-k3` on every run. There is a single K3 id — no `-code`/`-thinking` variants. Override with `--model` to point the Kimi seat at a different Moonshot model id `cline` recognizes.

## Prerequisites

- `cline` CLI installed and in `PATH` (`npm install -g cline`)
- A Cline provider authenticated via `cline auth` that can resolve `moonshotai/kimi-k3` (the `cline-pass` gateway carries Moonshot models; other providers may need their own Moonshot entitlement)

## Security Model

This skill delegates to `cline-runner`, so it has the same execution and data sharing model as the Cline wrapper — see `../cline-runner/SKILL.md`. Notably: `--model` mutates the authenticated provider's persisted default model in `~/.cline/data/settings/providers.json`; pass `--data-dir` for automated runs where that side effect is unwanted. Analysis roles (every role except `implementer`) default to native `--auto-approve false`, a real enforcement boundary — tool calls fail cleanly instead of running. Pass `--allow-write` to opt out.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read the cline-runner skill's SKILL.md (`../cline-runner/SKILL.md`) when you need flag or envelope details. The envelope is produced by `cline-runner/scripts/run_cline.py` with `runner=kimi`, `effective_runner=cline`, `effective_provider=moonshot` (inferred from the `moonshotai/...` model id).

## Usage

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Summarize the core module architecture"
python3 .agents/skills/kimi-runner/scripts/run_kimi.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Apply the accepted fix" --role implementer
python3 .agents/skills/kimi-runner/scripts/run_kimi.py "Resume and continue" --session 1782865158637_s2n62
```

## Behavior

1. Delegates to the shared `cline-runner` implementation with runner identity set to `kimi` (the envelope reports `runner=kimi`, `effective_runner=cline`).
2. Forwards `moonshotai/kimi-k3` as the native `--model` on every call, so the Kimi seat is the model that actually answers.
3. Never falls back to another provider. Missing CLI or auth failures block the Kimi seat explicitly (`status: seat_unavailable`, `return_code -2`) — this is **seat fidelity**, the same invariant every runner upholds: never substitute another model's answer for the Kimi seat.
4. Preserves the shared wrapper envelope so councils can compare Kimi output with other runners consistently.

## Migration Note

The dedicated `kimi-cli` binary is no longer required or invoked by this skill — it now depends solely on `cline`. If other tooling still shells out to `kimi-cli` directly, that is unaffected by this change.
