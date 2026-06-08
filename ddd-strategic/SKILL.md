---
name: ddd-strategic
description: Review the strategic Domain-Driven Design shape of a change — bounded-context boundaries, ubiquitous-language naming drift, and cross-context integration patterns (anticorruption layer, open-host service, conformist, saga, outbox, separate ways). Use when adding/moving a service or module, when code crosses a service/context boundary, when naming feels off from how the business talks, when integrating with a third party or another team's service, or when a change ripples across many contexts. Distinct from ddd-tactical (pattern/aggregate correctness inside one context), model-lens (generic layering), and architect-lens (trade-offs/connascence).
---

# DDD Strategic Lens — Boundaries, Language, Integration

Review the **strategic** shape of a change through the lenses from *Learning Domain-Driven
Design* (Vlad Khononov, O'Reilly), Parts I, III–IV. This is **not** about which pattern a
class uses inside a context (use `ddd-tactical`) and **not** a generic layering check (use
`model-lens`). It asks three questions:

1. **Are the bounded-context boundaries right** — does this change stay inside one context,
   or does it leak across and couple things that should be independent?
2. **Does the code speak the business's ubiquitous language**, consistently within its
   context?
3. **When contexts integrate, is the right integration pattern used** to protect each
   model?

Apply the relevant lenses, report findings grouped by lens, cite `file:line`, name the
rule, propose the fix. Skip lenses that don't apply. If it's clean, say so.

## Map: contexts in greenspark-aws

The backend services are the physical bounded contexts; each owns a model and a slice of
the ubiquitous language:

- `core-api` — main transactional model (scale ops, inventory, customers, finance).
- `dispatch` — asset & dispatch management.
- `erp-sync-workflow` — integration with external ERPs (QBO/QBD/Xero/Dynamics/Intacct…).
- `eda-worker` — event-driven processing off EventBridge.
- `compliance` — regulatory reporting.
- `pdf-generator` — document generation.
- `backend/common` + `gslogic` — shared kernel of entities/domain logic.
- `frontend/client` — its own model (RTK Query API layer generated from OpenAPI).

A *subdomain* is a problem area (pricing, dispatch, compliance); a *bounded context* is the
solution boundary where one model/language holds. They often align here but not always.

## Lens 1 — Bounded-context boundaries (Ch. 3, 10)

A bounded context is a **consistency boundary for one model and one ubiquitous language**.
Check whether the change respects it:

- **Cross-context ripple.** A "single" change that has to touch `core-api` *and* `dispatch`
  *and* `compliance` in lockstep signals a boundary in the wrong place — these should evolve
  independently. The book: changes spanning multiple contexts are expensive and a design
  smell. Flag what's rippling and why.
- **Model bleed.** One context reaching into another's internal entities/tables instead of
  going through its published interface/events. `erp-sync-workflow` reading `core-api`'s
  internal model directly, a worker importing another service's internals.
- **Term collision = boundary signal.** The *same word meaning different things* in two
  places (a "Customer" in finance vs. in dispatch) is the classic cue that you're at a
  context boundary and need translation, not a shared type.
- **Boundary sizing.** Don't optimize for "smallest service." Size the context to its model.
  For volatile/uncertain areas (core subdomains, new domains), **start wider** and split
  later — refactoring a logical boundary is cheap; refactoring a physical one isn't.

## Lens 2 — Ubiquitous language (Ch. 2, 6)

The model and the code should use the **exact terms the domain experts use**, consistently
within the context:

- **Naming drift.** Code names that don't match how the business talks (`processData`,
  `handleStuff`, `tmpFlag`) where the domain has a precise word (`settleTicket`,
  `voidWeighing`, `reconcileLoad`). Rename to the business term.
- **Technical-jargon model.** Class/table/field names describing mechanics
  (`status_int`, `flag2`, `misc_json`) instead of business concepts. The model should read
  like the domain, not like the database.
- **Inconsistent vocabulary.** The same concept under three names across files
  (`vendor` / `supplier` / `seller`) — pick the business's word and converge. *Different*
  words for the same thing inside one context is a defect; the same word in *two* contexts
  meaning two things is fine (that's why they're separate contexts).
- **Primitive obsession at the boundary.** Concepts passed as bare strings/numbers across
  module lines where a named type would carry the meaning (see `ddd-tactical` Lens 4).
- **Where the language lives:** keep the domain language in `common`/`gslogic`/domain
  entities; don't let HTTP/DTO/persistence shapes redefine the vocabulary.

## Lens 3 — Integration patterns between contexts (Ch. 4, 9)

When this change makes two contexts talk, name and check the relationship. The right
pattern protects each side's model:

- **Anticorruption Layer (ACL)** — the consuming context translates the other's model into
  its own at the boundary, so a foreign/legacy/messy model doesn't leak in. **Expect an ACL
  whenever we integrate an external ERP** (`erp-sync-workflow`) or any third party. Flag
  direct use of a foreign model deep inside our domain.
- **Open-Host Service (OHS)** — a context that's consumed by many publishes a stable,
  versioned *published language* (a public API/event contract) decoupled from its internal
  model. Check that consumers depend on the published contract, not internals. The
  OpenAPI-generated frontend API layer is an OHS-style boundary.
- **Conformist** — downstream simply accepts upstream's model (no translation). Acceptable
  only when upstream's model is good enough and you can't influence it; risky for core
  subdomains.
- **Shared Kernel** — a shared model owned jointly (here: `common`/`gslogic`). Powerful but
  high-coordination; every change ripples to all sharers. Flag growth of the kernel with
  context-specific logic that should live in one service instead.
- **Separate Ways** — sometimes the cheapest integration is *none* (duplicate rather than
  couple). Valid when integration cost outweighs the duplication.
- **Async integration** — across contexts on EventBridge, events must publish reliably
  (**outbox**) and multi-step cross-context flows need a **saga** or **process manager**,
  not synchronous chained calls. (Detailed in `ddd-tactical` Lens 5.)

## Lens 4 — Subdomain-type drift (Ch. 1, 11)

Strategic classification can change, and it should drive implementation effort:

- **Supporting/generic → core.** If a once-simple area is now where the business competes
  (and adding rules keeps hurting), it deserves in-house investment and a richer model.
  Stop outsourcing/CRUD-ing it.
- **Core → supporting.** If an area stopped being a differentiator, simplify it — don't keep
  paying domain-model tax for it.
- **Don't hand-build generic subdomains.** Auth, PDF, ERP connectors — integrate, don't
  model from scratch.

The trigger is the same as tactical: **pain** when extending it. Surface the mismatch as a
prompt to revisit the classification, not a hard rule.

## Output format

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
<one line: boundaries clean or the top 1–2 strategic risks to address>
```

Lead with the highest-leverage finding. If a lens is clean, write "clean" — don't invent
findings. See `references/context-patterns.md` for the integration-pattern catalog,
boundary heuristics, and the book provenance behind each lens.
