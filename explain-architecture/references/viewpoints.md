# Explain Architecture — viewpoints, templates & examples

A *viewpoint* (from *Practical Model-Driven Enterprise Architecture*, Ch 5) names **who**
the explanation is for and **what concern** it answers. Same codebase, different viewpoint =
different explanation. Pick one; don't blend three audiences into one wall of text.

---

## Viewpoint: Newcomer (onboarding)

**Concern:** "What is this, and where do I start?"

- Lead with the one-paragraph identity and the single organizing idea.
- Name the 5–8 top-level units, one line each. Skip internal detail.
- Trace ONE happy-path flow so they see the pieces move.
- End with "open these 3 files first."
- Minimize jargon; expand acronyms once.

Length: short. They will get lost in completeness — give them a map, not the territory.

## Viewpoint: Implementer (adding a feature)

**Concern:** "How do I add X without fighting the codebase?"

- Show the conventions: where routes/services/entities/components go, naming, the codegen
  step (OpenAPI → RTK Query), how migrations are created/run.
- Show the **extension points** for the area they're touching.
- Call out gotchas: org-scoping, event contracts, shared `common` types, feature flags.
- Trace the flow *of the kind of thing they're adding* (a new endpoint, a new event
  consumer), not a random one.

Length: medium, concrete, example-driven.

## Viewpoint: Reviewer / architect

**Concern:** "Where are the boundaries, dependencies, and risks?"

- Emphasize dependency direction and layer boundaries (pairs well with `model-lens`).
- Surface invariants, multi-tenancy enforcement points, transaction boundaries, the
  event-driven seams and their contracts.
- Note coupling hotspots and single-points-of-failure factually.
- A diagram earns its keep here.

Length: medium–long, precise.

---

## Structure vs behavior (always cover both)

The book splits every system into two view types — explain both:

- **Structural** — the parts and their relationships (component map, dependency direction,
  who-owns-what). Answers *what exists*.
- **Behavioral** — the sequence of what happens (request lifecycle, event flow, cron
  cadence). Answers *what happens, in what order*.

A list of components without a flow leaves the reader unable to reason about runtime; a flow
without the component map leaves them unable to locate code. Give both.

---

## Worked example

For a full worked example (greenspark-aws whole-repo, newcomer viewpoint), see
`greenspark.md` in this directory.

---

## Boundaries with neighboring skills

- `improve-codebase-architecture` finds **refactoring** opportunities — not orientation.
- `init` generates a `CLAUDE.md` — use that if the user wants a committed doc; this skill is
  for an in-session explanation (which can then feed `init`).
