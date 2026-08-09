---
name: qwen-runner
description: Execute prompts as the Qwen seat through Cline CLI headless mode, with Qwen3.8 Max forwarded as qwen/qwen3.8-max. Use when users explicitly request Qwen execution, when a workflow needs an independent Qwen seat, or when a cross-runner workflow selects Qwen.
---

# Qwen Runner

Execute prompts as the Qwen seat through the shared `cline-runner` implementation. The wrapper forwards `qwen/qwen3.8-max` to `cline`, which resolves it through the selected authenticated provider. The Qwen seat gets the requested Qwen model instead of a generic provider default.

## Default Model

`qwen/qwen3.8-max` is the default Qwen seat. The OpenRouter catalog exposes it as Qwen3.8 Max with a 1M token context window. Override it with `--model` only when the selected Cline provider recognizes another Qwen model ID.

## Prerequisites

1. `cline` CLI installed and in `PATH` (`npm install -g cline`).
2. A Cline provider authenticated through `cline auth` that can resolve `qwen/qwen3.8-max`. OpenRouter lists this model ID.

## Security Model

This skill delegates to `cline-runner`, so it has the same execution and data sharing model as the Cline wrapper. See `../cline-runner/SKILL.md`.

Passing `--model` changes the selected provider's persisted default model in `~/.cline/data/settings/providers.json`. Pass `--data-dir` for automated runs when that side effect is not wanted. A new data directory must have its own authenticated provider.

Analysis roles, every role except `implementer`, use native `--auto-approve false` by default. Tool calls then fail cleanly instead of running. Pass `--allow-write` to opt out.

## Shared Wrapper Reference

Supported options, roles, the JSON envelope contract, return codes, background jobs, and gotchas are defined by `cline-runner` and `_shared/references/runner-common.md`.

The envelope reports:

1. `runner=qwen`
2. `effective_runner=cline`
3. `effective_model=qwen/qwen3.8-max`, when the native receipt confirms it
4. `effective_provider=qwen`, inferred from the model ID

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
python3 .agents/skills/qwen-runner/scripts/run_qwen.py "Resume and continue" --session 1782865158637_s2n62
```

## Behavior

1. Delegates to `cline-runner` with the runner identity set to `qwen`.
2. Forwards `qwen/qwen3.8-max` through native `--model` on every default run.
3. Uses the Cline NDJSON stream and shared result envelope.
4. Never falls back to another provider. A missing CLI or failed model call blocks the Qwen seat and reports it unavailable.
5. Keeps Gemma and Minimax as separate model identities when their shims import this wrapper with their own default models.

## Seat Fidelity

The Qwen seat returns a Qwen response or reports the seat unavailable. It never substitutes another model. A missing Cline CLI maps to `return_code=-2`, `status=seat_unavailable`, and `auth_ok=null`.
