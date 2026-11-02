---
name: agent-architecture-lens
description: "Review agent control flow, durable state, retries, and recovery. Use when choosing a loop or state graph, or when a tool-calling workflow must survive failures and resume safely."
---

# Agent Architecture Lens

The ReAct loop (reason, act, observe, repeat) is the atom of every agent and is correct until the task outgrows it. A loop is a graph with one node and one edge back to itself. Architecture follows the shape and duration of the task, never the elegance of the diagram.

Two leitwörter anchor every pass; state them by name as you review. **A graph is not an upgrade**: structure answers a requirement the task actually has, and without one the loop stays. **The ledger, not the transcript**: progress that must survive anything lives in a durable artifact, never in the message history the model hopes to remember.

## The six signals

Before recommending structure, state which of **the six signals** fire, by number, with evidence:

1. **State exceeds one context window.**
2. **The run must survive crashes**: losing it costs minutes of work, real spend, or a waiting user.
3. **Human approval is required mid-run**, possibly hours later.
4. **The workflow has parallel branches** that are genuinely independent.
5. **Multiple models or agents must coordinate**, with different models, tools, or permissions per step.
6. **Execution must be replayable and auditable** after the fact.

Zero signals: _"No signal fires; this stays a loop. **A graph is not an upgrade**."_ Stop there. Otherwise each fired signal names the mechanism the design owes, and only the checks for those mechanisms apply.

## The escalation ladder

Each rung costs more than the last, and each needs a fired signal:

1. **Externalize state** into a typed structure with named fields and defaults (signals 1 and 6).
2. **Checkpoint** after each step, so a crash resumes instead of restarting (signals 2 and 3). This is the loop-to-graph transition.
3. **Separate named steps** where models, tools, permissions, or error handling differ (signal 5).
4. **Branch and parallelize** genuinely independent work (signal 4).

Name what the structure costs when you recommend it: a write per checkpoint, join and partial-failure handling per fan-out, a test per execution path (three conditional routes give up to eight), a schema to get right, and retry and ceiling code the loop never had.

For the shape of coordination itself (router, orchestrator-workers, evaluator-optimizer, fan-out with a join), read [references/topologies.md](references/topologies.md).

## Checks

### State

Per persisted field: a type (including whether empty is `null` or absent), a default, the steps allowed to write it, and a write rule (replace, append, merge, or max) when two steps write it. Store computed values (ids, amounts, statuses, counts) rather than prose the model must re-read. Keep fields to a few thousand tokens; larger payloads go to an external store with only the id in state. A summarization step at a token threshold bounds message history. This is **the ledger, not the transcript**.

### Retries

**The model never decides the retry.** A count held in the model's reasoning yields both failures: fifteen calls to a dead endpoint, or one attempt followed by a fabricated result. The attempt counter lives in state, increments _before_ the attempt so a crash mid-attempt still counts, and hits its bound into a named fallback. Transient and permanent failures are told apart. No path calls a failing tool again without an external bound.

### Termination

Every run has **three exits**: success, retries exhausted, and a hard ceiling (max steps, tokens, spend, or a deadline) counted without the model's cooperation. Success is a state value, not the model's opinion that it is done. Two of three is an unbounded run wearing a stopping condition. Someone sees the ceiling fire, and a paid or long run tells the user its spend bound.

### Side effects

Record the decision ("send this email, with this content") separately from the execution ("send it"), so a replay re-executes only the act. Each external effect (message, commit, PR, ticket, payment, deploy) is idempotent: its stable key is written to state _before_ the effect and checked on re-execution. Tools are scoped per step, so a read step cannot write. Parallel steps never share a state field without a write rule, or a rate-limited API without awareness of each other.

### Recovery

- A human gate is a durable state record that survives restart, not a conversational turn.
- Resume needs a run id the caller supplies, a status field with enumerated values, and a rule for the half-executed step: re-run it only if idempotent, skip it only if completion was recorded.
- Checkpoint after every step by default; after expensive or side-effecting steps only when the rest are cheap and idempotent. Keep checkpoints in memory only for tests, in a file for single-machine runs, and in a database for concurrent or queried runs.
- Every run gets a unique id. Checkpoints expire, completed runs are purged past a decided audit window, and failed or ceiling-hit runs are kept longest.
- The trace answers what ran, in what order, with what inputs and outputs.
- The **crash-resume test** is a required integration test: kill the run mid-flight, restart it, and assert it resumes at the right step with the right counters and repeats no side effect.

Not findings: a loop with no fired signal, a single-step agent without checkpoints, sequential execution of dependent steps, and missing observability on a run nobody audits that costs nothing to repeat.

## Verdict

Return `proceed` or `revise`; `signals_fired` by number with one line of evidence each (empty is a common, valid result); blocking findings that require plan changes; advisory findings; and, on `revise`, numbered required changes. When the lens changes the work, say so in one line:

```text
Agent architecture lens: signals [n] fire, so [mechanism owed]; [main risk], bounded by [ceiling].
```
