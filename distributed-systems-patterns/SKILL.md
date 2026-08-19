---
name: distributed-systems-patterns
description: >
  Name the container and multi-node pattern for a distributed app — sidecar,
  ambassador, adapter, replicated load-balanced serving, sharding, scatter/gather,
  FaaS, ownership election, work queues, and coordinated batch — then create,
  maintain, or review it against that pattern's failure modes. Use when designing
  or reviewing a distributed service, adding a sidecar/envoy/proxy, sharding a
  cache or store, choosing leader election vs a singleton, building a work-queue
  or scatter/gather pipeline, or asking "which distributed pattern is this",
  "do we need a sidecar", or "should this be sharded". Distinct from
  macro-architecture (monolith vs microservices style), event-driven-microservices
  (adopt Kafka/event streams as source of truth), data-systems-coding-lens
  (code-level retries, migrations, idempotent writes), and design-patterns
  (GoF object patterns).
---

# Distributed Systems Patterns

Read-only pattern skill grounded in Burns, *Designing Distributed Systems*. Do not implement unless the user asks after the brief.

Containers plus an orchestrator give a shared language for reusable distributed pieces. Name the pattern, then reuse or compose it. Do not invent a one-off topology the catalog already names.

## Outcome

- **Result:** a pattern brief with one named pattern (or an explicit compose of two) and the next concrete move.
- **Next consumer:** the user, or `design-gate` / `coding-design-plan` after they accept the brief.
- **Done:** every required brief field is filled; the pattern is from the catalog below; every load-bearing claim cites repo evidence or is marked `assumed`; at least one rejected alternative is named; the next move is one action.
- **Intent:** stop two failures — reinventing a named primitive, and applying a multi-node pattern when a **coscheduled pair** would do (or an election when a singleton would do).

State these four **leitwörter** by name as you decide, not only in headings:

- **coscheduled pair** — sidecar, ambassador, and adapter only work when the containers share a machine and the namespaces the pattern needs (network, filesystem, or PID). If they talk across the cluster network, this is a service, not a single-node pattern.
- **container API** — env vars, ports, files, and signals are a versioned contract. Renaming a parameter or changing its units is a breaking change.
- **readiness, not liveness** — a replica that is alive but not ready must stay out of the load balancer. Liveness restarts; readiness withholds traffic.
- **need a master** — most tasks do not need ownership election. A singleton under an orchestrator already restarts on crash and relocates on node death. Prove the SLA before electing.

Modelled sentence: *"This is a **coscheduled pair** (ambassador), not a new service — the app keeps a localhost **container API**; the rejected alternative (client-side sharding in every language) would break **change ownership**."*

## Classify the job

Pick one route and stay on it:

| Route | Signal |
|---|---|
| `create` | Greenfield service, "how should we structure this", first topology |
| `maintain` | Existing manifests/code; add a sidecar, re-shard, introduce election, split a queue |
| `review` | Diff, design, or PR that already claims a distributed shape |

If the ask is only "microservices or monolith" with no container, replica, shard, queue, or election language, stop — that is `macro-architecture`. If the ask is "should we use Kafka / event streams as the source of truth", stop — that is `event-driven-microservices`.

## Pick the family, then the pattern

Default to the **smallest coherent shape**: reusable container before new service; singleton before election; replica before shard; work queue before coordinated batch.

| If this is true | Family | Pattern |
|---|---|---|
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

## Evidence

Inspect the live system (or the stated requirements if there is no repo). Do not invent a topology.

Search for container groups / pods, sidecar/proxy/exporter containers, Services / Ingress / load balancers, readiness vs liveness probes, shard keys, consistent-hash configs, leader-election / lease / lock clients, Job / CronJob / queue consumers, FaaS handlers.

Read budget: enough to name the pattern, the roles, and the **container API**. Stop when another file would not change the brief.

If there is no repo, use the user's constraints (SLA, data size, request shape). Mark those `assumed`.

## Pattern brief

Emit the brief inline using `assets/pattern-brief.md`. Write a file only when the user asks to record it, or when the project's active instructions already require ADRs for this class of decision — then follow that convention, otherwise `docs/decisions/dds-YYYYMMDD-<slug>.md`.

Required fields (protocol — omitting one means the brief is not done):

1. `job` — route + one-sentence decision
2. `scale` — `single-node` \| `serving` \| `batch`
3. `pattern` — catalog name (compose at most two; name the join)
4. `roles` — which container or node does what
5. `container_api` — parameters, ports, files, signals; or `n/a` with why
6. `failure` — the failure that would make this pattern the wrong one
7. `evidence` — files, manifests, probes, keys; or `assumed: …`
8. `rejected` — at least one alternative and the cost of taking it
9. `next_move` — one action
10. `not_this_skill` — work that belongs to `macro-architecture`, `event-driven-microservices`, `data-systems-coding-lens`, or `design-patterns`

When invoked as a design-gate lens, also return `verdict: proceed|revise`, `blocking_findings`, `advisory_findings`, `required_changes`. Any of these is `revise`: a single-node pattern that is not a **coscheduled pair**; replicated serving without **readiness, not liveness**; a shard with no key; an election that failed **need a master**; FaaS used for long-running or warm-memory work; scatter/gather with unbounded leaves.

## Gotchas

1. A proxy on another host is a service, not an ambassador. Call the **coscheduled pair** test before naming sidecar / ambassador / adapter.
2. Do not bake HTTPS, metrics, log shipping, or config sync into every app image. That is a reusable container with a **container API**.
3. Do not shard to "handle load" when the service is stateless — replicate. Shard when the *state* no longer fits one machine, or when a replicated cache would store the same hot set N times.
4. Do not hash the whole request. Pick the key that groups *identical responses*. Too general serves the wrong body; too specific wrecks hit rate. Re-shard only with a consistent hash.
5. Do not elect a master because "distributed systems have leaders." Run **need a master**. Background work and two-nines SLAs take a singleton.
6. Do not treat FaaS as a universal hammer. No long jobs, no large warm indexes, no pay-per-request once a core stays busy.
7. Scatter/gather latency is the *slowest* leaf. More leaves raise straggler risk; the 99th percentile of one leaf becomes the median of a wide fan-out.
8. A message queue that deletes after consume is not Bellemare's data communication layer. If the user wants that architecture, hand off to `event-driven-microservices`.

## References

Load only the file the current step names:

- `references/single-node.md` — sidecar, ambassador, adapter
- `references/serving.md` — replica, shard, scatter/gather, FaaS, election
- `references/batch.md` — work queues, event-driven batch, join/reduce
- `references/pattern-catalog.md` — when-to / when-not-to matrix
- `assets/pattern-brief.md` — the brief template
