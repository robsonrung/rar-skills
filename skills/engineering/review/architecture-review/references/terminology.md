# Canonical terminology and decision use

Use these names consistently in questions, diagnoses, actions, and verification criteria. Definitions are written once in this catalog and mirrored into `assets/terms.json`. Copy only relevant definitions into a report glossary. Canonical vocabulary does not authorize a pattern: relevance still requires the actual workload, invariant, and evidence.

Book and community wording can differ. Preserve the source's meaning. “Read-After-Write” is also called “read-your-writes consistency.” “Effectively-Once Processing” is a community description of a scoped observable effect, not asserted to be a DDIA chapter heading. Use Cases are often implemented as Interactors. The deep-module terms (deletion test, leverage, locality, adapter, dependency category, design it twice) follow W21; seam keeps Feathers's meaning, and none of them replaces Bounded Context or the component principles. REP is also written Reuse Release Equivalence Principle or Reuse/Release Equivalence Principle. Do not silently change a database's documented isolation guarantee into a stronger one.

For DDD, use singular Entity, Value Object, Aggregate, Aggregate Root, Domain Service, Repository, Factory, and Specification when describing one instance; use the regular plurals when describing a category. “Entities” in Clean Architecture has its own explicitly scoped entry. Anticorruption Layer uses Evans's spelling. ACL means Anticorruption Layer in this catalog; distinguish an access-control list where that acronym is used for security.


## Decision anchors

### L01. fit for purpose

A local decision anchor: adequacy means meeting the relevant requirements at a justified total cost.

Activate when: Sufficiency, complexity, or scale decisions.

Decision question: Which agreed Quality Attribute Scenario is satisfied or not demonstrated?

Guardrail: Do not turn an unknown target into a failure or a forecast into a measurement.

Model decision: “The current topology is fit for purpose for the verified workload; peak capacity remains unknown.”

Sources: B01, W01.


### L02. smallest reversible move

A local decision anchor: prefer the least disruptive useful change with an explicit rollback or containment plan.

Activate when: Choosing a migration step.

Decision question: What is the minimum change that reduces the demonstrated risk, and how can it be reversed?

Guardrail: Small does not mean safe; data changes may need forward recovery rather than literal rollback.

Model decision: “The smallest reversible move is to add the public contract before changing callers.”

Sources: B09, B16.


### L03. evidence before opinion

A local decision anchor: establish observable facts and counterevidence before classifying a design.

Activate when: Every significant diagnosis.

Decision question: What source could confirm or falsify this claim?

Guardrail: Repeating a principle is not evidence that it is violated.

Model decision: “Evidence before opinion means checking middleware and database constraints before claiming validation is absent.”

Sources: B01, W01.


### L04. behavior-preserving

Refactoring changes internal structure while preserving the behavior included in the agreed contract.

Activate when: Restructuring existing code.

Decision question: Which observable behavior must remain unchanged, and which tests protect it?

Guardrail: A deliberate behavior change is not merely a refactoring; characterize existing defects without enshrining them as desired behavior.

Model decision: “This behavior-preserving refactoring keeps the public pricing contract unchanged.”

Sources: B09, B10.


### L05. deterministic oracle

A verification rule whose verdict is reproducible under controlled inputs, state, and explicitly stated assumptions.

Activate when: Agent checks and regression validation.

Decision question: What independent assertion decides success, without trusting the agent narrative?

Guardrail: Do not imply deterministic model behavior or universal determinism of external services.

Model decision: “The deterministic oracle checks the final order state and side-effect count after replay.”

Sources: B17, B18, W04.


### L06. end-to-end correctness

A local decision anchor: assess the complete externally relevant result across component and failure boundaries.

Activate when: Distributed writes, retries, and user-visible outcomes.

Decision question: Does the final business effect satisfy the invariant after partial failure and recovery?

Guardrail: A broker acknowledgement or HTTP 200 is not sufficient evidence of the business result.

Model decision: “End-to-end correctness requires checking the ERP effect as well as the local commit.”

Sources: B11, B14, W13.


## Domain-Driven Design

### T01. Ubiquitous Language

The model-based language used consistently by domain experts and developers within a Bounded Context.

Activate when: Naming, contracts, and domain discovery.

Decision question: Do business discussions, code, and tests use the same meaning?

Guardrail: A single enterprise-wide vocabulary can erase legitimate differences between contexts.

Model decision: “The Ubiquitous Language distinguishes an accepted order from an ERP-confirmed order.”

Sources: B05, W10.


### T02. Bounded Context

The explicit boundary within which a particular domain model and its language are consistent.

Activate when: Model boundaries and ownership.

Decision question: Where does this model apply, who maintains it, and how does it interact with other models?

Guardrail: A folder, deployment, team, or database is not automatically a Bounded Context.

