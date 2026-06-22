# DDD Tactical — Decision Trees & Checklists

Deep-dive reference for the `domain-driven-design` skill (tactical part — Part B). SKILL.md carries the operational
lenses; this file keeps only the verbatim figures and the details that go beyond them.
Source: *Learning Domain-Driven Design*, Vlad Khononov (O'Reilly, 2021), Chapters 5–11 —
Ch. 6 (aggregates & value objects), Ch. 9 (event publishing), Ch. 10 (pattern &
architecture decision trees, Figs. 10-3/10-4/10-7), Ch. 11 (evolving patterns).

## Business-logic pattern decision tree — verbatim (Ch. 10, Fig. 10-3 / 10-7)

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

The architecture/testing mapping that follows from each pattern is Ch. 10, Fig. 10-4 —
see SKILL.md Lens 2.

## Lens 3 — Aggregate correctness (Ch. 6) — only when it's a domain model

**Exhaustiveness bar: review each aggregate against ALL of the hard rules below — a
single passing rule does not make the aggregate clean.**

- **One aggregate per transaction.** A single operation may modify exactly one aggregate
  instance, committed atomically. Needing to write two aggregates in one transaction =
  **wrong boundary**. Eventual consistency (domain events) across aggregates; strong
  consistency within.
- **State changes only through the aggregate's own command methods.** External code reads
  state but never mutates it. Public setters on an aggregate/entity = leak. The aggregate's
  public interface validates input and enforces *all* invariants in one place.
- **The application layer stays thin:** load → execute command → save → return. Business
  rules that live in the service instead of the aggregate are misplaced.
- **Concurrency is guarded** — version field + optimistic check on write. Without it,
  concurrent updates silently corrupt state.
- **Boundaries as small as the invariants allow.** Don't pull unrelated entities into an
  aggregate just because they're related in the DB. Reference other aggregates by **id**,
  not by holding the object.

Details beyond the rules:

- **Optimistic-lock shape:** version field, incremented on write, with an optimistic
  check (`WHERE version = @expected`) so a stale write is rejected and retried.
- **Commands** may be plain methods (`ticket.AddMessage(...)`) or explicit command
  objects passed to `Execute(cmd)` — either is fine; be consistent.

## Lens 4 — Value objects & ubiquitous language (Ch. 6)

- **Primitive obsession.** Domain concepts modeled as bare `string`/`number`/`Date` —
  `countryCode: string`, `email: string`, `amount: number` — should be value objects
  (`Money`, `EmailAddress`, `Weight`) that centralize validation + behavior and make
  invalid states unrepresentable. Especially money, weights, and measures in this domain.
- **Value objects are immutable.** A change produces a new instance. A "value object" with
  setters is really an entity (or a bug).
- **Behavior, not just data.** Logic that manipulates a value belongs *on* the value object
  (`weight.convertTo(...)`, `money.add(...)`), not scattered in services.
- **Names speak the business language.** Code that reads as generic CRUD when the domain
  experts speak in processes is a naming/modeling smell — see Part A Lens A2 for the
  full ubiquitous-language lens.

Details beyond the rules:

- **Identity by value.** Two instances with equal fields are equal; no synthetic id.
- **Self-validating construction.** `EmailAddress.parse(...)` guarantees validity, so
  callers never hold an invalid value and validation isn't duplicated.

## Lens 5 — Reliable domain-event publishing (Ch. 9) — EDA-critical here

Flag:

- **Publishing from inside the aggregate**, or **publishing before the DB commit** — a
  subscriber can see an event that contradicts (or never matches) committed state.
- **Publish-after-commit in app code without an outbox** — if the process dies between
  commit and publish, the event is lost and the system is inconsistent.
- **Correct shape = outbox:** state change + outgoing event committed in one atomic
  transaction; a relay reads the outbox and publishes to the bus, marking sent. Look for
  this when domain events cross a transaction/bus boundary.
- **Cross-aggregate / cross-context workflows** that need a **saga** (reacts to events,
  issues commands, compensates on failure) or **process manager** (owns the state of a
  multi-step flow) — not a synchronous multi-aggregate write.

**Outbox mechanics (4 steps):**
1. Commit the aggregate's new state **and** the new domain events in one atomic DB
   transaction (dedicated outbox table, or embedded in the aggregate record for NoSQL).
2. A message relay polls newly committed events.
3. Relay publishes them to the message bus.
4. On success, mark/delete the published events.

**Saga vs process manager:**
- **Saga** — a component that listens to events from one aggregate/context and issues
  commands to another, with compensating actions on failure. For simple reactive flows.
- **Process manager** — owns the explicit state of a multi-step business process (it *is*
  an aggregate). For sequential/branching workflows that need their own lifecycle.

## Evolving patterns — details beyond Lens 6 (Ch. 11)

- "This is getting painful" ⇒ reassess the subdomain *type*, not just the pattern.
- Transaction script → active record: stop hitting the DB directly once the structures
  are encapsulated.
- Domain model → event-sourced: generate past transitions and model explicit migration
  events to backfill history.
- Migrations also run the other way (core → supporting) — then it's fine to *simplify* a
  domain model back down. Don't treat escalation as one-directional.
