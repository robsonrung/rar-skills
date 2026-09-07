---
name: agents-md-craft
description: Create, audit, or improve project agent instruction files such as AGENTS.md and CLAUDE.md. Use when the user asks to create, update, shrink, audit, or fix drift in project agent instructions. Keep the root file short and universal, move conditional detail into agent_docs, and use skill-expert for SKILL.md files.
disable-model-invocation: true
---

# Agent Instruction Files

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
4. Move runbooks, long command recipes, subsystem rules, ADRs, and style rules into `agent_docs/` or the project's existing documentation. Replace formatting prose with the formatter, linter, or hook that enforces it. Use verified `file:line` pointers instead of copied code.
5. For `audit`, return findings, a budget view, and a concrete draft without writing files. For `create` or `update`, write only the requested files and their necessary `agent_docs/` references. Do not invent project facts.
6. Verify every command, link, and `file:line` pointer that remains. Report the canonical file, any pointer stub, changes, unresolved facts, and validation evidence.

Read [references/principles.md](references/principles.md) for the placement and budget rules. Read [references/checklist.md](references/checklist.md) before reporting or writing.