Model decision: “This candidate Bounded Context owns order acceptance; Billing translates its published contract.”

Sources: B05, W10.


### T03. Context Map

A representation of Bounded Contexts and their model, integration, and organizational relationships.

Activate when: Cross-context interactions.

Decision question: Which side is upstream, which depends on it, and what relationship governs integration?

Guardrail: Do not substitute a deployment diagram or label every relationship identically.

Model decision: “The Context Map identifies the ERP as upstream and the local translation boundary as protective.”

Sources: B05, W10.


### T04. Anticorruption Layer

A translation boundary that protects one domain model from the assumptions of another.

Activate when: External or legacy model integration.

Decision question: Which foreign concepts are translated, and where can foreign semantics still leak inward?

Guardrail: Not every API client is an Anticorruption Layer; it must protect meaning, not only transport.

Model decision: “The Anticorruption Layer translates ERP status codes into the order model.”

Sources: B05, W10.


### T05. Tactical Building Blocks

The model implementation patterns used within a Bounded Context, including Entities, Value Objects, Aggregates, Services, Repositories, and Factories.

Activate when: Complex domain behavior.

Decision question: Which pattern expresses a real invariant or lifecycle need?

Guardrail: Do not mandate every building block for a simple Transaction Script.

Model decision: “These Tactical Building Blocks protect order invariants without adding a Repository for every table.”

Sources: B05, W10.


### T06. Entity

A domain object distinguished by identity and continuity through changes to its attributes.

Activate when: Identity and lifecycle modeling.

Decision question: What identifies the same conceptual object over time?

Guardrail: DDD Entity is not a synonym for an ORM record or for the Clean Architecture Entities layer.

Model decision: “The Order is an Entity because its identity persists when its status changes.”

Sources: B05, W10.


### T07. Value Object

A domain object defined by its attributes rather than conceptual identity, usually modeled as immutable.

Activate when: Money, quantities, addresses, and other descriptive values.

Decision question: Can equal values be substituted without tracking separate identities?

Guardrail: An arbitrary DTO does not automatically encode a useful Value Object or its invariants.

Model decision: “Money is a Value Object that carries amount and currency together.”

Sources: B05, W10.


### T08. Aggregate

A cluster of related domain objects treated as one consistency boundary for its invariants.

Activate when: Transactional rules and mutation ownership.

Decision question: Which changes must preserve an invariant together?

Guardrail: Avoid treating the entire object graph or database as one Aggregate.

Model decision: “The Aggregate boundary keeps order-line changes consistent with the order total.”

Sources: B05, W10.


### T09. Aggregate Root

The designated Entity through which external access to and mutation of an Aggregate are controlled.

Activate when: Aggregate access paths.

Decision question: Can callers bypass the root and violate an invariant?

Guardrail: A root is not required for every database table; identity references can cross Aggregate boundaries.

Model decision: “The Aggregate Root rejects a line change after the order is finalized.”

Sources: B05, W10.


### T10. Domain Service

A domain operation that does not naturally belong to an Entity or Value Object, expressed in the Ubiquitous Language.

Activate when: Domain behavior spanning concepts.

Decision question: Is this a domain operation or application orchestration and infrastructure work?

Guardrail: A class named Service is not necessarily a Domain Service.

Model decision: “The Domain Service calculates the eligibility decision without owning request orchestration.”

Sources: B05, W10.


### T11. Repository

An abstraction that provides collection-like access to domain objects while hiding persistence mechanisms.

Activate when: Domain object retrieval and persistence boundaries.

Decision question: Does this interface express domain access needs instead of exposing storage machinery?

Guardrail: A generic wrapper that duplicates an ORM API can add no useful boundary.

Model decision: “The Repository retrieves an Order Aggregate without exposing ORM session state.”

Sources: B05, B12, W10.


### T12. Factory

An abstraction that encapsulates complex creation and ensures a valid initial object or Aggregate.

Activate when: Complex construction and reconstitution.

Decision question: Where are construction invariants enforced?

Guardrail: Do not add a Factory when direct construction is clear and safe.

Model decision: “The Factory creates a valid Order Aggregate from the accepted input.”

Sources: B05, W10.


### T13. Side-Effect-Free Function

An operation that computes a result without changing observable state.

Activate when: Queries, calculations, and command/query separation.

Decision question: Does evaluating the result mutate domain or external state?

Guardrail: Side-effect freedom alone does not establish determinism or referential transparency if hidden inputs can vary.

Model decision: “This Side-Effect-Free Function computes the total; persistence remains in the command path.”

Sources: B05, W10.


### T14. Intention-Revealing Interface

An interface whose names and contracts communicate its purpose and effect without exposing implementation details.

Activate when: Public capabilities and ambiguous names.

Decision question: Can a caller understand the business intention without reading the implementation?

