---
name: glm-runner
description: Execute prompts as the GLM seat through the Pi CLI on OpenRouter, with Z.AI's GLM 5.2 pinned per invocation (z-ai/glm-5.2). Use when users explicitly request GLM execution, when a workflow needs a GLM-labelled seat, or when a cross-runner workflow selects GLM as a complementary provider.
---

# GLM Runner

Execute prompts as the GLM seat through the shared `pi-runner` implementation. This replaces the previous Cline-backed shim — `--provider openrouter --model z-ai/glm-5.2` is pinned on every invocation, so the per-provider model-id map (`z-ai/glm-5.2` on OpenRouter vs `zai/glm-5.2` on the cline gateway) is gone along with the mutable provider state that made it necessary.

## Default Model

- `z-ai/glm-5.2` — Z.AI's **GLM 5.2**, pinned as `--provider openrouter --model z-ai/glm-5.2` on every run. This is the single remaining id for the seat; override with `--model` to point the GLM seat at a different OpenRouter model id.

## Prerequisites

- `pi` CLI installed and in `PATH` (`npm install -g @mariozechner/pi-coding-agent`)
- `OPENROUTER_API_KEY` in the environment (or an OpenRouter credential in Pi's auth store)

## Security Model

This skill delegates to `pi-runner`, so it has the same execution and data sharing model as the Pi wrapper — see `../pi-runner/SKILL.md`. Runs are hermetic (no extensions, skills, or AGENTS.md/CLAUDE.md discovery). Analysis roles (every role except `implementer`) default to read-only mode (only Pi's file-reading tool enabled). Pass `--allow-write` to opt out, or `--no-tools` to block tools entirely.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read [`_shared/references/runner-common.md`](../_shared/references/runner-common.md) for the shared flags, envelope keys, return codes, and the seat-fidelity rule. The envelope is produced by `pi-runner/scripts/run_pi.py` with `runner=glm`, `effective_runner=pi`, `effective_provider=z-ai` (inferred from the `z-ai/...` model id); `native_provider=openrouter` is the serving gateway.

## Usage

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "Summarize the core module architecture"
python3 .agents/skills/glm-runner/scripts/run_glm.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/glm-runner/scripts/run_glm.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/glm-runner/scripts/run_glm.py "Answer from the brief only" --no-tools --json
```

## Behavior

1. Delegates to the shared `pi-runner` implementation with runner identity set to `glm` (the envelope reports `runner=glm`, `effective_runner=pi`).
2. Pins `--provider openrouter --model z-ai/glm-5.2` on every call, so the GLM seat is the model that actually answers — there is no mutable provider state that can silently reroute it.
3. Never falls back to another provider. A missing CLI blocks the seat explicitly (`status: seat_unavailable`, `return_code -2`); missing credentials report `status: auth_missing` with `auth_ok: false` — this is **seat fidelity**, the same invariant every runner upholds: never substitute another model's answer for the GLM seat.
4. Preserves the shared wrapper envelope so councils can compare GLM output with other runners consistently.

## Migration Note

The Cline-backed shim (and its `--lane glm` isolated-auth workflow) is no longer used by this skill — it now depends solely on `pi` and `OPENROUTER_API_KEY`. If other tooling still shells out to `cline` directly, that is unaffected by this change.
