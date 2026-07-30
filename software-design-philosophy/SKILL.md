---
name: software-design-philosophy
description: Review code and designs to minimize long-term complexity, combining the deep-modules framework from John Ousterhout's "A Philosophy of Software Design" with the conceptual-integrity lens from Brooks' "The Design of Design". Use when designing a module, class, or API; deciding where a boundary goes; judging whether an interface is too complex; weighing strategic vs tactical effort; shaping a design before code; comparing design alternatives or trade-offs; running a design review of an architecture, API surface, data model, module boundary, UI flow, or feature shape; reviewing code for design (not bug) quality; or when the user mentions deep modules, shallow modules, information hiding, complexity, pulling complexity down, conceptual integrity, change ownership, system shape, design review, Brooks, or The Design of Design. Read-only: it reports findings and recommends a shape, it does not implement. Distinct from clean-code (local refactoring moves), design-patterns (whether a specific GoF pattern fits), and architecture-lens (layer placement, connascence/trade-offs).
---

# A Philosophy of Software Design

A design lens with two anchors: **reducing complexity** (Ousterhout) — the thing that, accumulated over time, makes software hard to understand and risky to change — and **conceptual integrity** (Brooks) — whether what you built is still *one* idea. Use it while designing new modules, while reviewing a diff or a plan for design quality, or when deciding how to draw a boundary. It complements bug-finding review; it asks a different question: *will this be cheap or expensive to live with?*

This lens is **read-only**. It reports findings by name and recommends a shape; it does not implement the change and does not run tests. Applying a fix is a separate request.

## The one thing this is about: complexity

Complexity is anything about a system's structure that makes it hard to understand or modify. It is **incremental** — it accrues one small "this'll do" at a time, and no single change feels like the culprit. That is why discipline matters more than heroics.

Recognize complexity by its three symptoms:

1. **Change amplification** — a conceptually simple change forces edits in many places.
2. **Cognitive load** — how much a developer must hold in their head to make a change safely. More lines is not worse if it lowers what you must understand; fewer lines is not better if it raises it.
3. **Unknown unknowns** — it is not obvious *what* code must change, or *what* knowledge is needed to change it safely. This is the worst symptom: you cannot fix what you cannot see.

Complexity has two root causes, and most red flags below trace back to one of them:

- **Dependencies** — code that cannot be understood or changed in isolation. Good design doesn't eliminate dependencies (impossible); it makes them few, simple, and obvious.
- **Obscurity** — important information that is not apparent: a misleading name, an undocumented invariant, a convention you only learn by breaking it.

## Core stance