Guardrail: Readable names cannot replace precise error, mutation, and concurrency contracts.

Model decision: “An Intention-Revealing Interface distinguishes quotePrice from commitOrder.”

Sources: B05, W10.


### T15. Specification

An explicit predicate representing a domain criterion that can be tested or combined independently of the object it evaluates.

Activate when: Selection, validation, or construction criteria.

Decision question: Is the business criterion explicit and consistently applied?

Guardrail: Do not force a query framework or elaborate class hierarchy for a trivial condition.

Model decision: “The Specification names the eligibility criterion and tests its boundary cases.”

Sources: B05, W10.


## Clean Architecture

### T16. The Dependency Rule

Source code dependencies point toward higher-level policy, not outward toward implementation details.

Activate when: Layer boundaries and imports.

Decision question: Does inner policy name an outer adapter, framework type, or transport representation?

Guardrail: Runtime control flow may point outward through an inward-owned abstraction; source dependencies are the relevant graph.

Model decision: “The Dependency Rule requires the adapter to depend on the Use Case port, not the reverse.”

Sources: B06, W11.


### T17. Entities

The Clean Architecture policy layer containing the most general enterprise business rules.

Activate when: Allocation of core business policy.

Decision question: Are general business rules protected from application workflow and delivery mechanisms?

Guardrail: Distinguish these Entities from DDD identity-based Entities and ORM models.

Model decision: “These Entities hold the general pricing rules; request-specific orchestration belongs elsewhere.”

Sources: B06, W11.


### T18. Use Cases (Interactors)

Application-specific business rules that orchestrate Entities and the steps needed to achieve an application goal.

Activate when: Application workflow boundaries.

Decision question: Is application policy separated from transport and persistence details?

Guardrail: Not every handler must acquire an otherwise empty Interactor class.

Model decision: “The Use Cases (Interactors) define order acceptance independently of HTTP response formatting.”

Sources: B06, W11.


### T19. Interface Adapters

Code that converts representations between policy and external delivery or persistence mechanisms.

Activate when: Controllers, presenters, gateways, and mappings.

Decision question: Where are protocol and persistence representations translated?

Guardrail: A pass-through layer without meaningful conversion or boundary protection may be unnecessary.

Model decision: “The Interface Adapters map the request DTO into the Use Case input contract.”

Sources: B06, W11.


### T20. Frameworks and Drivers

The outer mechanisms, tools, and integration details such as web frameworks and databases.

Activate when: Infrastructure and composition.

Decision question: Which concrete mechanism is selected here, and does it leak into policy?

Guardrail: Calling the database a detail does not make data semantics or transaction design unimportant.

Model decision: “Frameworks and Drivers are selected at composition time without changing the core rules.”

Sources: B06, W11.


### T21. Component Cohesion

Principles governing which classes or responsibilities belong together in a component.

Activate when: Component boundaries and change history.

Decision question: How do REP, CCP, and CRP balance release, change, and reuse needs here?

Guardrail: Maximal fragmentation does not maximize cohesion; the principles create tradeoffs.

Model decision: “Component Cohesion favors keeping the pricing rules that change together in one component.”

Sources: B06, W20.


### T22. Reuse/Release Equivalence Principle (REP)

The granule that is reused should be a coherent unit of release.

Activate when: Reusable packages and versioned components.

Decision question: Can consumers adopt a coherent, managed release of what they reuse?

Guardrail: REP does not mean every class deserves its own released package.

Model decision: “The Reuse/Release Equivalence Principle (REP) supports versioning this shared component as one release.”

Sources: B06, W20.


### T23. Common Closure Principle (CCP)

Responsibilities that change for the same reasons and at the same times should be grouped together.

Activate when: Change ownership and hotspots.

Decision question: Which recurring changes cross this boundary, and why?

Guardrail: Coincidental edits alone do not prove a shared reason to change.

Model decision: “The Common Closure Principle (CCP) supports keeping the tax-policy changes within one component.”

Sources: B06, W20.


### T24. Common Reuse Principle (CRP)

Consumers should not be forced to depend on component contents they do not use.

Activate when: Broad shared libraries and unwanted dependencies.

Decision question: What unrelated classes or dependencies must a consumer take on?

Guardrail: Do not split coherent policy into tiny packages that amplify navigation and release work.

Model decision: “The Common Reuse Principle (CRP) exposes Billing dependence on unrelated Order internals.”

Sources: B06, W20.


### T25. Component Coupling

Principles governing dependencies among components and their stability.

Activate when: Dependency graphs and releases.

Decision question: Do ADP, SDP, and SAP explain a demonstrated dependency risk?

Guardrail: Distinguish static dependencies from runtime timing and model coupling.

Model decision: “Component Coupling makes a pricing implementation change visible to Billing.”

Sources: B06, W20.


### T26. Acyclic Dependencies Principle (ADP)

