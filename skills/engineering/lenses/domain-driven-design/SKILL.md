---
name: domain-driven-design
description: "Review domain boundaries, business language, aggregates, and domain events. Use when a change crosses bounded contexts or restructures business rules within one context."
---

# Domain-Driven Design

Review the domain shape of a change through Vlad Khononov's _Learning Domain-Driven Design_. Two routes compose:

- **Strategic**: where the boundaries are. Bounded contexts, **ubiquitous language**, and how contexts integrate.
- **Tactical**: how one context is built. The business-logic pattern, and whether aggregates and value objects hold their invariants and publish events safely.

When a change does both, run strategic first; the boundaries constrain the internal design. Layering belongs to `software-design-philosophy`, connascence to `coding-review-simplify`, and system style and service decomposition to `architecture-lens`.

Derive the context map from the repository's service and module layout before reviewing: each service or module that owns a model and a slice of the language is a candidate bounded context. A **subdomain** is a problem area (pricing, dispatch, compliance); a **bounded context** is the solution boundary where one model and one language hold. They often align, but not always.

## Strategic route

### Boundaries

A bounded context is the consistency boundary of one **ubiquitous language**.

- **Cross-context ripple**: a single change that must touch several contexts in lockstep means the boundary is in the wrong place.
- **Model bleed**: one context reaching into another's entities or tables instead of its published interface or events.
- **Term collision**: the same word meaning different things in two places (a finance "customer" and a dispatch "customer") marks a boundary that needs translation, not a shared type.
- **Sizing**: size a context to its model, not to "smallest service". For volatile or uncertain areas, start wide and split later; logical boundaries are cheap to move and physical ones are not. One team owns a context.

### Ubiquitous language

Code uses the exact terms domain experts use (class, method, table, field, test, and doc names), consistently within one context and free to differ across contexts.

- **Naming drift**: `processData` or a CRUD name where the business has a precise process verb (`settle`, `void`, `allocate`).
- **Technical-jargon model**: `status_int`, `flag2`, `misc_json` instead of business concepts.
- **Synonym split**: one concept under several names (`vendor`, `supplier`, `seller`) inside one context. Converge on the business's word.
- **Shape leak**: HTTP, DTO, or persistence shapes redefining the vocabulary.

### Integration patterns

When the change makes two contexts talk, name the relationship and check that it protects each model:

| Pattern | Use when | Flag |
| --- | --- | --- |
| **Partnership** | Two teams succeed or fail together and coordinate ad hoc | Partnership claimed between teams that do not coordinate |
| **Shared Kernel** | A small, stable model subset genuinely shared | Context-specific logic creeping into it; every change ripples to all sharers |
| **Conformist** | Upstream's model is good enough and cannot be influenced | Conforming inside a core subdomain |
| **Anticorruption Layer** | Integrating an external, legacy, or third-party system | A foreign model used deep inside the domain; translation belongs at the edge |
| **Open-Host Service** | A context with many consumers exposes a versioned **published language** | Consumers bound to internals instead of the published contract |
| **Separate Ways** | Integration costs more than duplication | Integration built where duplicating is cheaper |

Asynchronous integration across contexts publishes through an **outbox**, and multi-step cross-context flows run through a **saga** or **process manager**, not chained synchronous calls (see Event publishing). Watch for a distributed big ball of mud: temporal coupling (B must run right after A), functional coupling (B duplicates A's rules), and implementation coupling (B consumes A's internal event shape). Consumers take published events, not raw internal ones.

### Subdomain type

- **Core**: competitive advantage, complex and volatile rules. Build in-house and model richly.
- **Supporting**: necessary, simple, mostly CRUD and validation. Keep it cheap.
- **Generic**: solved elsewhere (auth, PDF, payments, ERP connectors). Integrate it rather than model it.

Types drift, and the signal is pain when extending the area. Supporting becoming core earns a richer model; core becoming supporting earns simplification. Surface a mismatch as a prompt to revisit the classification, not as a hard rule.

