---
name: _shared
description: Marker file. Shared contracts, references, and runner scripts that other skills load by file path — not a skill to invoke.
---

# _shared

Not an invocable skill. This directory holds the assets other skills reference by
path (`_shared/references/...`, `_shared/scripts/...`) once installed at
`.agents/skills/_shared/`.

## Why this file exists

AgentSkills hosts scan a skills directory two ways: directories containing a
`SKILL.md` load as one skill, and **every other loose `.md` file below the root
loads as a legacy always-on skill whose full body is pinned into the system
prompt**. Without this marker, each file under `references/` would be pinned that
way — roughly 32 KB of contracts in every request, on every run.

This file makes the host treat `_shared/` as a single unit and skip the tree.
The name `_shared` is deliberately not AgentSkills-valid, so the host skips
loading it as a skill too (one benign warning at startup). Net effect: the
references stay readable on disk, and none of them are pinned into context.

Contents: `references/` (run-state contract, runner-common, model roster,
task-shaped routing, engineering rules, local config, PR-watch contracts),
`scripts/` (runner discovery, job management, validators), `tests/`.