The component dependency graph should not contain directed cycles.

Activate when: Build, release, and source dependency cycles.

Decision question: Which cycle couples components that should be independently understandable or releasable?

Guardrail: A runtime request/response cycle is not automatically a source dependency cycle.

Model decision: “The Acyclic Dependencies Principle (ADP) flags the package cycle shown by the import graph.”

Sources: B06, W20.


### T27. Stable Dependencies Principle (SDP)

Dependencies should point toward components that are harder to change, rather than toward more volatile ones.

Activate when: Dependency direction and change impact.

Decision question: Is a widely depended-on component relying on a more volatile detail?

Guardrail: Stability means resistance to change through dependencies, not maturity or low defect counts.

Model decision: “The Stable Dependencies Principle (SDP) argues against core policy depending on the volatile ERP adapter.”

Sources: B06, W20.


### T28. Stable Abstractions Principle (SAP)

A component should be abstract in proportion to its stability so that stable components can still be extended.

Activate when: Rigid stable components and abstraction placement.

Decision question: Does a hard-to-change component expose the abstractions needed for extension?

Guardrail: Do not add empty interfaces solely to improve a numeric ratio.

Model decision: “The Stable Abstractions Principle (SAP) supports a policy-owned port at this stable boundary.”

Sources: B06, W20.


### T29. Main Sequence and Distance

The component metric model relating abstractness A and instability I, with Main Sequence A + I = 1 and normalized distance D = |A + I - 1|.

Activate when: Quantitative support for component dependency analysis.

Decision question: Are component boundaries and counts meaningful, and does the metric corroborate a real design issue?

Guardrail: This is a diagnostic heuristic, not a universal quality score; undefined denominators remain unknown.

Model decision: “Main Sequence and Distance suggest a rigid component; the change history must confirm whether that rigidity is harmful.”

Sources: B06, W20.


### T30. Humble Object Pattern

Separate hard-to-test interaction code from behavior that can be isolated and tested directly.

Activate when: UI, persistence, and infrastructure test seams.

Decision question: Which decisions can be extracted while keeping the interaction object simple?

Guardrail: The remaining interaction still needs appropriate integration verification.

Model decision: “The Humble Object Pattern moves formatting decisions out of the untestable view mechanism.”

Sources: B06.


### T31. Policy vs. Detail

Separate what the system must accomplish from the mechanisms used to accomplish it.

Activate when: Framework or persistence choices shaping business rules.

Decision question: Which part is a business decision, and which part is a replaceable mechanism?

Guardrail: Physical data constraints and security mechanisms still constrain feasible policy implementation.

Model decision: “Policy vs. Detail keeps the acceptance rule separate from the ERP transport client.”

Sources: B06, W11.


### T32. Screaming Architecture

The system structure communicates its purpose and Use Cases rather than primarily advertising its frameworks.

Activate when: Repository navigation and conceptual structure.

Decision question: Does the first architectural view reveal what the application does?

Guardrail: Renaming directories does not establish correct dependencies or a domain model.

Model decision: “Screaming Architecture makes order acceptance discoverable before framework plumbing.”

Sources: B06.


## Data-intensive systems

### T33. ACID

Atomicity, Consistency, Isolation, and Durability describe transaction properties, interpreted under the database guarantees and application invariants.

Activate when: Transactions and business integrity.

Decision question: Which property protects this invariant, at which boundary and under which failures?

Guardrail: ACID Consistency is not the same concept as replica consistency; isolation levels differ.

Model decision: “ACID protects the local transaction, not an uncoordinated ERP side effect.”

Sources: B11, W14.


### T34. SSTables and LSM-Trees

Sorted String Tables store immutable sorted key/value data; Log-Structured Merge-Trees combine buffered writes with sorted runs and compaction.

Activate when: Storage-engine workload and tuning decisions.

Decision question: How do write, read, and space amplification, compaction, and cache behavior match this workload?

Guardrail: An LSM-Tree is not automatically faster than a B-Tree; inspect the actual engine and measurements.

Model decision: “SSTables and LSM-Trees are relevant only if compaction and write amplification explain the observed bottleneck.”

Sources: B11.


### T35. B-Trees

Balanced page-oriented search structures, commonly implemented with B+Tree variants, supporting indexed lookup and ordered access.

Activate when: Indexes, point queries, and range queries.

Decision question: Do index ordering, selectivity, page access, and updates suit the query mix?

Guardrail: A B-Tree label alone cannot predict latency or justify changing databases.

Model decision: “B-Trees support this range predicate when the index prefix matches the filter.”

Sources: B11.


### T36. Column-Oriented Storage

Storage organized by column values to reduce scanned data and improve compression for suitable analytical workloads.

Activate when: Wide scans, aggregation, and analytical access.

Decision question: Which columns and row fractions does the query actually read?

