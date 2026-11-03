---
name: distributed-systems-patterns
description: "Choose or review distributed topology and event-stream patterns. Use for replicas, shards, container helpers, election, queues, batch pipelines, or event-driven adoption and migration; use architecture-lens for overall system style."
---

# Distributed Systems Patterns

Read-only pattern lens. Two bodies of knowledge: the **topology route** follows Burns, _Designing Distributed Systems_ (name the container-shaped pattern, then reuse or compose it); the **event-driven route** follows Bellemare (a durable, replayable **data communication layer** of schematized streams, not messages that vanish after consume). Don't invent a one-off topology the catalog already names, and don't call a delete-after-consume queue an event architecture.

The four failures this lens stops: reinventing a named primitive; a multi-node pattern where a **coscheduled pair** would do, or an election where a singleton would do; event-driven microservices where a modular monolith is cheaper; and building them without a data communication layer (implicit schemas, shared databases, CDC as the destination).

Elsewhere: overall style and service decomposition → `architecture-lens`; outbox writes, idempotency, retries, dead-letter handling, and transactions in code → `data-systems-coding-lens`; bounded-context alignment → `domain-driven-design`; in-process object structure → `software-design-philosophy`; agent loops → `agent-architecture-lens`.

## Select the route

| Need | Read |
| --- | --- |
| Containers, replicas, shards, scatter/gather, FaaS, election, work queues, batch pipelines | [references/topology.md](references/topology.md) |
| Adopt, review, or migrate event-driven services and public streams | [references/event-driven.md](references/event-driven.md) |

Choose the smallest pattern that meets the constraint. If no distributed pattern fires, say so and stop.

## Leitwörter

State these by name as you decide.

Topology:

- **coscheduled pair**: sidecar, ambassador, and adapter work only when the containers share a machine and the namespaces the pattern needs. Talking across the cluster network makes it a service.
- **container API**: env vars, ports, files, and signals are a versioned contract. Renaming a parameter or changing its units is a breaking change.
- **readiness, not liveness**: a replica that is alive but not ready stays out of the load balancer. Liveness restarts; readiness withholds traffic.
- **need a master**: most tasks don't need election. A singleton under an orchestrator already restarts on crash and relocates on node death. Prove the SLA before electing.

Event-driven:

- **data communication layer**: durable, replayable streams that decouple producing data from accessing it. Without it, this is not event-driven microservices.
- **single source of truth**: the stream is the fact; local stores are rebuildable projections.
- **single writer**: one service owns writes to a public stream.
- **event-first**: the public event is a first-class product. CDC bootstraps liberation; it is not the destination.

Modelled sentence: _"This is a **coscheduled pair** (ambassador), not a new service: the app keeps a localhost **container API**; the rejected alternative, client-side sharding in every language, would scatter **change ownership**."_

## Evidence

Inspect the live system, or the stated requirements when there is no repo, and mark those `assumed`.

- Topology: pods or container groups, sidecar and proxy containers, Services and load balancers, readiness and liveness probes, shard keys and hash configs, lease or lock clients, Jobs and queue consumers, FaaS handlers.
- Event-driven: broker clients, topic names, schema files, outbox or CDC connectors, consumer groups, changelogs. Sample two or three streams end to end (producer, schema, consumers) instead of listing every topic.

Stop reading when another file would not change the brief.

## Output

Standalone, emit one brief inline. Prefix every inferred fact with `assumed:`. Write a file only when the user asks or the project already requires decision records for this class of decision; then follow that convention.

**Topology brief:** job (create, maintain, or review, plus the decision in one sentence); scale (single-node, serving, or batch); pattern (catalog name; compose at most two and name the join); roles (container or node and its job; mark the coscheduled pair); container API (parameters, ports, files, signals, and what would break, or `n/a` with why); failure (what would make this pattern wrong); evidence; rejected (at least one alternative and its cost); next move (one action).

**Event-driven brief:** job (new-system, existing-edm, or migrate, plus the decision); verdict (`adopt`, `hybrid`, `hold`, `review-fix`, or `migrate-slice`); data communication layer (the stream-backed source of truth, or why there isn't one); single writer (producer per public stream, or the violation); evidence; rejected; next move (liberate this entity, add this schema, stop this second writer).

Under `design-gate`, return the caller's canonical gate result instead; carry pattern constraints and the event-driven verdict in findings or `review_focus`. Any of these is `revise`: a single-node pattern that is not a coscheduled pair; replicated serving without readiness, not liveness; a shard with no key; an election that failed need a master; FaaS for long-running or warm-memory work; scatter/gather with unbounded leaves; a missing data communication layer; a second writer on a public stream; CDC as the destination for a core entity. In an interview, add the decision, operating cost, evidence, and constraints to the existing decision record.
