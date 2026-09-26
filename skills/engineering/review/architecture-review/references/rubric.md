# Architecture assessment rubric

Report all 20 dimensions, with depth proportional to applicability and risk. This is a practical synthesis, not a scientific scoring scale or certification. Preserve working mechanisms as well as identifying risks. Use `adequate`, `attention`, `critical`, `unknown`, or `not_applicable` with confidence, evidence, and reasons. Do not average away a critical risk or convert unknown into zero.

Each checkpoint below is a question, not a conclusion. The answer must invoke the applicable canonical concept in the finding or decision, connect it to evidence, and constrain an action or check. Read detailed definitions only when needed in `terminology.md`.

## D01. Fitness for purpose and sufficiency

**Investigate:** Confirm purpose, stage, criticality, workload, team, cost of failure, and expected lifetime. Judge current adequacy separately from unknown future capacity. Look for requirements already met, unnecessary complexity, and unsupported requirements. A small stable product may already be sufficient.

**Decision checkpoint:** Which Quality Attribute Scenario makes this design fit for purpose, and what evidence limits that conclusion?

**Useful evidence:** Requirements, stakeholder statements, incidents, workload measurements, and explicit constraints.

**Source lenses:** B01, B02, W01.

## D02. Domain model and Bounded Contexts

**Investigate:** Establish Ubiquitous Language, subdomains, Bounded Contexts, and an evidence-backed Context Map. Inspect invariants, ownership, and write paths. Within a context, evaluate Tactical Building Blocks: Entities, Value Objects, Aggregates and Aggregate Roots, Domain Services, Repositories, Factories, and Specifications where justified. Check Side-Effect-Free Functions and Intention-Revealing Interfaces. Distinguish Strategic Design from mandatory tactical ceremony.

**Decision checkpoint:** Where does the Bounded Context change model meaning, and does an Anticorruption Layer protect that meaning at an external boundary?

**Useful evidence:** Business flows, vocabulary, public contracts, aggregate mutation paths, data ownership, and context relationships.

**Source lenses:** B05, B16, W10.

## D03. Component Cohesion and Component Coupling

**Investigate:** Map imports, dependency cycles, internal access, shared state, public exports, and recurring changes across components. Apply Component Cohesion through REP, CCP, and CRP and Component Coupling through ADP, SDP, and SAP. Check The Dependency Rule against source dependencies, not runtime arrows. Use Main Sequence and Distance only with meaningful counting conventions. Analyze connascence by its actual form, degree, and locality.

**Decision checkpoint:** Which component principle explains the observed change cost, and what contract or architectural fitness function would protect the boundary?

**Useful evidence:** Actual dependency graph, composition roots, callers, package releases, and change history when available.

**Source lenses:** B06, B08, B04, W11, W17, W20.

## D04. Code design and refactorability

**Investigate:** Inspect names, intent, contracts, side effects, duplication of knowledge, cohesive functions, error behavior, and empty abstractions. Balance SOLID, DRY, KISS, and YAGNI rather than applying them as absolute rules. Compare deep modules with shallow wrappers. Prefer explicit behavior to unjustified inheritance, indirection, and metaprogramming. Identify seams and enabling points before changing difficult legacy code.

**Decision checkpoint:** Which seam allows a behavior-preserving change, and does the proposed abstraction actually reduce caller knowledge?

**Useful evidence:** Representative implementations, callers, negative cases, and tests, not lint metrics alone.

**Source lenses:** B07, B08, B09, B10, W12.

## D05. Deployment topology

**Investigate:** Identify Monolith, Modular Monolith, coarse-grained services, microservices, functions, and hybrids. Separate logical modules from deployments. Assess actual needs for independent ownership, selective scaling, failure isolation, and release autonomy. Detect coordinated deployment and data dependencies that may create a Distributed Monolith. Consider consolidation as well as decomposition.

**Decision checkpoint:** Is the Modular Monolith fit for purpose, or does demonstrated autonomy or load justify selective extraction?

**Useful evidence:** Deployment manifests, runtime calls, transaction boundaries, ownership, and operational capability.

**Source lenses:** B02, B03, B15, B16, W05.

## D06. APIs and integration

**Investigate:** Assess contract semantics, schemas, input validation, authentication, object and tenant authorization, pagination, rate limits, errors, idempotency, compatibility, and versioning. Compare REST, GraphQL, RPC, webhooks, and streams by the actual use case. Inspect persistence-model leakage, excessive round trips, timeouts, and external failure. Verify current technology details rather than choosing by novelty.

**Decision checkpoint:** Does the Intention-Revealing Interface distinguish accepted, committed, and externally confirmed outcomes?