Guardrail: Do not assume an analytical layout is ideal for transactional point updates.

Model decision: “Column-Oriented Storage is a candidate for the measured analytical scan, not a default OLTP replacement.”

Sources: B11.


### T37. Quorums

Sets of replicas participating in an operation, chosen to satisfy the intersection requirements of a replication protocol.

Activate when: Replicated reads and writes.

Decision question: What do N, W, and R mean in this protocol, and which participating sets intersect?

Guardrail: W + R > N alone does not prove Linearizability; state membership, version selection, concurrent-write, and failure assumptions.

Model decision: “Quorums overlap for W + R > N under the fixed-set assumptions, but the read algorithm still needs inspection.”

Sources: B11, W18.


### T38. Read-After-Write

A session guarantee that a client reading after its own completed write sees that write or a later value.

Activate when: Reads served by lagging replicas after mutations.

Decision question: Can a writer read a replica that has not applied its own acknowledged write?

Guardrail: Also called read-your-writes consistency; not a guarantee that all clients immediately see all writes.

Model decision: “Read-After-Write is required for the user to see the order they just submitted.”

Sources: B11.


### T39. Monotonic Reads

A session guarantee that successive reads do not move backward to an older observed state.

Activate when: Clients switching between replicas.

Decision question: Can a later read expose a version older than one this client already observed?

Guardrail: This is weaker than Linearizability and is not the same as read-your-writes.

Model decision: “Monotonic Reads prevent the order status from appearing to move backward after replica switching.”

Sources: B11.


### T40. Consistent Prefix Reads

A guarantee that reads do not expose later writes before earlier writes in their causal sequence.

Activate when: Causally related writes replicated across partitions.

Decision question: Can a reader observe an effect before its cause?

Guardrail: An arbitrary timestamp sort does not necessarily preserve causal order.

Model decision: “Consistent Prefix Reads keep a confirmation from appearing before its related order creation.”

Sources: B11.


### T41. Linearizability

Operations appear to take effect atomically at a point between invocation and response, respecting real-time order of nonoverlapping operations.

Activate when: Freshness and coordination guarantees.

Decision question: Which object or operation history must satisfy real-time ordering?

Guardrail: Do not conflate Linearizability with Serializability, quorum overlap, or all forms of strong consistency.

Model decision: “Linearizability is required for this compare-and-set decision, not necessarily for every report query.”

Sources: B11, W18.


### T42. Multi-Version Concurrency Control (MVCC)

A concurrency-control technique that retains multiple data versions so readers and writers can use suitable visibility rules.

Activate when: Database reads, writes, snapshots, and retention.

Decision question: Which snapshot and visibility rules does the actual transaction use?

Guardrail: MVCC alone does not guarantee Serializable isolation or prevent write skew.

Model decision: “Multi-Version Concurrency Control (MVCC) supplies snapshots; the configured isolation level determines permitted anomalies.”

Sources: B11, W14, W15.


### T43. Serializable Snapshot Isolation (SSI)

A technique that augments snapshot-based execution with dependency checks and transaction aborts to prevent serialization anomalies.

Activate when: Serializable transactions implemented using snapshots.

Decision question: Are serialization failures retried correctly across the entire transaction?

Guardrail: Do not call ordinary Snapshot Isolation SSI or assume every database implements it.

Model decision: “Serializable Snapshot Isolation (SSI) can abort this transaction, so the retry must repeat the whole unit of work.”

Sources: B11, W14.


### T44. Total Order Broadcast

A broadcast abstraction in which participating correct nodes deliver messages in the same total order, with the stated reliability guarantees.

Activate when: Replicated ordering and state-machine execution.

Decision question: What order, membership, and delivery guarantees does the protocol provide?

Guardrail: A timestamp on messages or a FIFO queue is not by itself Total Order Broadcast.

Model decision: “Total Order Broadcast is relevant to replicated command ordering, not to an unrelated HTTP request flow.”

Sources: B11, W18.


### T45. Consensus

A distributed agreement problem with validity, agreement, and termination conditions under an explicit failure model.

Activate when: Replicated decisions and coordination.

Decision question: What value is agreed, who participates, and what assumptions permit progress?

Guardrail: Consensus is not an automatic solution to every cross-system business transaction.

Model decision: “Consensus establishes the replicated decision under the protocol assumptions; it does not execute the external payment atomically.”

Sources: B11, W16, W18, W19.


### T46. Paxos

A family of consensus protocols that uses intersecting quorums to preserve agreement under its fault assumptions.

Activate when: Infrastructure using Paxos-based agreement.

Decision question: Which variant, quorum, membership, and recovery rules are actually implemented?

Guardrail: Do not recommend implementing a custom Paxos protocol as a routine application refactoring.

