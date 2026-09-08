---
name: distributed-systems-patterns
description: "Choose or review distributed topology and event-stream patterns. Use for replicas, shards, container helpers, queues, or event-driven adoption and migration; use macro-architecture for overall system style."
---

# Distributed Systems Patterns

Read-only pattern skill. Do not implement unless the user asks after the brief.

Two bodies of knowledge, one skill. The **topology routes** are grounded in Burns, _Designing Distributed Systems_: containers plus an orchestrator give a shared language for reusable distributed pieces — name the pattern, then reuse or compose it. The **event-driven route** is grounded in Bellemare: a durable, replayable **data communication layer** of schematized event streams, not point-to-point messages that vanish after consume. Do not invent a one-off topology the catalog already names, and do not call a delete-after-consume queue an event architecture.

## Outcome

- **Result:** a brief with one named pattern (or an explicit compose of two), or — on the event-driven route — one verdict, plus the next concrete move.
- **Next consumer:** the user, or `design-gate` / `coding-design-plan` after they accept the brief.
- **Done:** every required brief field is filled; the pattern is from the selected method's catalog; every load-bearing claim cites repo evidence or is marked `assumed`; at least one rejected alternative is named; the next move is one action.
- **Intent:** stop four failures — reinventing a named primitive; applying a multi-node pattern when a **coscheduled pair** would do (or an election when a singleton would do); adopting event-driven microservices when a modular monolith is cheaper; and building them without a **data communication layer** (implicit schemas, shared DBs, CDC as the destination).

## Select the route

| Need | Read |
| --- | --- |
| Create, maintain, or review containers, replicas, shards, election, queues, or batch topology | [references/topology-review.md](references/topology-review.md) |
| Adopt, review, or migrate event-driven services and public streams | [references/event-driven-review.md](references/event-driven-review.md) |

If the question is only monolith versus services, use macro-architecture. Choose the smallest pattern that meets the constraint. The selected method contains the decision process, focused source references, and required brief fields.

## Shared vocabulary

State these **leitwörter** by name as you decide, not only in headings.

Topology routes:

- **coscheduled pair** — sidecar, ambassador, and adapter only work when the containers share a machine and the namespaces the pattern needs (network, filesystem, or PID). If they talk across the cluster network, this is a service, not a single-node pattern.
- **container API** — env vars, ports, files, and signals are a versioned contract. Renaming a parameter or changing its units is a breaking change.
- **readiness, not liveness** — a replica that is alive but not ready must stay out of the load balancer. Liveness restarts; readiness withholds traffic.
- **need a master** — most tasks do not need ownership election. A singleton under an orchestrator already restarts on crash and relocates on node death. Prove the SLA before electing.

Event-driven route:

- **data communication layer** — durable, replayable streams that decouple producing data from accessing it. If this is not being built, this is not event-driven microservices.
- **single source of truth** — the stream is the fact; local stores are projections that can be rebuilt.
- **single writer** — one service owns writes to a stream.
- **event-first** — the public event is a first-class product. CDC/outbox bootstraps liberation; it is not the destination.

Modelled sentence: _"This is a **coscheduled pair** (ambassador), not a new service — the app keeps a localhost **container API**; the rejected alternative (client-side sharding in every language) would break **change ownership**."_

## Evidence

Inspect the live system (or the stated requirements if there is no repo). Do not invent a topology.

Topology routes: search for container groups / pods, sidecar/proxy/exporter containers, Services / Ingress / load balancers, readiness vs liveness probes, shard keys, consistent-hash configs, leader-election / lease / lock clients, Job / CronJob / queue consumers, FaaS handlers. Event-driven route: search for broker clients, topic/stream names, schema files, outbox/CDC connectors, consumer groups, changelogs; sample two or three streams end to end — producer, schema, consumers — rather than listing every topic.

Read budget: enough to name the pattern, the roles, and the **container API** (or, on the event-driven route, the owners, contracts, and current source of truth). Stop when another file would not change the brief.

If there is no repo, use the user's constraints (SLA, data size, request shape; team size, shared data, the tax they will pay). Mark those `assumed`.

## Delivery

Topology routes emit the pattern brief from `assets/pattern-brief.md`; the event-driven route emits the decision brief from `assets/edm-decision-brief.md`. Emit inline. Write a file only when the user asks to record it, or when the project's active instructions already require ADRs for this class of decision — then follow that convention, otherwise `docs/decisions/dds-YYYYMMDD-<slug>.md` (topology) or `docs/decisions/edm-YYYYMMDD-<slug>.md` (event-driven).

When invoked as a design-gate lens, also return `verdict: proceed|revise`, `blocking_findings`, `advisory_findings`, `required_changes`. Any of these is `revise`: a single-node pattern that is not a **coscheduled pair**; replicated serving without **readiness, not liveness**; a shard with no key; an election that failed **need a master**; FaaS used for long-running or warm-memory work; scatter/gather with unbounded leaves; a missing **data communication layer**; a second writer on a public stream; CDC-as-destination on a core entity.

## Focused references

Load only a file selected by the active method:

- `references/single-node.md` — sidecar, ambassador, adapter
- `references/serving.md` — replica, shard, scatter/gather, FaaS, election
- `references/batch.md` — work queues, event-driven batch, join/reduce
- `references/pattern-catalog.md` — when-to / when-not-to matrix
- `references/edm-adopt-or-not.md` — adopt gate, the tax, when hold is correct
- `references/edm-event-contracts.md` — event shapes, schema rules, breaking changes
- `references/edm-implementation-styles.md` — FaaS / BPC / heavy / light, workflows, state
- `references/edm-review-and-migrate.md` — smell catalog, liberation patterns, one-slice migration
- `assets/pattern-brief.md` — the pattern brief template
- `assets/edm-decision-brief.md` — the event-driven decision brief template
