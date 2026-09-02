# Adopt or not

Read this before naming `adopt`, `hybrid`, or `hold` on a `new-system` or `migrate` job.

## Contents

1. [What this architecture is](#what-this-architecture-is)
2. [The missing layer](#the-missing-layer)
3. [Hold vs adopt vs hybrid](#hold-vs-adopt-vs-hybrid)
4. [Microservice tax](#microservice-tax)
5. [Synchronous microservices are not the fallback default](#synchronous-microservices-are-not-the-fallback-default)

## What this architecture is

Event-driven microservices (EDM) here means: services aligned to business bounded contexts communicate by publishing and consuming **replayable, schematized events** on an event broker. Events stay after consume. Any consumer can rebuild state from the log.

That is not:

- a message queue used as async RPC
- "we put Kafka in front of the monolith"
- a fleet of REST services that happen to emit logs

If the design cannot name the **data communication layer** — the streams that are the **single source of truth** for shareable domain data — verdict is `hold` or the design is incomplete.

## The missing layer

Three communication structures exist in every org:

| Structure | Job | Failure mode when it is missing |
| --- | --- | --- |
| Business | who owns which requirement | teams reorganize, implementations cannot |
| Implementation | logic + private state of one product | grows into a monolith because data is local |
| Data | how other products get domain facts | ad-hoc copies, shared DBs, stale dumps |

EDM exists to install the data structure. Producers own production. Consumers own modeling and queries. Implementations stop serving other teams' data access.

Conway follows the data path. If getting another system's data is harder than adding a feature to the current service, the team will enlarge the monolith. That is evidence for EDM only if the org will actually publish those facts as streams.

## Hold vs adopt vs hybrid

Score the unit of decision (whole company, one product, one bounded context). Do not score "the industry."

**`hold`** — keep a modular monolith or the current style — when:

- one team, one product, one data store, and no second consumer in the planning horizon
- the pain is request latency or CRUD, not locked domain data
- nobody will operate a broker, schema registry, and self-serve deploy/reset path
- leadership will not accept streams as authoritative (analytics dump only)

**`adopt`** when most shareable domain facts will live on streams and new work will compose from those streams. Rare as a whole-org flip; treat it as a direction, not a cutover.

**`hybrid`** (default yes) when some facts belong on streams _and_ request-response remains for:

- user/mobile/web experiences
- auth, feature flags, third-party APIs
- queries that must answer in tens of milliseconds from a purpose-built store

A `hybrid` brief must name which facts go on the data communication layer and which stay request-shaped. "We'll event-drive everything later" is `hold` wearing a costume.

## Microservice tax

The tax is paid once, centrally, or every team pays a worse version.

Minimum platform before recommending more than one or two event-driven services:

- event broker with partitions, retention, replay, and quotas
- schema registry with compatibility checks in CI
- container/function deploy with owner-driven rollback
- consumer-group offset reset and state wipe, owner-only
- ACLs that can enforce **single writer**
- ownership map: team → service → streams

If two or more of those are missing and there is no funded plan, `hold` on further decomposition. One well-liberated stream feeding a modular monolith is cheaper than twenty unmanaged topics.

Small orgs: prefer one modular monolith that _publishes_ the important entities. That still installs a data communication layer without paying the full tax.

## Synchronous microservices are not the fallback default

If EDM is `hold`, the usual better alternative is a **modular monolith** (or a few coarse services), not a mesh of request-response microservices. Sync microservices keep data access tied to implementations and add fan-out, coupled scaling, and distributed-monolith risk.

Use sync calls where they are the native shape (the UI, the payment vendor). Do not use them as the organization's data bus.
