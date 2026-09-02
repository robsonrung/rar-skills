---
name: dynamic-harness
description: "Dynamic multi agent harness orchestration plus thin manager mission control for complex, high value tasks. Use when the user invokes $dynamic-harness or asks for a workflow, dynamic workflow, dynamic harness, ultracode style harness, many subagents, competing agents, tournament, fan out and synthesis, generate and filter, adversarial verification, classify and act routing, loop until done investigation, large migration, multi agent deep research, deep verification, qualitative sorting, triage at scale, or root cause analysis at scale with competing hypotheses. Also use for mission control: preserve context, avoid compaction, run subagents, create focused threads, split workstreams, manage handoffs, or supervise parallel agent execution."
disable-model-invocation: true
---

# Dynamic Harness

Use this skill as a Codex port of dynamic workflows: move orchestration into a compact plan, split context across focused agents, verify adversarially, and synthesize only evidence that survives. The skill invocation means the user wants workflow orchestration; use subagents only when they are available, useful, and safe.

## First Move

1. Restate the user goal, success criteria, constraints, risk level, and available budget.
2. Decide whether this needs a full workflow, a quick workflow, or a direct answer with normal verification. For small tasks, use a quick workflow only when independent checking adds value. When the run is a long mission across turns or threads and the manager's context is the scarce resource, add [Manager Mode](#manager-mode-codex-host).
3. Identify the immediate critical path task for the main agent. Do that locally while subagents handle independent side work.
4. Use the smallest sufficient parallelism, then scale up aggressively only when slices are independent and added agents reduce context pressure or improve verification. Avoid duplicate agents that would produce the same evidence.

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

## Runtime

1. If subagent tools are not visible, call tool search for multi agent spawn subagents.
2. In Codex, orchestrate with available subagent tools such as `multi_agent_v1.spawn_agent`, `wait_agent`, `send_input`, and `close_agent`. Call `wait_agent` only at a real barrier — do non overlapping local work while agents run — inspect each worker's report and changed files before integrating, and close agents that are no longer needed. Record the preflight result (which tools are visible, or that none are) wherever the run keeps its ledger.
3. If running inside Claude Code with native dynamic workflows enabled, prefer the native workflow runtime for repeatable large runs because the host script can hold intermediate results, run in the background, and be saved for reuse.
4. If the user asks for a reusable native workflow artifact, place it where the host expects workflow files, such as project or user workflow folders, only after confirming the runtime format from local evidence or official docs.
5. If no subagent tools are available, emulate the workflow serially, state that no subagents were spawned, and do not imply parallel execution happened.
6. Do not invent native JavaScript workflow function names. If the host exposes a saved script, inspect or adapt that script. If it does not expose the API, run the skill as a Codex style agent orchestration.

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

A loop-until-done workflow needs **three exits**, not one: the stop condition when the work converges, an escalation exit when it cannot, and a hard ceiling on batches and total agents that fires regardless of progress. A stop condition that depends on the loop noticing its own lack of progress is not a ceiling. Record the batch count and dispatched-agent count as they are spent and compare them against the declared bounds before each batch — **the model never decides the retry**, and it does not decide to grant itself another batch either.

## Budget Defaults

1. Quick workflow: use 1 to 3 agents, usually a classifier, a worker, or a verifier.
2. Standard workflow: use 4 to 12 agents across workers, verifiers, and synthesis support.
3. Large workflow: start with a small representative slice before scaling beyond 12 agents.
4. Deep loop: cap each batch, report progress between batches when interactive, and stop when evidence no longer improves.
5. Expensive workflow: ask the user for a budget if the task could consume many agents, long running commands, paid APIs, production data, or broad web research. Record the answer as the run's ceiling rather than holding it in the conversation — a budget the user granted once is the bound for the whole run, and a resumed run that cannot find it asks again rather than assuming it.

## Synthesis Rules

1. Keep a compact ledger of agents, assignments, status, evidence, changed paths, and verdicts. In context is enough for a quick or standard workflow that fits in one window and costs little to repeat. Write it to a durable run state (`shared/references/run-state-contract.md`) whenever the run must survive a crash or compaction, exceeds one context window, dispatches beyond a single batch, or will be audited afterwards — there, progress lives in **the ledger, not the transcript**, because a harness that loses its ledger re-dispatches work it already paid for.
2. Never accept a worker output only because it is confident. Require evidence.
3. Mark every important claim as verified, refuted, or unresolved.
4. Prefer pairwise comparison for ranking large qualitative sets.
5. Run the nearest real verification command when code changed and the command is safe.
6. If verification cannot run, say exactly what was not verified and why.

## Manager Mode (Codex Host)

Use manager mode when the run is a long **mission** rather than one fan-out: it spans multiple turns or threads, the manager's own context is the scarce resource, and workstreams must survive compaction. The manager stays **thin** — it owns the goal, constraints, workstream map, routing, handoffs, thread registry, integration, and the final answer, and nothing else. Deep exploration, long logs, and bounded implementation slices move out. The manager never redoes delegated work; it integrates, verifies, and resolves conflicts.

