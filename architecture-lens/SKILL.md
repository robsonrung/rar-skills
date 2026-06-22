---
name: architecture-lens
description: Review code or a design through code-level architecture lenses — trade-off/decision coaching, coupling/connascence, layer placement & boundary leaks, element cohesion, dependency direction, and over-scoping ("boiling the ocean"). Use when choosing between design approaches ("which option is better", "what's the trade-off", "help me decide"), weighing a refactor, picking a data model or boundary, reviewing code for tight coupling or hidden dependencies, sanity-checking where code belongs, spotting a module doing too much, questioning a dependency direction, or when a change is getting too big. Triggers on "is this too coupled", "review this for coupling", "should I extract/split/merge this", "review the architecture", "where does this belong". Do not use for pure bug-fixing or formatting (use code-review). Distinct from macro-architecture (macro style selection + service decomposition / data ownership / sagas) and domain-driven-design (domain modeling).
---

# Architecture Lens

Reusable **code-level** architecture lenses for decisions and reviews made while writing code, distilled from *Fundamentals of Software Architecture* (Richards & Ford) and *Practical Model-Driven Enterprise Architecture* (ArchiMate/TOGAF). Pick the lens that fits the moment — they compose.

Core principle that governs all of them: **everything is a trade-off, and *why* matters more than *how*.** If an analysis ends with a single obviously-correct option and no cost, you have not finished analyzing. The single measure of a structure's quality is **ease of change**: does this code sit in the right place, do one job, depend in the right direction, stay scoped — and when you must choose, is the trade-off named?

**Distinct from** `macro-architecture` (macro style selection and service-decomposition / data-ownership / saga territory — the system level), `domain-driven-design` (domain modeling), and `code-review` (bugs). This lens works at the level of the code under your hands.

## When to use which lens

- **Deciding** an approach, boundary, library, sync vs async, build vs reuse → **Lens 1 (Decision / trade-off)**.
- **"This feels tangled"**, a refactor, deciding what to extract or merge → **Lens 2 (Coupling / connascence)**.
- **Reviewing a diff or design** for where code belongs, what it depends on, and how big it's grown → **Lenses 3–6 (Placement, Cohesion, Dependency direction, Scope)**.

Use several together when they apply (e.g. "should I split this module?" is a decision *and* a coupling *and* a cohesion question). For a full review, walk Lenses 3–6 in order; read `references/review-rubric.md` first for the per-lens checklists and the "What this skill is NOT" redirects.

---

## Lens 1 — Decision / trade-off (trade-off coach)

Goal: turn a fuzzy "which is better?" into an explicit, defensible choice.

1. **Name what actually matters here.** Identify the 2–4 *architecture characteristics* (the "-ilities") this decision really trades on — not all of them, the ones in tension (performance, scalability, testability, maintainability, fault-tolerance, simplicity, deployability, security, evolvability). Most decisions trade two against each other. See `references/architecture-characteristics.md`.
2. **List the real options.** At least two. "Do nothing / keep current" is valid and usually one of them.
3. **For each option, state the trade-off explicitly** — what you *gain* and what you *give up*. There is no free option; if you can't name a cost, look harder.
4. **Decide against the characteristics from step 1**, and say *why* in one sentence. The reasoning is the deliverable, not the choice.
5. **Watch for decision anti-patterns:** re-deciding the same thing repeatedly ("Groundhog Day" → record it); deciding to avoid blame rather than for the system ("covering your assets"); decisions that live only in chat/email (if significant, write it down).
6. **If the decision is *architecturally significant*, offer an ADR** (affects structure, a cross-cutting characteristic, dependencies, or interfaces; expensive to reverse; or likely to be re-litigated). Use the template in `references/adr-template.md`. Don't write ADRs for trivia.
7. **If a decision encodes a rule future code could violate, suggest a fitness function** — an automated guard (lint rule, arch test, CI check) so the rule enforces itself. See `references/fitness-functions.md`.

## Lens 2 — Coupling / connascence (coupling reviewer)

Goal: replace vague "this is too coupled" with a precise diagnosis and a concrete way to weaken it.

**Connascence** = two pieces of code are connascent if changing one forces a change in the other to keep the system correct. Three questions rank any coupling:

