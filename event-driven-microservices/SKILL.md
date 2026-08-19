---
name: event-driven-microservices
description: >
  Decide whether to adopt, keep, or migrate to event-driven microservices, then
  review the design or codebase against event-stream contracts, single-writer
  ownership, and data-liberation discipline. Use when designing a new
  event-driven system, reviewing Kafka/Pulsar/Kinesis/EventBridge/event-stream
  architecture, choosing choreography vs orchestration, designing event schemas,
  planning CDC/outbox data liberation, or asking "should we use events / Kafka /
  event-driven microservices". Distinct from macro-architecture (whether
  event-driven is the right style), domain-driven-design (bounded-context
  modeling without broker/stream contracts), data-systems-coding-lens
  (code-level retries/migrations, not the adopt/migrate decision), and
  distributed-systems-patterns (Burns container/replica/shard/queue
  topology, not the stream-as-source-of-truth decision).
---

# Event-Driven Microservices

Read-only decision skill. Do not implement the architecture unless the user asks after the brief.

Grounded in Bellemare: a durable, replayable **data communication layer** of schematized event streams, not point-to-point messages that vanish after consume.

## Outcome

- **Result:** a decision brief with one verdict and the next concrete move.
- **Next consumer:** the user, or a planning skill after they accept the verdict.
- **Done:** every required brief field is filled; every load-bearing claim cites repo evidence or is marked `assumed`; rejected alternatives are named; the next move is one action, not a roadmap.
- **Intent:** stop two failures — adopting EDM when a modular monolith is cheaper, and building EDM without a data communication layer (implicit schemas, shared DBs, CDC as the destination).

Verdicts: `adopt` | `hybrid` | `hold` | `review-fix` | `migrate-slice`

State these four **leitwörter** by name as you decide, not only in headings:

- **data communication layer** — durable, replayable streams that decouple producing data from accessing it. If this is not being built, this is not Bellemare EDM.
- **single source of truth** — the stream is the fact; local stores are projections that can be rebuilt.
- **single writer** — one service owns writes to a stream.
- **event-first** — the public event is a first-class product. CDC/outbox bootstraps liberation; it is not the destination.

## Classify the job

Pick one route from the user's ask and the repo, then stay on it:

| Route | Signal |
|---|---|
| `new-system` | Greenfield, "should we use events/Kafka", first service on a broker |
| `existing-edm` | Broker clients, topics, schemas, stream processors already in the repo |
| `migrate` | Monolith/SOA with locked data, batch syncs, shared DBs, "liberate this" |

If the ask is only "microservices or monolith" with no event/broker/stream language, stop and say this skill does not apply — that is `macro-architecture`.

## Evidence

Capability first: inspect the live system (or the stated requirements if there is no repo). Do not invent a topology.

Search for broker clients, topic/stream names, schema files, outbox/CDC connectors, consumer groups, changelogs. Sample two or three streams end to end — producer, schema, consumers — rather than listing every topic.

Read budget: enough to name owners, contracts, and the current source of truth. Stop when another file would not change the verdict.

If there is no repo, use the user's constraints (team size, shared data, tax they will pay). Mark those `assumed`.

## Adopt gate

Run this gate on `new-system` and `migrate` before any design. Read `references/adopt-or-not.md` before naming the verdict.

**`hold`** if any of these is true:

1. The org will not treat streams as the **single source of truth** (the monolith DB stays authoritative and streams are a dump).
2. The **microservice tax** (broker, schema registry, deploy/reset tooling, ownership) will not be paid centrally in the planning horizon.
3. No second team or product needs the same domain data in near real time.
4. The work is request-shaped (auth, fetch-a-profile, third-party HTTP) with no shareable narrative.

**`adopt`** or **`hybrid`** only when shared domain data is locked in an implementation *and* the tax will be paid. **`hybrid` is the default** when adopting — request-response stays for UIs, auth, and third parties.

On `hold`, write the brief and stop. Do not design topics.

## Routes

**`new-system`** — after a non-hold gate, read `references/event-contracts.md`, then `references/implementation-styles.md`. Design the data communication layer first (streams, schemas, writers), then pick one implementation style per bounded context.

**`existing-edm`** — read `references/review-and-migrate.md` and walk the smell catalog against repo evidence. For every contract finding, load `references/event-contracts.md` before prescribing a fix. Verdict is `review-fix` unless the system already satisfies the catalog.

**`migrate`** — after a non-hold gate, read `references/review-and-migrate.md`. Pick **one** liberation slice: the most-shared, most-locked domain data. Name the liberation pattern and why it is **event-first** enough. Do not plan a rewrite.

## Decision brief

Emit the brief inline using `assets/decision-brief.md`. Write a file only when the user asks to record it, or when the project's active instructions already require ADRs for this class of decision — then follow that convention, otherwise `docs/decisions/edm-YYYYMMDD-<slug>.md`.

Required fields (protocol — omitting one means the brief is not done):

1. `job` — route + one-sentence decision
2. `verdict`
3. `data_communication_layer` — what is (or would be) the stream-backed source of truth; or why there isn't one
4. `single_writer` — producer per public stream, or the violation
5. `evidence` — files, topics, schemas, or `assumed: …`
6. `rejected` — at least one alternative and the cost of taking it
7. `next_move` — one action (liberate *this* entity, add *this* schema, stop *this* second writer)
8. `not_this_skill` — adjacent work that belongs to `macro-architecture`, `domain-driven-design`, `data-systems-coding-lens`, or `distributed-systems-patterns`

When invoked as a design-gate lens, also return `verdict: proceed|revise`, `blocking_findings`, `advisory_findings`, `required_changes`. A missing data communication layer, a second writer on a public stream, or CDC-as-destination on a core entity is `revise`.

## Gotchas

1. A message queue that deletes after consume is not a data communication layer. Call that messaging, not EDM.
2. Do not split services to look "micro." Align on a business bounded context. Technical layers as services are a defect.
3. Do not share a materialized store across services. Each consumer projects its own copy.
4. Do not mix incompatible event types in one stream to "save topics."
5. Do not dual-produce two versions of a service onto the same output stream (blue-green on a reacting producer).
6. Do not treat connector-based CDC as the finished architecture.
7. Do not recommend a distributed transaction when a compensation workflow will do.
8. Hybrid is expected. An all-event architecture is almost never the answer.

## References

Load only the file the current step names:

- `references/adopt-or-not.md` — adopt gate, tax, when hold is correct
- `references/event-contracts.md` — event shapes, schema rules, breaking changes
- `references/implementation-styles.md` — FaaS / BPC / heavy / light, workflows, state
- `references/review-and-migrate.md` — smell catalog, liberation patterns, one-slice migration
- `assets/decision-brief.md` — the brief template
