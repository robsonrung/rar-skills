---
name: dynamic-harness
description: "Dynamic multi agent harness orchestration for complex, high value tasks. Use when the user invokes $dynamic-harness or asks for a workflow, dynamic workflow, dynamic harness, ultracode style harness, many subagents, competing agents, tournament, fan out and synthesis, generate and filter, adversarial verification, classify and act routing, loop until done investigation, large migration, deep research, deep verification, qualitative sorting, triage at scale, or root cause analysis."
---

# Dynamic Harness

Use this skill as a Codex port of dynamic workflows: move orchestration into a compact plan, split context across focused agents, verify adversarially, and synthesize only evidence that survives. The skill invocation means the user wants workflow orchestration; use subagents only when they are available, useful, and safe.

## First Move

1. Restate the user goal, success criteria, constraints, risk level, and available budget.
2. Decide whether this needs a full workflow, a quick workflow, or a direct answer with normal verification. For small tasks, use a quick workflow only when independent checking adds value.
3. Identify the immediate critical path task for the main agent. Do that locally while subagents handle independent side work.
4. If subagent tools are not visible, call tool search for multi agent spawn subagents. If none are available, emulate the workflow serially, state that no subagents were spawned, and do not imply parallel execution happened.
5. Use the smallest sufficient parallelism, then scale up aggressively only when slices are independent and added agents reduce context pressure or improve verification. Avoid duplicate agents that would produce the same evidence.

## Workflow Brief

Before spawning agents, create a terse brief:

```text
Objective:
Success criteria:
Workflow type:
Why this type:
Phases:
Agent plan:
Verification plan:
Stop condition:
Budget guard:
Risk guard:
Expected output:
```

For GreenSpark AWS tasks, obey root and nested `AGENTS.md`, start topic discovery from `docs/REPO_KNOWLEDGE_MAP.md`, and use repo skills that match the task. For reproductions, prefer `npm run local:env`, then `npm run local:verify`, then fixture backed reproduction before reaching for development database dumps.

## Runtime Adaptation

1. In Codex, orchestrate with available subagent tools such as `multi_agent_v1.spawn_agent`, `wait_agent`, and `send_input`.
2. If running inside Claude Code with native dynamic workflows enabled, prefer the native workflow runtime for repeatable large runs because the host script can hold intermediate results, run in the background, and be saved for reuse.
3. Do not invent native JavaScript workflow function names. If the host exposes a saved script, inspect or adapt that script. If it does not expose the API, run the skill as a Codex style agent orchestration.
4. If the user asks for a reusable native workflow artifact, place it where the host expects workflow files, such as project or user workflow folders, only after confirming the runtime format from local evidence or official docs.

## Choose The Workflow Type

1. Classify and act

Use when the right route, domain, skill, model, or verification strategy is unclear. Spawn a classifier or mapper first, then route to the chosen specialists. Also use at the end when outputs need classification into approve, escalate, fix, discard, or ask user.

2. Fan out and synthesize

Use when the task can be divided into many independent shards, such as files, claims, tickets, resumes, endpoints, logs, modules, source links, or hypotheses. Spawn one agent per shard or per small shard group when cost and independence justify it. Wait at the synthesis barrier, then merge structured outputs.

3. Adversarial verification

Use when correctness matters, when agents may be biased toward their own findings, or when the output will guide edits, decisions, money, security, production data, or public claims. For high risk outputs, pair each worker result with one or more independent verifier agents. For lower risk batches, verify the highest impact outputs and sample the rest. Give verifiers the rubric and evidence, not the worker's confidence.

4. Generate and filter

Use for naming, design options, product strategy, plans, prompts, architecture alternatives, or other creative searches. Spawn generators with different angles. Deduplicate outputs. Spawn filter agents that score against a rubric. Verify only the survivors.

5. Tournament

Use when multiple agents should attempt the same task and compete, or when qualitative ranking is more reliable by comparison than absolute scoring. Spawn contestants with different approaches. Run pairwise judging agents or bracket rounds. Use a final judge and optional verifier for the winner.

6. Loop until done

