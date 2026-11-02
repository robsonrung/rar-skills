# Topologies

Ordered by cost. Choose the first that answers the signals that fired; later entries subsume earlier ones and charge for it.

| Signals fired | Smallest topology |
| --- | --- |
| None | Single loop |
| 1, 6 | Single loop with externalized state |
| 2, 3 | Named steps with checkpoints; the gate is a step |
| Different handling per input | Router |
| 4 | Parallel fan-out with a join |
| 5 | Orchestrator-workers |
| Quality needs an independent pass | Evaluator-optimizer, bounded |

Combining topologies is normal. Adopting one whose signal never fired is the failure this table prevents.

## Single loop

One model, one message list, tools until it stops. The model owns sequencing, retries, and termination, which works while nothing in the task punishes it.

## Router

One classification step sends input to one of several handlers that do not coordinate. Costs one step and one test per route. A misroute is silent unless handlers validate their input.

## Orchestrator-workers

An orchestrator decomposes, dispatches, and integrates. Answers signals 4 and 5 together. It owes:

- **Ownership**: which state each side may read and write.
- **Per-worker tool scoping**: a researcher reads and searches, a writer edits, neither does both. This is the concurrency guard that prompt instructions cannot give.
- **A join**: where results are collected, and whether a failed branch invalidates, degrades, or is ignored.
- **A worker ceiling** on concurrency and on total dispatch, counted outside the model.

## Evaluator-optimizer

A generator and a separate critic step, with its own model and tools, in a bounded cycle. Use when quality is measurable by a separate pass and the first attempt reliably improves. Self-critique inside one call is not this topology. It is a loop, so it needs **three exits**: the cycle count lives in state, the ceiling is enforced outside the critic, and "the critic is satisfied" is never the only exit.

## Parallel fan-out with a join

Concurrent independent subtasks merged at a barrier. If branch B needs anything branch A produced, it is a sequence. It owes a write rule for every shared field, rate-limit awareness on shared services, and a partial-failure rule decided in advance.

Prefer a pipeline, where each item flows through all stages independently, over a barrier between stages. A barrier is justified only when a stage needs every prior result at once: deduplication across the full set, an early exit on a total count, or a comparison across branches. Reshaping results belongs inside a stage.
