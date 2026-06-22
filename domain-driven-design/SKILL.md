---
name: domain-driven-design
description: Review code or a design with Domain-Driven Design — from strategic context shape (bounded-context boundaries, ubiquitous-language naming drift, cross-context integration patterns like anticorruption layer / open-host service / conformist / saga / outbox / separate ways) down to tactical pattern & aggregate correctness (transaction script / active record / domain model / event-sourced via a decision tree; aggregate transaction boundaries, invariants, value-object immutability, reliable event publishing). Use when adding/moving a service or module, when code crosses a service/context boundary, when naming feels off from how the business talks, when integrating a third party, when a change ripples across contexts, when starting a new feature/subdomain ("how should this be structured"), when a service is accreting business rules, when reviewing an aggregate/entity/value-object, or when domain events feel risky to publish. Distilled from Khononov's "Learning Domain-Driven Design". Distinct from architecture-lens (generic layering/cohesion and trade-offs/connascence), macro-architecture (macro style selection + service decomposition / data ownership), and code-review (bugs).
---

# Domain-Driven Design

Review the domain shape of a change through the lenses from *Learning Domain-Driven Design* (Vlad Khononov, O'Reilly). DDD works at two altitudes that compose:

- **Strategic** (Parts I, III–IV) — *where the boundaries are*: bounded contexts, ubiquitous language, and how contexts integrate.
- **Tactical** (Parts II–III) — *how one context is built*: the business-logic pattern, and whether aggregates/value-objects hold their invariants and publish events safely.

This is **not** a generic layering/cohesion check or trade-off/connascence audit (use `architecture-lens`), **not** macro style selection or service decomposition (use `macro-architecture`), and **not** a bug hunt (use `code-review`).

## Pick your zoom (read only the part you need)

- **Change crosses or moves a context/service boundary, naming drifts from the business, or integrates another system** → **Part A — Strategic**.
- **Change structures business logic inside one context** — choosing the pattern, reviewing an aggregate/entity/value-object, publishing domain events → skip directly to **Part B — Tactical**.
- **Change does both** (a cross-context change that also reshapes a context's internals) → do Part A first (boundaries constrain the tactical choices), then Part B.

Apply only the relevant lenses, report findings grouped by lens, cite `file:line`, name the rule, propose the fix. Skip lenses that don't apply. If it's clean, say so.

**Deriving the context map:** the physical bounded contexts are usually the backend services/modules, each owning a model and a slice of the ubiquitous language (e.g. a transactional core service, an integration/sync service, an event worker, a shared kernel of domain entities, the frontend's own API-layer model). Derive this map from the repo's service/module layout before reviewing. A *subdomain* is a problem area (pricing, dispatch, compliance); a *bounded context* is the solution boundary where one model/language holds — they often align but not always.

---

## Part A — Strategic: boundaries, language, integration

Three questions: are the **bounded-context boundaries** right; does the code speak the **ubiquitous language**; and when contexts integrate, is the right **integration pattern** used to protect each model?

### Lens A1 — Bounded-context boundaries (Ch. 3, 10)

A bounded context is a **consistency boundary for one model and one ubiquitous language**. Check the change respects it:

- **Cross-context ripple.** A "single" change that must touch several services in lockstep signals a boundary in the wrong place — these should evolve independently. Changes spanning multiple contexts are expensive and a design smell. Flag what's rippling and why.
- **Model bleed.** One context reaching into another's internal entities/tables instead of going through its published interface/events (a worker importing another service's internals).
- **Term collision = boundary signal.** The *same word meaning different things* in two places (a "Customer" in finance vs. in dispatch) is the classic cue that you're at a context boundary and need translation, not a shared type.
- **Boundary sizing.** Don't optimize for "smallest service" — size the context to its model. For volatile/uncertain areas (core subdomains, new domains), **start wider** and split later.

### Lens A2 — Ubiquitous language (Ch. 2, 6)

The model and code should use the **exact terms domain experts use**, consistently within the context:

- **Naming drift.** Code names that don't match how the business talks (`processData`, `handleStuff`) where the domain has a precise word (`settleTicket`, `voidWeighing`), and CRUD names hiding a real business process. Rename to the business term.
- **Technical-jargon model.** Names describing mechanics (`status_int`, `flag2`, `misc_json`) instead of business concepts. The model should read like the domain, not the database.
- **Inconsistent vocabulary.** The same concept under three names (`vendor`/`supplier`/`seller`) — converge on the business's word. *Different* words for the same thing inside one context is a defect; the same word in *two* contexts meaning two things is fine (that's why they're separate).
- **Primitive obsession at the boundary.** Concepts passed as bare strings/numbers across module lines where a named type would carry the meaning (see Lens B4).
- **Where the language lives:** keep the domain language in shared-kernel/domain entities; don't let HTTP/DTO/persistence shapes redefine the vocabulary.

### Lens A3 — Integration patterns between contexts (Ch. 4, 9)

When the change makes two contexts talk, name and check the relationship — the right pattern protects each side's model. Read `references/context-patterns.md` before classifying a relationship or when a finding needs the full definition, boundary heuristics, or book provenance. Flag:

- **Anticorruption Layer (ACL)** — expect one whenever integrating an external system or third party. Flag direct use of a foreign model deep inside our domain.
- **Open-Host Service (OHS)** — consumers should depend on the published contract, not internals (an OpenAPI-generated client layer is an OHS-style boundary).
- **Conformist** — acceptable only when upstream's model is good enough and you can't influence it; risky for core subdomains.
- **Shared Kernel** — flag growth of a shared kernel with context-specific logic that should live in one service.
- **Separate Ways** — no integration; valid when integration cost outweighs the duplication.
- **Async integration** — across contexts, events must publish reliably (**outbox**) and multi-step cross-context flows need a **saga** or **process manager**, not synchronous chained calls (detailed in Lens B5).

### Lens A4 — Subdomain-type drift (Ch. 1, 11)

Strategic classification can change and should drive implementation effort. The trigger is **pain** when extending an area:

- **Supporting/generic → core.** A once-simple area is now where the business competes and adding rules keeps hurting — invest in a richer model.
- **Core → supporting.** No longer a differentiator — simplify; stop paying domain-model tax.
- **Don't hand-build generic subdomains.** Auth, PDF, ERP connectors — integrate, don't model from scratch.

Surface the mismatch as a prompt to revisit the classification, not a hard rule.

### Strategic output format

```
## DDD Strategic review
### Bounded-context boundaries
- [file:line] <cross-context ripple / model bleed> — <fix or boundary question>
### Ubiquitous language
- [file:line] <name> drifts from domain term <X> — rename / model as <type>
### Integration patterns
- [boundary] integrates <A>↔<B> as <conformist/no-ACL/…> — should be <ACL/OHS/…> because <reason>
### Subdomain type
- <area> looks like it's drifting <supporting→core/…> — <implication>
### Verdict
<one line: boundaries clean or the top 1–2 strategic risks>
```

---

## Part B — Tactical: right pattern, correct aggregates

Two questions: is this the **right business-logic pattern** for this subdomain (decision tree), and if it's a domain model, do the **aggregates and value objects** hold their invariants and publish events safely (correctness rules)?

### First: classify the subdomain

Pattern choice follows from subdomain type:

- **Core** — competitive advantage, complex & volatile rules (pricing, compliance logic, lifecycle, optimization). Deserves the expensive patterns.
- **Supporting** — bespoke but simple, mostly CRUD/validation around core. Keep it cheap.
- **Generic** — solved problems you'd buy/integrate (auth, PDF, connectors). Don't hand-roll a domain model.

If the *language* is mostly CRUD ("create/update/list X"), it's simple. If it's processes, rules, and invariants ("escalate", "settle", "reconcile", "void", "authorize", "allocate"), it's complex. Place domain models in shared domain/entities code, not in route/HTTP handlers; don't leave money/audit logic as a bare transaction script.

### Lens B1 — Business-logic pattern decision tree (Ch. 10)

Walk top-down; stop at the first match. Bias: **use the simplest pattern that works**, escalate only when forced.

1. **Tracks money / needs a consistent audit log / needs deep behavioral analytics?** → **Event-sourced domain model** (state is a stream of events; requires CQRS to query).
2. **Else — business logic genuinely complex** (rules, invariants, algorithms)? → **Domain model** (aggregates + value objects; ports & adapters; testing pyramid).
3. **Else — complex data structures** but logic is procedural validation? → **Active record** (objects encapsulate DB mapping; layered + service layer; testing diamond).
4. **Else** → **Transaction script** (a procedure per operation; minimal layers; lean on end-to-end tests).

**Validation check:** if you called something a *core* subdomain but the best-fit pattern is transaction script/active record — or a *supporting* subdomain wants a full domain model — the subdomain classification is probably wrong. Flag the mismatch; it's a signal, not noise.

### Lens B2 — Architecture & testing follow the pattern (Ch. 8, 10)

Once the pattern is chosen, these are near-mechanical:

- **Event-sourced** → **CQRS** required (otherwise you can only fetch one instance by id).
- **Domain model** → **ports & adapters** (aggregates/value objects stay persistence-ignorant) → **testing pyramid**.
- **Active record** → **layered + application/service layer** → **testing diamond** (logic spans service + record layers).
- **Transaction script** → **minimal 3-layer** → **reversed pyramid** (lean on end-to-end).
- **CQRS exception:** worth it for *any* pattern when the same data needs multiple persistent read models.

Flag combinations that fight each other: a domain model leaking persistence into the aggregate; an event-sourced model with no read-side projection.

### Lenses B3–B5 — Domain-model correctness (only on the domain-model branch)

These apply **only** when Lens B1 lands on a domain model. Each has full hard rules in `references/decision-trees.md` — read it before reviewing the matching code, and review against *every* rule, not just the first that catches.

- **Lens B3 — Aggregate correctness (Ch. 6).** Transaction boundaries, command-only state changes, thin app layer, concurrency guard, smallest boundary. Review each aggregate against ALL the hard rules — passing one does not make it clean.
- **Lens B4 — Value objects & ubiquitous language (Ch. 6).** Primitive obsession, immutability, behavior-on-the-value, business-language names. (Part A Lens A2 owns the full ubiquitous-language lens.)
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

---

Lead with the highest-leverage finding. If a lens is clean, write "clean" — don't invent findings to fill it.