Use when the amount of work is unknown, such as flaky test reproduction, log mining, security sweeps, backlog triage, migration cleanup, or root cause analysis. Spawn batches, synthesize findings, update the search frontier, and repeat until the stop condition is met.

Compose these modes freely. Common combinations are classify then fan out, fan out plus adversarial verification, generate and filter plus tournament, and loop until done with verifier gates after every batch.

## Agent Design

Give every subagent a narrow, self contained assignment:

```text
Role:
Input slice:
Goal:
Do:
Avoid:
Tools or commands allowed:
Write scope:
Evidence required:
Output schema:
```

Use these rules:

1. Pass only the context needed for that slice. Keep broad conversation history out unless it is essential.
2. Prefer `fork_context=false` unless the subagent truly needs prior turns.
3. For coding workers, assign disjoint files or modules. Tell them they are not alone in the codebase, must not revert others, and must list changed paths.
4. Use worktree isolation when available for large parallel edits or risky experiments.
5. For untrusted public content, quarantine reader agents from agents that can take privileged actions.
6. For expensive commands, production data, destructive edits, or external side effects, keep the action in the main agent and require explicit user approval when needed.
7. Use lower effort agents for simple classification or extraction only when the user permits model routing or the tool policy makes it appropriate. Otherwise inherit the current model.

## Execution Patterns

1. Classifier phase

Spawn one classifier when route uncertainty is high. Ask it to return a single recommended workflow type, specialist list, sharding plan, and risks. Continue collecting safe local context in parallel, but wait for classification before actions that depend on permissions, production risk, data source choice, or write scope.

2. Worker phase

Spawn as many independent workers as useful. For a large list, batch by risk or similarity. For code, keep write scopes disjoint. For research, assign separate source families or angles.

3. Verification phase

Spawn verifier agents for outputs that matter. A verifier should try to refute the candidate, check sources or code paths, run targeted checks when safe, and mark the candidate as verified, refuted, or unresolved.

4. Judge phase

Use judges for tournaments and generate and filter runs. Judges must compare concrete outputs against the rubric, not agent reputations or verbosity.

5. Synthesis phase

The main agent owns final synthesis. Merge duplicates, resolve conflicts, prefer verified evidence, retain dissent when unresolved, and inspect any file edits before presenting or committing them.

## Loop Controls

For loop until done workflows, define all of these before the first batch:

1. Progress signal, such as new verified findings, failing tests, unexplored shards, or unresolved hypotheses.
2. Stop condition, such as no new findings in two batches, all tests pass, all claims checked, all shards processed, or budget reached.
3. Escalation condition, such as conflicting evidence, production risk, missing access, or a decision only the user can make.
4. Batch size and maximum total agents. Treat 16 concurrent agents and 1000 total agents as hard upper bounds when using a native dynamic workflow runtime, not as goals. Use smaller limits when the current tools, task value, or machine call for it.

## Budget Defaults

1. Quick workflow: use 1 to 3 agents, usually a classifier, a worker, or a verifier.
2. Standard workflow: use 4 to 12 agents across workers, verifiers, and synthesis support.
3. Large workflow: start with a small representative slice before scaling beyond 12 agents.
4. Deep loop: cap each batch, report progress between batches when interactive, and stop when evidence no longer improves.
5. Expensive workflow: ask the user for a budget if the task could consume many agents, long running commands, paid APIs, production data, or broad web research.

## Synthesis Rules

1. Keep a compact ledger of agents, assignments, status, evidence, changed paths, and verdicts. Use a temporary artifact only when the run is too large to track in context.
2. Never accept a worker output only because it is confident. Require evidence.
3. Mark every important claim as verified, refuted, or unresolved.
4. Prefer pairwise comparison for ranking large qualitative sets.
5. Run the nearest real verification command when code changed and the command is safe.
6. If verification cannot run, say exactly what was not verified and why.

## Final Response

Report:

1. Workflow type used and why.
2. Number and roles of agents spawned.
3. Verified result or winning option.
4. Evidence, commands, sources, or changed files.
5. Unresolved risks or blocked decisions.

Keep the final answer concise. Do not include raw subagent transcripts unless the user asks.