1. **Working code is not enough.** The goal is a system that stays cheap to change. Be **strategic**, not **tactical**: a tactical mindset ("just make the feature work") buys speed today and pays compound interest in complexity. Invest a steady ~10–20% of effort in design and cleanup continuously — not a big upfront design phase, and not a someday-rewrite. Watch for the *tactical tornado*: the developer who ships fastest by leaving a mess for everyone else.
2. **Make modules deep.** A module is anything with an interface and an implementation — a function, class, or service. Its *cost* is the complexity of its interface; its *benefit* is the functionality it provides. A **deep** module hides a lot of functionality behind a simple interface (best benefit-to-cost ratio). A **shallow** module's interface is complex relative to what little it does — it adds more complexity (what you must learn to use it) than it removes. Many tiny classes/methods ("classitis") is shallow by construction.
3. **Information hiding is the primary technique for depth.** Each module should encapsulate a few design decisions — a data structure, a file format, an algorithm — behind its interface, so callers neither know nor depend on them. The opposite, **information leakage**, is the most important red flag: a design decision reflected in two or more modules so they must change together. Leakage through a *back door* (a shared file format, an assumed ordering) is the most dangerous because it is invisible.
4. **Pull complexity downward.** When complexity is unavoidable, it is better for the *module* to absorb it than for its *users* to. One implementer suffers once; every caller suffers forever. A simple interface is worth a more complicated implementation. (But don't over-pull: don't bake in a policy the module can't actually decide correctly.)
5. **Define errors out of existence.** Exceptions are a leading source of complexity because they create rarely-tested code paths. The best handler is one you don't need: redesign semantics so the error case is *normal* (e.g. "delete a range" instead of erroring on an empty range; "unset returns the default" instead of throwing on a missing key). Then **mask** exceptions low in the stack, **aggregate** handling so many errors flow to one place, and **crash** for truly unrecoverable cases rather than threading recovery everywhere.
6. **Design it twice.** For any consequential interface or module, sketch two or three *meaningfully different* designs and compare them on interface simplicity, generality, and the symptoms above. The cost is small; picking the better of two designs is one of the highest-leverage habits available, even for experts.
7. **Make code obvious.** Obvious code is read at full speed with correct assumptions and no backtracking. Nonobvious code is a red flag. Achieve obviousness with precise names, consistency, judicious white space, and comments that capture intent. Things that erode it: event-driven control flow, generics/inheritance hiding behavior, and anything that violates a reader's reasonable expectations.

## Conceptual integrity — the Brooks lens

Complexity asks *how much* a reader must understand. **Conceptual integrity** asks whether what they understand is **one thing**. Brooks (*The Design of Design*, *The Mythical Man-Month*) treats it as the first property of a good design: a design has conceptual integrity when it presents **one clear model, consistent vocabulary, coherent boundaries, and predictable interfaces** — so someone who learns one part can correctly predict the rest. Two half-models cost more than either model applied whole.

Three checks carry this lens, and **you name the check as you apply it** — stating which check you are invoking, and what it costs, is what makes a trade-off legible:

1. **conceptual integrity** — is there a single central concept, and do the names match it? Does every edge case follow the same model, or does one branch quietly run on a second model?
2. **change ownership** — a change wants to live in exactly one place. When it doesn't, you are looking at the **information leakage** red flag below from the design side: one decision is reflected in two or more modules that must now move together. Diagnose it as leakage and give the decision a single owning module; do not treat it as a separate finding.
3. **smallest coherent shape** — the scope check. Is the design no larger than the problem requires? A coherent design that is bigger than the problem still costs more than it earns, and a smaller design that splits the model is not a design at all. Take the smallest shape that keeps one model intact.

Modelled sentence — produce sentences of this kind: *"Option B keeps **conceptual integrity** but at the cost of **change ownership** — the pricing rule would then live in two modules that have to move together."*

Where the design is consequential, say the central idea in one sentence before judging it. If you cannot state the idea in a sentence, that is the finding.

**Gotcha:** Do not confuse consistency with conceptual integrity — repeating an old mistake consistently is still a design problem. Use the codebase's strongest local patterns as exemplars, except when the pattern is itself what the change is fixing.

## When designing new code (apply, in order)

1. **State the abstraction first.** What simplified view does this module offer — what does the caller get to *not* know? If you can't say it in a sentence, the boundary is wrong.
2. **Design the interface twice**, then pull complexity down so the interface is simpler than the implementation.
3. **Prefer somewhat general-purpose interfaces.** A slightly general interface ("insert text at a position") is usually both simpler and deeper than a special-purpose one ("handle the backspace key"). Don't over-generalize into speculative configurability — aim for the interface that serves today's needs without encoding today's *specific* caller.
4. **Keep each layer at a distinct abstraction.** Adjacent layers that share an abstraction signal a missing or misplaced boundary. Two specific smells:
   - **Pass-through method** — does nothing but forward to another method with the same signature. It adds interface, hides no decision, and couples two classes. Remove it: let the caller talk to the deeper module, combine the layers, or give the method real responsibility.
   - **Pass-through variable** — a parameter threaded through many methods that don't use it just to reach a deep one. Eliminate via a shared context object rather than the long thread.
5. **Better together or better apart?** Combine two pieces when they share information, when combining *simplifies the interface*, or when it removes duplication; separate them when they're genuinely independent and combining would force a reader to understand both at once. Method length is not itself a smell — split a method only when the pieces are independent, each is simpler in isolation, and the split doesn't create conjoined methods you must read together to understand either.
6. **Comment as you design — the comment is part of the design.** If a method's interface comment is long or has to enumerate special cases, the interface is too complex (the **hard-to-describe** red flag). Writing the comment first surfaces that early.

## When reviewing for design quality

1. Establish the diff/design under review and, for each module touched, name the abstraction it's *supposed* to present.
2. Walk the **Red flags** checklist below; collect findings with `file:line`, the flag's name, *which root cause* (dependency or obscurity) it stems from, and the fix.
3. Run the three conceptual-integrity checks — **conceptual integrity**, **change ownership**, **smallest coherent shape** — and name each one as you apply it.
4. Order findings by leverage (a leaked decision across modules beats a single vague name). Give a one-line verdict.
5. If a category is clean, say "clean" — don't invent findings.

## Red flags

Each is a *warning that something may be too complex*. Name the flag, then propose the structural fix. Full descriptions and worked fixes are in `references/red-flags.md` — read it before a thorough review.

- **Shallow module** — interface complexity is high relative to functionality; the module costs about as much to learn as to inline.
- **Information leakage** — a design decision is baked into two+ modules that must now change together.
- **Temporal decomposition** — structure mirrors the *order operations run in* (read, then process, then write) instead of grouping by the knowledge each piece hides; a classic leakage generator.
- **Overexposure** — using a common case forces the caller to learn rarely-used options.
- **Pass-through method / pass-through variable** — forwarding without adding value; threading an unused parameter.
- **Repetition** — the same snippet recurs because no module owns it.
- **Special-general mixture** — special-purpose code embedded in general-purpose code (or vice versa), so neither is clean.
- **Conjoined methods** — two methods so entangled you must read both to understand either.
- **Comment repeats code** — a comment that restates what the code already says, adding no information that isn't obvious.
- **Implementation detail in interface comment** — interface docs leak how it works, not just what it does, coupling callers to internals.
- **Vague name / hard to pick a name** — a name like `data`/`obj`/`tmp`, or a struggle to name something, usually means the underlying entity is muddled.
- **Hard to describe** — the interface comment is long or full of caveats; the interface is doing too much.
- **Nonobvious code** — a reader can't quickly tell what it does or why; the meaning isn't on the surface.

## Evaluating "best practices" through this lens

Judge any trend, pattern, or rule by one test: *does it reduce complexity here, or add it?*

- **Inheritance** — implementation inheritance creates dependencies up the hierarchy; prefer composition unless the "is-a" is real and stable.
- **Design patterns** — valuable when they fit, complexity when forced; not every problem needs one.
- **TDD / agile** — good for incremental progress, but bias toward feature-completion can crowd out design; deliberately reserve design moments.
- **Getters/setters, micro-classes, tiny methods** — often shallow; don't add interface that hides no decision.
- **Performance** — usually simpler code is also faster; measure before complicating, and when you must optimize, design around the few critical paths rather than scattering micro-optimizations.

## Output contract

For a standalone review, lead with findings ordered by leverage:

```
## Design review (Philosophy of Software Design lens)

### Findings
- [file:line] <red-flag name> (<dependency|obscurity>) — <what's complex>. Fix: <structural change>.

### Conceptual integrity
<which of conceptual integrity / change ownership / smallest coherent shape holds, and which doesn't>

### Verdict
<one line: is this strategic or tactical, and the top 1–2 things to address>
```

When run as a **reviewer** — under `design-gate`, or any time a caller asks for a proceed-or-revise verdict — return exactly:

1. `verdict`: `proceed` or `revise`.
2. `conceptual_integrity_check`: whether the design still has one coherent model, naming which of the three checks (**conceptual integrity** / **change ownership** / **smallest coherent shape**) fails if any.
3. `blocking_findings`: load-bearing findings requiring plan changes (empty when `proceed`).
4. `advisory_findings`: non-blocking observations worth carrying into implementation.
5. `required_changes`: numbered plan amendments (only when `revise`).

Reviewer mode stays read-only: no edits, no test runs — findings and required changes only.

For new-design work, state the design's central idea in one sentence, then the module's abstraction, why the interface is simple, what complexity you pulled downward, and which errors you defined out of existence.

## Gotchas

1. Do not turn a small bug fix into a design exercise — match effort to stakes.
2. Do not preserve an existing pattern blindly when the broken model *is* the request.
3. Do not confuse consistency with conceptual integrity — repeating an old mistake consistently is still a design problem.
4. Do not invent findings to fill a category; "clean" is a valid result for any lens.
