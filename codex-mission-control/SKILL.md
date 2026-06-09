---
name: codex-mission-control
description: Coordinate Codex app missions as a context light manager that creates a run scoped ledger, discovers native subagent tools, spawns bounded workers when authorized, and writes compact handoffs for separate threads. Use when the user asks to preserve context, avoid compaction, run subagents, create focused Codex threads, split workstreams, manage handoffs, or supervise parallel agent execution.
---

# Codex Mission Control

Act as a thin manager for a larger Codex mission. Keep this thread focused on decisions, routing, status, and final integration. Move deep exploration, long logs, and bounded implementation slices into focused subagents or separate Codex threads when the user has authorized that style of execution.

## Core Model

1. The manager owns the mission goal, constraints, workstream map, handoffs, thread registry, integration, and final answer.
2. Subagents are best for parallel, bounded work inside the current turn.
3. Separate Codex threads are best for context isolation, longer work, different branches, different worktrees, or multi turn follow up.
4. Every mission must use a run scoped ledger path. Never rely on one global shared filename across missions.
5. Every worker must return a compact report: result, files changed, tests run, risks, and next handoff.
6. This skill is an orchestration workflow. It must discover and use host tools for subagents; it cannot create workers merely by describing them.

## First Move

1. Create the mission ledger before delegating meaningful work. Use an OS temp root when the current workspace should not receive support files.
2. Run a native runtime preflight and record it in the ledger:
   1. Check whether Codex subagent tools are already visible.
   2. If they are not visible and `tool_search` exists, call it with a query like `multi agent spawn_agent wait_agent subagents`.
   3. If tools become available, use `multi_agent_v1.spawn_agent`, `wait_agent`, `send_input`, and `close_agent`.
   4. If no subagent tools are available, continue serially, say that no subagents were spawned, and do not imply parallel execution happened.
3. Identify the immediate critical path task for the manager to do locally.
4. Identify independent sidecar workstreams that can run while the manager continues local work.
5. Spawn only the useful sidecar agents, then keep moving locally until an integration barrier requires their results.

## Start A Mission

Create a mission ledger before delegating meaningful work. Prefer the helper script when available:

```bash
python3 /Users/robson/.agents/skills/codex-mission-control/scripts/start_mission.py --title "short task title"
```

The helper creates a unique directory under `work/codex-missions/<task-slug>/<timestamp>-<suffix>/` by default and writes a uniquely named ledger file inside it. If the current workspace should not receive support files, pass an OS temp root:

```bash
python3 /Users/robson/.agents/skills/codex-mission-control/scripts/start_mission.py --title "short task title" --root /tmp/codex-missions
```

If the script is unavailable, create the same structure manually:

1. Choose a task slug from the current goal.
2. Create a unique run directory with timestamp plus short random suffix.
3. Create a mission ledger named with that same run id.
4. Create sibling directories for handoffs and worker reports.

## Mission Workflow

1. Capture the goal in one sentence.
2. Record constraints from the user, repository instructions, safety boundaries, and dirty worktree state.
3. Split the work into workstreams only when the split reduces context load or enables real parallel progress.
4. Mark each workstream as local, subagent, or separate thread.
5. Keep the immediate critical path local. Delegate sidecar work that can run in parallel.
6. For separate threads, seed each one with a compact handoff instead of the full manager context.
7. For subagents, give concrete ownership and a bounded output contract.
8. Integrate worker results into the ledger using summaries and links, not pasted logs.
9. Verify final behavior from the manager thread.
10. Close with the final answer and note any thread ids, changed files, tests, and unresolved risks.

## Delegation Rules

Use subagents when all of these are true:

1. The user explicitly asked for subagents, delegation, parallel agent work, or mission control behavior.
2. The subtask is concrete, bounded, and materially advances the mission.
3. The subtask can run without blocking the manager immediate next step.
4. For code edits, the write scope is disjoint from other active work.

Use a separate Codex thread when one of these is true:

1. The slice will take multiple turns.
2. The slice needs a fresh worktree, branch, or repo scoped environment.
3. The slice is a follow up audit or implementation item that should preserve its own context.
4. The manager thread is becoming too full and the next workstream can start from a compact handoff.

