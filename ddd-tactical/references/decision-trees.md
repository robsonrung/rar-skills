# DDD Tactical — Decision Trees & Checklists

Detailed reference for the `ddd-tactical` skill. Source: *Learning Domain-Driven Design*,
Vlad Khononov (O'Reilly, 2021), Chapters 5–11.

## Business-logic pattern decision tree (Ch. 10, Fig. 10-3 / 10-7)

```
Does the subdomain track money / monetary transactions,
require a consistent audit log, or need deep behavioral analytics?
│
├─ YES ─────────────────────────────► Event-Sourced Domain Model  (→ CQRS)
│
└─ NO → Is the business logic complex
        (intricate rules, invariants, algorithms — not just input validation)?
        │
        ├─ YES ─────────────────────► Domain Model  (→ Ports & Adapters, testing pyramid)
        │
        └─ NO → Does it involve complex data structures
                (non-trivial mapping to storage)?
                │
                ├─ YES ─────────────► Active Record  (→ layered + service layer,
                │                                       testing diamond)
                │
                └─ NO ──────────────► Transaction Script  (→ minimal layers,
                                                            reversed testing pyramid)
```

Complexity heuristic: look at the **ubiquitous language**. CRUD verbs
(create/read/update/delete/list) → simple. Process/rule verbs (escalate, settle,
reconcile, void, authorize, allocate) → complex.

Cross-check: pattern should match subdomain *type*. Core ⇒ domain model or event-sourced.
Supporting ⇒ transaction script or active record. Generic ⇒ integrate, don't model. A
contradiction means the subdomain was misclassified — revisit it.

## Architecture pattern decision tree (Ch. 10, Fig. 10-4)

| Business-logic pattern    | Architecture                          | Testing strategy        |
|---------------------------|---------------------------------------|-------------------------|
| Event-sourced domain model| CQRS (required)                       | Testing pyramid         |
| Domain model              | Ports & adapters                      | Testing pyramid         |
| Active record             | Layered + application/service layer   | Testing diamond         |
| Transaction script        | Layered, minimal (3 layers)           | Reversed pyramid        |

CQRS is *also* justified for any pattern when the same data must be served from multiple
persistent read models.

Why each architecture:
- **Ports & adapters for domain model** — keeps aggregates/value objects ignorant of
  persistence; the layered architecture makes that hard.
- **CQRS for event sourcing** — an event store can only fetch one aggregate by id;
  projections give you queryable read models.
- **Service layer for active record** — somewhere has to hold the procedural logic that
  drives the records.

## Aggregate checklist (Ch. 6)

- [ ] **One aggregate per transaction.** Operation mutates a single aggregate instance,
      committed atomically (all-or-nothing). Multi-aggregate write ⇒ wrong boundary.
- [ ] **Encapsulated state.** No public setters; external code reads only. Mutation happens
      exclusively through command methods on the aggregate's public interface.
- [ ] **Invariants enforced inside.** The aggregate validates every incoming change; all
      related business rules live in one place (the aggregate), not in the service.
- [ ] **Thin application layer.** load → execute command → save → return result. The app
      layer orchestrates a transaction; it doesn't hold domain rules.
- [ ] **Concurrency guard.** Version field, incremented on write, with an optimistic check
      (`WHERE version = @expected`) so a stale write is rejected and retried.
- [ ] **Smallest viable boundary.** Include only what shares a true consistency requirement.
      Reference other aggregates by **id**, never by holding the instance.
- [ ] **Commands** may be plain methods (`ticket.AddMessage(...)`) or explicit command
      objects passed to `Execute(cmd)` — either is fine; be consistent.

## Value object checklist (Ch. 6)

- [ ] **No primitive obsession.** Domain concepts (Money, Weight, EmailAddress, PhoneNumber,
      CountryCode, Color) are types, not bare strings/numbers.
- [ ] **Immutable.** Operations return new instances; no setters.
- [ ] **Self-validating.** Construction (`EmailAddress.parse(...)`) guarantees validity, so
      callers never hold an invalid value. Validation isn't duplicated across the codebase.
- [ ] **Owns its behavior.** Manipulation logic lives on the value object
      (`weight.toImperial()`, `money.add(other)`), centralized and easily unit-tested.
- [ ] **Identity by value.** Two instances with equal fields are equal; no synthetic id.

## Reliable event publishing (Ch. 9)

**Anti-patterns:**
- Publishing from inside the aggregate (events fire before commit; can't be retracted).
- Publishing in the application layer *after* commit but with no durability (process crash
  between commit and publish ⇒ lost event, inconsistent system).

**Outbox pattern (correct):**
1. Commit the aggregate's new state **and** the new domain events in one atomic DB
   transaction (dedicated outbox table, or embedded in the aggregate record for NoSQL).
2. A message relay polls newly committed events.
3. Relay publishes them to the message bus.
4. On success, mark/delete the published events.

**Cross-aggregate coordination:**
- **Saga** — a component that listens to events from one aggregate/context and issues
  commands to another, with compensating actions on failure. For simple reactive flows.
- **Process manager** — owns the explicit state of a multi-step business process (it *is*
  an aggregate). For sequential/branching workflows that need their own lifecycle.

In greenspark-aws these map onto EventBridge + `eda-worker` / `erp-sync-workflow`.

## Evolving patterns — migration signals (Ch. 11)

The universal trigger is **pain**: each new rule is harder to add; duplication and
inconsistencies multiply. "This is getting painful" = reassess subdomain type and pattern.

- **Transaction script → active record:** data access/mapping became complicated.
  Encapsulate the structures in active records; stop hitting the DB directly.
- **Active record → domain model:** logic over the records grew complex; inconsistencies
  appear. Extract value objects first; then make every setter private and let the compile
  errors reveal where state is mutated — those sites define the transaction boundaries.
- **Domain model → event-sourced domain model:** the business needs full history / audit /
  temporal analysis, not just current state. Generate past transitions; model migration
  events.

Migrations also run the other way (core → supporting) — then it's fine to *simplify* a
domain model back down. Don't treat escalation as one-directional.
