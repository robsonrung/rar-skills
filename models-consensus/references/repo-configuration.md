# Repository Configuration

This reference documents the default seat-to-runner mapping for a repository. Adapt paths and model defaults if using this skill in another project.

## Runner Base Path

In an installed deployment, all runner scripts live under:

```
.agents/skills/{runner-name}/scripts/run_{runner-name}.py
```

When running from the skills source repo itself, skills live at the repo root — drop the `.agents/skills/` prefix (e.g. `codex-runner/scripts/run_codex.py`). When adapting this skill to another project, update the base path or set a `RUNNER_BASE_PATH` variable.

## Available Seats

| Seat | Native Tool | Runner Fallback | Default Model |
|------|-------------|-----------------|---------------|
| Claude Opus 4.8 | `Agent` (Claude Code) | `claude-runner --model claude-opus-4-8` | `claude-opus-4-8` |
| Claude Sonnet 5 | `Agent` (Claude Code) | `claude-runner --model claude-sonnet-5-0` | `claude-sonnet-5-0` |
| Codex (GPT 5.6 Sol) | `spawn_agent` + `wait_agent` (Codex host) | `codex-runner --model gpt-5.6-sol` | `gpt-5.6-sol` |
| Gemini (3.6 Flash) | — | `gemini-runner --model gemini-3.6-flash` | `gemini-3.6-flash` (premium; agy's own picker sets the real model) |
| Kimi (K3) | — | `kimi-runner --model moonshotai/kimi-k3` | `moonshotai/kimi-k3` |
| GLM (5.2) | — | `glm-runner` (via `cline`) | `zai/glm-5.2` |

## CLI Prerequisites

| Seat(s) | Required Binary | Notes |
|---------|-----------------|-------|
| Claude (runner fallback) | `claude` | Must pass auth smoke test |
| Codex (runner fallback, non-Codex hosts) | `codex` | Must pass auth smoke test |
| Gemini | `agy` | Antigravity CLI; must pass auth smoke test and have its `/model` picker configured (see gemini-runner SKILL.md) |
| Kimi | `cline` | Cline CLI (`npm install -g cline`); a provider authenticated via `cline auth` that resolves `moonshotai/kimi-k3` |
| GLM | `cline` | Cline CLI (`npm install -g cline`); a provider authenticated via `cline auth` that resolves `zai/glm-5.2` |

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
