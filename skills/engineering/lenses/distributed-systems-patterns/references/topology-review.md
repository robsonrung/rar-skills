# Topology Selection and Review

Paths named below are relative to the loaded skill root.

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

## Pattern brief

Use `assets/pattern-brief.md` from this skill directory.

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

## Pattern constraints

1. A proxy on another host is a service, not an ambassador. Call the **coscheduled pair** test before naming sidecar / ambassador / adapter.
2. Do not bake HTTPS, metrics, log shipping, or config sync into every app image. That is a reusable container with a **container API**.
3. Do not shard to "handle load" when the service is stateless — replicate. Shard when the _state_ no longer fits one machine, or when a replicated cache would store the same hot set N times.
4. Do not hash the whole request. Pick the key that groups _identical responses_. Too general serves the wrong body; too specific wrecks hit rate. Re-shard only with a consistent hash.
5. Do not elect a master because "distributed systems have leaders." Run **need a master**. Background work and two-nines SLAs take a singleton.
6. Do not treat FaaS as a universal hammer. No long jobs, no large warm indexes, no pay-per-request once a core stays busy.
7. Scatter/gather latency is the _slowest_ leaf. More leaves raise straggler risk; the 99th percentile of one leaf becomes the median of a wide fan-out.
