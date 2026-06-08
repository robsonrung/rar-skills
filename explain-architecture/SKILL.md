---
name: explain-architecture
description: Explain the architecture of a codebase (or a subsystem/service/module within it) — its layers, components, key flows, boundaries, and the "why". Use when the user asks "how does this codebase/service work", "explain the architecture", "give me the lay of the land", "walk me through how X flows", "onboard me to this repo", "what talks to what", "where does Y live". Produces an audience-tuned explanation (newcomer / implementer / reviewer) with an optional diagram. For REVIEWING architecture quality use model-lens; this skill EXPLAINS, it does not judge.
---

# Explain Architecture

Build an accurate mental model of a codebase (or a chosen part of it) and explain it
clearly. The goal is **orientation**, not critique — a reader should finish knowing what
the pieces are, how they fit, where data flows, and where to look next.

Borrowed from *Practical Model-Driven Enterprise Architecture*: an explanation is a **view**
that answers a defined question for a defined **audience**, split into **structure** (what
the parts are and how they connect) and **behavior** (what happens, in what order). Pick the
scope and audience first, then explain only what serves them — "a single view tells a single
idea."

## Step 0 — Scope & audience (ask only if unclear)

Settle two things before exploring; infer from the request when you can, ask at most one
short question when you can't:

- **Scope** — whole repo, one service (`core-api`, `dispatch`, `eda-worker`,
  `erp-sync-workflow`, `frontend`, `common`/`gslogic`), one feature/flow, or one module.
- **Audience / depth**:
  - *Newcomer* — onboarding overview, minimal jargon, "where do I start".
  - *Implementer* — enough to add a feature here: extension points, conventions, gotchas.
  - *Reviewer* — boundaries, dependencies, invariants, risk areas.

Default to *newcomer + whole-repo overview* if the user just says "explain the architecture"
with no qualifier.

## Step 1 — Explore (don't guess)

Ground every claim in files you actually read. Move outside-in:

1. **Entry points & manifests** — `package.json`/workspaces, `template.yaml`/SAM,
   `CLAUDE.md` files, READMEs, `docs/`, config. These declare intent cheaply.
2. **Top-level structure** — map the directory tree to responsibilities. Name each major
   unit and its one-line job.
3. **The seams** — how units communicate: HTTP routes, EventBridge events, shared
   `common` entities/TypeORM, RTK Query API layer, cron/workers. The seams *are* the
   architecture.
4. **One real flow end-to-end** — trace a representative request or event through the
   layers (e.g. frontend action → API route → service → entity/DB → emitted event →
   worker). A concrete trace beats abstract description.
5. **Cross-cutting** — auth, multi-tenancy (org-scoping), error handling, migrations,
   codegen (OpenAPI → RTK Query).

Use `Explore`/`general-purpose` subagents for breadth on large scopes so you keep only the
conclusions, not the file dumps. Cite findings as `file:line`.

## Step 2 — Organize into layers (this repo)

Group components into the three layers (from the book), so the reader sees order, not a list:

- **Business** — domain rules & invariants: `backend/common` entities/domain, `gslogic`.
- **Application** — software automating the domain: `core-api` routes & services,
  `dispatch`, `eda-worker`, `erp-sync-workflow`, `compliance`, `pdf-generator`, frontend
  RTK/API layer & React app.
- **Technology** — infra plumbing: AWS SAM/Lambda/EventBridge/S3, Postgres/TypeORM,
  Amplify auth, Vite build/deploy.

For a non-greenspark repo, derive the equivalent layers from what you find rather than
forcing these names.

## Step 3 — Explain (output)

Tune length to audience. Lead with the big picture, then drill down. Use this skeleton:

```
## Architecture: <scope>

### In one paragraph
<what this system is and the single organizing idea — e.g. "event-driven serverless
monorepo, org-scoped multi-tenant, OpenAPI-first frontend">

### The pieces (structure)
- **<component>** (`path/`) — <one-line job>. Talks to: <neighbors>.
- ...

### How it fits together
<the seams: how components communicate, dependency direction, the layer story>

### A flow end-to-end (behavior)
1. <step> (`file:line`)
2. ...
<one concrete request/event traced through the layers>

### Cross-cutting concerns
<auth, multi-tenancy, migrations, codegen — only what's relevant to the scope>

### Where to look next
<the 3–5 files/dirs the reader should open first for their goal>
```

Rules from the book's "modeling best practices", applied to prose:
- **One idea per explanation.** If two subsystems each need a full treatment, say so and
  offer to explain the second separately rather than tangling them.
- **Only necessary detail** for the audience — a newcomer doesn't need every Lambda; a
  reviewer does need the boundaries.
- **Name things with the codebase's own vocabulary** (its taxonomy), not invented terms.
- **Don't editorialize.** Note a smell in one line if it blocks understanding, but routing
  a quality verdict is `model-lens`'s job, not this skill's.

## Step 4 — Offer a diagram (don't auto-generate)

After the written explanation, offer a visual if it would help:
- A quick **Mermaid** block inline (component or sequence diagram) for most cases.
- For a polished standalone artifact, suggest `visual-explainer:generate-web-diagram` or
  `visual-explainer:project-recap`.

Only produce the diagram if the user wants it — keep the default response readable text.

See `references/viewpoints.md` for per-audience templates and example flows.
