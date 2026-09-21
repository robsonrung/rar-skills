---
name: software-design-philosophy
description: "Reduce design complexity through deep modules, information hiding, and coherent interfaces. Use when a module or API is hard to understand or change; use clean-code for local cleanup."
---

# A Philosophy of Software Design

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Use Ousterhout's _A Philosophy of Software Design_, 2nd edition, to reduce the cost of understanding and changing software. Brooks' **conceptual integrity** is the second anchor. Return a named design or fix, its reason, and the next move.

## Select the route

| Work | Method to load |
| --- | --- |
| New module or consequential API/interface shape | [references/design-mode.md](references/design-mode.md) |
| Change existing code while reducing its complexity | [references/improve-mode.md](references/improve-mode.md) |
| Assess a diff, design, PR, or `design-gate` input | [references/review-mode.md](references/review-mode.md) |

Use `clean-code` for a local naming or structure cleanup with no boundary decision, and `tdd` for test-first execution. Continue the requested work through that skill; selecting the proper method is not a new approval gate.

## Shared design rules

Use these **leitwörter** to explain an actual design decision:

- **strategic** — invest a little design now so the next change is cheaper. The opposite is **tactical** ("just make it work") and the **tactical tornado** (the person who ships fastest by leaving a mess).
- **deep module** — a simple interface hiding a lot of functionality. Cost is the interface; benefit is what it hides. A **shallow module** costs about as much to learn as to inline.
- **information leakage** — one design decision reflected in two or more modules. That _is_ a **change ownership** failure; give the decision one owner.
- **design it twice** — for any consequential interface, sketch two or three _meaningfully different_ shapes before coding.
- **stay strategic** — when modifying existing code, do not tack on a special case that makes the design worse. Fit the change, or improve the design.
- **decide what matters** — name the few things this situation depends on, minimize that set, and emphasize only those.
- **reader, not writer** — complexity is judged by the next person to change the code. If it is simple only to you, it is complex.
- **conceptual integrity** / **smallest coherent shape** — one model, no larger than the problem.

Modelled sentence: _"This is **tactical** — a special case on a **shallow module**. **Design it twice** keeps **conceptual integrity**; the cost is one extra hour now vs **information leakage** later."_

A second modelled sentence, from the official extract: _"`backspace(cursor)` is a **false abstraction** — the UI still has to know which characters vanish. One `delete(start, end)` has **leverage**; the special methods do not."_

## Evidence and authority

Inspect enough of the live code or stated design to identify the abstraction, the informal interface (everything a caller must know), and a relevant red flag or principle. Read further only when it could change the decision. With no repository, use the supplied constraints and mark assumptions.

Ask **reader, not writer**: would the next developer need a fact absent from the interface? That is evidence of leakage or obscurity. Reuse settled choices; alternatives belong to a consequential unresolved design decision, not every local edit.

`review` and all `design-gate` invocations are read-only: findings only, no edits or test runs. `design` and `improve` may edit within the user's request. They do not authorize unrelated refactors.

## Acceptance contract

Use the selected mode's output fields. Name the official red flag or principle behind each finding. Report real rejected alternatives, or state that no new design choice was required. For edits, identify changed files, behavior-preserving work or exact behavior changes, and checks run or unavailable.

Under `design-gate`, return `verdict` (`proceed` | `revise`), `conceptual_integrity_check`, `blocking_findings`, `advisory_findings`, and `required_changes`. A leaked decision, shallow new public interface, or tactical special case can block when it is load-bearing; cosmetic naming is advisory.

## Gotchas

1. Do not turn a one-line bug fix into a design exercise. Match effort to stakes.
2. Do not preserve an existing pattern when the broken model _is_ the request.
3. Do not confuse consistency with conceptual integrity — repeating a mistake consistently is still a defect.
4. Do not invent findings to fill a category. `clean` is valid.
5. Do not quote or reconstruct source text from the book this skill distills.
6. **Depth before length** (ch. 9.8). After a few dozen lines, shortening a function rarely helps the system. More tiny functions means more interfaces and **conjoined methods**. Do not replace an **earned comment** with a ten-word method name. Small classes that leak one format are usually _too many_ classes — merge them.
7. Do not hide a design decision in a commit message. Comments belong in the code.
8. `private` plus a getter is not information hiding. If callers must know the field exists, it is in the interface.
9. Lots of documentation is often a **hard to describe** flag, not a virtue. Simplify the design.

## Chapter lookup

The selected mode links to its needed principles, red flags, and methods. Load [references/chapter-map.md](references/chapter-map.md) only to locate a question that does not fit those routes.