**Useful evidence:** Schemas, handlers, clients, contract tests, compatibility policy, error mappings, and measurements.

**Source lenses:** B12, B14, B15, W10.

## D07. Data modeling and integrity

**Investigate:** Inspect keys, constraints, types, money precision, time zones, relations, cardinality, indexing, and write ownership. Balance normalization and denormalization against queries and invariants. Review tenant isolation, retention, deletion, compatible migrations, backfills, and restore procedures. Consider B-Trees, SSTables and LSM-Trees, or Column-Oriented Storage only when engine and workload evidence make them relevant.

**Decision checkpoint:** Which invariant is enforced by the Aggregate or database, and how does Expand and Contract preserve it during migration?

**Useful evidence:** Schema, migrations, queries, representative data distribution, engine configuration, and recovery plans.

**Source lenses:** B11, B13.

## D08. Persistence, ORM, and concurrency

**Investigate:** Trace the Unit of Work, transaction boundaries, generated SQL, N+1 queries, lazy loading, batching, pools, pagination, and ORM leakage. Compare ORM, query builder, and explicit SQL without assuming one wins. Do not add a Repository that merely duplicates an adequate ORM. Inspect ACID guarantees, actual isolation, lost updates, write skew, locks, deadlocks, uniqueness, and optimistic or pessimistic concurrency. Distinguish MVCC, Snapshot Isolation, Serializability, and SSI using the actual database version.

**Decision checkpoint:** What invariant can concurrent transactions violate, and does the configured isolation or locking protocol prevent it?

**Useful evidence:** Queries, transactions, constraints, authorized plans, contention data, retry behavior, and controlled concurrency tests.

**Source lenses:** B11, B12, W14, W15.

## D09. Events and distributed consistency

**Investigate:** Distinguish Domain Events, Integration Events, notifications, event-carried state transfer, CDC, Event Sourcing, and CQRS. Check the database/message dual-write gap, Transactional Outbox, retries, duplicates, ordering, dead-letter queues, replay, compensation, schema evolution, and tracing. Evaluate Effectively-Once Processing only within an explicit effect boundary. Inspect quorums, Replication Lag Anomalies, Total Order Broadcast, and Consensus only where the actual architecture uses or requires them.

**Decision checkpoint:** Does end-to-end correctness survive partial failure, replay, reordering, and concurrent duplicates?

**Useful evidence:** Producers, consumers, storage transactions, sink contracts, recovery traces, and final business effects.

**Source lenses:** B11, B14, B03, W13, W16, W18, W19.

## D10. Capacity, performance, and scalability

**Investigate:** Separate offered load from completed throughput. Examine percentiles, error rates, saturation, queues, contention, CPU, memory, I/O, connections, and data skew. Check algorithms, query plans, indexing, batching, caching, pools, replicas, and vertical scaling before services or sharding. Do not extrapolate linearly outside the measured operating range. For replicated reads, consider Read-After-Write, Monotonic Reads, and Consistent Prefix Reads alongside latency.

**Decision checkpoint:** Which measured resource or waiting time limits the Quality Attribute Scenario, and what is the smallest reversible move to test?

**Useful evidence:** Authorized representative load tests, telemetry, profiling, query behavior, and workload conditions.

**Source lenses:** B01, B11, B21.

## D11. Reliability and recovery

**Investigate:** Inspect timeouts, cancellation, retry budgets, circuit breakers, bulkheads, bounded queues, load shedding, readiness, graceful shutdown, and degraded operation. Assess restore evidence, RTO/RPO, migration failure, and partial recovery. Backup configuration is not proof of restoration. Avoid costly availability mechanisms without an agreed requirement.

**Decision checkpoint:** Which failure leaves a recoverable state, and what end-to-end correctness check demonstrates recovery?

**Useful evidence:** Failure scenarios, runbooks, incident evidence, and recovery tests in an authorized safe environment.

**Source lenses:** B20, B21.

## D12. Security and privacy

**Investigate:** Map trust boundaries, external surfaces, authorization by object and tenant, untrusted input, injection, uploads, SSRF, secrets, supply-chain exposure, least privilege, and audit trails. Verify encryption, minimization, retention, and supported dependencies as applicable. Identify declared compliance requirements without claiming certification or giving a legal conclusion. Sanitize all evidence.

**Decision checkpoint:** Which trust boundary and negative test demonstrate the stated protection rather than merely the presence of a library?

**Useful evidence:** Implementation, sanitized configuration, applicable policies, and explicitly authorized checks.

**Source lenses:** B01, B21, B22.

## D13. Testing and testability

