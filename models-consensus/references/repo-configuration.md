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
| Claude Opus 4.8 | `Agent` (Claude Code) | `claude-runner --model claude-opus-4-8` | `claude-opus-4-8` |
| Claude Sonnet 5.0 | `Agent` (Claude Code) | `claude-runner --model claude-sonnet-5-0` | `claude-sonnet-5-0` |
| Codex | `spawn_agent` + `wait_agent` (Codex host) | `codex-runner --model gpt-5.5` | `gpt-5.5` |
| Gemini | — | `gemini-runner` | runner default or verified local CLI model |
| Kimi | — | `kimi-runner --model kimi-code/kimi-for-coding` | `kimi-code/kimi-for-coding` |
| GLM | — | `glm-runner` (delegates to `dcode-runner`) | whichever model `dcode` is configured with |

## CLI Prerequisites

| Seat(s) | Required Binary | Notes |
|---------|-----------------|-------|
| Claude (runner fallback) | `claude` | Must pass auth smoke test |
| Gemini | `gemini` | Must pass auth smoke test |
| Kimi | `kimi-cli` | Must pass auth smoke test |
| GLM | `dcode` | DeepAgents CLI; must be configured with a GLM provider in `~/.deepagents/` |

## Core Seats Definition

"Core seats" refers to the highest-diversity non-duplicate set available:
1. Native Codex (when on Codex host)
2. Native Claude seats (when on Claude Code host)
3. Gemini
4. Kimi
5. GLM

## Artifact Directory

Persisted council artifacts write to:

```
.ai-workflow/consensus/
```

In this repo, the `.ai-workflow/` directory is guaranteed writable.
