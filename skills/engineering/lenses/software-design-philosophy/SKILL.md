---
name: software-design-philosophy
description: "Design and review module-level structure: deep modules, information hiding, placement, cohesion, dependency direction, scope, and whether a design pattern is earned. Use when a module or API is hard to understand or change; use clean-code for local cleanup and architecture-lens for system shape."
---

# Software Design Philosophy

Reduce the cost of understanding and changing a module, following Ousterhout's _A Philosophy of Software Design_ with Brooks' **conceptual integrity** as the second anchor. Return a named design or fix, its reason, and the next move.

Use `clean-code` for local naming or structure with no boundary decision, `architecture-lens` for system style and service boundaries, `tdd` for test-first execution, and the **Connascence Pass** in `coding-review-simplify` for coupling inside a diff.

## Leitwörter

Use these by name to explain an actual decision:

- **strategic** versus **tactical**: invest a little design now so the next change is cheaper. A tactical special case is how systems rot.
- **deep module**: a simple interface hiding a lot. A shallow module costs about as much to learn as to inline.
- **information leakage**: one design decision reflected in two or more modules. That is a **change ownership** failure; give the decision one owner.
- **design it twice**: for a consequential unresolved interface, compare two or three meaningfully different shapes before coding. Reuse a settled interface unless new evidence challenges it.
- **stay strategic**: when modifying code, don't tack on a special case that makes the design worse. Fit the change, or improve the design, or say why you won't.
- **decide what matters**: name the few invariants, error behaviors, and compatibility needs the situation depends on, give that knowledge one owner, emphasize it, hide the rest.
- **reader, not writer**: complexity is judged by the next person to change the code. If a caller needs a fact absent from the interface, that is leakage or obscurity.
- **smallest coherent shape**: one model, no larger than the problem.

Modelled sentence: _"`backspace(cursor)` is a **false abstraction**: the UI still has to know which characters vanish. One `delete(start, end)` is deeper, and **design it twice** keeps **conceptual integrity**; the cost is an hour now versus **information leakage** later."_

## Interface judgment

- **Somewhat general.** Functionality reflects today's needs; the interface does not encode today's specific caller. Fewer, more general methods usually beat special-purpose ones. One planned call site is a sign the method is too special. If callers must write a lot of glue, you over-generalized.
- **Push specialization up or down.** Feature code owns the special case (backspace, selection); the lower module keeps the general mechanism. Represent the edge as the normal case (`start == end`, not `hasSelection`).
- **Pull complexity down**, but not a policy the module cannot know. Define errors out of existence where the caller has nothing useful to do, but keep errors the caller must handle.
- **Depth before length.** After a few dozen lines, shortening a function rarely lowers system complexity; more tiny functions means more interfaces and conjoined methods. Small classes that each half-know one format should usually merge.
- **Fix the seam, not the callsite.** When the obvious call on a public seam does the wrong thing, move the invariant into the seam: make the default safe, narrow the type so bad states can't be represented, or rename the dangerous path. "Remember to call X first" is documentation standing in for design.
- `private` plus a getter is not information hiding. Lots of documentation is often a **hard to describe** flag; simplify the design. Comments follow clean-code's **earned comment** rule.

## Module structure

Infer the repo's equivalents of domain, application, and infrastructure code before judging.

- **Placement.** Business rules with money, compliance, or lifecycle consequences live in domain code and are reused, not re-derived in a route handler, component, worker, or migration. SQL, cloud SDKs, queue payloads, and HTTP shapes stay out of domain code.
- **Cohesion.** Write a one-line purpose for the element. If it needs an "and," suspect two concerns. A `utils` grab-bag, a component that fetches, decides, and renders, or an entity carrying an unrelated concern is modeling two things.
- **Dependency direction.** Domain code never imports application or frontend code. Depend on a sibling's public interface, not its internals. A direct call that bypasses an async boundary recreates the coupling the boundary removed.
- **Scope.** An abstraction earns its boundary by enforcing an invariant, hiding real complexity, or giving a decision clear **change ownership**; one caller can justify that. Speculative config, plugin points, and generic engines do not. Call out refactors that crept past the stated goal: "X is in scope; Y looks speculative. Split or drop?"

## Pattern pressure

Most code should not use a named pattern. Reach for one only once the need has emerged: repeated change in one spot, or an extension point you keep fighting, not a hypothetical future. Work in order: name the pressure, try the plain fix (a function, a map, an early return, one of the module rules above), then match a pattern, preferring the one with less machinery. Once a pattern genuinely fits, name it; the shared name carries the design to the next reader.

Every recommendation names its cost in classes and indirection, and why that cost is worth paying here. "None needed, here's the three-line version" is a success.

Judge "overkill when" before recommending: Strategy when there is one behavior or two that will never grow (an `if` or a passed function is clearer); Observer for one fixed listener, or when the platform already has events; Factory when creation does not vary by subtype; Singleton almost always (a module value or an injected instance is testable); State with few trivial transitions (an enum and `switch`); Decorator or Proxy added "just in case"; Visitor when element types change often; Mediator that is growing into a god object.

## Modes

Match effort to stakes; a one-line fix is not a design exercise. Inspect enough live code to identify the abstraction, its informal interface (everything a caller must know), and the relevant red flag. With no repository, use the supplied constraints and mark assumptions.

- **Design** a new module or consequential interface: state in one sentence what the caller can safely ignore, apply the interface judgment, and **design it twice** only if the choice is open.
- **Improve** existing code: **stay strategic**. Leave a deeper abstraction, not a new branch: no boolean that forks a deep module into two models, no copy "just this once." Pin behavior with a characterization test before a risky structural change. Match the codebase's strongest local convention unless that convention is what you are fixing; never mix two in one change. Reread the diff for comments it made false.
- **Review** a diff, design, or PR: walk [references/red-flags.md](references/red-flags.md), name each finding, and judge **conceptual integrity**, **change ownership**, and the **smallest coherent shape** at the affected boundary. Consistency is not integrity: a mistake repeated consistently is still a defect. `clean` is a valid result.

Standalone output:

```text
Mode: design | improve | review
Abstraction: <one sentence>
Findings: [file:line] <red flag or rule>: <what's complex>. Fix: <structural change>. (or clean)
Conceptual integrity: <holds or where it breaks>
Rejected: <a real alternative and its cost, or no new choice>
Next move: <one action>
```

If you edited code, add files touched, **behavior-preserving** or the exact behavior change, and checks run.

## Authority

Review and every `design-gate` call are read-only: findings only, no edits or test runs. Under `design-gate`, return the caller's canonical gate result and put the conceptual integrity conclusion in `review_focus`. A leaked decision, a shallow new public interface, or a load-bearing tactical special case can block; cosmetic naming is advisory. Design and improve may edit within the user's request, never unrelated refactors. In an interview, record the boundary decision, rationale, constraints, and sources in the existing decision record. Don't hide a design decision in a commit message, and don't reproduce text from the book.