**Investigate:** Distinguish Unit, Integration, Contract, Component, End-to-End, Property-Based, concurrency, and load tests. Examine behavioral assertions, isolation, fixtures, test doubles, feedback time, and brittleness. Use Characterization Tests before uncertain legacy restructuring and the Humble Object Pattern when useful. Protect test oracles from changes made merely to make a test pass. High coverage with weak assertions is not sufficient.

**Decision checkpoint:** What deterministic oracle catches the important regression, and can the test fail for the right reason?

**Useful evidence:** Read tests, actual executions, negative cases, false positives, and all flaky attempts.

**Source lenses:** B10, B17, B18, B22.

## D14. Build, delivery, and dependencies

**Investigate:** Review lockfiles, pinned runtimes, reproducible builds, environments, CI automation, traceability, migration compatibility, rollout, and rollback. Compare local and CI behavior and feedback time. Inspect unsupported dependencies, upgrade effort, and release policies. Do not execute dependency or install scripts automatically.

**Decision checkpoint:** Which architectural fitness function or pipeline gate enforces the actual requirement with actionable failure output?

**Useful evidence:** Manifests, pipelines, artifacts, environment recipes, and available delivery history.

**Source lenses:** B19, B22, B04.

## D15. Observability and operations

**Investigate:** Inspect structured logs, request and business correlation, product and service metrics, useful traces, actionable alerts, and runbooks. Consider cardinality and sensitive-data leakage. A tracing package does not prove useful instrumentation. Follow one diagnostic path from user symptom to responsible component and recovery action.

**Decision checkpoint:** Can end-to-end correctness be diagnosed from the persisted state and correlated attempts after a partial failure?

**Useful evidence:** A complete diagnostic journey and the sanitized evidence available to an operator.

**Source lenses:** B20, B21.

## D16. Economics and total cost

**Investigate:** Include compute, database, storage, network, observability, licenses, maintenance, incidents, onboarding, and migration. State the horizon and meaningful cost unit, such as completed order or active customer. Use sanitized bills and verified prices when available; otherwise provide qualitative scenarios. Separate recurring cost from migration investment and disclose uncertain labor assumptions.

**Decision checkpoint:** Is the proposed change fit for purpose when migration and operating costs are included?

**Useful evidence:** Sanitized bills, consumption, measured effort or explicit assumptions, and sensitivity analysis.

**Source lenses:** B01, B03, B21.

## D17. User interface and experience

**Investigate:** For a UI, assess local versus server state, contracts, navigation, component boundaries, errors, accessibility, loading states, and perceived performance. Inspect excessive dependencies and calls. For mobile or offline behavior, include synchronization and connectivity failure. Mark not applicable when no UI is in scope; absence of inspection is unknown, not not applicable.

**Decision checkpoint:** Does the Interface Adapter present a state consistent with the completed business operation?

**Useful evidence:** Journeys, UI code, contracts, and authorized browser or device evidence.

**Source lenses:** B01, B22, W11.

## D18. Team, documentation, and learning

**Investigate:** Assess ownership, team cognitive load, onboarding, decision records, Ubiquitous Language, review, knowledge distribution, and operating capacity. Recommend mentoring with a concrete system example, a worked change, and independent verification, not personal judgments about developers. Identify coordination dependencies that code changes alone cannot remove.

**Decision checkpoint:** Which Bounded Context or change ownership ambiguity creates unnecessary coordination, and what shared example would clarify it?

**Useful evidence:** Documentation, declared ownership, change workflow, onboarding evidence, and coordination points.

**Source lenses:** B23, B22, B05.

## D19. Agent legibility

**Investigate:** Assess the entry map, concise instructions, consistent local guidance, versioned documentation, canonical examples, explicit contracts, and discoverable ownership. Use Screaming Architecture and Ubiquitous Language where they aid navigation. Look for stale knowledge, hidden rules, excessive indirection, and undocumented code generation. Do not infer measured agent performance from file layout.

**Decision checkpoint:** Can an agent find the relevant Use Case and its invariant without inventing a contract?

**Useful evidence:** Repository instructions, linked documents, representative navigation tasks, and observed gaps.

**Source lenses:** W03, W09, B22.

## D20. Agent execution and verification

**Investigate:** Assess isolated setup, synthetic seed data, safe reset, per-session resources, controlled time and randomness, semantic UI locators, structured observations, independent oracles, and bounded tool permissions. Distinguish deterministic, statistical, integration-dependent, and exploratory checks. Run representative agent tasks only when authorized and record every attempt.

**Decision checkpoint:** What deterministic oracle verifies the final state, and what uncontrolled variables still make the check probabilistic?

**Useful evidence:** Actual task artifacts, commands, final state, environment, model/tool configuration, interventions, and failed attempts.

**Source lenses:** W03, W04, B17, B18, B19.
