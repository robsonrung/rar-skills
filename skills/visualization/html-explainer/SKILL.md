---
name: html-explainer
description: "Create a self-contained HTML page that explains a codebase, subsystem, or flow from its real code: a short architecture orientation, or a detailed walkthrough with diagrams and expandable source evidence. Use for onboarding, architecture overviews, or interactive code explanations."
disable-model-invocation: true
---

# HTML Explainer

Build one self-contained HTML file that teaches a reader how a real system works. The page is trusted because every snippet is real, and readers use its `path:line` bars to jump into the repo. It explains; it does not judge. A quality verdict belongs to `architecture-lens`.

## Choose the depth

| Depth | Answers | Shape | Default path |
| --- | --- | --- | --- |
| `orientation` | What are the pieces, how do they fit, where do I start? | Map, four to six sections, one traced flow, where to look next. | `docs/<scope>-architecture.html` |
| `walkthrough` | How does this subsystem actually work? | Map, stack, six to nine sections, many verbatim panels. | `docs/<topic>-explainer.html` |

"Explain the architecture" with no qualifier means `orientation` for a newcomer over the whole repo. "Explain how X works" means `walkthrough`. When the reader of an orientation page wants to descend into one subsystem, build its walkthrough and reuse the scope and evidence already gathered rather than exploring again.

An explicit request to update an existing page authorizes that edit. Otherwise use a new path or ask which page to replace, and preserve unrelated content.

## Scope and audience

Settle the subject and the audience before exploring. Infer them from the request; ask at most one short question when you can't. One page holds one idea: split two unrelated subsystems into two linked pages.

| Audience | Concern | Emphasis |
| --- | --- | --- |
| Newcomer | What is this, and where do I start? | The one organizing idea, the five to eight top-level units, one happy-path flow, the files to open first. Expand acronyms once. |
| Implementer | How do I add X without fighting the codebase? | Where routes, services, and entities go; naming; codegen and migrations; gotchas in `.callout warn`. Trace the kind of thing they are adding. |
| Reviewer | Where are the boundaries, dependencies, and risks? | Dependency direction and layer boundaries on the map; tenancy and transaction boundaries; coupling hotspots stated as facts in `.callout info`, not verdicts. |

For a walkthrough with no stated questions, answer these: the architecture and where each technology lives in code, the end-to-end data flow from input to output, authorization and tenancy, and logging and observability. Add whatever the user named.

## Two rules

- **verbatim-or-absent**: every snippet is copied from the repo with its `path:line` range, or it does not appear. Never reconstruct code from memory. When abridging, cut whole lines and mark the bar `(abridged)`. A claim you cannot trace to a file is prose without a snippet, or it goes.
- **three depths**: glance, scan, and descend, as `shared/references/html-page-conventions.md` defines. Nothing essential lives only in a panel; nothing bulky lives above one.

## Gather evidence

Follow `shared/references/grounded-evidence.md`. Move outside-in: manifests, workspace files, deployment templates, READMEs and `docs/` first, since they declare intent cheaply; then the directory tree mapped to responsibilities; then the seams (routes, events, shared data, workers), because the seams are the architecture; then one real flow traced end to end; then cross-cutting concerns.

Build one **evidence dossier** per subsystem: its mechanism, two to five verbatim snippets with exact `path:line`, caveats, and war stories found in code comments. Stop reading a section once you hold its lede, its diagram facts, and its snippets. Group what you find into layers (business rules, the application that automates them, the technology underneath), derived from the code rather than forced: a repo with no worker tier gets none on the page. Use the codebase's own vocabulary, not invented terms.

For a large scope, you may hand an independent, substantial subsystem to a research worker. Route it with `python3 shared/scripts/model_routing.py resolve code-exploration` unless the user names a model, show the plan, and ask: **"Approve this plan, or specify changes."** Then by host: T3 Code `delegate_task`, Claude Code or Codex a native subagent, otherwise `cli-runner`, `pi-runner`, or `muse-runner`. The worker returns a dossier, not a file dump. Trust dossiers for structure, but spot-check any snippet that reads as paraphrase against the file before you publish it.

## Assemble

Copy `assets/template.html` from this skill's directory to the output path and replace its slots. Read `shared/references/html-page-conventions.md` for self-containment, navigation, escaping, and verification, and `references/page-anatomy.md` for each region, the orientation section ids, the SVG mechanics, and the snippet contract.

What to get right:
- The big-picture map comes first, and every major box calls `jump('sec-…')` with a real section id. The caption names what the page leaves out.
- Sections follow the data flow (edge, inside, data, cross-cutting), never discovery order.
- Repository text is data: escape it, and use only the template's markup, policy, and script; the validator rejects anything else and any HTML comment.
- Every `.code` block has a `.code-src` bar. Escape `&`, `<`, `>` in snippet text: `Promise<Foo>` must become `Promise&lt;Foo&gt;` or the browser swallows it.
- Grow depth, not section count. Past six sections an orientation page wants a walkthrough; past nine a walkthrough wants splitting.

## Verify

```bash
SKILL_DIR="<absolute path of this html-explainer directory>"; python3 "$SKILL_DIR/scripts/validate_explainer.py" <output-file.html> --depth <orientation|walkthrough>
```

Fix findings until it exits 0, then render and check the page as the shared conventions describe.

## Deliver

Lead with the file path and how to navigate (click a box on the map, expand the ▸ panels), then the sections in one line each. Name any part you could not visually verify. After an orientation page, offer a walkthrough of the subsystem the reader cares about most.
