---
name: domain-driven-design
description: "Review domain boundaries, business language, aggregates, and domain events. Use when a change crosses bounded contexts or restructures business rules within one context."
---

# Domain-Driven Design

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Review the domain shape of a change through the lenses from _Learning Domain-Driven Design_ (Vlad Khononov, O'Reilly). DDD works at two altitudes that compose:

- **Strategic** (Parts I, III–IV) — _where the boundaries are_: bounded contexts, ubiquitous language, and how contexts integrate.
- **Tactical** (Parts II–III) — _how one context is built_: the business-logic pattern, and whether aggregates/value-objects hold their invariants and publish events safely.

This is **not** a generic layering/cohesion check or trade-off/connascence audit (use `architecture-lens`), **not** macro style selection or service decomposition (use `macro-architecture`), and **not** a bug hunt (use `code-review`).

## Select the review

| Change | Read |
| --- | --- |
| Moves or crosses a bounded context, changes business naming, or integrates another system | [references/strategic-review.md](references/strategic-review.md) |
| Structures business logic, aggregates, value objects, or domain events inside one context | [references/tactical-review.md](references/tactical-review.md) |
| Does both | Strategic review first, then the affected tactical rules; boundaries constrain the internal design |

Apply only the relevant lenses. Report findings with file and line, the rule, and a proposed fix. A clean lens needs no invented finding.

**Deriving the context map:** the physical bounded contexts are usually the backend services/modules, each owning a model and a slice of the ubiquitous language (e.g. a transactional core service, an integration/sync service, an event worker, a shared kernel of domain entities, the frontend's own API-layer model). Derive this map from the repo's service/module layout before reviewing. A _subdomain_ is a problem area (pricing, dispatch, compliance); a _bounded context_ is the solution boundary where one model/language holds — they often align but not always.

## Evidence and output

The selected method contains its standalone output format. Lead with the highest-impact finding and distinguish evidence from an unresolved domain decision.

Under design-gate, remain read-only and return its contract: `verdict: proceed|revise`, `blocking_findings`, `advisory_findings`, and `required_changes`. Preserve actual invariants and integration boundaries; cosmetic preferences are advisory.

## Detailed references

- [references/context-patterns.md](references/context-patterns.md): load before classifying a context relationship or when the finding needs its full definition.
- [references/decision-trees.md](references/decision-trees.md): load for borderline pattern classification or in-depth aggregate, value-object, and event checks.