Model decision: “Paxos describes the infrastructure agreement mechanism; application idempotency remains a separate concern.”

Sources: W19, B11.


### T47. Raft

A consensus algorithm for managing a replicated log through leader election, log replication, and safety rules.

Activate when: Infrastructure using Raft-based replicated logs.

Decision question: What are the configured membership, durability, and failure assumptions?

Guardrail: A Raft-backed store does not make arbitrary external operations transactional.

Model decision: “Raft governs this replicated log; the report must still trace the application commit boundary.”

Sources: W16, B11.


### T48. Change Data Capture (CDC)

A mechanism that captures changes in a source data store and propagates them to downstream consumers.

Activate when: Derived stores, integration, and change streams.

Decision question: What is captured, how are positions tracked, and how do schema changes and replay work?

Guardrail: Storage change records are not necessarily business events or an Event Sourcing model.

Model decision: “Change Data Capture (CDC) updates the search projection without making the database log the domain event model.”

Sources: B11.


### T49. Event Sourcing

A model in which an event history is the authoritative record from which application state is derived.

Activate when: Auditability, temporal reconstruction, and state evolution.

Decision question: Are the events the source of truth, and can state be rebuilt with defined event semantics?

Guardrail: Using a broker, audit log, CDC, or outbox is not automatically Event Sourcing.

Model decision: “Event Sourcing would change the authoritative state model; the current outbox proposal does not require it.”

Sources: B11.


### T50. Effectively-Once Processing

A common community term for making repeated processing attempts produce one observable effect within an explicitly defined boundary.

Activate when: Retries, deduplication, and business side effects.

Decision question: Which key, atomicity boundary, retention window, and sink contract prevent duplicate effects?

Guardrail: Not a universal delivery guarantee or a claim that the phrase is a DDIA chapter heading; preserve a source's scoped exactly-once terminology.

Model decision: “Effectively-Once Processing requires atomic deduplication and the protected effect, or an equivalent contract with the sink.”

Sources: B11, W13.


### T51. Transactional Outbox

Persist business state and a publication intent in the same local transaction, then deliver that intent separately.

Activate when: The database commit plus message-send dual-write gap.

Decision question: Can committed business state lose its publication intent, or can replay duplicate its external effect?

Guardrail: Delivery can repeat; an outbox does not alone guarantee exactly-once business effects.

Model decision: “The Transactional Outbox closes the local dual-write gap; idempotent handling still protects the remote effect.”

Sources: B11, B14.


### T52. Serializability

Concurrent transactions have an effect equivalent to some serial execution order.

Activate when: Multi-operation transactional invariants.

Decision question: Can the observed transaction history be equivalent to a serial history?

Guardrail: Serializability alone does not require the real-time order of Linearizability.

Model decision: “Serializability protects the invariant across concurrent transactions; freshness is a separate contract.”

Sources: B11, W14.


### T53. Snapshot Isolation

Transactions read from a consistent snapshot and conflicting writes are handled according to the database rules.

Activate when: Snapshot-based transactions and write skew.

Decision question: Can concurrent transactions update different rows while jointly violating an invariant?

Guardrail: Snapshot Isolation is not generally Serializability.

Model decision: “Snapshot Isolation can permit write skew in this invariant; test the actual engine behavior.”

Sources: B11, W14.


## Design and verification

### T54. seam

A point where behavior can be changed without editing the code at that point; an enabling point controls which behavior is used.

Activate when: Isolating a dependency in legacy code.

Decision question: Where is the seam, and what exact enabling point selects the behavior?

Guardrail: A generic module boundary is not enough; identify the substitution mechanism.

Model decision: “The seam is the gateway call; the composition root is its enabling point.”

Sources: B10, W12.


### T55. Characterization Tests

Tests that capture the actual observable behavior of existing code before it is changed.

Activate when: Legacy refactoring with uncertain behavior.

Decision question: Which behavior must first be recorded to make a controlled change?

Guardrail: Observed behavior can include defects; distinguish preservation from explicitly approved correction.

Model decision: “Characterization Tests first capture the timeout behavior before the contract is deliberately changed.”

Sources: B10.


### T56. deep module

A module that hides substantial useful complexity behind a relatively simple interface.

Activate when: Abstraction and interface review.

Decision question: Does this interface reduce the knowledge required of callers?

Guardrail: A long module is not necessarily deep, and a tiny module is not necessarily shallow.

Model decision: “A deep module would hide the pricing policy instead of requiring callers to coordinate its internal steps.”

Sources: B08.


### T57. connascence

A relationship in which elements must change together or agree on some property for the system to remain correct.

Activate when: Hidden cross-component dependencies.

Decision question: What form of connascence is present, at what strength, degree, and locality?

Guardrail: Do not use the word as a generic replacement for every kind of coupling.

Model decision: “Connascence of position makes the tuple contract fragile; a named representation removes that positional dependency.”

