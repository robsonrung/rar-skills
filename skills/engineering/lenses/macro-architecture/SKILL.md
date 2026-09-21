---
name: macro-architecture
description: "Choose a system architecture style or assess service decomposition and data ownership. Use for monolith, service, event-driven, or distributed-system boundaries; use architecture-lens for code-level structure."
---

# Macro Architecture

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Two complementary system-level tools that work at the same altitude — **what shape should this system take?**

- **Style selection** — given a system/service/feature and its driving requirements, which macro architecture style (or hybrid) fits, and what does the book warn about if you pick it? (from _Software Architecture Patterns, 2nd ed._, Mark Richards.)
- **Hard-parts decomposition** — once you're decomposing, merging, or re-shaping a system, which way do the trade-offs actually push, anchored in the current code and runtime? (from _Software Architecture: The Hard Parts_, Ford & Richards.)

Use **Style selection** when choosing an overall shape for something new (or sanity-checking an existing one). Use **Hard-parts decomposition** when the decision is whether to pull a system apart or put it back together. They compose: pick a style, then stress-test the decomposition.

**Distinct from** `architecture-lens` (code-level trade-offs/connascence and layer placement/cohesion in the code under your hands), `domain-driven-design` (bounded-context boundaries, ubiquitous language, cross-context integration patterns), and `design-patterns` (GoF code patterns). This skill picks the MACRO shape; those review the code and contexts within it.

## Select the decision

| Need | Read |
| --- | --- |
| Choose or assess an overall architecture style | [references/style-selection.md](references/style-selection.md) |
| Split, merge, or reshape services and data ownership | [references/decomposition.md](references/decomposition.md) |
| Both | Select the style, then assess only its unresolved decomposition tradeoffs |

Use current code, runtime evidence, and the user's constraints. The **smallest coherent shape** is the one that meets the actual requirements. Name the benefit, cost, and next concrete move. Do not turn a routine code change into a system redesign.

## Authority and output

A decision or review request returns the selected method's recommendation. Implement only when the user's request authorizes implementation. Under design-gate, stay read-only and return `verdict: proceed|revise`, `blocking_findings`, `advisory_findings`, and `required_changes`.

Use **all three or no ADR**: hard to reverse, surprising without context, and a real tradeoff. **Record on settle** using the existing ADR convention when all three apply. The decomposition method contains the fallback path and helper command.

## Focused knowledge

Load only the material the selected method needs:

- Style details: [layered](references/layered.md), [microkernel](references/microkernel.md), [event-driven](references/event-driven.md), [microservices](references/microservices.md), [space-based](references/space-based.md).
- [references/traps.md](references/traps.md): before a distributed-style recommendation.
- [references/other-styles.md](references/other-styles.md): when the main matrix does not fit, or coarse-grained services may suffice.
- [references/catalog.md](references/catalog.md): decomposition, granularity, ownership, transactions, and workflow tradeoffs.
- [references/adrtemplate.md](references/adrtemplate.md): when writing a durable decision.
