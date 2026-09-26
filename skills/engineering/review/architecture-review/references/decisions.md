# Decisions, capacity, and evolution

## Central test, fit for purpose

Compare benefits to a real requirement against implementation, operation, migration, and cognitive cost. Prefer the simplest option that satisfies constraints. Keeping the current architecture is a valid decision. Explain tensions among local simplicity, consistency, team autonomy, availability, and cost [B01, B02, B03].

## Deployment topology

Consider keeping the system when needs are met and growth is manageable, with an owner for accepted risks and a reassessment trigger. Consider a **Modular Monolith** when domain boundaries help but independent deployment does not. Enforce internal contracts; folders alone do not establish modularity.

Consider a monolith with workers or selected services when one workload needs isolation. Require evidence of a bottleneck or failure boundary, a contract, state ownership, and recovery. Coarse-grained services can provide autonomy without the full coordination cost of microservices.

Consider **Microservices** only when selective scaling, fault isolation, or independent delivery outweigh distributed transactions, compatibility, latency, testing, observability, and on-call cost. Identify a **Distributed Monolith** when services require coordinated releases or share intimate data dependencies. Consolidation is an option.

Consider serverless execution only after verifying duration, concurrency, latency, state, connections, cold starts, platform limits, and cost for the actual workload. No topology is automatically the next maturity level [B15, B16, W05].

For every option answer: Why now? Why not now? What evidence would change the decision? Use **smallest reversible move** in the recommendation, not merely its heading.

## Domain model and internal design

Use **Ubiquitous Language** and **Bounded Contexts** to identify model boundaries. Draw a **Context Map** that reflects actual team and integration relationships. Do not turn every table into an Aggregate or every Bounded Context into a service. Let Aggregate invariants drive transaction boundaries. Simple work may fit a **Transaction Script** better than a rich Domain Model [B05, B12].

Use an **Anticorruption Layer** when translation protects a model from another model, not as a new label for every API adapter. A **Domain Service** expresses domain behavior that has no natural home in an Entity or Value Object; an application service orchestrates a Use Case.

Compare **deep modules** against shallow wrappers. Balance local clarity with navigation and interface complexity. Apply **Component Cohesion** and **Component Coupling** to the actual release and dependency structure. REP, CCP, and CRP pull in different directions; do not present them as simultaneous absolute maxima. **Connascence** must name what must change or execute together, with degree and locality. Do not diagnose architecture by line count [B06, B07, B08, W17].

## Persistence and transactions

Keep an ORM when it helps the actual Use Cases and permits control of generated SQL, transaction boundaries, and performance. Prefer a query builder or localized SQL for complex queries where justified. Add a persistence port or Repository to protect a meaningful boundary, not to repeat the ORM API.

Changing an ORM does not fix a poor index, a long transaction, or a wrong invariant. Distinguish **Unit of Work**, **Data Mapper**, **Repository**, **ACID**, **MVCC**, **Snapshot Isolation**, and **Serializable Snapshot Isolation**. Confirm the actual engine and isolation level. Use deterministic concurrent schedules and invariant assertions for lost updates or write skew, not arbitrary sleeps [B11, B12, B13, W14, W15].

## Storage and replication, conditional depth

Activate **SSTables and LSM-Trees**, **B-Trees**, and **Column-Oriented Storage** when storage-engine behavior or OLTP/analytics separation affects the decision. Inspect access patterns, read/write/space amplification, compaction, cache effects, indexes, and operational constraints. An application assessment rarely justifies implementing a storage engine.

Activate **quorums** only for the replication protocol in use. `W + R > N` expresses overlap for fixed replica sets and successful responses under stated assumptions. It does not establish linearizability, eliminate concurrent-write conflicts, or make sloppy quorums equivalent to fixed quorums.

Connect replication-lag anomalies to the required **Read-After-Write Consistency**, **Monotonic Reads**, or **Consistent Prefix Reads** guarantee. Distinguish those session/ordering guarantees from **Linearizability** and transaction **Serializability**. Inspect failover and stale reads, not just steady state.

Use **Total Order Broadcast** and **Consensus** to examine replicated ordering and leader/commit semantics when relevant. Paxos and Raft are protocol families, not a reason to build application-level consensus. Identify exactly which histories and failure assumptions the existing system guarantees [B11, W16, W18, W19].

## Events and end-to-end correctness

Ask whether the producer needs an immediate result, how much consumer delay is acceptable, and who reconciles partial failure. Distinguish Domain Events, Integration Events, Event-Carried State Transfer, **Change Data Capture**, **Event Sourcing**, and **CQRS**. Each addresses a different need.

A durable job can be enough without a streaming platform. Recommend a **Transactional Outbox** only when local state and publication intent must commit atomically. Outbox does not by itself provide one business effect. State the retry, deduplication, retention, concurrency, transaction, and external side-effect boundaries behind any **Effectively-Once Processing** claim [B11, B14, W13].

Checkpoint: “End-to-end correctness requires [invariant] across [failure window]; the broker's delivery guarantee does not cover [external effect].”

## Capacity without invented numbers

Define workload units, offered rate, duration, distribution, payloads, tenants, bursts, and asynchronous work. Record targets and data state. Never convert active sessions to requests per second without a behavior model.

For a stable system, **Little's Law**, `L = λ × W`, relates average in-flight work to average completed throughput and average time in the same system boundary. Use seconds consistently. It does not predict maximum capacity. Do not substitute a percentile for the mean. Record assumptions and compare against measurement.

An authorized load test separates warm-up, steady state, tail latency, errors, and saturation. Record infrastructure, cold/warm caches, database size/distribution, concurrency, and duration. Do not extrapolate linearly outside the observed operating regime. Without measurements, produce a capacity experiment, not a performance improvement chart.

Separate current, agreed-growth, and optional stress scenarios from forecasts. Do not assume tenfold growth. Compare only compatible measurements, with units, evidence, environment, and target provenance.

## Economics

Compare recurring and transition costs over an explicit horizon:

`total cost = infrastructure + services/licenses + operations/maintenance + migration + estimated outage impact`

Do not add hours to money without a stated rate. Record currency, date, region, known taxes/discounts, and verified price sources. Do not invent a savings percentage. Use ranges and sensitivity analysis where evidence is weak. Include support, onboarding, observability, and coordination, not just compute bills.

## Incremental migration

Use a **seam** and **Characterization Tests** when legacy behavior is uncertain. Establish contracts before moving boundaries. Consider **Branch by Abstraction**, **Strangler Fig**, and **Expand and Contract** where applicable [B09, B10, B13, B16].

State what each **behavior-preserving** step keeps unchanged. Separate intentional behavior changes and their approval from refactoring. Include dependencies, scope, acceptance, rollout, observation, rollback, and stop conditions.

For data changes, plan compatibility, backfill, reconciliation, and forward repair when rollback would destroy valid data. Turning off a feature is not data rollback. Defer unnecessary changes with a measurable trigger, such as sustained SLO violation after local optimization or demonstrated independent-delivery needs.