Everything above still applies and is not restated here: [Runtime](#runtime) is the only preflight (run it and record the result in the ledger before delegating), [Agent Design](#agent-design) is the only worker contract and the only disjoint-write-scope rule, and [Synthesis Rules](#synthesis-rules) item 1 is the only ledger rule. Manager mode adds the following.

### Start the mission

```bash
python3 <skill_dir>/scripts/start_mission.py --title "short task title"
# keep support files out of the workspace:
python3 <skill_dir>/scripts/start_mission.py --title "short task title" --root .ai-workflow/harness-missions
```

It creates a unique run directory (`.ai-workflow/harness-missions/<task-slug>/<timestamp>-<slug>-<suffix>/` by default) with sibling `handoffs/` and `worker-reports/` directories and a uniquely named ledger inside. Mission ids are collision-proof by construction — timestamp plus slug plus random suffix, created with `exist_ok=False` so a collision fails loudly instead of joining someone else's mission. A single fixed ledger or handoff filename collides across runs; always use the mission-scoped path, and use that same run directory for the run state. If the script is unavailable, replicate its layout by hand — read it for the exact ledger template.

### Subagent or separate thread

Spawn a **subagent** when all of these hold: the user asked for delegation or parallel agent work; the slice is concrete, bounded, and materially advances the mission; it can run without blocking the manager's next step; and, for edits, its write scope is disjoint from other active work.

Open a **separate thread** when any of these holds: the slice will take multiple turns; it needs its own worktree, branch, or repo-scoped environment; it is a follow-up audit or implementation item that should keep its own context; or the manager thread is filling up and the next workstream can start from a compact handoff. Keep read-only audits separate from mutating implementation threads unless the user asks otherwise.

**Fork policy:** `fork_context=false` is the default (Agent Design item 2). Never fork a bloated manager context — a clean thread seeded by a compact handoff beats a fork carrying everything the manager has already spent.

### Separate-thread reality

A skill file cannot open a Codex UI thread. If the host exposes a thread-creation tool, use it and record the returned thread id. If it does not, **emit a handoff file plus the exact seed prompt** for that thread and record both in the ledger — never imply a thread exists that nobody opened. Integration stays with the manager after the thread reports back.

### Configuration reality

1. Native subagent availability is controlled by the host runtime and config, such as `~/.codex/config.toml` with the multi agent feature enabled.
2. A project `routing.toml` is not a subagent switch. TOML routing files matter only to skills that parse them explicitly.
3. `agents/openai.yaml` is Codex UI metadata (display name, default prompt, invocation policy), not a runtime.
4. If the preflight cannot expose `multi_agent_v1`, patching TOML from inside a skill will not create subagent tools for this turn. Continue serially and say no subagents were spawned.

### Handoff contract

The brief, report, and envelope shapes are `shared/references/handoff-contract.md` — read it before writing the first handoff, and follow its rule: **hand off the path, not the payload**. A manager that pastes a worker's output into the next worker's brief has re-absorbed the context delegation just bought.

Manager mode binds it to the mission layout:

1. The brief's `run_id` is the mission id and its `run_state` is the mission's `run-state.json`; add a third mission field, the **runtime target** (subagent role or separate thread).
2. Briefs are saved under the mission's `handoffs/` directory, named with the mission id, workstream slug, and a timestamp or thread id. Worker reports go under `worker-reports/` with the matching name.
3. A worker brief is the [Agent Design](#agent-design) contract plus those three mission fields. Agent Design governs the worker's role, write scope, and evidence; the handoff contract governs what crosses in and out.

### Ledger versus run state

The Markdown ledger is for humans and is **write-only from the machine's side** — nothing reads it back, so it cannot drive a resume. Keep it (update it after each meaningful event: preflight, workstream start, thread created or handoff written or subagent spawned, worker completed, decision, files changed, verification, final integration; link to reports instead of pasting logs), and write a `run-state.json` beside it in the same mission directory per `shared/references/run-state-contract.md`.

- `status`, `phase`, and `steps` mirror the workstream table, so a resumed mission reconstructs what completed from the file rather than from the manager's memory.
- `ceilings.max_workers` bounds concurrent workers, `ceilings.max_dispatched` the total spawned. A manager with no worker ceiling is the shape that spawns until something else stops it.
- Every spawned agent id, role, scope, and final status goes in `steps` as well as the ledger table — that is the replay trace.
- Worker side effects (commits, merges, PRs) carry a `side_effects` key written before the effect, so re-dispatching a crashed worker does not duplicate what it already landed.
- **Resume:** load `run-state.json`, resume at `phase` with `attempts` intact, treat every gate in `gates` as already decided, skip every step in `steps` and every key in `side_effects`, and terminate orphaned workers from the prior session before dispatching new ones.

## Final Response

Report:

1. Workflow type used and why.
2. Number and roles of agents spawned.
3. Verified result or winning option.
4. Evidence, commands, sources, or changed files.
5. Unresolved risks or blocked decisions.
6. In manager mode, also the mission id and ledger path, any thread ids, and the handoffs written.

Keep the final answer concise. Do not include raw subagent transcripts unless the user asks.
