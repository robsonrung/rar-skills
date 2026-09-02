# Review and migrate

Read this on `existing-edm` and `migrate` jobs. For contract findings, also read `references/edm-event-contracts.md` before prescribing a fix.

## Contents

1. [Detect the current medium](#detect-the-current-medium)
2. [Smell catalog](#smell-catalog)
3. [Liberation](#liberation)
4. [One-slice migration](#one-slice-migration)
5. [Test and deploy facts that change the verdict](#test-and-deploy-facts-that-change-the-verdict)

## Detect the current medium

Find evidence, then classify what you actually have:

| Evidence | Likely medium |
| --- | --- |
| Kafka/Pulsar/Kinesis clients, compacted topics, schema registry | event broker (candidate data communication layer) |
| Rabbit/SQS/NATS with delete-on-ack, no replay | message broker (not EDM) |
| Kafka Connect / Debezium / Maxwell, no app-owned outbox | liberation in progress — or stuck |
| Shared Postgres/Mongo across services | implementation still playing the data layer |
| Nightly dumps, S3 sync, replica reads | ad-hoc data communication |

Name the current **single source of truth** as it exists today, even if it is "the monolith database." A review that skips this cannot recommend liberation.

Sample two or three facts end to end (who writes, what schema, who reads, how they project). That is enough to judge the medium.

## Smell catalog

Each smell is a `review-fix` candidate. Cite `file` / topic / connector. Skip smells you cannot evidence.

| Smell | Why it matters | Default fix |
| --- | --- | --- |
| Implicit or undocumented schema | consumers invent meaning; producer changes silently break them | explicit schema + compatibility in CI |
| Second writer on a public stream | lineage lies; **single writer** is gone | split stream or merge writers |
| Consumer reads another service's changelog/internal topic | coupled to an implementation | consume the public stream only |
| Shared materialized DB | two bounded contexts, one store | each service projects its own copy |
| Event as semaphore ("ready", payload elsewhere) | two sources of truth | put the result in the event |
| Type-overloaded schema | evolution and meaning rot | split into single-purpose streams |
| Technical service alignment (app team / data team) | one business change fans out | realign ownership to the bounded context |
| CDC dumping internal tables as public streams | consumers couple to private models | **event-first** outbox or an eventification job in a _private_ namespace, public denormalized entities |
| Connector team on the hook for producer schema breaks | tax paid in the wrong place | producing team owns the contract |
| No changelog / no rebuild story for stateful services | outage becomes archaeology | compacted changelog or snapshot+offsets |
| Choreography that must be reordered | change cost is N services + N schemas | orchestrator for that workflow only |
| Blue-green dual-produce to one output | duplicates or overwrites | full-stop or rolling update; never two writers |
| Replay would re-email / re-charge | side effects are not gated | idempotency keys or skip side effects on replay |
| Order across streams with a plain consumer | nondeterministic money/stock | lightweight/heavyweight scheduler, or don't claim determinism |

If the catalog is clean, say so. Do not invent findings.

## Liberation

Liberation publishes cross-domain data that other systems already need. It is how you _start_ a data communication layer. It is not the architecture.

Three patterns. Prefer the most **event-first** the producing team can actually ship:

| Pattern | How | Prefer when | Avoid when |
| --- | --- | --- | --- |
| **Outbox** | same DB transaction as the business write; publisher drains the table | you can change the app; you need a public contract and delete tracking | the team cannot touch the monolith |
| **Log CDC** (Debezium / WAL / binlog) | tail the store's log | low-latency, hard deletes, cannot change app code yet | the public stream would be the raw internal model with no eventification |
| **Query** | poll `updated_at` / autoincrement | any store, custom joins/views | you need hard deletes, or polling load is unacceptable |

Protocol:

- Timestamp output with the _source_ `updated_at`, not publish time.
- Schema the liberated stream like any native stream.
- Isolate the internal model: views, outbox shaping, or a private-namespace eventification job that denormalizes to a public entity.
- Serialize/validate **before** commit when using an outbox, so a bad contract rolls back the business write.
- Triggers are a last resort on ancient DBs.

Sinking (stream → existing store) is how a legacy reader joins the layer without a rewrite. The sink is invisible to that app; it is not a second source of truth.

Culture check: if the producing team will not own latency, ordering, and compatibility SLAs for the stream, liberation will rot. `hold` further slices until that ownership is real.

## One-slice migration

A migration brief names **one** slice, not a program.

1. Pick the most-shared, most-locked entity or fact (the one other systems already query or copy).
2. Name the writer that will own the public stream.
3. Name the liberation pattern and how the public contract hides the internal model.
4. Name the first consumer that will stop hitting the old store.
5. Leave the monolith running. Do not rewrite it in the same move.
6. After the first consumer is healthy, the next brief can pick the next fact.

Stop conditions for the slice: producer owns the contract; at least one consumer uses only the stream; old point-to-point path for _that_ fact is scheduled for removal.

Do not migrate request-shaped edges (login, payment vendor) onto streams just to look consistent.

## Test and deploy facts that change the verdict

These are not a testing guide. They change whether a recommendation is honest:

- If the team cannot spin an ephemeral broker + registry in CI, they cannot safely evolve schemas or topologies. Call that a tax gap.
- If a topology or state-store shape change has no rebuild path, do not recommend rolling updates — recommend full-stop + replay, and name the downstream load.
- If replay volume can melt the cluster, quotas are part of the next move, not a later polish.
- Breaking entity schemas without a new stream is not a deploy pattern; it is a contract breach.
