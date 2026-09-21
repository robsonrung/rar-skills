---
name: agents-md-craft
description: Create, audit, or simplify project instruction files such as AGENTS.md and CLAUDE.md. Use to fix instruction drift or separate conditional guidance; use skill-expert for SKILL.md files.
disable-model-invocation: true
---

# Agent Instruction Files

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Treat the root instruction file as cached context. Keep only rules that apply to most work. Move conditional detail to focused files and point to them from the root.

## Outcome

Produce one authoritative instruction set grounded in verified project facts. An audit reports a proposed diff. A create or update request writes the agreed scope and verifies its pointers.

## Workflow

1. Classify the request as `audit`, `create`, `update`, or `staleness check`. Inspect the target files and the project facts that support their instructions: purpose, layout, commands, and durable constraints.
2. If both `AGENTS.md` and `CLAUDE.md` exist, choose the maintained file as canonical unless the project requires separate content. Keep the other as a short text pointer when the active tools can follow it. Do not create two copies that will drift.
3. Keep the root file to its smallest coherent shape:
   1. project purpose and major areas;
   2. commands and constraints that apply to normal work;
   3. short links to conditional guidance.
4. Move runbooks, long command recipes, subsystem rules, and ADRs into `agent_docs/` or the project's existing documentation. Point to existing formatters, linters, and hooks for rules they enforce. Preserve team standards and security boundaries that need prose. Use stable file or symbol pointers instead of copied code; verify line numbers when including them.
5. For `audit`, return findings, a budget view, and a concrete draft without writing files. For `create` or `update`, write only the requested files and their necessary `agent_docs/` references. Do not invent project facts.
6. Check changed commands against their actual definitions and resolve changed links or line pointers. Run commands only when needed to resolve a material uncertainty or satisfy a repository gate; documenting a deployment command does not authorize deployment. Reuse valid evidence for unchanged content. Report the canonical file, changes, unresolved facts, and validation evidence.

Read [references/principles.md](references/principles.md) when deciding placement or scope. Use [references/checklist.md](references/checklist.md) for an audit or a substantial restructure; a small edit needs only the checks for its changed contract.