## Tactical route

### Business-logic pattern

The language is the first clue: "create, update, list" is simple; "escalate, settle, reconcile, authorize" is complex. Choose the **smallest coherent shape** that meets the actual guarantees:

1. **Integrity or history the current model cannot meet?** Name the invariant, retention, and replay need, and show that transactions, constraints, an immutable audit record, or a ledger cannot meet it. Only that gap opens an **event-sourced domain model**, with owners for schema evolution, replay side effects, and read projections. A money field or an audit-log request alone does not select it.
2. **Complex rules or invariants**: **domain model**.
3. **Complex data mapping with procedural validation**: **active record**.
4. **Otherwise**: **transaction script**.

Architecture and testing follow almost mechanically:

| Pattern | Architecture | Testing |
| --- | --- | --- |
| Event-sourced | CQRS (required) | as domain model |
| Domain model | Ports and adapters; aggregates persistence-ignorant | Pyramid |
| Active record | Layered with a service layer | Diamond |
| Transaction script | Minimal layers | Reversed pyramid |

CQRS is worth it for any pattern when the same data needs several persistent read models. Flag combinations that fight: persistence leaking into an aggregate, or an event-sourced model with no projection.

A core subdomain whose best fit is a transaction script, or a supporting one that wants a full domain model, means the classification is probably wrong. Flag the mismatch.

### Aggregates (domain model only)

Review each aggregate against every rule; passing one does not make it clean.

- **One aggregate per transaction.** Writing two in one transaction means a wrong boundary. Strong consistency inside, eventual consistency (domain events) across.
- **State changes only through the aggregate's commands.** A public setter is a leak. The aggregate enforces all its invariants in one place.
- **Thin application layer**: load, execute command, save, return. Business rules in the service are misplaced.
- **Concurrency guard**: a version field with an optimistic check (`WHERE version = @expected`), so a stale write is rejected.
- **Smallest boundary the invariants allow.** Reference other aggregates by id, not by holding the object.

### Value objects (domain model only)

- **Primitive obsession**: `amount: number`, `email: string`, `countryCode: string` where `Money`, `EmailAddress`, or `CountryCode` would centralize validation and make invalid states unrepresentable.
- **Immutable**: a change yields a new instance. A value object with setters is an entity or a bug.
- **Equal by value**, with no synthetic id, and **self-validating** on construction, so callers never hold an invalid value.
- **Behavior on the value**: `money.add(...)`, `weight.convertTo(...)`, not scattered in services.

### Event publishing (domain model only)

- **Publishing from inside the aggregate, or before commit**, lets a subscriber see an event that contradicts committed state.
- **Publishing after commit without an outbox** loses the event when the process dies between the two.
- **Outbox**: commit the new state and its events in one transaction (an outbox table, or embedded in the record for NoSQL); a relay reads them, publishes to the bus, and marks them sent.
- **Saga**: reacts to events from one aggregate or context and issues commands to another, compensating on failure. For simple reactive flows.
- **Process manager**: owns the explicit state of a multi-step, branching process and is itself an aggregate.

### Outgrown patterns

Escalate one step only when extending the area genuinely hurts:

- Transaction script to active record: the data handling became tangled.
- Active record to domain model: rules multiply. Extract value objects, then make setters private; the compile errors reveal the real transaction boundaries.
- Domain model to event-sourced: only after the gap in step 1 is shown. Preserve known history, mark unknown history, and never invent past transitions.

Migration runs downward too: a demoted subdomain is simplified back. An important but stable supporting area keeps its simple pattern.

## Verdict

Lead with the highest-impact finding. Each finding gives the file and line, the rule by name, and the fix, and separates evidence from an unresolved domain decision. A clean route needs no invented finding. Blocking findings are broken invariants and integration boundaries; naming preferences are advisory. End with one line: the boundaries and pattern are sound, or the top one or two corrections.
