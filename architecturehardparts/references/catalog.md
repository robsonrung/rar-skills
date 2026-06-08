# Architecture Decision Catalog

Use this catalog only after the main workflow identifies the decision type.

## Coupling And Architecture Quantum

Architecture quantum means a unit that can be reasoned about as a deployable architectural part. Use it to test whether a proposed boundary is real.

Check four properties:

1. Independent deployability
2. High functional cohesion
3. High static coupling inside the unit
4. Dynamic coupling to other units through communication, consistency, and coordination

If a service boundary still requires the same database, the same release train, the same shared mutable model, or synchronous coordination for most work, the boundary may not create a useful quantum.

## Modularity Drivers

Use these forces to justify pulling code apart:

1. Maintainability improves because changes become easier to locate and isolate.
2. Testability improves because the unit has a smaller behavioral surface.
3. Deployability improves because release scope and deployment risk shrink.
4. Scalability improves because high demand functions can scale alone.
5. Availability and fault tolerance improve because failures stop spreading across unrelated behavior.

## Component Decomposition

Use this sequence when splitting a monolith or a large module:

1. Identify and size components around cohesive behavior.
2. Gather common domain components when repeated domain concepts are scattered.
3. Flatten orphan components that exist only as pass through wrappers or accidental layers.
4. Determine dependencies before moving code.
5. Create component domains when components naturally cluster around business areas.
6. Create domain services only after component domains are clear enough to support runtime boundaries.

Use tactical forking only when the current code shape is tangled and the target extraction is concrete. Fork the code for a bounded time, remove unrelated parts, then converge on the extracted module or service.

## Data Decomposition

Data disintegrators justify breaking data apart:

1. Change control problems caused by many services depending on the same schema.
2. Connection saturation from many service instances sharing one database.
3. Scalability limits caused by a database that cannot scale with services.
4. Fault tolerance problems caused by one database outage stopping too much of the system.
5. Architecture quantum problems caused by one shared database forcing one architectural unit.
6. Database type mismatch where one store is poor for all data shapes.

Data integrators justify keeping data together:

1. Strong table relationships such as foreign keys, triggers, views, and stored procedures.
2. Required ACID transactions across the data.

A safe decomposition path is iterative: define data domains, assign tables, separate connections, move schemas, then switch to independent servers only when the tests and migrations prove the boundary.

## Service Granularity

Granularity disintegrators justify smaller services:

1. Weak cohesion or a service that is hard to name.
2. Code volatility isolated to one part of the service.
3. Different scaling or throughput needs.
4. Failure in one function should not take down another.
5. Security requirements differ by function or data access.
6. Planned extensibility means new variants will keep appearing.

Granularity integrators justify larger services:

1. A single ACID transaction is required.
2. Workflow chatter between split services dominates the request.
3. Shared domain code changes often or cannot be versioned safely.
4. Data relationships force repeated cross service reads or writes.

Balance both sides. The right size is the boundary where the most important driver wins with acceptable consequences.

## Reuse Choices

Code replication can be acceptable when duplication protects independent deployability, the logic is small, or the variants are likely to diverge.

Shared library works well for stable common logic with controlled versioning. It can create coordinated deployment pressure when shared domain behavior changes often.

Shared service works well when the behavior is a runtime capability that needs independent ownership, operational scaling, or centralized policy. It adds latency, availability dependency, and contract management.

Sidecar or service mesh works best for operational concerns such as observability, routing, retries, security policy, or traffic control. Avoid using it to hide unclear domain ownership.

## Data Ownership

Single ownership is simplest: one service writes the data and others request through a contract.

Common ownership is risky: multiple services write the same data and change control becomes difficult.

Joint ownership needs a resolution technique:

1. Table split when different services own different columns or concerns.
2. Data domain when a larger domain boundary clarifies ownership.
3. Delegate when one service owns writes and another delegates through it.
4. Service consolidation when ownership cannot be separated without damaging consistency or workflow.

## Distributed Transactions And Eventual Consistency

ACID fits a single database transaction. Distributed business requests usually move to BASE behavior: basic availability, soft state, and eventual consistency.

Use background synchronization when the systems are loosely connected and slow consistency is acceptable. Watch for duplicated business logic and broken bounded contexts.

Use orchestrated request based consistency when the user must wait for the whole business request and a coordinator can own the process. Watch for slower response and difficult compensation.

Use event based consistency when responsiveness, decoupling, and short eventual consistency windows matter. Watch for error handling, durable subscribers, replay, idempotency, and dead letter handling.

## Workflow Coordination

Orchestration centralizes workflow state and is easier to reason about. It can concentrate coupling and become a performance or availability dependency.

Choreography decentralizes control and can scale better. It can hide workflow state, spread logic across services, and increase stamp coupling because events carry more data than receivers need.

Choose by asking who owns state, who handles errors, how much coupling is acceptable, and whether the workflow needs a visible coordinator.

## Saga Analysis

Analyze sagas through three axes:

1. Communication: synchronous or asynchronous
2. Consistency: atomic or eventual
3. Coordination: orchestrated or choreographed

High atomicity plus high distribution usually increases coupling and compensation complexity. Asynchronous eventual patterns usually improve scale and responsiveness, but require idempotency, state tracking, replay handling, and clearer error operations.

Use the pattern names from the book only as shorthand. The decision should be explained by the axes and tradeoffs, not by the name alone.

## Contracts

Strict contracts provide stronger guarantees and clearer compatibility checks. They can slow change and require coordinated versioning.

Loose contracts support extensibility and consumer flexibility. They can hide breakage until runtime.

Stamp coupling happens when a workflow passes more data than the receiver needs. Reduce it by passing minimal contracts, explicit identifiers, or purpose built events.

## Analytical Data

Separate operational data decisions from analytical data decisions. Operational data protects business execution. Analytical data supports reporting, prediction, and strategic insight.

Data mesh can help when analytics ownership should align with business domains and data products. It is not a shortcut for unclear operational data ownership.

## Tradeoff Analysis Technique

1. Find the entangled dimensions.
2. Model the relevant coupling points.
3. Compare feasible options with a short qualitative scale.
4. Keep the comparison mutually exclusive and collectively complete.
5. Avoid out of context scoring.
6. Model concrete domain scenarios.
7. Present the bottom line in stakeholder outcomes.
8. Guard the decision with tests, checks, monitors, or architecture fitness functions.
