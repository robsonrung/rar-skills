# DDD Tactical — Decision Trees & Checklists

Deep-dive reference for the `ddd-tactical` skill. SKILL.md carries the operational
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

## Aggregate details beyond Lens 3 (Ch. 6)

- **Optimistic-lock shape:** version field, incremented on write, with an optimistic
  check (`WHERE version = @expected`) so a stale write is rejected and retried.
- **Commands** may be plain methods (`ticket.AddMessage(...)`) or explicit command
  objects passed to `Execute(cmd)` — either is fine; be consistent.

## Value-object details beyond Lens 4 (Ch. 6)

- **Identity by value.** Two instances with equal fields are equal; no synthetic id.
- **Self-validating construction.** `EmailAddress.parse(...)` guarantees validity, so
  callers never hold an invalid value and validation isn't duplicated.

## Event-publishing details beyond Lens 5 (Ch. 9)

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