- **Strength** — how hard is it to refactor? Static (visible in source) is weaker than dynamic (only shows at runtime).
- **Locality** — how far apart are the connascent elements? The *same* coupling is far worse across module/service boundaries than within one function.
- **Degree** — how many elements are involved?

**The rule:** the farther apart two elements are, the weaker the connascence between them should be. Strong coupling is fine locally, dangerous at a distance.

Review workflow:
1. Identify the coupled elements and **name the connascence type** (see `references/connascence.md` for the full taxonomy and each type's remedy).
2. Judge it by strength × locality × degree. Local + static = usually leave it. Distant + dynamic = flag it.
3. For each thing worth fixing, suggest a concrete weakening — e.g. magic value → named constant (meaning→name).
4. Don't over-refactor: removing all coupling is impossible and chasing it creates indirection. Weaken the *strong, distant, high-degree* cases; leave the rest.

## Lens 3 — Layer placement & boundary leaks

Each piece of code belongs to one layer. Map the codebase first (generic model; infer the repo's equivalent before reviewing):

- **Business layer** — domain rules: invariants, pricing, compliance, lifecycle. Lives in domain/entities, callable from any application caller.
- **Application layer** — software that automates business logic: routes & services, workers, the frontend state/API layer.
- **Technology layer** — infra-neutral plumbing: cloud, DB connection, auth. Business-agnostic.

Flag leaks:
- **Business logic in the wrong layer** — pricing/compliance/lifecycle rules inside a route handler, a UI component, a glue function, or a migration. It belongs in domain code.
- **Technology bleeding up** — raw SQL, cloud SDK calls, queue payloads, storage keys showing up in business/domain code. The domain shouldn't know what it runs on.
- **Layer skip** — frontend reaching past the application API into infra; a route reaching past services into raw infra.

Rule of thumb: *application services apply technology to solve business problems* — business rules stay technology-neutral, tech stays business-neutral.

## Lens 4 — Element cohesion ("one element = one idea")

An element (module, service, function, component, entity) should have **one focus**:

- A function/service doing two unrelated jobs → split it.
- A `util`/`helpers`/`misc` grab-bag accreting unrelated responsibilities → name the real responsibilities and separate them.
- A component mixing data-fetching, business rules, and presentation → extract.
- An entity carrying fields/logic for an unrelated concern → it's modeling two things.

Ask: *if I had to write a one-line "viewpoint" for this element — who reads it, what's its one concern — could I?* If the sentence needs an "and", suspect low cohesion. Low cohesion + high coupling is the signal to split or regroup.

## Lens 5 — Dependency direction

In a focused model each element only connects to elements it's *allowed* to, and dependencies flow a defined way:

- **Direction across layers** — dependencies point **down**: application → business → (nothing); technology supports above. Business code importing a route handler, or domain importing application code, is backwards.
- **Allowed relationships** — does this new import/call connect things that *should* know about each other? A worker reaching into frontend code, a service importing a sibling's internals instead of its public interface, etc.
- **Depend on the exposed interface, not the implementation.** Importing internals = depending on structure, not behavior.

## Lens 6 — Scope discipline (the smallest coherent shape)

Hold the change to its **smallest coherent shape**:

- **Premature abstraction / gold-plating** — generic frameworks, config knobs, or extension points with one caller and no second use case in sight. Deliver the MVP slice.
- **Scope creep** — a focused bugfix/feature that's quietly become a refactor of everything it touched. Flag the part that exceeds the stated goal.
- **Over-modeling** — layers, indirection, or "future-proofing" the task didn't ask for. Tangible artifacts now over complete theory later.

State it as: "X is in scope; Y, Z look like scope creep / speculative — split or drop?"

## Output style

- Be concrete and short. Name the characteristic / connascence type / layer, state the trade-off or fix, move on.
- Always surface at least one cost or counter-point — never present a choice as free.
- Match effort to stakes: a small decision gets a two-line trade-off note inline; only significant ones get the full pass, an ADR, or a fitness function.
- For a review pass, group findings by lens with `file:line`, the rule, and the fix; lead with the highest-leverage finding; if a lens is clean, write "clean" — don't invent findings to fill it.
- Reference files load on demand — read them when you need the taxonomy, the characteristics checklist, the review rubric, or a template, not preemptively.
- This lens reports; it does **not** auto-edit unless the user asks for fixes.
