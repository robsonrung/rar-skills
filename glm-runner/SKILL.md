---
name: glm-runner
description: Execute prompts as the GLM seat through DeepAgents CLI (`dcode`) in non-interactive mode. Use when users explicitly request GLM execution, when a workflow needs a GLM-labelled seat, or when a cross-runner workflow selects GLM as a complementary provider.
---

# GLM Runner

Execute prompts as the GLM seat through the shared DeepAgents CLI (`dcode`) wrapper. This keeps GLM seats headless without depending on the Qwen CLI's GLM provider plumbing.

## Default Model

- `z-ai/glm-5.2` (metadata label only — NOT forwarded to dcode)

The GLM identity is a **seat label** in the output envelope; the model dcode actually calls is whichever one the user has configured in dcode itself (`/model`, `/auth`, `~/.deepagents/config.toml`, or a project `.env`). To make the GLM seat truly GLM, configure dcode to use a GLM provider — this wrapper deliberately never forwards `--model` to dcode, matching `dcode-runner`'s "no configuration on the runner" design.

## Prerequisites

- `dcode` installed and in `PATH` (`curl -LsSf https://langch.in/dcode | bash`)
- A model and credentials configured in dcode. To preserve true GLM semantics, point dcode at a GLM provider (e.g., `dcode --default-model openrouter:z-ai/glm-5.2` or equivalent in `~/.deepagents/config.toml`).

## Security Model

This skill delegates to `dcode-runner`, so it has the same execution and data sharing model as the dcode wrapper. Prompt text, prompt files, session files, metadata, and any files dcode reads during the run may be sent to whichever provider dcode is configured to use. Analysis roles (every role except `implementer`) default to a read-only prompt overlay; pass `--allow-write` to opt out, or `--auto-approve` to forward `dcode -y` and skip human-in-the-loop prompts. The overlay is a prompt-level soft constraint, not a hard sandbox.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas are identical to the shared wrapper — read the dcode-runner skill's SKILL.md (`../dcode-runner/SKILL.md`) when you need flag or envelope details. The envelope is produced by `dcode-runner/scripts/run_dcode.py` with `runner=glm`.

## Usage

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "your prompt here"
```

## Examples

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py "Summarize the core module architecture"
python3 .agents/skills/glm-runner/scripts/run_glm.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/glm-runner/scripts/run_glm.py "Read-only analysis" --restrict-tools --json
python3 .agents/skills/glm-runner/scripts/run_glm.py "Apply the accepted fix" --role implementer --auto-approve
```

## Behavior

1. Delegates to the shared `dcode-runner` implementation with runner identity set to `glm` (the envelope reports `runner=glm`, `effective_runner=dcode`).
2. Does not forward `--model` to dcode — the actual model is whichever one dcode is configured with. To run GLM specifically, configure dcode itself.
3. Falls back through dcode-runner's chain (claude → codex → qwen → kimi) when `dcode` is unavailable, unless `--disable-fallback` is passed. Fallback runs are labelled `fallback_from: glm` so council orchestrators can account for the missing GLM seat — never substitute another provider as GLM.
4. Preserves the shared wrapper envelope so councils can compare GLM output with other runners consistently.
