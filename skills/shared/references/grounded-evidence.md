# Grounded evidence contract

Shared by every skill that explains real code to a reader — `explain-architecture` (orientation page) and `html-explainer` (drill-down page) load this file by path. It fixes what counts as evidence so the two outputs never disagree about the same codebase.

## 1. Ground every claim in files you read

Nothing is asserted from memory or from a file's name. Explore outside-in, because the cheap layers declare intent before the expensive ones confirm it:

1. **Entry points and manifests** — package manifests, workspace files, deploy templates, `CLAUDE.md` / `AGENTS.md`, READMEs, `docs/`, config.
2. **Top-level structure** — map directories to responsibilities, one line each.
3. **The seams** — how units talk: HTTP routes, buses and events, shared data layer, cron and workers. The seams _are_ the architecture.
4. **One real flow end-to-end** — trace a representative request or event through every layer. One concrete trace beats any abstract description.
5. **Cross-cutting** — auth, tenancy, error handling, migrations, codegen, observability.

Stop reading a subsystem once you hold what the output needs: its one-paragraph mechanism, its diagram facts, and a handful of load-bearing snippets.

## 2. Cite as `path:line`

Every finding is cited as a repo-relative `path:line` or `path:start-end`. A claim that cannot be traced to a file is stated as prose without a citation, or dropped.

## 3. Verbatim-or-absent

A code snippet is copied verbatim from the repo and labeled with its exact `path:line` range, or it does not appear. Never reconstruct code from memory. When abridging, cut whole lines only and mark the label `(abridged)` or `(excerpt)`. Keep snippets to the load-bearing 5–20 lines; longer means pasting, not explaining.

A snippet arriving without a `path:line` is the signature of paraphrase: re-read the file or drop the snippet.

## 4. The evidence dossier

When a subject spans several subsystems, build one dossier per subsystem before writing any output. A dossier is a short markdown report with:

- the mechanism, explained in the codebase's own vocabulary;
- 2–5 verbatim snippets, each with exact `path:line`;
- caveats and war stories found in code comments — these make the best callouts.

With subagent delegation, dispatch one subagent per subsystem in parallel and keep only the dossiers, not the file dumps. Trust dossiers for structure; spot-check any snippet that looks paraphrased against the file before publishing it (rule 3 still applies).

## 5. Use the codebase's vocabulary

Name components, layers, and events the way the repo names them. Do not invent a taxonomy the reader will not find in the code. Expand an acronym once.

## 6. Safety of what you publish

- Never reproduce secrets, credentials, tokens, or live hostnames found in config. Refer to the secret's _name_ and where it is resolved.
- Governed content stays governed: if the codebase deliberately hides something from a surface (SQL redacted from clients, PII masked in logs), mirror that restraint in your examples.

## 7. Say what you could not verify

Name any component, flow, or snippet you described without reading its source, and any rendering you could not check. An honest gap beats a confident guess.
