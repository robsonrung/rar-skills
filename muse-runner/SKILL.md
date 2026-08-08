---
name: muse-runner
description: Execute prompts as the Meta Muse Spark seat through Cline CLI headless mode. Use when users request Muse Spark, when a workflow needs the Muse model, or when a multi-model workflow selects the Muse seat.
---

# Muse Runner

Execute prompts as the Muse seat through the shared `cline-runner` implementation. The next consumer receives the shared runner envelope. The run is done when the envelope confirms the Muse model or reports the seat unavailable.

## Default Model

`meta/muse-spark-1.1` is the single default model declaration for this skill. OpenRouter lists Muse Spark 1.1 with a 1M token context window and United States only availability.

## Prerequisites

1. Install `cline` in `PATH` (`npm install -g cline`).
2. Authenticate a Cline provider through `cline auth` that can resolve the default model.
3. Use an OpenRouter account and request location that meet the model's United States availability rule.

## Security Model

This skill uses the Cline execution and data sharing contract. Prompt text, prompt files, metadata, and files read during the run may be sent to the selected provider.

Passing `--model` changes the selected provider's persisted default in `~/.cline/data/settings/providers.json`. Use `--data-dir` when the run must not change that default. A new data directory needs its own authenticated provider.

Analysis roles use native `--auto-approve false` by default. Pass `--allow-write` only when the role must change files.

## Usage

```bash
SKILL_DIR="<absolute path of the directory containing this SKILL.md>";
python3 "$SKILL_DIR/scripts/run_muse.py" "your prompt here"
```

## Examples

```bash
SKILL_DIR="<absolute path of the directory containing this SKILL.md>";
python3 "$SKILL_DIR/scripts/run_muse.py" "Explain this module" --role researcher
```

```bash
SKILL_DIR="<absolute path of the directory containing this SKILL.md>";
python3 "$SKILL_DIR/scripts/run_muse.py" --prompt-file /tmp/review.md --role codereviewer --json
```

## Behavior

1. Delegate to `cline-runner` with `runner=muse` and `effective_runner=cline`.
2. Forward the default model through native `--model` on every run unless the caller overrides it.
3. Use Cline NDJSON output and the shared result envelope.
4. Preserve **seat fidelity**. The Muse seat returns a Muse receipt or reports an observable failure. It never substitutes another model.

State the result as: "The Muse seat preserved seat fidelity and returned `<effective_model>`," or name the blocking error.

## Acceptance Contract

The runner is ready when:

1. `--help` exits with code 0.
2. A missing Cline binary returns `runner=muse`, `effective_runner=cline`, `return_code=-2`, and `status=seat_unavailable`.
3. A successful live run returns `native_model_id=meta/muse-spark-1.1`.
