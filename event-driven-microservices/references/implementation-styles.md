# Implementation styles

Read this after the data communication layer is named and the adopt gate is not `hold`. Pick a style per bounded context, not one framework for the company.

## Contents

1. [Topologies](#topologies)
2. [Time and determinism](#time-and-determinism)
3. [State](#state)
4. [Style picker](#style-picker)
5. [Workflows](#workflows)
6. [Request-response edges](#request-response-edges)

## Topologies

- **Microservice topology** — the processing graph *inside* one service (filter, join, emit).
- **Business topology** — services + public streams + APIs that fulfill a workflow.

Design the business topology as composition of streams. Do not design a call graph and then "add Kafka."

## Time and determinism

If replaying from offset 0 must reproduce the same outputs, the service needs:

- **event time** on the record (producer-assigned), not wall-clock
- an **event scheduler** that always dispatches the oldest timestamp across assigned partitions
- a late-event policy the business named: drop, wait, or emit-then-update during a grace window

Basic consumer clients and most FaaS triggers do **not** ship a scheduler. If order across streams matters (deposits vs withdrawals), do not pick BPC/FaaS unless you will build that scheduler — and you should not.

Windows (tumbling / sliding / session) are time-based business logic. Late events are a product decision.

Side effects on replay (re-email, re-charge) must be gated. If they cannot be, the service is not safely replayable; say so in the brief.

## State

**Materialized state** is a projection of a stream. **State store** is the service's own mutable working set. Both exist; do not conflate them.

| Store | Use | Cost |
|---|---|---|
| Internal (e.g. RocksDB in the instance) | high-throughput keyed joins/aggs; restore from compacted changelog | disk follows the instance; rebuild on rebalance unless hot replicas |
| External (DB, search, geo) | query shapes the broker cannot serve; FaaS/BPC | network latency; the *owning team* runs it |

Rules:

- never share the store with another service
- global materialization (every instance has the full table) is for small lookup data, not for driving emits (duplicates)
- changelogs belong on the broker so a crashed instance can rebuild without replaying all inputs
- "effectively once" is offset + state + output committed together (broker transactions) or offsets stored in the same DB transaction as state. At-least-once plus idempotent writes is the fallback.

Rebuild from inputs when the topology or stored shape changes. Migrate the store only when the business will not replay history — and test the migration against a rebuild.

## Style picker

Default: **lightweight** (Kafka Streams / embedded Samza-class) for a long-running stateful business service on Kafka.

| Style | Pick when | Do not pick when |
|---|---|---|
| **Lightweight** | keyed joins, indefinite tables, changelog restore, deploy like any container | you are not on Kafka, or the team cannot run a JVM library |
| **Heavyweight** (Flink / Spark / Beam) | large windowed/session analytics, existing data-platform cluster | this is a request-serving product service and you would add a cluster just for it |
| **BPC** (plain producer/consumer) | sidecar into a legacy app; gating where arrival *order* does not matter; the data layer does the work | multi-stream event-time order, local state scale-out |
| **FaaS** | bursty, short, stateless or external-state; queue-shaped work | copartitioned joins, long local state, commit-offset-before-work frameworks |

A hybrid BPC that outsources a join to KSQL/Flink is allowed. Treat the pair as **one** bounded context and one deployable story, or you will orphan jobs.

## Workflows

**Choreography** — services react to public events. Default for *independent* business workflows and for inter-team composition. Fragile when you must reorder the middle of a chain or see "where is order 123."

**Orchestration** — one service owns *only* workflow sequencing and talks to workers that own their business rules. Default when the sequence changes, needs visibility, or is a saga. A god-orchestrator that retries payments is a boundary leak.

**Saga** — last resort for a write that spans services. Prefer not to. If required, orchestrated saga over choreographed: one output stream, one writer, one place to watch.

**Compensation** — oversell, delay, discount, refund. Often cheaper than a distributed rollback. Name it when the business already handles the failure that way.

Worker rule: the worker decides how to succeed or fail its own job (retries included). The orchestrator only hears done / failed.

## Request-response edges

Inbound autonomous events (mobile metrics): schematize on the client, ingest via HTTP, route to streams. Plan for many in-field schema versions.

Outbound third-party calls inside a topology are nondeterministic. Throttle replays. Record the response as an event if downstream accounting needs it.

Serving state over HTTP:

- sharded internal state → route by key → partition → owner; instances must still redirect
- external store → any instance can answer; processor and API may be two processes, still one bounded context

Prefer **write the event first**, then materialize, when other services must share that fact. Accept read-after-write lag or keep the just-written value in memory for the caller.

Micro-frontends compose the same way backends do: each product slice materializes what it needs. Do not put business logic in the stitch layer.
