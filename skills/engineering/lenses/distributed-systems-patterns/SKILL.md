---
name: distributed-systems-patterns
description: Name the container and multi-node pattern for a distributed app — sidecar, ambassador, adapter, replicated serving, sharding, scatter/gather, FaaS, ownership election, work queues, coordinated batch — and review it against that pattern's failure modes; or, on the event-driven route, decide whether to adopt, keep, or migrate to event-driven microservices and review event-stream contracts, single-writer ownership, and data liberation. Use when designing or reviewing a distributed service, adding a sidecar/proxy, sharding a store, choosing election vs a singleton, building a work-queue or scatter/gather pipeline, reviewing Kafka/Pulsar architecture, choreography vs orchestration, event schemas, CDC/outbox liberation, or asking "which distributed pattern is this" or "should Kafka be the source of truth". Distinct from macro-architecture (monolith vs microservices), domain-driven-design (bounded contexts, no broker contracts), data-systems-coding-lens (code-level retries, migrations), and design-patterns (GoF).
---

# Distributed Systems Patterns

Read-only pattern skill. Do not implement unless the user asks after the brief.

Two bodies of knowledge, one skill. The **topology routes** are grounded in Burns, _Designing Distributed Systems_: containers plus an orchestrator give a shared language for reusable distributed pieces — name the pattern, then reuse or compose it. The **event-driven route** is grounded in Bellemare: a durable, replayable **data communication layer** of schematized event streams, not point-to-point messages that vanish after consume. Do not invent a one-off topology the catalog already names, and do not call a delete-after-consume queue an event architecture.

## Outcome

- **Result:** a brief with one named pattern (or an explicit compose of two), or — on the event-driven route — one verdict, plus the next concrete move.
- **Next consumer:** the user, or `design-gate` / `coding-design-plan` after they accept the brief.
- **Done:** every required brief field is filled; the pattern is from the catalog below; every load-bearing claim cites repo evidence or is marked `assumed`; at least one rejected alternative is named; the next move is one action.
- **Intent:** stop four failures — reinventing a named primitive; applying a multi-node pattern when a **coscheduled pair** would do (or an election when a singleton would do); adopting event-driven microservices when a modular monolith is cheaper; and building them without a **data communication layer** (implicit schemas, shared DBs, CDC as the destination).

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

## Classify the job

Pick one route and stay on it:

| Route | Signal |
| --- | --- |
| `create` | Greenfield service, "how should we structure this", first topology |
| `maintain` | Existing manifests/code; add a sidecar, re-shard, introduce election, split a queue |
| `review` | Diff, design, or PR that already claims a distributed shape |
| `event-driven` | "Should we use events / Kafka", broker clients or topics in the repo, "liberate this data", choreography vs orchestration, event schema design |

If the ask is only "microservices or monolith" with no container, replica, shard, queue, election, or stream language, stop — that is `macro-architecture`.

## Topology routes: pick the family, then the pattern

Default to the **smallest coherent shape**: reusable container before new service; singleton before election; replica before shard; work queue before coordinated batch.

| If this is true | Family | Pattern |
| --- | --- | --- |
| Two processes must share a machine + a namespace | single-node | sidecar (augment), ambassador (broker outbound), adapter (normalize inbound) |
| Every replica can serve every request | serving | replicated load-balanced |
| Each replica owns a key-space subset | serving | sharded (optionally replicated shards; watch **hot shards**) |
| One request fans out; the root merges all answers | serving | scatter/gather |
| Short, stateless, event-triggered; no warm working set | serving | FaaS (decorator / event / pipeline) |
| Exactly one process must own a task | serving | first: **need a master**? if no, singleton; if yes, ownership election |
| One input → one reliable output | batch | work queue (source + worker **container API**) |
| Queues are linked | batch | event-driven batch (copier / filter / splitter / sharder / merger) |
| Wait-for-all, or fold many outputs to one | batch | coordinated batch (join / reduce) |

Load only the family the table selected:

- `references/single-node.md` — sidecar vs ambassador vs adapter; parameterization; reuse rules
- `references/serving.md` — replica / shard / scatter-gather / FaaS / election gates
- `references/batch.md` — work-queue interfaces; workflow primitives; join vs reduce
- `references/pattern-catalog.md` — full when-to / when-not-to matrix. Read when two families both look plausible, or before composing patterns.

## Event-driven route

Sub-route from the ask and the repo, then stay on it:

| Sub-route | Signal |
| --- | --- |
| `new-system` | Greenfield, "should we use events/Kafka", first service on a broker |
| `existing-edm` | Broker clients, topics, schemas, stream processors already in the repo |
| `migrate` | Monolith/SOA with locked data, batch syncs, shared DBs, "liberate this" |

Verdicts: `adopt` | `hybrid` | `hold` | `review-fix` | `migrate-slice`.

**Adopt gate** — run on `new-system` and `migrate` before any design; read `references/edm-adopt-or-not.md` before naming the verdict. **`hold`** if any of these is true: the org will not treat streams as the **single source of truth** (the monolith DB stays authoritative and streams are a dump); the microservice tax (broker, schema registry, deploy/reset tooling, ownership) will not be paid centrally in the planning horizon; no second team or product needs the same domain data in near real time; the work is request-shaped (auth, fetch-a-profile, third-party HTTP) with no shareable narrative. `adopt` or `hybrid` only when shared domain data is locked in an implementation _and_ the tax will be paid; **`hybrid` is the default** when adopting — request-response stays for UIs, auth, and third parties. On `hold`, write the brief and stop. Do not design topics.

