# Architecture rubric

Rate all 20 dimensions as `adequate`, `attention`, `critical`, `unknown`, or `not_applicable`, each with confidence, a short assessment, and evidence. Depth follows applicability and risk. Unknown is not zero, and not applicable needs a reason; an area you did not inspect is unknown, not not applicable. Never compute an overall score or average a critical risk away.

Each dimension lists what reviewers tend to miss, then the checkpoint question its rating must answer. Activate a concept only when the evidence makes it relevant: a small single-database application does not need LSM-Trees, quorums, consensus, or Event Sourcing because they appear here.

## D01. Fitness for purpose and sufficiency
Judge current adequacy separately from unknown future capacity. A small stable product may already be sufficient, and keeping the design is a valid verdict. Look for complexity no requirement asks for as well as requirements left unmet.
**Checkpoint:** Which Quality Attribute Scenario makes this design fit for purpose, and what evidence limits that conclusion?

## D02. Domain model and Bounded Contexts
Find where the meaning of a term changes; that is a context boundary, whatever the folders say. Run the concept-duplication investigation in [module-design.md](module-design.md): a concept with several differing copies and no owning module is usually a missing owner, not a naming issue. Strategic design does not require tactical ceremony; simple work may fit a Transaction Script better than a rich model. An Anticorruption Layer protects a model from another model; it is not a new name for every API adapter. DDD Entities and Clean Architecture Entities are different definitions.
**Checkpoint:** Where does the model's meaning change, and what protects that meaning at the boundary?

## D03. Component Cohesion and Component Coupling
Check The Dependency Rule against source imports, never runtime arrows. Report cycles both at module level and including in-function imports (`measure.py imports`): deferred imports can hide a large cycle behind an acyclic top level. REP, CCP, and CRP pull against each other; do not present them as simultaneous maxima. Use Main Sequence distance only with a stated counting convention. Co-change from `measure.py history` reveals hidden coupling but does not prove causation.
**Checkpoint:** Which component principle explains the observed change cost, and which fitness function would protect the boundary?

## D04. Code design and refactorability
Apply the module-design lens: the deletion test for suspected pass-throughs, depth as leverage at the interface rather than line counts, locality of change, and one adapter as a hypothetical seam. A long, cohesive module with a stable contract and good tests is not a finding. Record the dependency category on every seam finding.
**Checkpoint:** Which seam allows a behavior-preserving change, and does the proposed abstraction actually reduce what callers must know?

## D05. Deployment topology
Separate logical modules from deployment units. A Modular Monolith needs enforced internal contracts; folders alone are not modularity. Extract a service only for demonstrated needs (selective scaling, failure isolation, release autonomy) that outweigh distributed transactions, compatibility, latency, testing, and on-call cost. Coordinated releases or shared tables across services mean a Distributed Monolith, and consolidation is an option. No topology is the next maturity level.
**Checkpoint:** Is the current topology fit for purpose, or does demonstrated autonomy or load justify selective extraction?

## D06. APIs and integration
Check object- and tenant-level authorization, idempotency, pagination, error semantics, timeouts, and compatibility policy. A response must distinguish accepted, committed, and externally confirmed outcomes; HTTP 200 does not prove the business operation completed. Watch for persistence models leaking through the contract.
**Checkpoint:** Does the interface tell the caller which outcome actually happened?

## D07. Data modeling and integrity
Find which invariants the database enforces (keys, constraints, types, money precision, time zones) and which depend on application code alone. Check tenant isolation, retention and deletion, and whether migrations are compatible with the running version (Expand and Contract). Storage-engine internals matter only when engine and workload evidence make them relevant.
**Checkpoint:** Which invariant is enforced where, and how does a migration preserve it?

## D08. Persistence, ORM, and concurrency
Trace transaction boundaries, generated SQL, N+1 queries, and pooling. A Repository that merely repeats an adequate ORM is indirection; changing an ORM does not fix a bad index, a long transaction, or a wrong invariant. Confirm the actual engine and isolation level: MVCC is not automatically Serializable Snapshot Isolation, and Snapshot Isolation permits write skew on multi-row invariants. Bulk updates usually bypass ORM event listeners. Prove lost updates or write skew with deterministic interleavings, not sleeps.
**Checkpoint:** Which invariant can concurrent transactions violate, and does the configured isolation or locking prevent it?

## D09. Events and distributed consistency
Find every dual write (database plus message, database plus external call) and trace the path after an ambiguous outcome, such as a timeout after sending. A Transactional Outbox makes state and publication intent commit together; it does not by itself produce one business effect. Effectively-once claims hold only inside a stated retry, deduplication, and side-effect boundary. CDC is not Event Sourcing; broker delivery is not end-to-end correctness. `W + R > N` gives overlap for fixed replica sets under stated assumptions; it does not give linearizability or remove concurrent-write conflicts. Tie replication lag to the read guarantee the use case needs (read-after-write, monotonic reads, consistent prefix), which is not linearizability.
**Checkpoint:** Does end-to-end correctness survive partial failure, replay, reordering, and concurrent duplicates?

