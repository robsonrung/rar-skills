---
name: explain-architecture
description: Explain the architecture of a codebase (or a subsystem/service/module within it) as a self-contained HTML orientation page — a clickable component map, the layers and seams, one flow traced end-to-end with file:line evidence, cross-cutting concerns, and "where to look next" — tuned to a newcomer, implementer, or reviewer audience. Use when the user asks "how does this codebase/service work", "explain the architecture", "give me the lay of the land", "onboard me to this repo", "what talks to what", or wants an architecture overview page. A single narrow lookup ("where does Y live") gets a direct answer, not a page. For an exhaustive drill-down walkthrough of one subsystem with many verbatim code panels use html-explainer; for REVIEWING architecture quality use architecture-lens — this skill EXPLAINS, it does not judge.
disable-model-invocation: true
---

# Explain Architecture

Build an accurate mental model of a codebase (or a chosen part of it) and deliver it as one self-contained HTML **orientation page**. The goal is **orientation**, not critique — a reader should finish knowing what the pieces are, how they fit, where data flows, and where to look next.

Borrowed from _Practical Model-Driven Enterprise Architecture_: an explanation is a **view** that answers a defined question for a defined **audience**, split into **structure** (what the parts are and how they connect) and **behavior** (what happens, in what order). Pick the scope and audience first, then explain only what serves them — "a single view tells a single idea."

**Outcome spine**

- **Result:** a single `.html` file (inline CSS/JS/SVG) at `docs/<scope>-architecture.html` by default, rendered from `html-explainer`'s template.
- **Next consumer:** the person orienting themselves — opened straight from disk, no server.
- **Done:** the file exists, `html-explainer`'s validator exits 0, and the page was rendered or sent to the user.
- **Intent:** a map, not the territory. 4–6 sections, one traced flow, every claim grounded in files actually read. Depth beyond that belongs to `html-explainer`.

## Step 0 — Scope & audience (ask only if unclear)

Settle two things before exploring; infer from the request when you can, ask at most one short question when you can't:

- **Scope** — whole repo, one service, one feature/flow, or one module.
- **Audience / viewpoint**:
  - _Newcomer_ — onboarding overview, minimal jargon, "where do I start".
  - _Implementer_ — enough to add a feature here: extension points, conventions, gotchas.
  - _Reviewer_ — boundaries, dependencies, invariants, risk areas.

Default to _newcomer + whole-repo overview_ if the user just says "explain the architecture" with no qualifier.

Once the viewpoint is fixed, read `references/viewpoints.md` for that viewpoint's emphasis and page budget before exploring.

Output path: `docs/<scope>-architecture.html` in the project repo. Only ask when a same-named file you did not create already exists.

## Step 1 — Explore (don't guess)

Follow the shared evidence contract, `../shared/references/grounded-evidence.md` (resolved from this skill's directory): ground every claim in files you actually read, cite `path:line`, never reconstruct code. Move outside-in:

1. **Entry points & manifests** — `package.json`/workspaces, `template.yaml`/SAM, `CLAUDE.md` files, READMEs, `docs/`, config. These declare intent cheaply.
2. **Top-level structure** — map the directory tree to responsibilities. Name each major unit and its one-line job.
3. **The seams** — how units communicate: HTTP routes, message buses/events, shared data layer, cron/workers. The seams _are_ the architecture.
4. **One real flow end-to-end** — trace a representative request or event through the layers (e.g. frontend action → API route → service → entity/DB → emitted event → worker). A concrete trace beats abstract description.
5. **Cross-cutting** — auth, multi-tenancy, error handling, migrations, codegen.

Use `Explore`/`general-purpose` subagents for breadth on large scopes so you keep only the conclusions, not the file dumps. Stop when you hold, for each planned section, its lede, its map facts, and 1–3 verbatim snippets with `path:line`.

## Step 2 — Organize into layers

Group components into the three layers (from the book), so the reader sees order, not a list:

- **Business** — domain rules & invariants.
- **Application** — software automating the domain: services, routes, workers, the frontend app.
- **Technology** — infra plumbing: cloud runtime, database, auth, build/deploy.

Derive the layers from what you actually find rather than forcing these names — a repo that has no separate worker tier does not get one in the page.

## Step 3 — Assemble the page

Copy `../html-explainer/assets/template.html` (resolved from this skill's directory) to the output path and replace its slots. Read `../shared/references/html-page-conventions.md` (self-containment, three depths, escaping, verification) and `../html-explainer/references/page-anatomy.md` (slot definitions, SVG mechanics, code snippet contract, component cheat sheet) before editing.

Map the explanation onto the template like this:

| Page region | Content |
| --- | --- |
| Header subtitle | **In one paragraph:** what this system is and its single organizing idea (e.g. "event-driven serverless monorepo, org-scoped multi-tenant, OpenAPI-first frontend"). |
| Big-picture map | The pieces and their seams as one SVG, boxes grouped by layer (business / application / technology), each box `onclick="jump('sec-…')"` to its section. Caption names what the page leaves out. |
| Tech-stack grid | Only what the viewpoint needs: newcomer gets 3–5 items, reviewer gets the full runtime picture. Drop the region if it adds nothing. |
| 1 · The pieces (structure) | One `details.drill` per major component: one-line job, path, neighbors it talks to. |
| 2 · How it fits together | The layer story, dependency direction, the seams and their contracts. A small section diagram when direction matters. |
| 3 · A flow end-to-end (behavior) | `.flow` steps tracing one real request/event, each step with a `path:line` bar and a short verbatim snippet. |
| 4 · Cross-cutting concerns | Auth, multi-tenancy, migrations, codegen — only what is relevant to the scope. |
| 5 · Where to look next | The 3–5 files/dirs the reader should open first for their goal. |

Add a sixth section only when the viewpoint demands it (reviewer: boundaries & invariants; implementer: extension points & conventions). Never exceed six — more means the subject wants `html-explainer`.

Rules from the book's "modeling best practices", applied to the page:

- **One idea per page.** If two subsystems each need a full treatment, build two pages and link them.
- **Only necessary detail** for the audience — a newcomer doesn't need every Lambda; a reviewer does need the boundaries.
- **Name things with the codebase's own vocabulary** (its taxonomy), not invented terms.
- **Don't editorialize.** Note a smell in one callout if it blocks understanding, but a quality verdict is `architecture-lens`'s job, not this skill's.
- **Verbatim-or-absent** for every snippet, as the evidence contract states.

## Step 4 — Verify

```
SKILL_DIR="<absolute path of the directory containing this SKILL.md>";
python3 "$SKILL_DIR/../html-explainer/scripts/validate_explainer.py" <output-file.html>
```

Fix findings until exit 0, then follow the verification steps in the shared conventions (render, one `jump()` click reaches its section, DOM queries below the first screen).

## Step 5 — Deliver

Lead with the file path and how to navigate (click a box on the map, expand ▸ panels); list the sections in one line each; name any part you could not visually verify. Offer `html-explainer` when the reader wants to descend further into one subsystem — carry over the scope, viewpoint, and dossiers so it does not re-explore.