- **`new-system`** — after a non-hold gate, read `references/edm-event-contracts.md`, then `references/edm-implementation-styles.md`. Design the **data communication layer** first (streams, schemas, writers), then pick one implementation style per bounded context.
- **`existing-edm`** — read `references/edm-review-and-migrate.md` and walk the smell catalog against repo evidence. For every contract finding, load `references/edm-event-contracts.md` before prescribing a fix. Verdict is `review-fix` unless the system already satisfies the catalog.
- **`migrate`** — after a non-hold gate, read `references/edm-review-and-migrate.md`. Pick **one** liberation slice: the most-shared, most-locked domain data. Name the liberation pattern and why it is **event-first** enough. Do not plan a rewrite.

## Evidence

Inspect the live system (or the stated requirements if there is no repo). Do not invent a topology.

Topology routes: search for container groups / pods, sidecar/proxy/exporter containers, Services / Ingress / load balancers, readiness vs liveness probes, shard keys, consistent-hash configs, leader-election / lease / lock clients, Job / CronJob / queue consumers, FaaS handlers. Event-driven route: search for broker clients, topic/stream names, schema files, outbox/CDC connectors, consumer groups, changelogs; sample two or three streams end to end — producer, schema, consumers — rather than listing every topic.

Read budget: enough to name the pattern, the roles, and the **container API** (or, on the event-driven route, the owners, contracts, and current source of truth). Stop when another file would not change the brief.

If there is no repo, use the user's constraints (SLA, data size, request shape; team size, shared data, the tax they will pay). Mark those `assumed`.

## Brief

Topology routes emit the pattern brief from `assets/pattern-brief.md`; the event-driven route emits the decision brief from `assets/edm-decision-brief.md`. Emit inline. Write a file only when the user asks to record it, or when the project's active instructions already require ADRs for this class of decision — then follow that convention, otherwise `docs/decisions/dds-YYYYMMDD-<slug>.md` (topology) or `docs/decisions/edm-YYYYMMDD-<slug>.md` (event-driven).

Pattern brief, required fields (protocol — omitting one means the brief is not done):

1. `job` — route + one-sentence decision
2. `scale` — `single-node` \| `serving` \| `batch`
3. `pattern` — catalog name (compose at most two; name the join)
4. `roles` — which container or node does what
5. `container_api` — parameters, ports, files, signals; or `n/a` with why
6. `failure` — the failure that would make this pattern the wrong one
7. `evidence` — files, manifests, probes, keys; or `assumed: …`
8. `rejected` — at least one alternative and the cost of taking it
9. `next_move` — one action
10. `not_this_skill` — work that belongs to `macro-architecture`, `data-systems-coding-lens`, or `design-patterns`

Decision brief (event-driven), required fields:

1. `job` — sub-route + one-sentence decision
2. `verdict`
3. `data_communication_layer` — what is (or would be) the stream-backed source of truth; or why there isn't one
4. `single_writer` — producer per public stream, or the violation
5. `evidence` — files, topics, schemas, or `assumed: …`
6. `rejected` — at least one alternative and the cost of taking it
7. `next_move` — one action (liberate _this_ entity, add _this_ schema, stop _this_ second writer)
8. `not_this_skill` — adjacent work that belongs to `macro-architecture`, `domain-driven-design`, or `data-systems-coding-lens`

When invoked as a design-gate lens, also return `verdict: proceed|revise`, `blocking_findings`, `advisory_findings`, `required_changes`. Any of these is `revise`: a single-node pattern that is not a **coscheduled pair**; replicated serving without **readiness, not liveness**; a shard with no key; an election that failed **need a master**; FaaS used for long-running or warm-memory work; scatter/gather with unbounded leaves; a missing **data communication layer**; a second writer on a public stream; CDC-as-destination on a core entity.

## Gotchas

1. A proxy on another host is a service, not an ambassador. Call the **coscheduled pair** test before naming sidecar / ambassador / adapter.
2. Do not bake HTTPS, metrics, log shipping, or config sync into every app image. That is a reusable container with a **container API**.
3. Do not shard to "handle load" when the service is stateless — replicate. Shard when the _state_ no longer fits one machine, or when a replicated cache would store the same hot set N times.
4. Do not hash the whole request. Pick the key that groups _identical responses_. Too general serves the wrong body; too specific wrecks hit rate. Re-shard only with a consistent hash.
5. Do not elect a master because "distributed systems have leaders." Run **need a master**. Background work and two-nines SLAs take a singleton.
6. Do not treat FaaS as a universal hammer. No long jobs, no large warm indexes, no pay-per-request once a core stays busy.
7. Scatter/gather latency is the _slowest_ leaf. More leaves raise straggler risk; the 99th percentile of one leaf becomes the median of a wide fan-out.
8. A message queue that deletes after consume is not a **data communication layer**. Call that messaging, not event-driven microservices.
9. Do not split services to look "micro." Align on a business bounded context. Technical layers as services are a defect.
10. Do not share a materialized store across services; each consumer projects its own copy. Do not mix incompatible event types in one stream to "save topics." Do not dual-produce two versions of a service onto the same output stream.
11. Do not treat connector-based CDC as the finished architecture, and do not recommend a distributed transaction when a compensation workflow will do. Hybrid is expected; an all-event architecture is almost never the answer.

## References

Load only the file the current step names:

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
