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

## Worked example — greenspark-aws whole-repo, newcomer viewpoint

> **In one paragraph.** greenspark-aws is a multi-tenant scrap-metal recycling platform: a
> React/Vite frontend and a serverless AWS backend (SAM) split into domain services that
> communicate over EventBridge. All data is org-scoped (multi-tenant). The frontend's API
> layer is generated from the backend's OpenAPI schema, so types flow backend → frontend
> automatically.
>
> **The pieces.**
> - `frontend/client` — React 17 + MUI + Redux Toolkit app; API calls via generated RTK
>   Query endpoints.
> - `backend/core-api` — main REST API, business logic by domain.
> - `backend/common` — shared TypeORM entities & utilities (the data model).
> - `backend/eda-worker` — event-driven processing off EventBridge.
> - `backend/dispatch`, `erp-sync-workflow`, `compliance`, `pdf-generator` — domain
>   services for assets, ERP integration, regulatory reporting, documents.
>
> **How it fits together.** Frontend → core-api over HTTP; services emit/consume
> EventBridge events; everything shares the `common` entities and one Postgres DB; the
> frontend's typed client is regenerated from core-api's OpenAPI schema (`npm run
> generate:api`).
>
> **A flow end-to-end.** (trace a real request through route → service → entity → emitted
> event → worker, with `file:line` cites)
>
> **Where to look next.** Root `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`, then
> `backend/core-api` routes for the domain you care about.

(Replace the flow section with an actual traced request when running the skill — don't ship
the placeholder.)

---

## Diagram options

- **Inline Mermaid** — fastest. Component graph (`graph LR`) for structure; `sequenceDiagram`
  for a flow. Good default when the user wants a picture.
- **`visual-explainer:generate-web-diagram`** — polished standalone HTML diagram.
- **`visual-explainer:project-recap`** — when they want the broader "state of the project"
  rather than a pure structure diagram.

Always offer; never auto-generate unless asked.

---

## Boundaries with neighboring skills

- This skill **explains**; `model-lens` **reviews** architecture quality.
- `improve-codebase-architecture` finds **refactoring** opportunities — not orientation.
- `init` generates a `CLAUDE.md` — use that if the user wants a committed doc; this skill is
  for an in-session explanation (which can then feed `init`).
