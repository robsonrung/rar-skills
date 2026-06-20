---
name: architect-lens
description: Apply two software-architecture lenses during coding — a trade-off/decision coach and a coupling/connascence reviewer. Use when choosing between design approaches, weighing a refactor, picking a data model or boundary, or when reviewing code for tight coupling, hidden dependencies, or "which option is better" questions. Triggers on "what's the trade-off", "which approach", "is this too coupled", "review this for coupling", "should I extract/split/merge this", "help me decide". Do not use for pure bug-fixing or formatting.
---

# Architect Lens

Two reusable lenses, distilled from *Fundamentals of Software Architecture* (Richards & Ford), for decisions made while writing code. Pick the lens that fits the moment — they compose.

Core principle that governs both: **everything is a trade-off, and *why* matters more than *how*.** If an analysis ends with a single obviously-correct option and no cost, you have not finished analyzing.

**Distinct from** `architecturehardparts` (service-decomposition / data-ownership / saga territory): this lens works at the code level — connascence and trade-offs in the code under your hands.

## When to use which lens

- **Decision / trade-off lens** — you are *choosing*: an approach, a boundary, a library, sync vs async, monolith vs split, build vs reuse. → see `Decision lens` below.
- **Connascence / coupling lens** — you are *evaluating existing code*: a refactor, a review, "this feels tangled," deciding what to extract or merge. → see `Coupling lens` below.

Use both when a decision *is* about reducing coupling (e.g. "should I split this module?").

---

## Decision lens (trade-off coach)

Goal: turn a fuzzy "which is better?" into an explicit, defensible choice.

1. **Name what actually matters here.** Identify the 2–4 *architecture characteristics* (the "-ilities") that this decision is really trading on — not all of them, the ones in tension. Common ones: performance, scalability, testability, maintainability, fault-tolerance, simplicity, deployability, security, evolvability. Most decisions trade two of these against each other. See `references/architecture-characteristics.md` for the checklist.

2. **List the real options.** At least two. "Do nothing / keep current" is a valid option and should usually be one of them.

3. **For each option, state the trade-off explicitly** — what you *gain* and what you *give up*. Force the cost out:
   - "Option A is faster but couples X to Y."
   - "Option B is simpler now but harder to evolve when Z changes."
   - There is no free option. If you can't name a cost, look harder.

4. **Decide against the characteristics from step 1**, and say *why* in one sentence. The reasoning is the deliverable, not the choice.

5. **Watch for decision anti-patterns:**
   - *Re-deciding the same thing repeatedly* ("Groundhog Day") → if this keeps coming up, it's worth recording.
   - *Deciding to avoid blame rather than for the system* ("covering your assets") → choose for the system.
   - *Decisions that live only in chat/email* → if it's significant, write it down (step 6).

6. **If the decision is *architecturally significant*, offer an ADR.** Significant = affects structure, a cross-cutting characteristic, dependencies, or interfaces; expensive to reverse; or likely to be re-litigated. Don't write ADRs for trivia. Use the lightweight template in `references/adr-template.md`.

7. **If a decision encodes a rule that future code could violate, suggest a fitness function** — an automated guard (lint rule, arch test, CI check) so the rule enforces itself instead of relying on memory. See `references/fitness-functions.md`.

---

## Coupling lens (connascence reviewer)

Goal: replace vague "this is too coupled" with a precise diagnosis and a concrete way to weaken it.

**Connascence** = two pieces of code are connascent if changing one forces a change in the other to keep the system correct. Two questions rank any coupling:

- **Strength** — how hard is it to refactor? Static (visible in source) is weaker than dynamic (only shows at runtime).
- **Locality** — how far apart are the connascent elements? The *same* coupling is far worse across module/service boundaries than within one function.
- **Degree** — how many elements are involved?

**The rule:** the farther apart two elements are, the weaker the connascence between them should be. Strong coupling is fine locally, dangerous at a distance.

Review workflow:
1. Identify the coupled elements and **name the connascence type** (see `references/connascence.md` for the full taxonomy — name, type, meaning/convention, position, algorithm; execution order, timing, value, identity).
2. Judge it by strength × locality × degree. Local + static = usually leave it. Distant + dynamic = flag it.
3. For each thing worth fixing, suggest a concrete weakening — e.g. magic value → named constant (meaning→name). The reference file maps each type to its remedy.
4. Don't over-refactor: removing all coupling is impossible and chasing it creates indirection. Weaken the *strong, distant, high-degree* cases; leave the rest.

Also check **cohesion** while you're there: do the things in this module belong together (change for the same reason)? Low cohesion + high coupling is the signal to split or regroup.

---

## Output style

- Be concrete and short. Name the characteristic / connascence type, state the trade-off or remedy, move on.
- Always surface at least one cost or counter-point — never present a choice as free.
- Match effort to stakes: a small decision gets a two-line trade-off note inline; only significant ones get the full pass, an ADR, or a fitness function.
- Reference files are loaded on demand — read them when you need the taxonomy, the characteristics checklist, or a template, not preemptively.
