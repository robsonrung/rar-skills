# Pattern catalog

Read when two families both look plausible, or before composing patterns.

## Contents

1. [What this catalog is](#what-this-catalog-is)
2. [Decision order](#decision-order)
3. [When-to / when-not-to](#when-to--when-not-to)
4. [Legal composes](#legal-composes)
5. [Handoffs](#handoffs)

## What this catalog is

The Burns catalog is a *shared language* for container-shaped distributed systems, not a style selector and not a data-layer doctrine.

- Style (monolith vs microservices vs event-driven) → `macro-architecture`
- Streams as the source of truth → `event-driven-microservices`
- How a write retries, migrates, or stays **idempotent** in code → `data-systems-coding-lens`
- GoF object structure → `design-patterns`

This file only decides *which Burns pattern names the topology*.

## Decision order

Walk top to bottom. Stop at the first yes. This *is* the **smallest coherent shape** for this skill.

1. Do two processes need a shared machine + namespace? → single-node (`references/single-node.md`)
2. Is the work one-shot / offline transformation of a set? → batch (`references/batch.md`)
3. Otherwise it is serving (`references/serving.md`)
    1. Does every replica hold enough to answer every request, with no per-user durable state? → replicated
    2. Does a request need *all* leaves, merged at a root, to finish faster or to cover sharded data? → scatter/gather
    3. Does each replica own a key-space slice because state (or cache working set) no longer fits one machine? → sharded
    4. Is it a short stateless transform you want to scale independently of the service? → FaaS
    5. Must *exactly one* process own a task at a time? → **need a master**; singleton or election

If none fire, you do not need a distributed pattern. Say so and stop.

## When-to / when-not-to

| Pattern | When | When not |
|---|---|---|
| Sidecar | Augment an app you will not change; share a helper image | Helper must scale or place independently |
| Ambassador | App should keep a localhost client; helper owns shard / broker / experiment | The router is a cluster service in front of many clients |
| Adapter | Normalize metrics / logs / health of a vendor or mixed image | You own the app and can implement the contract cheaper |
| Replicated | Stateless; SLA or load needs N identical servers | State does not fit one replica (that's shard) |
| Sharded | State or cache working set > one machine | Stateless load (replicate); no shard key designed |
| Scatter/gather | Parallelize one request's compute or query every data shard | Leaf count unbounded; merge function unnamed |
| FaaS | Short, stateless, event-triggered transform | Long job, large warm set, sustained busy-core traffic |
| Singleton | One owner; SLA ≤ ~two–three nines or background work | Four+ nines and two actives would corrupt ownership |
| Ownership election | **need a master** is proven; use CAS+TTL in a real store | Home-rolled Paxos; lock with no TTL |
| Work queue | One item → one reliable job | Multi-stage graph (name the event-driven primitives) |
| Event-driven batch | Linked queues with named hops | Hidden function graph; queue used as "the source of truth" (that's EDM) |
| Join | Barrier: do not proceed until every branch finishes | You meant to fold values (that's reduce) |
| Reduce | Fold partial outputs, same shape in and out | You only needed to wait (that's join) |

## Legal composes

Compose at most two in the brief; if you need more, the graph belongs in `roles` and the *headline* pattern is the outermost one.

Common legal composes:

- ambassador + sharded service (client-side shard router)
- adapter + anything (metrics/logs/health never change the serving pattern)
- replicated shards (hot-shard remedy)
- scatter/gather + leaf sharding (search)
- FaaS decorator in front of a replicated service
- work-queue shard + join + copier + reduce (coordinated pipeline)

Illegal (name the actual pattern instead):

- "sidecar" that lives on another node → service
- "shard" of a stateless HTTP API with no key → replica
- "election" around a Job queue → singleton or work queue
- "FaaS pipeline" whose stages are long Jobs → event-driven batch

## Handoffs

| Symptom | Hand to |
|---|---|
| "Should this even be many services?" | `macro-architecture` |
| "Should Kafka / events be the source of truth?" | `event-driven-microservices` |
| Retry, migration, **idempotent** write, transaction boundary in code | `data-systems-coding-lens` |
| Class/module structure, Strategy vs Decorator *in process* | `design-patterns` |
| LLM agent loop vs graph | `agent-architecture-lens` |
