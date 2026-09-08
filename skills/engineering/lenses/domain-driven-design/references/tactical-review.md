# Tactical Domain Review

Paths named below are relative to the loaded skill root.

Two questions: is this the **right business-logic pattern** for this subdomain (decision tree), and if it's a domain model, do the **aggregates and value objects** hold their invariants and publish events safely (correctness rules)?

### First: classify the subdomain

Pattern choice follows from subdomain type:

- **Core** — competitive advantage, complex & volatile rules (pricing, compliance logic, lifecycle, optimization). Deserves the expensive patterns.
- **Supporting** — bespoke but simple, mostly CRUD/validation around core. Keep it cheap.
- **Generic** — solved problems you'd buy/integrate (auth, PDF, connectors). Don't hand-roll a domain model.

If the _language_ is mostly CRUD ("create/update/list X"), it's simple. If it's processes, rules, and invariants ("escalate", "settle", "reconcile", "void", "authorize", "allocate"), it's complex. Place domain models in shared domain/entities code, not in route/HTTP handlers; don't leave money/audit logic as a bare transaction script.

### Lens B1 — Business-logic pattern decision tree (Ch. 10)

Walk top-down; stop at the first match. Bias: **use the simplest pattern that works**, escalate only when forced.

1. **Tracks money / needs a consistent audit log / needs deep behavioral analytics?** → **Event-sourced domain model** (state is a stream of events; requires CQRS to query).
2. **Else — business logic genuinely complex** (rules, invariants, algorithms)? → **Domain model** (aggregates + value objects; ports & adapters; testing pyramid).
3. **Else — complex data structures** but logic is procedural validation? → **Active record** (objects encapsulate DB mapping; layered + service layer; testing diamond).
4. **Else** → **Transaction script** (a procedure per operation; minimal layers; lean on end-to-end tests).

**Validation check:** if you called something a _core_ subdomain but the best-fit pattern is transaction script/active record — or a _supporting_ subdomain wants a full domain model — the subdomain classification is probably wrong. Flag the mismatch; it's a signal, not noise.

### Lens B2 — Architecture & testing follow the pattern (Ch. 8, 10)

Once the pattern is chosen, these are near-mechanical:

- **Event-sourced** → **CQRS** required (otherwise you can only fetch one instance by id).
- **Domain model** → **ports & adapters** (aggregates/value objects stay persistence-ignorant) → **testing pyramid**.
- **Active record** → **layered + application/service layer** → **testing diamond** (logic spans service + record layers).
- **Transaction script** → **minimal 3-layer** → **reversed pyramid** (lean on end-to-end).
- **CQRS exception:** worth it for _any_ pattern when the same data needs multiple persistent read models.

Flag combinations that fight each other: a domain model leaking persistence into the aggregate; an event-sourced model with no read-side projection.

### Lenses B3–B5 — Domain-model correctness (only on the domain-model branch)

These apply **only** when Lens B1 lands on a domain model. Each has full hard rules in `references/decision-trees.md` — read it before reviewing the matching code, and review against _every_ rule, not just the first that catches.

- **Lens B3 — Aggregate correctness (Ch. 6).** Transaction boundaries, command-only state changes, thin app layer, concurrency guard, smallest boundary. Review each aggregate against ALL the hard rules — passing one does not make it clean.
- **Lens B4 — Value objects & ubiquitous language (Ch. 6).** Primitive obsession, immutability, behavior-on-the-value, business-language names. (Lens A2 in `references/strategic-review.md` owns the full ubiquitous-language lens.)
- **Lens B5 — Reliable domain-event publishing (Ch. 9).** Don't publish from inside the aggregate or before commit; use an outbox; route cross-aggregate flows through a saga or process manager. Outbox mechanics and saga-vs-process-manager are in the reference.

### Lens B6 — Has the pattern been outgrown? (Ch. 11)

The signal is **pain**: adding a rule keeps getting harder, inconsistencies/duplication creep in. Recommend the next step up only when pain is real:

- **Transaction script → active record:** data handling got gnarly; encapsulate the structures.
- **Active record → domain model:** rules/invariants multiplying. Extract value objects, then make setters private — the compile errors show the real transaction boundaries.
- **Domain model → event-sourced:** the business now needs full history / audit / time-travel.

Don't over-escalate: a stable, simple supporting subdomain does **not** need a domain model just because it's "important." Migration also runs downward — a demoted subdomain should be simplified back down.

### Tactical output format

```
## DDD Tactical review
### Subdomain & pattern
- <feature> looks like a <core/supporting/generic> subdomain → recommend <pattern> (because <reason>). [mismatch note if off]
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

Read `references/decision-trees.md` when the pattern classification is borderline (you need the verbatim decision tree), when reviewing aggregate/event code in depth (optimistic-lock shape, command-style choice, outbox mechanics, saga vs process manager), or when citing book provenance.
