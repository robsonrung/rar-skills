---
name: ddd-tactical
description: Pick and review the right tactical Domain-Driven Design pattern for code under change — business-logic pattern (transaction script / active record / domain model / event-sourced) via the decision tree, plus aggregate & value-object correctness (transaction boundaries, invariants, immutability, reliable event publishing). Use when starting a new feature/subdomain and asking "how should this be structured", when a service is accreting business rules, when reviewing an aggregate/entity/value-object, or when domain events feel risky to publish. Distinct from model-lens (generic layering/cohesion), architect-lens (trade-offs/connascence), and code-review (bugs).
---

# DDD Tactical Lens — Right Pattern, Correct Aggregates

Decide and review the **tactical** design of code through the lenses from *Learning
Domain-Driven Design* (Vlad Khononov, O'Reilly), Parts II–III. This is **not** a generic
layering/cohesion check (use `model-lens`) and **not** a bug hunt (use `code-review`). It
asks two questions:

1. **Is this the right business-logic pattern for this subdomain?** (decision tree)
2. **If it's a domain model, do the aggregates and value objects actually hold their
   invariants and publish events safely?** (correctness rules)

Apply the relevant lenses, report findings grouped by lens, cite `file:line`, name the
rule, propose the fix. Skip lenses that don't apply rather than padding. If it's clean,
say so plainly.

## First: classify the subdomain

Pattern choice follows from subdomain type. Before recommending, place the work:

- **Core** — competitive advantage, complex & volatile rules (pricing, netValue,
  compliance logic, ticket/booking lifecycle, freight-lane optimization). Deserves the
  expensive patterns.
- **Supporting** — bespoke but simple, mostly CRUD/validation around core. Keep it cheap.
- **Generic** — solved problems you'd buy/integrate (auth via Amplify, PDF rendering,
  ERP connectors). Don't hand-roll a domain model here.

If the *language* is mostly CRUD ("create/update/list X"), it's simple. If it's processes,
rules, and invariants ("escalate", "settle", "reconcile", "void"), it's complex.

## Lens 1 — Business-logic pattern decision tree (Ch. 10)

Walk the tree top-down; stop at the first match. The book's bias — and this repo's —
is **use the simplest pattern that works**, escalate only when forced.

1. **Tracks money / needs a consistent audit log / needs deep behavioral analytics?**
   → **Event-sourced domain model** (state is a stream of events; requires CQRS to query).
2. **Else — business logic genuinely complex** (rules, invariants, algorithms)?
   → **Domain model** (aggregates + value objects; ports & adapters; testing pyramid).
3. **Else — complex data structures** but logic is procedural validation?
   → **Active record** (objects encapsulate DB mapping; layered + service layer; testing
   diamond).
4. **Else** → **Transaction script** (a procedure per operation; minimal layers; lean on
   end-to-end tests).

**Validation check:** if you called something a *core* subdomain but the best-fit pattern
is transaction script/active record — or a *supporting* subdomain wants a full domain
model — your subdomain classification is probably wrong. Flag the mismatch; it's a signal,
not noise.

**In this repo:** most `core-api` routes/services are transaction-script-shaped
orchestration. Real domain models belong in `backend/common` entities/domain and
`gslogic`. Don't push a domain model into a Fastify handler; don't leave money/audit logic
as a bare transaction script.

## Lens 2 — Architecture & testing follow the pattern (Ch. 8, 10)

Once the business-logic pattern is chosen, these are near-mechanical:

- **Event-sourced** → **CQRS** required (otherwise you can only fetch one instance by id).
- **Domain model** → **ports & adapters** (so aggregates/value objects stay
  persistence-ignorant). → **testing pyramid** (aggregates make perfect units).
- **Active record** → **layered + application/service layer** (logic that drives the active
  records). → **testing diamond** (logic spans service + record layers, so integration).
- **Transaction script** → **minimal 3-layer**. → **reversed pyramid** (lean on end-to-end).
- **CQRS exception:** worth it for *any* pattern when the same data needs multiple
  persistent read models — not only for event sourcing.

Flag combinations that fight each other: a domain model wired through a layered
architecture that leaks persistence into the aggregate; an event-sourced model with no
read-side projection.

## Lens 3 — Aggregate correctness (Ch. 6) — only when it's a domain model

Review each aggregate against these hard rules:

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
  experts speak in processes is a naming/modeling smell — see `ddd-strategic` for the
  full ubiquitous-language lens.

## Lens 5 — Reliable domain-event publishing (Ch. 9) — EDA-critical here

greenspark-aws is event-driven (EventBridge / `eda-worker` / `erp-sync-workflow`), so this
matters. Flag:

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

## Lens 6 — Has the pattern been outgrown? (Ch. 11)

The signal is **pain**: adding a rule keeps getting harder, inconsistencies/duplication
creep in. Recommend the next step up only when the pain is real:

- **Transaction script → active record:** data handling got gnarly; encapsulate the
  structures.
- **Active record → domain model:** rules/invariants multiplying, inconsistencies
  appearing. Start by extracting value objects, then make setters private — the compile
  errors show you where the real transaction boundaries are.
- **Domain model → event-sourced:** the business now needs the full history / audit /
  time-travel, not just current state.

Don't over-escalate: a stable, simple supporting subdomain does **not** need a domain
model just because it's "important."

## Output format

```
## DDD Tactical review

### Subdomain & pattern
- <feature> looks like a <core/supporting/generic> subdomain → recommend <pattern>
  (because <decision-tree reason>). [mismatch note if classification seems off]

### Aggregate correctness
- [file:line] <rule broken> — <fix>

### Value objects / language
- [file:line] <primitive obsession / mutable VO> — model as <value object>

### Event publishing
- [file:line] <publishes before commit / no outbox> — <fix>

### Pattern fit over time
- <outgrown? recommend next step, or "appropriate, hold">

### Verdict
<one line: right pattern + the top 1–2 corrections, or "clean">
```

Lead with the highest-leverage finding. If a lens is clean, write "clean" — don't invent
findings to fill it. See `references/decision-trees.md` for the full trees, the
aggregate/value-object checklist, and the book provenance behind each lens.
