---
name: agent-architecture-lens
description: Review the control-flow architecture of an LLM agent system — decide whether a task needs a plain agent loop or an explicit state graph, then check typed state, checkpoints, bounded retries, termination ceilings, idempotent steps, and human gates. Use when designing or reviewing an agent, a tool-calling loop, a multi-agent pipeline, or a long-running autonomous run; when an agent retries forever, loses work on a crash, needs mid-run human approval, or must be replayable and auditable; or when the question is whether something should be a loop or a graph. Distinct from data-systems-coding-lens, which covers retries and idempotency for stored state (databases, queues, caches) rather than agent steps; from macro-architecture, which decomposes services and assigns data ownership; and from knowledge-graph, which builds a graph an agent reads rather than the graph an agent runs on.
---

# Agent Architecture Lens

Use this skill to review how an agent's control flow, state, and failure handling are structured. The ReAct loop — reason, act, observe, repeat — is the atom of every agent, and it is correct. It is also incomplete: as runs get longer and messier it does not break in one dramatic failure, it quietly stops being enough.

A loop is a graph with one node and one edge pointing back at itself. The governing principle is **architecture follows the shape and duration of the task** — never the elegance of the diagram.

Two leitwörter anchor every pass. **A graph is not an upgrade**: structure is a response to a requirement you actually hit, so a task with no such requirement keeps its loop and the review says so. **The ledger, not the transcript**: progress that must survive anything lives in a durable artifact, never in the message history the model is hoping to remember. State both by name as you review.

## First pass: the six signals

Before recommending any structure, state which of **the six signals** fire, by number:

1. **State exceeds one context window.** The run tracks more than fits in the model's working memory.
2. **The run must survive crashes.** Losing it mid-execution is unacceptable — minutes of work, real API spend, a waiting user.
3. **Human approval is required mid-run.** A person must review before the agent continues, and they may take hours.
4. **The workflow has parallel branches.** Genuinely independent subtasks that should not be serialized.
5. **Multiple models or agents must coordinate.** Different steps need different models, tools, or permissions.
6. **Execution must be replayable and auditable.** Someone will ask "what exactly happened in this run?" after the fact.

Zero signals fire → recommend keeping the loop and stop. Say it plainly: _"No signal fires; this stays a loop — **a graph is not an upgrade**."_ Adding structure here buys latency and testing surface and returns nothing.

One or more fire → each one names the specific mechanism the design owes, and the checks below verify only those. Do not import the rest.

## The escalation ladder

Structure is added in this order, because each rung costs more than the one before it. Every rung must be justified by a signal that actually fired.

1. **Externalize state.** Pull what the run must remember out of the message list into a typed structure with named fields and declared defaults. Highest return, lowest cost — the model stops digging through its own prior reasoning to find a value it produced six steps ago.
2. **Add checkpoints.** Write state after each step so a crash resumes instead of restarting. This is the actual loop-to-graph transition.
3. **Separate responsibilities into named steps.** Split when steps need different models, tools, permissions, or error handling. One step, one job.
4. **Branch and parallelize.** Last, and only for genuinely independent work or genuinely divergent routes.

Signals 1 and 6 are usually satisfied at rung 1. Signals 2 and 3 need rung 2. Signal 5 needs rung 3. Only signal 4 needs rung 4.

## Implementation lens

Inspect these five areas in order. Skip any area whose signal did not fire.

### State

Check what the run remembers, where it lives, who writes it, and what it costs to grow.

Ask:

1. Which values must outlive the current context window, and which are genuinely scratch?
2. Does every persisted field have a type, a default, and a rule for what happens when two steps write it?
3. Can the state be reconstructed from durable inputs if it is lost, or is it the only copy?
4. Do large payloads sit inline in state, or behind an external store id?
5. What bounds message-history growth — a summarization step at a token threshold, or nothing?

### Retries

**The model never decides the retry.** A retry count that lives inside the model's reasoning produces both failure modes: fifteen attempts at a dead endpoint, and a single attempt followed by a fabricated result.

Ask:

