# Topologies

Read this when the shape of the coordination is the open question. Ordered by cost. Choose the first one that satisfies the signals that fired — later entries subsume earlier ones and charge for it.

## Single loop

One model, one message list, tools called until it stops. The atom. Correct whenever no signal fires: a question answered from a knowledge base, a document summarized, a ticket classified.

Failure boundary: everything is implicit. The model owns sequencing, retries, and termination. It works because nothing in the task punishes that.

## Router

One classification step routes to one of several handlers. The cheapest structure that is not a loop.

Use when different inputs need genuinely different handling — billing vs shipping vs fraud — and the branches do not need to coordinate. Cost is one extra step and one test per route.

Failure boundary: the router's own accuracy. A misroute is silent unless handlers validate their inputs.

## Orchestrator-workers

An orchestrator decomposes work, dispatches workers, and integrates results. Satisfies signals 4 and 5 together, which is why it is the common shape for anything at scale.

Requirements it brings with it:

- **Ownership.** Declare which state each side may read and write. `knowledge-graph/references/agent-access.md` defines exactly this table for the orchestrator/worker split.
- **Per-worker tool scoping.** A researcher gets read and search; a writer gets edit; neither gets both. This is the concurrency guard that prompt instructions cannot provide.
- **A join.** Every fan-out needs a defined point where results are collected, and a rule for what a failed branch does to the others — invalidate, degrade, or ignore.
- **A worker ceiling.** Concurrency has a bound and total dispatch has a bound, both counted outside the model.

## Evaluator-optimizer

A generator step and a critic step in a bounded cycle: produce, evaluate, revise.

Use when quality is measurable by a separate pass and the first attempt is reliably improvable. The critic must be a distinct step with its own model choice and its own tools — a self-critique inside one call is not this topology.

Failure boundary: it is a loop, so it needs **three exits**. The cycle count is written down, the ceiling is enforced outside the critic's judgment, and "the critic is satisfied" is never the only exit.

## Parallel fan-out with a join

Independent subtasks executed concurrently, results merged at a barrier.

Use only for genuinely independent work — checking three orders, researching three topics. The test: if branch B needs anything branch A produced, this is a sequence, not a fan-out.

Requirements:

- A write rule for every state field two branches can touch.
- Rate-limit awareness when branches call the same external service.
- A partial-failure rule decided in advance.

Prefer a pipeline where each item flows through all stages independently over a barrier between every stage. A barrier is justified only when a stage genuinely needs all prior results at once — deduplication across the full set, an early exit on a total count, or a comparison across branches. "I need to reshape the results first" is not a barrier; that reshaping belongs inside a stage.

## Choosing

| Signals fired | Smallest topology that answers them |
| --- | --- |
| None | Single loop |
| 1, 6 | Single loop with externalized state |
| 2, 3 | Named steps with checkpoints; the gate is a step |
| Different handling per input | Router |
| 4 | Parallel fan-out with a join |
| 5 | Orchestrator-workers |
| Quality needs an independent pass | Evaluator-optimizer, bounded |

Combining topologies is normal; adopting one whose signal never fired is the failure this table exists to prevent.