Do not fork a bloated manager context by default. Prefer a clean thread seeded by a compact prompt. Use context forking only when the worker truly needs the completed conversation history.

## Native Subagent Runtime

In Codex, prefer native subagents over CLI runner fallbacks when the tools are exposed.

1. Use `multi_agent_v1.spawn_agent` for a new subagent.
2. Use `agent_type="explorer"` for specific codebase questions.
3. Use `agent_type="worker"` for bounded implementation with a clear write scope.
4. Omit `model`, `reasoning_effort`, and `service_tier` unless the user explicitly asks or the work has a clear need. Let the worker inherit the parent defaults.
5. Set `fork_context=false` by default and pass a compact brief. Use `fork_context=true` only when the worker truly needs the completed conversation history.
6. For code edits, assign disjoint files or modules. Tell each worker that other agents may be editing in parallel and that it must not revert unrelated changes.
7. Use `wait_agent` only at a real barrier. While agents run, do non overlapping manager work.
8. When a worker finishes, inspect its report and changed files before integrating or presenting its result.
9. Close agents that are no longer needed.
10. Record every spawned agent id, role, scope, and final status in the ledger.

## Separate Thread Reality

Do not assume a skill file can directly open a new Codex UI thread.

1. If the host exposes an explicit thread creation tool, use it and record the returned thread id.
2. If no thread creation tool is exposed, create a compact handoff file and an exact seed prompt for the new thread.
3. Keep the manager thread responsible for integration after the separate thread reports back.
4. Prefer separate threads over subagents when the work needs long context isolation, a fresh worktree, or multiple future turns.

## Configuration Reality

1. Native Codex subagent availability is controlled by the host runtime and config, such as `~/.codex/config.toml` having the multi agent feature enabled.
2. A project `routing.toml` is not required for Codex native subagents. TOML routing files are useful only for skills that parse them explicitly.
3. `agents/openai.yaml` is useful for Codex UI metadata, default prompts, and invocation policy. It is not the subagent runtime itself.
4. If the runtime preflight cannot expose `multi_agent_v1`, patching TOML inside this skill will not create subagent tools for the current turn.

## Handoff Contract

Each handoff should fit on one screen when possible and include:

1. Mission id and source ledger path.
2. Goal for this workstream.
3. Relevant files, routes, commands, docs, or issue links.
4. Constraints and non goals.
5. Expected deliverable.
6. Required verification.
7. Output contract for the worker final.

Save handoffs under the current mission `handoffs` directory with filenames that include the mission id, workstream slug, and timestamp or thread id.

## Worker Prompt Pattern

Use this structure for a subagent or new thread:

```text
You are working inside mission <mission_id>.

Goal: <specific workstream goal>
Source ledger: <absolute path>
Runtime target: <subagent role or separate thread>
Write scope: <files or modules, or read only>
Constraints: <important user and repo constraints>
Do not revert unrelated changes. Other agents may be working in parallel.

Return a compact final with:
1. result
2. files changed
3. tests run
4. risks
5. recommended next handoff
```

## Ledger Discipline

Update the mission ledger after each meaningful event:

1. Runtime preflight completed.
2. Workstream started.
3. Thread created, handoff written, or subagent spawned.
4. Worker completed.
5. Decision made.
6. Files changed.
7. Verification passed or failed.
8. Final integration completed.

Keep evidence compact. Link to files, thread ids, commands, and reports. Do not paste long terminal logs unless the exact error text is required.

## Gotchas

1. Asking for depth is not the same as asking for subagents. Use this skill when the user asked for mission control, subagents, parallel execution, separate threads, or context preservation.
2. A single fixed handoff file creates collisions across repeated runs. Always use mission scoped paths with a timestamp or unique suffix.
3. The manager should not redo delegated work. It should integrate, verify, and resolve conflicts.
4. Separate read only audits from mutating implementation threads unless the user explicitly asks to change code in the audit context.
5. Do not treat a TOML routing file as a magic subagent switch. First prove whether native subagent tools are exposed.