1. Is the attempt count written down somewhere the next execution reads, or re-derived from memory each time?
2. Is the counter incremented _before_ the attempt? A crash mid-attempt must still count as an attempt.
3. What is the fallback route when the count hits its bound — a named escalation, or an unhandled dead end?
4. Does a retried step distinguish a transient failure from a permanent one, or retry both identically?
5. Is there any path where a failing tool can be called again with no external bound on the count?

### Termination

Every run needs **three exits**: success, retries-exhausted, and a hard ceiling — max steps, max tokens, a spend cap, or a deadline. Two out of three is an unbounded run wearing a stopping condition.

Ask:

1. Which condition ends this run successfully, and is it a state value or the model's opinion that it is done?
2. What happens when the work is not finishable — is there a named failure exit, or does it loop?
3. What is the hard ceiling, in a unit that can be counted without the model's cooperation?
4. Who observes the ceiling being hit, and what do they see?
5. For anything long-running or paid: is there a spend bound, and was the user told about it?

### Side effects

Separate the **decision** ("this email should be sent, with this content") from the **execution** ("send it"). Decision steps replay safely; execution steps must be idempotent, because a crash between the side effect and the checkpoint replays that step on recovery.

Ask:

1. Which steps write outside the run — messages, commits, PRs, tickets, payments, deploys?
2. Does each carry a stable key written to state _before_ the effect, and checked at the top on re-execution?
3. Is the decision to act recorded separately from the act, so a replay re-executes only the second?
4. Can two parallel steps write the same state field or hit the same rate-limited API?
5. Are tools scoped per step, so a step that should only read cannot write?

### Recovery and gates

Ask:

1. Where does a human gate pause the run, and does the approval survive a process restart — or is it a conversational turn that vanishes?
2. On resume, what identifies the run, and how does it find the step to resume from?
3. Is there a **crash-resume test** — kill the run mid-flight, restart it, assert it resumes at the right step with the right counters? This is a required integration test, not an optional one.
4. Can the execution trace answer "what ran, in what order, with what inputs and outputs"?
5. What purges old checkpoints, and what is the audit window?

## What a graph costs

Name the cost when recommending structure — this is what lets the lens return `proceed` on a plain loop.

| Cost | What it looks like |
| --- | --- |
| Latency | Each checkpoint is a write, each boundary a serialization cycle — real but usually invisible; it matters for sub-second interactive work. |
| Coordination | Parallel branches need join points, and each branch fails independently — more error-handling code than the loop version needed. |
| Path explosion | Three conditional routes give up to eight execution paths, and each path needs a test. |
| Schema design | Every state field needs a type, a default, and a write rule; get it wrong and the errors surface in every step. |
| Maintenance | Retry logic, fallback routes, error handlers, and ceilings are all new code the loop did not have. |

The graph is more reliable precisely because it does not trust the model with orchestration. That reliability is paid for in engineering hours.

## Output contract

Return:

1. `verdict`: `proceed` or `revise`.
2. `signals_fired`: which of **the six signals** apply, by number, with one line of evidence each. An empty list is a valid and common result.
3. `blocking_findings`: load-bearing findings requiring plan changes (empty when `proceed`).
4. `advisory_findings`: non-blocking observations worth carrying into implementation.
5. `required_changes`: numbered plan amendments (only when `revise`).

When this lens changes the work, say so in one line:

```text
Agent architecture lens: signals [n] fire, so [mechanism owed]; [main risk], bounded by [ceiling].
```

## Gotchas

1. Do not recommend a graph because the design looks more serious with one. Zero signals means the loop is the answer.
2. Do not treat parallelism as sophistication — it multiplies the testing surface and is the last rung, not the first.
3. Do not accept "the agent will stop when it is done" as a termination condition. It needs **three exits**.
4. Do not accept a retry bound stated only in prose. If nothing outside the model counts the attempts, there is no bound.
5. Do not let checkpoints accumulate forever — unbounded state growth is a slow outage.

## References

Load on demand, not preemptively:

- `references/failure-modes.md` — symptom → structural remedy, with calibration for how far unbounded runs actually go.
- `references/state-and-checkpoints.md` — typed-state schema design, checkpoint cadence, TTL and purge.
- `references/topologies.md` — loop, router, orchestrator-workers, evaluator-optimizer, parallel fan-out with a join.
