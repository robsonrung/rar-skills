---
name: shared
description: Marker file. Shared contracts, references, and runner scripts that other skills load by file path — not a skill to invoke.
disable-model-invocation: true
---

# shared

Not an invocable skill. This directory holds the assets other skills reference by
path (`shared/references/...`, `shared/scripts/...`) once installed at
`.agents/skills/shared/`.

## Why this file exists

AgentSkills hosts scan a skills directory two ways: directories containing a
`SKILL.md` load as one skill, and **every other loose `.md` file below the root
loads as a legacy always-on skill whose full body is pinned into the system
prompt**. Without this marker, each file under `references/` would be pinned that
way — roughly 32 KB of contracts in every request, on every run.

This file makes the host treat `shared/` as a single unit and skip the tree.
The name is `shared`, not `shared`: hosts validate the frontmatter name against
the AgentSkills rule (lowercase a-z, 0-9, hyphens), and an underscore only earns
a startup warning — it does not stop the load, so the skill was being listed
anyway. `disable-model-invocation: true` is what actually keeps it out of the
prompt, on Claude Code and on AgentSkills hosts alike (Codex reads the same
intent from `agents/openai.yaml`). Net effect: the references stay readable on
disk, none of them are pinned into context, and startup is quiet.

Contents: `references/` (run-state contract, runner-common, model roster,
task-shaped routing, engineering rules, local config, PR-watch contracts),
`scripts/` (runner discovery, job management, validators), `tests/`.
