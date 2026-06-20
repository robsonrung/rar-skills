---
name: model-lens
description: Review code or a design through model-driven architecture lenses — layer placement & boundary leaks, element cohesion (one thing does one thing), dependency direction, and over-scoping ("boiling the ocean"). Use when the user asks to review architecture, sanity-check where code belongs, check layering/boundaries, spot a module doing too much, question a dependency direction, or warns a change is getting too big. Distinct from architect-lens (trade-offs/connascence) and code-review (bugs).
---

# Model Lens — Model-Driven Architecture Review

Review the change (or design) through four lenses adapted from *Practical Model-Driven
Enterprise Architecture* (ArchiMate/TOGAF). It asks one question: **does this code sit in
the right place, do one job, depend in the right direction, and stay scoped?** For what
this skill is *not* — and which sibling skill to use instead — see "What this skill is
NOT" in `references/review-rubric.md`.

## How to run a review

1. Determine the diff/design under review (`git diff`, a branch, or a described plan).
2. Before walking the lenses, read `references/review-rubric.md` for the per-lens
   checklists; cite its provenance table when a finding is challenged.
3. Walk each lens; collect findings grouped by lens, with `file:line`, the layer, the
   rule, the fix.
4. Order findings by leverage; give a one-line verdict.
5. This lens reports; it does **not** auto-edit unless the user asks for fixes.

## The three layers (worked example: greenspark-aws)

The book's Business / Application / Technology layers map onto greenspark-aws as:

- **Business layer** — domain rules, what the business does: invariants, pricing,
  compliance, ticket/booking lifecycle. Should live in `backend/common` entities/domain
  and `gslogic`, not in HTTP handlers or React components.
- **Application layer** — software that automates business logic: `core-api` routes &
  services, `dispatch`, `eda-worker`, `erp-sync-workflow`, the frontend RTK/API layer.
- **Technology layer** — infra-neutral plumbing: AWS (SAM, EventBridge, Lambda, S3),
  Postgres/TypeORM connection, auth (Amplify). Should be business-agnostic.

A frontend React component is application layer; an AWS SAM template is technology layer; a
TypeORM entity's invariant is business layer. Keep them from bleeding into each other.

In other repos, infer the equivalent mapping first (domain/entities = business;
routes/services/UI state = application; infra/DB/cloud config = technology) and state it
before reviewing.

## Lens 1 — Layer placement & boundary leaks

Each piece of code belongs to one layer. Flag leaks:

- **Business logic in the wrong layer** — pricing/compliance/lifecycle rules inside a
  Fastify route handler, a React component, a Lambda glue function, or a migration. It
  belongs in `common`/domain/`gslogic` and should be callable from any application-layer
  caller.
- **Technology bleeding up** — raw SQL, EventBridge payloads, S3 keys, or AWS SDK calls
  showing up in business/domain code. The domain shouldn't know it's on AWS or Postgres.
- **Layer skip** — frontend reaching past the application API straight into infra
  concerns, or a route reaching past services into raw infra.

Rule of thumb from the book: *"application services apply technology to solve business
problems"* — so business rules stay technology-neutral, and tech stays business-neutral.

## Lens 2 — Element cohesion ("one element = one idea")

The book's strongest rule: **a single diagram tells a single idea**; mixing two ideas
"only adds noise and confuses the reader." Applied to code, an element (module, service,
function, component, entity) should have **one focus**:

- A function/service that does two unrelated jobs → split it (the "two ideas in one
  diagram" smell).
- A `util`/`helpers`/`misc` grab-bag accreting unrelated responsibilities → name the real
  responsibilities and separate them.
- A React component mixing data-fetching, business rules, and presentation → extract.
- An entity carrying fields/logic for an unrelated concern → it's modeling two things.

Ask: *if I had to write a one-line "viewpoint" for this element — who reads it, what's its
one concern — could I?* If the sentence needs an "and", suspect low cohesion.

## Lens 3 — Dependency direction (the "focused metamodel" check)

In a focused metamodel each element only connects to elements it's *allowed* to, and
dependencies flow a defined way. Check:

- **Direction across layers** — dependencies should point **down**: application → business
  → (nothing), and technology supports above. Business code importing from a route handler,
  or `common` importing from `core-api`, is backwards.
- **Allowed relationships** — does this new import/call connect things that *should* know
  about each other? A worker reaching into frontend code, a service importing a sibling
  service's internals instead of its public interface, etc.
- **Service vs. component (book distinction)** — depend on the *exposed service/interface*,
  not the implementation. Importing internals = depending on structure, not behavior.

## Lens 4 — Scope discipline (the smallest coherent shape)

Hold the change to its **smallest coherent shape**. The book's "Effort Blackhole" and
"boil the ocean" warnings, applied to a change:

- **Premature abstraction / gold-plating** — generic frameworks, config knobs, or
  extension points with one caller and no second use case in sight. Deliver the MVP slice.
- **Scope creep** — a focused bugfix/feature that's quietly become a refactor of
  everything it touched. Flag the part that exceeds the stated goal.
- **Over-modeling** — adding layers, indirection, or "future-proofing" the task didn't ask
  for. The book's whole thesis is *tangible artifacts now over complete theory later*.

State it as: "X is in scope; Y, Z look like scope creep / speculative — split or drop?"

## Output format

```
## Model Lens review

### Layer placement
- [file:line] <leak> — belongs in <layer>. <fix>

### Cohesion
- [file:line] <element> does <A> and <B> — split. <fix>

### Dependency direction
- [file:line] <import/call> points <wrong way> — <fix>

### Scope
- <what's in scope> vs <what looks speculative/creeping>

### Verdict
<one line: clean, or the top 1–2 things to address first>
```

Lead with the highest-leverage finding. If a lens is clean, write "clean" — don't invent
findings to fill it.