Sources: W17, B03.


### T58. architectural fitness function

An objective check that assesses whether an architectural characteristic is being preserved.

Activate when: Automated architectural constraints.

Decision question: What relevant property can the check observe, and what constitutes a violation?

Guardrail: A check of import rules does not prove every architectural quality or business invariant.

Model decision: “The architectural fitness function rejects imports of this module's internal files.”

Sources: B04.


### T59. Quality Attribute Scenario

A concrete quality requirement described by stimulus source, stimulus, environment, artifact, response, and response measure.

Activate when: Converting vague nonfunctional goals into testable requirements.

Decision question: Who causes what, under which conditions, and what measurable response is acceptable?

Guardrail: Do not invent targets or treat a proposed threshold as an agreed requirement.

Model decision: “The Quality Attribute Scenario states the peak workload and agreed latency boundary.”

Sources: B01, W01.


### T60. Unit of Work

A pattern coordinating changes within a business transaction and their persistence.

Activate when: Transaction ownership and change tracking.

Decision question: Which operations must commit or roll back together?

Guardrail: An ORM session or request scope is not automatically the correct business transaction boundary.

Model decision: “The Unit of Work must include the order update and its durable publication intent.”

Sources: B12.


### T61. Data Mapper

A persistence layer that moves data between objects and the database while keeping their representations independent.

Activate when: ORM mappings and storage coupling.

Decision question: Does the mapping isolate representation differences without hiding critical transaction behavior?

Guardrail: Not every ORM follows Data Mapper; distinguish Active Record and the actual implementation.

Model decision: “The Data Mapper translates storage fields without moving business rules into SQL mapping code.”

Sources: B12.


### T62. Strangler Fig

An incremental replacement approach in which new behavior gradually takes over from the existing system through controlled routing or boundaries.

Activate when: Large-system replacement.

Decision question: Which slice can be replaced independently, and how does traffic switch safely?

Guardrail: It is not a promise of zero migration cost or an excuse to maintain two sources of truth indefinitely.

Model decision: “The Strangler Fig migration replaces one capability while preserving the existing contract.”

Sources: B16.


### T63. Branch by Abstraction

Introduce an abstraction that allows old and new implementations to coexist while switching incrementally.

Activate when: Large implementation changes without long-lived source branches.

Decision question: Which contract permits both implementations and a controlled switch?

Guardrail: The abstraction must be removable or independently valuable after the migration.

Model decision: “Branch by Abstraction preserves the old gateway while the replacement is validated.”

Sources: B16, B19.


### T64. Expand and Contract

Evolve a contract or schema by adding a compatible form, migrating users or data, then removing the old form.

Activate when: Safe API and database evolution.

Decision question: Which versions must coexist, and when is removal safe?

Guardrail: Do not remove the old form before all consumers and backfills are verified.

Model decision: “Expand and Contract allows both order-status representations during the migration.”

Sources: B13, B16.


### T65. Modular Monolith

A system deployed as a single principal unit while maintaining explicit internal module boundaries.

Activate when: Proportional topology choices.

Decision question: Are module contracts, ownership, and dependencies enforced inside the deployment?

Guardrail: One deployable with many folders is not automatically modular.

Model decision: “The Modular Monolith remains proportionate if its public boundaries are enforced.”

Sources: B02, B16.


### T66. Distributed Monolith

A distributed deployment whose components remain tightly coupled in change, failure, or release.

Activate when: Coordinated releases and synchronous dependency chains.

Decision question: Does distribution deliver useful autonomy, or only introduce network boundaries?

Guardrail: Shared infrastructure alone does not establish this diagnosis.

Model decision: “This Distributed Monolith requires coordinated releases despite separate deployment units.”

Sources: B03, B15, B16.


### T69. deletion test

A thought experiment for a suspected shallow module: if deleting it makes its complexity vanish, it was a pass-through; if the complexity reappears across callers, it was earning its keep.

Activate when: Judging whether a module, wrapper or layer is worth keeping or merging.

Decision question: Where would this module's complexity go if it were deleted, and how many callers would absorb it?

Guardrail: The test judges placement of complexity, not code style; a small module can pass it and a large one can fail it.

Model decision: “The deletion test shows the retry rule would be copied into four callers, so the module stays and absorbs the fifth copy.”

Sources: W21, B08.


### T70. leverage

What callers and tests gain from depth: more behavior exercised per unit of interface they must learn.

Activate when: Comparing interfaces or justifying a deeper module.

Decision question: How much behavior does one entry point give its callers and tests?

Guardrail: Leverage is measured at the interface a caller must learn, not by implementation size.

Model decision: “One settings object with typed values gives every billing caller leverage that eight key-string reads did not.”

Sources: W21, B08.


### T71. locality

