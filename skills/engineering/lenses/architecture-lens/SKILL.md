---
name: architecture-lens
description: "Review code-level coupling, cohesion, dependency direction, and module boundaries. Use when deciding where code belongs or whether to split, merge, or refactor a module; use macro-architecture for system shape."
---

# Architecture Lens

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Review code-level structure using Richards and Ford's _Fundamentals of Software Architecture_ and _Practical Model-Driven Enterprise Architecture_. Judge **ease of change** through coupling, placement, cohesion, dependency direction, and scope. A real choice has a tradeoff; state its cost without manufacturing alternatives to settled decisions.

Use `macro-architecture` for system style, `domain-driven-design` for domain modeling, and `full-review` for a correctness or security review.

## Select the lens

| Decision or review | Method to load |
| --- | --- |
| Unresolved approach, boundary, library, sync/async, or build/reuse choice | Lens 1: [references/decision-review.md](references/decision-review.md) |
| Tangled code or deciding what to split, extract, or merge | Lens 2: [references/coupling-review.md](references/coupling-review.md) |
| Layer placement, cohesion, dependency direction, or scope in a diff or design | Lenses 3–6: [references/structural-review.md](references/structural-review.md) |

Combine methods only when the question needs them. Inspect the affected code and its contracts; a local boundary review does not require mapping the whole repository. Reuse existing design decisions and evidence.

**Connascence** ranks coupling by strength × locality × degree. Strong coupling can be acceptable locally; distant dynamic coupling deserves attention. Keep the **smallest coherent shape**: remove speculative scope without introducing more indirection than the change needs.

## Authority and output

This skill reports findings. A user's request for scoped fixes authorizes those edits. A `design-gate` or other read-only reviewer invocation returns findings only and overrides standalone edit routes.

For a standalone review, group findings by selected lens with `file:line`, the violated rule, and a concrete fix. For a decision, state the chosen shape, actual tradeoff, and next move. A small decision can use two lines. A clean lens returns `clean`; do not invent findings or a counterpoint to fill a category.

Under `design-gate`, return `verdict` (`proceed` | `revise`), `blocking_findings`, `advisory_findings`, and `required_changes`. A load-bearing issue can require revision; cosmetic preference cannot.

Use **all three or no ADR**: hard to reverse, surprising without context, and a real tradeoff. **Record on settle** using [references/adr-template.md](references/adr-template.md) when all three apply. Otherwise preserve the decision in the existing task or review note.

## Additional references

- [references/verification-menu.md](references/verification-menu.md): when a finding needs an executable check.
- [references/fitness-functions.md](references/fitness-functions.md): when a durable architecture rule needs enforcement.
- [references/risk-and-diagrams.md](references/risk-and-diagrams.md): when a migration, availability boundary, unproven technology, or requested diagram needs a risk model.

The selected methods link to their detailed taxonomies and checklists. Load those only when the decision needs them.
