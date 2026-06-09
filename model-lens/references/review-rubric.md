# Model Lens — detailed rubric & provenance

Source: *Practical Model-Driven Enterprise Architecture* (Packt, ISBN 9781801076166 /
B17363), Bahaaldine et al. The book teaches TOGAF + ArchiMate 3.1 modeling in Sparx EA.
Most of it is tool-specific; this skill distills only the transferable *modeling
discipline*. Each lens below cites the chapter it came from so you can defend a finding.

---

## Provenance map

| Lens | Book source | Original idea |
|---|---|---|
| Layer placement | Ch 1, 6–8 (Business/Application/Technology layers) | Every element belongs to exactly one architecture layer; layers have distinct concerns. |
| Cohesion | Ch 4 "Keeping your diagram focused" | "A single diagram better tells a single main idea… more than one idea adds noise and confuses the reader." |
| Dependency direction | Ch 4–5 "focused metamodels" | A focused metamodel shows, per element, only the relationships it is *allowed* to have; depend on the exposed **service**, not the **component's** internals (Ch 5 service-vs-component distinction). |
| Scope | Ch 1 "Effort Blackhole" / "boil the ocean" / MVP | Deliver tangible artifacts incrementally; don't expand scope to "do it all" before shipping anything. |
| (cross-cutting) Audience | Ch 5 "views & viewpoints", Ch 4 "Knowing your audience" | A view answers one question for one stakeholder; name who reads it and what concern it serves. |

---

## Lens 1 — Layer placement (expanded checklist)

- [ ] Domain invariants (validation that protects a business rule, not just input shape)
      live in entities/domain (`backend/common`, `gslogic`), not in route handlers,
      components, or migrations.
- [ ] Pricing, weight/SOLAS, compliance, ticket/booking/dispatch lifecycle rules are in
      the business layer and reused, not re-implemented per caller.
- [ ] No AWS SDK / EventBridge / S3 / raw SQL inside domain or business code.
- [ ] No JSX, HTTP status codes, or request/response shapes inside domain logic.
- [ ] Migrations contain schema + data shape only — not business decisions.
- [ ] Frontend talks to the application API; it does not encode infra assumptions.

**Why it matters (book):** the value of EA is "bridging business and IT"; the failure mode
is logic scattered so no layer is the source of truth. Same in code — a rule duplicated
across a handler, a worker, and a component will drift.

## Lens 2 — Cohesion (expanded checklist)

- [ ] Can you write a one-sentence "viewpoint" for the element (who/what-concern) with no
      "and"? If not, it likely models two things.
- [ ] Functions/services do one job; a name like `handleAndSyncAndNotify` is three.
- [ ] No `utils`/`helpers`/`common` dumping ground growing unrelated exports.
- [ ] React components separate fetch / business-rule / presentation concerns.
- [ ] An entity isn't carrying columns/methods for an unrelated bounded concern.

**Book test (Ch 4):** they show a diagram that's "still correct" but bad because it
describes *two* components at once — correctness isn't the bar, **focus** is. A function can
be bug-free and still be wrong because it does two things.

## Lens 3 — Dependency direction (expanded checklist)

- [ ] Imports point down the layer stack: application → business; technology underpins.
      `common` must not import from `core-api`/`frontend`.
- [ ] No sibling service reaching into another service's internals — go through its public
      interface (book: depend on the **service**, not the **component**).
- [ ] New cross-module edge is one the design *allows* — would it appear in that element's
      focused metamodel? If it's a surprising connection, question it.
- [ ] Event-driven boundaries (EventBridge / eda-worker) aren't bypassed by a direct call
      that recreates a hidden coupling.

**Book idea (Ch 4–5):** the focused metamodel exists precisely so contributors know which
relationships are legitimate for a given element. A dependency that wouldn't be on that
diagram is a smell.

## Lens 4 — Scope discipline (expanded checklist)

- [ ] Abstractions have ≥2 real callers or a concrete near-term second use; otherwise
      inline and wait (YAGNI = the book's "don't boil the ocean").
- [ ] The diff matches the stated goal; refactors that crept in are called out separately.
- [ ] No speculative config flags, plugin points, or generic engines the task didn't need.
- [ ] If the change is large, is there a smaller vertical slice (the book's MVP artifact)
      that delivers value now?

**Book idea (Ch 1):** the "Effort Blackhole" — effort that never ends because the scope
keeps expanding ("must finish the whole phase first"). The antidote is shipping a focused
artifact and growing it.

---

## What this skill is NOT

- Not a bug/security finder → use `code-review` / `full-review`.
- Not a coupling/connascence + trade-off coach → use `architect-lens`.
- Not a clean-code refactor pass → use `clean-code`.
- It is the **"is this in the right place, focused, pointed the right way, and scoped"**
  lens, and nothing more.