What maintainers gain from depth: change, bugs, knowledge and verification concentrate in one place instead of spreading across callers.

Activate when: Assessing change cost or proposing to consolidate scattered rules.

Decision question: How many places must one rule change touch today, and how many after the move?

Guardrail: Locality does not justify merging unrelated responsibilities; check cohesion and reasons to change.

Model decision: “Moving the five status writers behind one module gives locality: a retry bug is fixed once.”

Sources: W21, B08.


### T72. adapter

A concrete implementation that satisfies an interface at a seam; the term names its role, not its size. One adapter makes a seam hypothetical, two make it real.

Activate when: Deciding whether to introduce a port or interface at a seam.

Decision question: Which two adapters, typically production and a test fake, justify this port?

Guardrail: A port with a single adapter is indirection; do not propose it without a concrete second adapter.

Model decision: “A production Channex adapter and an in-memory fake justify the provider port.”

Sources: W21, B10.


### T73. dependency category

The kind of dependency behind a seam: in-process, local-substitutable, ports and adapters (owned remote), or true external. It decides how the deepened module is tested.

Activate when: Recommending a seam, port or deepening and its test strategy.

Decision question: What sits behind this seam, and can the tests use a real stand-in or do they need an adapter?

Guardrail: A local stand-in such as a real test database needs no port; add a port only for owned remote or true external dependencies.

Model decision: “The delivery module is local-substitutable for PostgreSQL and uses ports and adapters for the provider.”

Sources: W22, W21.


### T74. design it twice

Produce several radically different interfaces for the same module before choosing one, then compare them by depth, locality and seam placement.

Activate when: A finding proposes a new module interface and the first design may not be the best.

Decision question: Which alternative interfaces were compared, and why did the chosen one win?

Guardrail: Alternatives must differ in shape, not in naming; compare them against the same constraints.

Model decision: “Design it twice produced a minimal, a flexible and a common-case interface; the minimal one won on locality.”

Sources: B08, W21.


## Data-intensive systems

### T67. CQRS

Command Query Responsibility Segregation separates models or responsibilities for updates and reads when their needs differ.

Activate when: Different read and write models.

Decision question: What concrete complexity is reduced by separate command and query models?

Guardrail: CQRS does not require Event Sourcing, microservices, or two databases.

Model decision: “CQRS is optional here; the outbox does not require separate read and write stores.”

Sources: B11, B03.


### T68. Replication Lag Anomalies

Observable inconsistencies caused when replicas expose different stages of applied writes.

Activate when: Asynchronous replication and read routing.

Decision question: Which user-visible history violates Read-After-Write, Monotonic Reads, or Consistent Prefix Reads?

Guardrail: Those three names denote guarantees that constrain anomalies, not names for the anomalies themselves.

Model decision: “Replication Lag Anomalies explain this stale read only after confirming the actual routing and replication history.”

Sources: B11.


## Main Sequence calculation contract

For a component with meaningful type and dependency counts, let `Na` be its abstract classes and interfaces, `Nc` all its counted classes/types, `Ca` incoming component dependencies, and `Ce` outgoing component dependencies. Define `A = Na / Nc` and `I = Ce / (Ca + Ce)`. Document the counting convention, language, component boundary, and treatment of generated or dynamic dependencies.

The Main Sequence is `A + I = 1`. Use the normalized distance `D = abs(A + I - 1)`. The ordinary perpendicular Euclidean distance to that line is `D / sqrt(2)`; do not silently mix the conventions. When a denominator is zero or counts are not meaningful, report unknown or not applicable. Values near either rigid or overly abstract extremes are prompts to inspect actual change and use, not an instruction to optimize every component to zero distance. Source lens: B06 and W20.

## Quorum calculation contract

For a fixed replica set, `N` is its size, `W` the acknowledged write-set size, and `R` the read-set size. `W + R > N` makes such a read set intersect such a write set. `2W > N` gives write-set intersection when the protocol requires it. These set relations are not a complete read/write algorithm or a proof of Linearizability. State the membership, failure, incomplete-write, concurrent-write, version-ordering, and sloppy-quorum assumptions. Inspect the actual protocol and histories. Source lenses: B11 and W18.

## Context Map relationships

When they explain actual coordination, name Evans's relationships rather than drawing an undifferentiated integration line: Shared Kernel, Customer/Supplier, Conformist, Anticorruption Layer, Open Host Service, Published Language, and Separate Ways. Identify which side is upstream and downstream and whether the relationship is observed or proposed. A Context Map models context relationships; a deployment map models running units. Source lenses: B05 and W10.

## Apply, do not recite

Use one main concept per checkpoint. Mention a second only to explain an important distinction. State the actual subject, evidence, consequence, and check. Record unsupported applicability as unknown, and justified irrelevance as not applicable. Do not generate dozens of empty findings merely to mention every term.