## D10. Capacity, performance, and scalability
Without measurements, capacity is unknown, not slow; propose an experiment rather than an improvement. Registered users, active sessions, in-flight requests, and requests per second are different quantities; never convert one to another without a behavior model. Little's Law (`L = λ × W`) relates averages in a stable system and does not predict maximum capacity. Check algorithms, queries, indexes, batching, and vertical scaling before services or sharding. Do not extrapolate outside the measured range or assume tenfold growth.
**Checkpoint:** Which measured resource limits the scenario, and what is the smallest reversible move to test?

## D11. Reliability and recovery
Check timeouts, retry budgets, bounded queues, graceful shutdown, and degraded operation. Backup configuration is not proof of restoration. Turning off a feature is not data rollback. Do not demand costly availability mechanisms without an agreed requirement.
**Checkpoint:** Which failure leaves a recoverable state, and what check demonstrates recovery?

## D12. Security and privacy
Map trust boundaries and check authorization by object and tenant, untrusted input, SSRF, secrets handling, supply chain, and least privilege. The presence of a security library proves nothing; a negative test does. Name declared compliance requirements without certifying or giving legal conclusions. Sanitize all evidence.
**Checkpoint:** Which trust boundary and negative test demonstrate the stated protection?

## D13. Testing and testability
Look for tests that cross past the interface (hand-built internal state, patched private names); they pass while the production path is broken. Check whether safety-critical calls and guard-relaxing parameters have tests that pin their allowed callers. Count module paths named in tests (`measure.py test-pins`) before recommending file moves. High coverage with weak assertions is not sufficient; use characterization tests before restructuring uncertain legacy code.
**Checkpoint:** What deterministic oracle catches the important regression, and can the test fail for the right reason?

## D14. Build, delivery, and dependencies
Check lockfiles, pinned runtimes, reproducible builds, local versus CI parity, rollout and rollback, and unsupported dependencies. Never run install or dependency scripts automatically.
**Checkpoint:** Which pipeline gate enforces the actual requirement with actionable failure output?

## D15. Observability and operations
A tracing package does not prove useful instrumentation. Follow one diagnostic path from a user symptom to the responsible component and the recovery action. Check correlation of business operations, alert actionability, cardinality, and sensitive data in logs.
**Checkpoint:** Can an operator diagnose a partial failure from persisted state and correlated attempts?

## D16. Economics and total cost
Compare recurring and transition cost over a stated horizon and a meaningful unit (per order, per active customer). Include operations, onboarding, observability, and migration, not only compute. Never add hours to money without a stated rate or invent a savings percentage; use ranges where evidence is weak.
**Checkpoint:** Is the proposed change fit for purpose once migration and operating costs are included?

## D17. User interface and experience
For a UI, check server versus local state, error and loading states, accessibility, and whether the UI shows the state of the completed operation. Mark not applicable only when no UI is in scope.
**Checkpoint:** Does the interface present a state consistent with the completed business operation?

## D18. Team, documentation, and learning
Assess ownership, cognitive load, decision records, and coordination points that code changes alone cannot remove. Recommend concrete worked examples, never personal judgments about developers.
**Checkpoint:** Which ownership ambiguity creates unnecessary coordination, and what shared example would clarify it?

## D19. Agent legibility
Can an agent find the responsibility, contract, and invariant for a change without inventing one? Check for a concise entry map, one authoritative source per fact, canonical commands and examples, and rules that live only in conversations or stale diagrams. List the domain terms the review had to name that the glossary lacks. File layout does not measure agent performance.
**Checkpoint:** Can an agent find the relevant use case and its invariant without inventing a contract?

## D20. Agent execution and verification
Static legibility is not task success; an `AGENTS.md` file is not an evaluation. Check noninteractive setup, synthetic seed data, safe reset, per-session resources (ports, databases, queues; a worktree does not isolate these), controlled time and randomness, and oracles outside the agent's narrative. A screenshot shows presentation, not persistence or authorization. Classify each check as deterministic, statistical, integration-dependent, or exploratory, and keep every attempt; rerunning until green hides flakiness. A check that passes only because an assertion, snapshot, or gate was relaxed has not passed. Run representative agent tasks only when authorized, with the budget and trial count set first; otherwise record the protocol as not run.
**Checkpoint:** What deterministic oracle verifies the final state, and what uncontrolled variables still make the check probabilistic?
