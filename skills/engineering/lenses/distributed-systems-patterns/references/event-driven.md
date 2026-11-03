# Event-driven

Event-driven microservices here means services aligned to business bounded contexts that share domain facts through replayable, schematized streams that persist after consume. Not a queue used as async RPC, not "Kafka in front of the monolith." Bounded-context alignment itself belongs to `domain-driven-design`; services split along technical layers are a defect.

| Sub-route | Signal | Path |
| --- | --- | --- |
| `new-system` | Greenfield, "should we use Kafka", first service on a broker | Adopt gate, then contracts, then style per bounded context |
| `existing-edm` | Broker clients, topics, schemas already in the repo | Smell table; verdict `review-fix` unless clean |
| `migrate` | Shared databases, batch syncs, "liberate this" | Adopt gate, then one liberation slice |

## Adopt gate

Run before any design on `new-system` and `migrate`. Score the unit of decision (company, product, or one context), not the industry.

`hold` if any holds: the org won't treat streams as the **single source of truth** (the monolith database stays authoritative, streams are a dump); nobody will pay the platform tax below; no second team or product needs the same domain data in near real time; the work is request-shaped (auth, profile fetch, third-party HTTP). On `hold`, stop; don't design topics. The usual better alternative is a modular monolith or a few coarse services, not a mesh of synchronous microservices, which keeps data access tied to implementations.

`hybrid` is the default when adopting: some facts go on streams; request-response stays for UIs, auth, feature flags, third parties, and queries that must answer in milliseconds. The brief names which facts go where. "We'll event-drive everything later" is `hold` in a costume. `adopt` across a whole org is a direction, not a cutover.

The tax, paid once centrally or worse by every team: broker with partitions, retention, replay, and quotas; schema registry with compatibility checks in CI; owner-driven deploy and rollback; owner-only offset reset and state wipe; ACLs that enforce **single writer**; a team-to-service-to-stream ownership map. With two or more missing and no funded plan, hold further decomposition. One well-liberated stream feeding a modular monolith beats twenty unmanaged topics. Small orgs: a modular monolith that publishes its important entities still installs a **data communication layer**.

## Detect the current medium

| Evidence | Medium |
| --- | --- |
| Kafka, Pulsar, or Kinesis; compacted topics; schema registry | Event broker (candidate layer) |
| Rabbit, SQS, or NATS with delete-on-ack, no replay | Messaging, not event-driven |
| Debezium or Connect with no app-owned outbox | Liberation in progress, or stuck |
| Shared Postgres or Mongo across services | The implementation is still the data layer |
| Nightly dumps, S3 syncs, replica reads | Ad hoc data communication |

Name today's source of truth, even if it is the monolith database.

## Smells

Cite the file, topic, or connector; skip what you can't evidence.

| Smell | Default fix |
| --- | --- |
| Implicit or undocumented schema | Explicit schema with compatibility checked in CI |
| Second writer on a public stream | Split the stream or merge the writers into one context; never "coordinate harder" |
| Consumer reads another service's changelog or internal topic | Consume the public stream only |
| Shared materialized database | Each consumer projects its own copy |
| Event as semaphore ("ready," payload elsewhere) | Put the result in the event |
| One schema overloaded by a `type` field | Single-purpose streams |
| CDC publishing internal tables as public streams | **Event-first** outbox or a private eventification job emitting denormalized public entities |
| Connector team owns the producer's schema breaks | The producing team owns the contract |
| Stateful service with no changelog or rebuild story | Compacted changelog, or snapshot plus offsets |
| Choreography that keeps being reordered | An orchestrator for that workflow only |
| Blue-green deploy dual-producing one output | Full stop or rolling update; never two writers |
| Replay re-sends email or re-charges cards | Gate side effects on replay |
| Cross-stream order assumed with a plain consumer | An event-time scheduler, or stop claiming determinism |

## Contracts

- Entity streams (keyed by the thing's id, latest value is current) are what other contexts materialize; spend design time there. A consumer that needs "current X" needs an entity stream or compacted changelog, not an unkeyed firehose.
- Explicit schema (Avro, Protobuf, Thrift) plus the triggering logic in its header. JSON without a compatibility framework is not a contract. Default to full compatibility; loosening later is cheap, tightening is not.
- The event is the whole fact, one definition per stream, narrowest types, at least one real consumer in the design. No signal-only business events.
- A breaking change is a domain redefinition: the producer writes a new stream (rebuilding every entity for entity streams), consumers move, the old stream ages out. Never write two incompatible schemas into one stream.

## Liberation and migration

Liberation publishes data other systems already need; it starts the layer and is not the architecture. Prefer the most event-first pattern the team can ship: an outbox in the business write's transaction (write mechanics → `data-systems-coding-lens`); log CDC when the app can't change yet; polling queries when nothing else works and hard deletes don't matter. Timestamp with the source `updated_at`, and hide the internal model behind a public entity. CDC is a bootstrap, never the destination for a core entity. If the producing team won't own latency, ordering, and compatibility for the stream, hold further slices.

A migration brief names one slice: the most-shared, most-locked fact, its future single writer, the liberation pattern, and the first consumer that stops reading the old store. Leave the monolith running. The slice is done when the producer owns the contract and one consumer uses only the stream. Don't move request-shaped edges onto streams for consistency.

## Implementation

- Pick a style per bounded context: a lightweight stream library for long-running stateful services; a heavyweight cluster only for large windowed analytics that already have one; a basic producer and consumer or FaaS only where cross-stream arrival order doesn't matter.
- Deterministic replay needs producer-assigned event time, a scheduler dispatching the oldest timestamp across partitions, and a late-event policy the business chose.
- Never share a state store across services. Keep changelogs on the broker. When the topology or stored shape changes, rebuild from inputs and plan for the replay load.
- Choreography by default for independent workflows; orchestration when the sequence changes or needs visibility. The orchestrator only sequences; workers own their rules and retries. A saga is the last resort, orchestrated rather than choreographed, and compensation (refund, delay, discount) often beats a distributed rollback. Don't recommend a distributed transaction when compensation will do.
- Write the event first, then materialize, when others must share the fact; accept read-after-write lag.
