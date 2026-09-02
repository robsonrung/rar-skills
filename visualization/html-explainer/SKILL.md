---
name: html-explainer
description: Create a self-contained, drill-down HTML explainer for a codebase subsystem, service, or architecture — a clickable big-picture SVG map, numbered sections, and expandable panels holding verbatim code snippets with file:line sources. Use when the user asks for an HTML page that explains how a system/feature/service works, an interactive architecture explainer, "document how X works as HTML", or a drill-down technical walkthrough grounded in real code. For a lighter orientation page (map, layers, one flow, where to look next) use explain-architecture; not for a single standalone diagram (use architecture-diagram) and not for slide decks.
disable-model-invocation: true
---

# HTML Explainer

Produce one self-contained HTML file that teaches a reader how a real system works, grounded in the repo's actual code.

**Outcome spine**

- **Result:** a single `.html` file (inline CSS/JS, Google Fonts as the only external resource) explaining the subject at three depths.
- **Next consumer:** the user and their teammates, opening the file directly in a browser — no server, no build step.
- **Done:** the file exists at the agreed path, `scripts/validate_explainer.py` exits 0, and the file was delivered/rendered to the user.
- **Intent:** the page is trusted because every code snippet is real. Readers use the `path:line` bars to jump into the repo.

## Two rules that govern everything

- **verbatim-or-absent** — every code snippet is copied verbatim from the repo and labeled with its `path:line` range, or it does not appear on the page. Never reconstruct code from memory; when abridging, mark the source bar `(abridged)` and cut whole lines only. If a claim can't be traced to a file, state it as prose without a snippet or drop it.
- **drill-down contract** — the page must work at three depths: **glance** (the clickable big-picture map + one-paragraph ledes), **scan** (section summaries, tables, diagrams), **descend** (expandable panels with the code). Nothing essential may live only at descend depth; nothing bulky may live above it.

## Workflow

### 1. Scope

Pin down: the subject (one subsystem/service/flow — split unrelated subjects into separate pages), the audience, and the questions the page must answer.

Pick the audience as one of `explain-architecture`'s viewpoints — read `../explain-architecture/references/viewpoints.md` (resolved from this skill's directory): _newcomer_ keeps sections few and ledes plain, _implementer_ foregrounds extension points and conventions, _reviewer_ foregrounds boundaries, invariants, and dependency direction. When `explain-architecture` already produced an orientation page for this subject, reuse its scope, viewpoint, and dossiers instead of re-exploring, and link the two pages.

Default question set when the user just says "explain how X works": architecture + technologies and where each lives in code, the end-to-end data flow (input → output), authorization/tenancy, and logging/observability. Honor any additions the user named.

Default output path: `docs/<topic>-explainer.html` in the project repo. Only ask when a same-named file you did not create already exists.

### 2. Evidence pass

The evidence rules live in `../shared/references/grounded-evidence.md` (resolved from this skill's directory) — read it, then build one **evidence dossier** per subsystem as it defines (mechanism, 2–5 verbatim snippets with exact `path:line`, caveats and war stories from code comments) before writing any HTML.

Typical decomposition (adapt to the subject): entry/infrastructure + deployment, the main processing pipeline, data access + safety mechanisms, observability/logging. When the harness supports delegating work to subagents, dispatch the dossiers in parallel — one subagent per subsystem, each instructed to return verbatim snippets with `path:line`. Without delegation, explore inline, capped at what the three-depth page actually needs: for each planned section, stop reading once you hold its lede, its diagram facts, and 2–5 snippets.

Trust dossiers for structure, but the snippets you publish are covered by verbatim-or-absent: spot-check any snippet that looks paraphrased against the file before including it.

### 3. Assemble

Copy `assets/template.html` (from this skill's directory) to the output path, then replace its placeholder slots. Read `../shared/references/html-page-conventions.md` first (the floor every page skill shares: self-containment, three depths, escaping, verification), then `references/page-anatomy.md` — it defines each slot, the SVG diagram mechanics (arrow z-order, masking, spacing, clickable groups, palette), and the snippet-escaping rules.

Ordering that matters:

- The big-picture map comes first and every major box carries `onclick="jump('sec-…')"` pointing at a real section id.
- Sections are numbered and ordered along the data flow (edge → inside → data → cross-cutting concerns), not by discovery order.
- Every `.code` block gets a `.code-src` bar with the repo-relative `path:line`.
- Escape `&`, `<`, `>` in snippet text. TypeScript generics are the classic casualty — `Promise<Foo>` must be `Promise&lt;Foo&gt;` or the browser silently swallows it.

### 4. Verify

Run the deterministic check:

```
SKILL_DIR="<absolute path of the directory containing the SKILL.md you just read>";
python3 "$SKILL_DIR/scripts/validate_explainer.py" <output-file.html>
```

Fix findings until exit 0. Then, when a browser surface is available, render the file and confirm the big-picture map draws and a `jump()` click opens its section, following the verification steps in the shared conventions (DOM queries over screenshots below the first screen).

### 5. Deliver

Send/render the file to the user. Lead the summary with the file path and how to navigate (click the map, expand panels); list the sections in one line each. Name any part you could not visually verify.

## Gotchas

- A dossier snippet with no `path:line` is a red flag for paraphrase — re-read the file or drop it (verbatim-or-absent).
- Secrets, live hostnames, and governed/redacted content: §6 of the shared evidence contract applies unchanged — name the secret and where it is resolved, mirror the codebase's own redaction.
- Don't let the page grow section-count instead of depth: 6–9 numbered sections is the ceiling; beyond that, merge or split the page.
