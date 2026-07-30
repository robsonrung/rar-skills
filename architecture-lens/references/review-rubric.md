# Architecture Lens — detailed review rubric & provenance

Expanded checklists for **Lenses 3–6** of `architecture-lens` (layer placement, cohesion,
dependency direction, scope discipline). Lens numbering here matches SKILL.md exactly:
1 decision/trade-off, 2 connascence, 3 layer placement, 4 cohesion, 5 dependency direction,
6 scope. Lenses 1–2 live in SKILL.md and are not expanded here.

Source: *Practical Model-Driven Enterprise Architecture* (Packt, ISBN 9781801076166 /
B17363), Bahaaldine et al. The book teaches TOGAF + ArchiMate 3.1 modeling in Sparx EA.
Most of it is tool-specific; this rubric distills only the transferable *modeling
discipline*. Each lens below cites the chapter it came from so you can defend a finding.

The checklists are deliberately **generic** — substitute this repo's real module names for
the placeholders before reviewing. A worked example with concrete names is in the appendix
at the end.

---

## Provenance map

| Lens | Book source | Original idea |
|---|---|---|
| 3 — Layer placement | Ch 1, 6–8 (Business/Application/Technology layers) | Every element belongs to exactly one architecture layer; layers have distinct concerns. |
| 4 — Cohesion | Ch 4 "Keeping your diagram focused" | "A single diagram better tells a single main idea… more than one idea adds noise and confuses the reader." |
| 5 — Dependency direction | Ch 4–5 "focused metamodels" | A focused metamodel shows, per element, only the relationships it is *allowed* to have; depend on the exposed **service**, not the **component's** internals (Ch 5 service-vs-component distinction). |
| 6 — Scope | Ch 1 "Effort Blackhole" / "boil the ocean" / MVP | Deliver tangible artifacts incrementally; don't expand scope to "do it all" before shipping anything. |
| (cross-cutting) Audience | Ch 5 "views & viewpoints", Ch 4 "Knowing your audience" | A view answers one question for one stakeholder; name who reads it and what concern it serves. |

---

## Lens 3 — Layer placement (expanded checklist)

Map the repo's equivalents first: `<domain module>` (entities, invariants, business rules),
`<application module>` (routes, services, workers, frontend state), `<infrastructure>`
(cloud SDKs, DB drivers, queues, storage).

- [ ] Domain invariants (validation that protects a business rule, not just input shape)
      live in `<domain module>`, not in route handlers, UI components, or migrations.
- [ ] Domain rules with regulatory or money consequences — pricing, limits, safety or
      compliance thresholds, entity lifecycle transitions — are in the business layer and
      reused, not re-implemented per caller.
- [ ] No cloud SDK calls, message-bus clients, object-storage keys, or raw SQL inside
      domain or business code.
- [ ] No view-layer types (JSX/templates), HTTP status codes, or request/response shapes
      inside domain logic.
- [ ] Migrations contain schema + data shape only — not business decisions.
- [ ] The frontend talks to the application API; it does not encode infra assumptions.

**Why it matters (book):** the value of EA is "bridging business and IT"; the failure mode
is logic scattered so no layer is the source of truth. Same in code — a rule duplicated
across a handler, a worker, and a component will drift.

## Lens 4 — Cohesion (expanded checklist)

- [ ] Can you write a one-sentence "viewpoint" for the element (who/what-concern) with no
      "and"? If not, it likely models two things.
- [ ] Functions/services do one job; a name like `handleAndSyncAndNotify` is three.
- [ ] No `utils`/`helpers`/`common` dumping ground growing unrelated exports.
- [ ] UI components separate fetch / business-rule / presentation concerns.
- [ ] An entity isn't carrying columns/methods for an unrelated bounded concern.

**Book test (Ch 4):** they show a diagram that's "still correct" but bad because it
describes *two* components at once — correctness isn't the bar, **focus** is. A function can
be bug-free and still be wrong because it does two things.

## Lens 5 — Dependency direction (expanded checklist)

- [ ] Imports point down the layer stack: application → business; technology underpins.
      A shared/domain module must not import from an application or frontend module.
- [ ] No sibling service reaching into another service's internals — go through its public
      interface (book: depend on the **service**, not the **component**).
- [ ] A new cross-module edge is one the design *allows* — would it appear in that element's
      focused metamodel? If it's a surprising connection, question it.
- [ ] Async/event-driven boundaries aren't bypassed by a direct call that recreates the
      coupling the boundary existed to remove.

**Book idea (Ch 4–5):** the focused metamodel exists precisely so contributors know which
relationships are legitimate for a given element. A dependency that wouldn't be on that
diagram is a smell.

## Lens 6 — Scope discipline (expanded checklist)

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

## What this rubric is NOT

- Not a bug/security finder → use `code-review` / `full-review`.
- Not the coupling/connascence + trade-off coach → that is **Lenses 1–2** (decision /
  trade-off and connascence), which live in this skill's SKILL.md, not in this rubric.
- Not a clean-code refactor pass → use `clean-code`.
- It expands the **"is this in the right place, focused, pointed the right way, and
  scoped"** lenses (3–6), and nothing more.

---

## Appendix — worked example (generic shapes)

Illustration only, using placeholder names. Use it as a model for how to instantiate the
placeholders above, then work from your own repo's names.

Take a repo with `<domain-module>` holding the business rules, `<application-module>` as the
API/orchestration layer, `<worker-module>` consuming an event bus, and a cloud SDK, object
storage, and a message bus as infrastructure.

- **Lens 3:** compliance thresholds and entity-lifecycle transitions belong in
  `<domain-module>`, reused by every caller — not re-derived inside an `<application-module>`
  route or a UI component. No cloud SDK, message-bus, object-storage, or raw SQL calls
  inside the domain module.
- **Lens 5:** `<domain-module>` must not import from `<application-module>` or the frontend.
  Where the design puts a message-bus hop between `<application-module>` and
  `<worker-module>`, a direct function call between them recreates exactly the coupling the
  event boundary removed.
- **Lens 4:** a component that fetches records, applies a business rule, and renders a
  document is three concerns wearing one name.
