---
name: glm-runner
description: Execute prompts as the GLM seat through Cline CLI headless mode, with the model actually forwarded (zai/glm-5.2). Use when users explicitly request GLM execution, when a workflow needs a GLM-labelled seat, or when a cross-runner workflow selects GLM as a complementary provider.
---

# GLM Runner

Execute prompts as the GLM seat through the shared `cline-runner` implementation. Unlike the previous dcode-backed version of this skill, the GLM identity is a **real forwarded model** — `--model zai/glm-5.2` is passed straight through to `cline`, not just a label on an unrelated seat.

## Default Model

- `zai/glm-5.2` — forwarded to `cline` as `--model zai/glm-5.2` on every run. Override with `--model` to point the GLM seat at a different Z.AI model id `cline` recognizes.

## Prerequisites

- `cline` CLI installed and in `PATH` (`npm install -g cline`)
- A Cline provider authenticated via `cline auth` that can resolve `zai/glm-5.2` (verified against the `cline-pass` gateway; other providers may need their own GLM entitlement)

## Security Model

This skill delegates to `cline-runner`, so it has the same execution and data sharing model as the Cline wrapper — see `../cline-runner/SKILL.md`. Notably: `--model` mutates the authenticated provider's persisted default model in `~/.cline/data/settings/providers.json`; pass `--data-dir` for automated runs where that side effect is unwanted. Analysis roles (every role except `implementer`) default to native `--auto-approve false`, a real enforcement boundary — tool calls fail cleanly instead of running. Pass `--allow-write` to opt out.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read the cline-runner skill's SKILL.md (`../cline-runner/SKILL.md`) when you need flag or envelope details. The envelope is produced by `cline-runner/scripts/run_cline.py` with `runner=glm`, `effective_runner=cline`, `effective_provider=z-ai` (inferred from the `zai/...` model id).

## Usage

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "Summarize the core module architecture"
python3 .agents/skills/glm-runner/scripts/run_glm.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/glm-runner/scripts/run_glm.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/glm-runner/scripts/run_glm.py "Apply the accepted fix" --role implementer
python3 .agents/skills/glm-runner/scripts/run_glm.py "Run this in CI" --data-dir /tmp/glm-ci-state
```

## Behavior

1. Delegates to the shared `cline-runner` implementation with runner identity set to `glm` (the envelope reports `runner=glm`, `effective_runner=cline`).
2. Forwards `zai/glm-5.2` as the native `--model` on every call, so the GLM seat is the model that actually answers, not just a label.
3. Never falls back to another provider. Missing CLI or auth failures block the GLM seat explicitly (`status: seat_unavailable`, `return_code -2`) — this is **seat fidelity**, the same invariant every runner upholds: never substitute another model's answer for the GLM seat.
4. Preserves the shared wrapper envelope so councils can compare GLM output with other runners consistently.
