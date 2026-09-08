# Strategic Domain Review

Paths named below are relative to the loaded skill root.

Three questions: are the **bounded-context boundaries** right; does the code speak the **ubiquitous language**; and when contexts integrate, is the right **integration pattern** used to protect each model?

### Lens A1 — Bounded-context boundaries (Ch. 3, 10)

A bounded context is a **consistency boundary for one model and one ubiquitous language**. Check the change respects it:

- **Cross-context ripple.** A "single" change that must touch several services in lockstep signals a boundary in the wrong place — these should evolve independently. Changes spanning multiple contexts are expensive and a design smell. Flag what's rippling and why.
- **Model bleed.** One context reaching into another's internal entities/tables instead of going through its published interface/events (a worker importing another service's internals).
- **Term collision = boundary signal.** The _same word meaning different things_ in two places (a "Customer" in finance vs. in dispatch) is the classic cue that you're at a context boundary and need translation, not a shared type.
- **Boundary sizing.** Don't optimize for "smallest service" — size the context to its model. For volatile/uncertain areas (core subdomains, new domains), **start wider** and split later.

### Lens A2 — Ubiquitous language (Ch. 2, 6)

The model and code should use the **exact terms domain experts use**, consistently within the context:

- **Naming drift.** Code names that don't match how the business talks (`processData`, `handleStuff`) where the domain has a precise word (`settleTicket`, `voidWeighing`), and CRUD names hiding a real business process. Rename to the business term.
- **Technical-jargon model.** Names describing mechanics (`status_int`, `flag2`, `misc_json`) instead of business concepts. The model should read like the domain, not the database.
- **Inconsistent vocabulary.** The same concept under three names (`vendor`/`supplier`/`seller`) — converge on the business's word. _Different_ words for the same thing inside one context is a defect; the same word in _two_ contexts meaning two things is fine (that's why they're separate).
- **Primitive obsession at the boundary.** Concepts passed as bare strings/numbers across module lines where a named type would carry the meaning (Lens B4 in `references/tactical-review.md`).
- **Where the language lives:** keep the domain language in shared-kernel/domain entities; don't let HTTP/DTO/persistence shapes redefine the vocabulary.

### Lens A3 — Integration patterns between contexts (Ch. 4, 9)

When the change makes two contexts talk, name and check the relationship — the right pattern protects each side's model. Read `references/context-patterns.md` before classifying a relationship or when a finding needs the full definition, boundary heuristics, or book provenance. Flag:

- **Anticorruption Layer (ACL)** — expect one whenever integrating an external system or third party. Flag direct use of a foreign model deep inside our domain.
- **Open-Host Service (OHS)** — consumers should depend on the published contract, not internals (an OpenAPI-generated client layer is an OHS-style boundary).
- **Conformist** — acceptable only when upstream's model is good enough and you can't influence it; risky for core subdomains.
- **Shared Kernel** — flag growth of a shared kernel with context-specific logic that should live in one service.
- **Separate Ways** — no integration; valid when integration cost outweighs the duplication.
- **Async integration** — across contexts, events must publish reliably (**outbox**) and multi-step cross-context flows need a **saga** or **process manager**, not synchronous chained calls (Lens B5 in `references/tactical-review.md`).

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
