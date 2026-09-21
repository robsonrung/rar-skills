---
name: shared
description: Shared references, schemas, and scripts used by the other skills. This directory is a library dependency, not an executable workflow.
disable-model-invocation: true
---

# Shared library

Load only the reference or script needed by the current skill. This marker keeps the library discoverable as one installation unit; it does not guarantee identical loading behavior across hosts.

## Resolve shared resources

A path such as `shared/references/model-roster.md` is relative to the skill collection, not the user's project directory.

1. Use the loaded `shared` skill's directory when available.
2. For a source checkout, use `skills/shared/` under this repository.
3. For a flat installation, find `shared/` beside the installed skills. If it is missing, report the missing library dependency instead of guessing a path or silently skipping a contract.

Before a shell command, set `SHARED_DIR` to that resolved absolute directory in the same command. Other skills resolve their own scripts from their loaded skill directory. The `scripts/skill_paths.py` helper supports repository scripts that must find skills in both nested and flat layouts.

## Contents

1. `model-routing.json`: the single source for model identities, reasoning settings, and role routes. Use `scripts/model_routing.py` to inspect, resolve, or validate it.
2. `references/`: workflow stages, model routing, runner behavior, evidence, handoffs, and run state. Every executable skill starts with `references/model-preview.md` on direct invocation; nested calls reuse the parent selection.
3. `scripts/`: runner discovery, jobs, output handling, and validation.
4. `tests/`, schemas, and hooks: executable checks and shared formats.
