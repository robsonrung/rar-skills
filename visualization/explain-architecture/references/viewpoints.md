# Explain Architecture — viewpoints & page budgets

A _viewpoint_ (from _Practical Model-Driven Enterprise Architecture_, Ch 5) names **who** the explanation is for and **what concern** it answers. Same codebase, different viewpoint = different page. Pick one; don't blend three audiences into one wall of panels.

---

## Viewpoint: Newcomer (onboarding)

**Concern:** "What is this, and where do I start?"

- Lead with the one-paragraph identity and the single organizing idea in the subtitle.
- Map shows the 5–8 top-level units; section 1 gives each one line and one panel. Skip internal detail.
- Trace ONE happy-path flow so they see the pieces move.
- Section 5 ("open these 3 files first") is the payoff — make it concrete.
- Minimize jargon; expand acronyms once.

Page budget: 4–5 sections, ≤ 8 drill panels, snippets only in the flow. They will get lost in completeness — give them a map, not the territory.

## Viewpoint: Implementer (adding a feature)

**Concern:** "How do I add X without fighting the codebase?"

- Show the conventions: where routes/services/entities/components go, naming, the codegen step (e.g. OpenAPI → generated client), how migrations are created/run.
- Add the sixth section: **extension points & conventions** for the area they're touching.
- Call out gotchas in `.callout warn` panels: tenancy scoping, event contracts, shared types, feature flags.
- Trace the flow _of the kind of thing they're adding_ (a new endpoint, a new event consumer), not a random one.

Page budget: 5–6 sections, 8–14 drill panels, concrete and example-driven.

## Viewpoint: Reviewer / architect

**Concern:** "Where are the boundaries, dependencies, and risks?"

- Emphasize dependency direction and layer boundaries on the map (dashed boundary rects, arrows only in the allowed direction). Pairs well with `architecture-lens`.
- Add the sixth section: **boundaries & invariants** — multi-tenancy enforcement points, transaction boundaries, the event-driven seams and their contracts.
- Note coupling hotspots and single points of failure factually, in `.callout info`, not as verdicts.

Page budget: 5–6 sections, 10–16 drill panels, precise. A section diagram earns its keep here.

---

## Structure vs behavior (always cover both)

The book splits every system into two view types — the page has a section for each:

- **Structural** (sections 1–2) — the parts and their relationships (component map, dependency direction, who-owns-what). Answers _what exists_.
- **Behavioral** (section 3) — the sequence of what happens (request lifecycle, event flow, cron cadence). Answers _what happens, in what order_.

A list of components without a flow leaves the reader unable to reason about runtime; a flow without the component map leaves them unable to locate code. Give both.

---

## Boundaries with neighboring skills

- `html-explainer` is the **descend** step: 6–9 sections and many verbatim panels on one subsystem. This skill is the **glance and scan** page that points into it.
- `architecture-lens` **judges** quality (coupling, boundaries, trade-offs) — this skill orients.
- `init` generates a `CLAUDE.md` — use that if the user wants a committed prose doc; the page produced here can feed it.
