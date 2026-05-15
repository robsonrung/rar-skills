# Repository Configuration

This reference documents the default seat-to-runner mapping for a repository. Adapt paths and model defaults if using this skill in another project.

## Runner Base Path

In this repo, all runner scripts live under:

```
.agents/skills/{runner-name}/scripts/run_{runner-name}.py
```

When adapting this skill to another project, update the base path or set a `RUNNER_BASE_PATH` variable.

## Available Seats

| Seat | Native Tool | Runner Fallback | Default Model |
|------|-------------|-----------------|---------------|
| Claude Opus 4.7 | `Agent` (Claude Code) | `claude-runner --model claude-opus-4-7` | `claude-opus-4-7` |
| Claude Sonnet 4.6 | `Agent` (Claude Code) | `claude-runner --model claude-sonnet-4-6` | `claude-sonnet-4-6` |
| Codex | `spawn_agent` + `wait_agent` (Codex host) | `codex-runner --model gpt-5.5` | `gpt-5.5` |
| Gemini | — | `gemini-runner` | runner default or verified local CLI model |
| Kimi | — | `kimi-runner --model kimi-code/kimi-for-coding` | `kimi-code/kimi-for-coding` |
| Gemma | — | `gemma-runner --model google/gemma-4-31b-it` | `google/gemma-4-31b-it` |
| GLM Pragmatic | — | `glm-runner --model glm-5.1` | `glm-5.1` |
| GLM Critic | — | `glm-runner --model glm-5.1` | `glm-5.1` |
| Minimax | — | `minimax-runner --model minimax/minimax-m2.7` | `minimax/minimax-m2.7` |

## CLI Prerequisites

| Seat(s) | Required Binary | Notes |
|---------|-----------------|-------|
| Claude (runner fallback) | `claude` | Must pass auth smoke test |
| Gemini | `gemini` | Must pass auth smoke test |
| Kimi | `kimi-cli` | Must pass auth smoke test |
| Gemma, GLM, Minimax | `qwen` | Shared transport; must pass per-model smoke test |

## Core Seats Definition

"Core seats" refers to the highest-diversity non-duplicate set available:
1. Native Codex (when on Codex host)
2. Native Claude seats (when on Claude Code host)
3. Gemini
4. Kimi
5. One of Gemma or GLM

Duplicate-coverage seats (e.g., GLM Critic) are only considered after core seats are exhausted.

## Artifact Directory

Persisted council artifacts write to:

```
.ai-workflow/consensus/
```

In this repo, the `.ai-workflow/` directory is guaranteed writable.
