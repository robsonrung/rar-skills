---
name: interview-me
description: Grill a feature idea, plan, or design against the code, the glossary (CONCEPTS.md), and past decisions (docs/adr/) until nothing is silently assumed, writing glossary entries and ADRs as decisions settle. The pipeline's specify-phase interview, run before `to-prd`. Use when the user says interview me, grill me on this, stress-test this plan, make this spec-ready, or write an ADR for this decision. Detours to `to-prototype` for a question only running code can settle. Not `brainstorm` (decides WHETHER to build), `to-prd` (synthesizes without interviewing), or `diagnose` (root-causes a bug).
disable-model-invocation: true
---

# Interview — Grill It Until Nothing Is Silently Assumed

Stress-test a feature idea, plan, or design in rounds until it is **spec-ready**: every question the autonomous phases (`to-tasks` and everything after the approval gate) would otherwise have to ask is answered, recorded as an explicit assumption with a default, or descoped. That is the exit test — say it back while working: _"the data-retention question is not spec-ready yet; the rollback question is spec-ready as an assumption with a default."_ The output is a decision record `to-prd` can synthesize a PRD from without asking anything, plus whatever docs settled on the way: glossary entries in `CONCEPTS.md`, and an ADR in `docs/adr/` for any decision that clears the bar. Most simple features produce no ADR; that is correct.

`brainstorm` decides WHETHER to build; this skill pins down WHAT to build; `to-prd` writes it down. Do not implement anything.

## Ground before you grill

Read before asking anything:

1. **`CONCEPTS.md`** (repo-root glossary) — ask in its **ubiquitous language**; a question in the wrong vocabulary collects a wrong answer.
2. **`docs/adr/`** — decisions there are **already decided**: inputs, not questions. Re-open one only with new evidence, and say so.
3. **The code the feature touches** — modules, schemas, tests, integration points. When the user states how something works, check whether the code agrees and surface a contradiction as a question.

If either file is missing, note the gap and ground in the code; create the file lazily when the first entry is ready to write.

**The user's time is the bottleneck.** Facts are your job; decisions are the user's. A question exploration could answer — the code, the glossary, an ADR — is never asked: read it, then bring the finding. When a frontier question needs a fact you have not found yet, dispatch an extraction-tier subagent or read the files yourself without blocking the round; only the questions downstream of that fact wait.

## The design tree and the frontier

Every decision branches into the decisions that hang off it — a **design tree**. **The frontier** is every question you can ask _now_ without guessing at an answer you have not heard: prerequisites settled, nothing assumed. Work the tree in rounds:

1. Compute the frontier. A question that depends on another question still open this round belongs to the _next_ round — say it: _"Q4 hangs off Q1; it waits for the next round."_
2. Ask the whole frontier in one round. Number each question, ground it in what you found in the code (_"the code does X — is that intended here?"_), and give your recommended answer with a one-line reason — **recommendation, not survey**.
3. Wait for the answers. Each one settles a node, pushes the frontier outward, and may prune branches. Recompute and go again.

Use the interactive question tool where it exists (AskUserQuestion in Claude Code): one entry per frontier question, recommended option first and marked as such, an explicit "Other", consecutive calls when a round exceeds the tool's per-call limit. Without one, print the round as numbered `❓ Qn — title: question` / `➡️ Recommended: answer` blocks and wait. Frontier questions are independent by construction, so a round is safe to batch; two questions that could reshape each other are never in the same round.

**Seed the tree from these angles**, skipping any with no exposure — ask only where the answer changes what gets built: actors and permissions; edge cases and failure modes (empty, huge, concurrent, partial, offline); scope boundaries (what is explicitly OUT); sequencing and dependencies; data lifecycle and ownership; integration points and what must not change; non-functional needs that matter here; migration and rollback.

Two passes ride along with the angles:

- **Security rows.** Run the `security-gate` **threat-model-lite** rows the feature exposes — that skill owns the rows; read them there, never copy them here. Record each answer so `to-prd` lifts it into the PRD's Security Decisions.
- **Test seams.** For each major requirement, name the **observable behavior** at the **highest seam** possible (per `test-lens`). These become `to-prd`'s Testing Decisions and, later, slice acceptance behaviors.

## Detour: prototype

Some frontier questions cannot be answered by reading — a state model that has to be pushed through its awkward cases, a page that has to be seen in two or three shapes, an integration whose behavior nobody can state from the docs. When a question meets **both** tests — only running code can settle it, and the answer changes what gets built — hand that one question to `to-prototype` and pause the round it belongs to. Say it: _"Q3 is a prototype question: reading cannot settle whether the reducer shape holds under concurrent edits, and the PRD's data model depends on it."_

`to-prototype` returns `question`, `answer`, `snippets`, `disposition`. Record the `answer` as a settled node like any other; the decision-rich `snippets` are the one kind of code `to-prd` may paste into the PRD. Then recompute the frontier and resume the rounds. Questions that do not hang off the prototyped one keep being asked while it is built — the detour blocks its branch, not the interview.

A question the code, the glossary, or an ADR already answers never earns a prototype, and a prototype question whose answer would not change the spec is a curiosity to record as an assumption, not a detour.

## Record on settle

Docs are written the moment a node settles, not at the end — **record on settle**.

- **Terms.** Challenge a term that conflicts with `CONCEPTS.md` (_"the glossary says 'cancellation' means X; you seem to mean Y — which?"_); sharpen a fuzzy one to a single canonical word. When a term resolves, write its entry now, matching the file's shape: a heading, a one-sentence definition of what the term _is_, an _Avoid:_ line for retired synonyms, no implementation detail. `capture-learning` owns the full vocabulary rules; read them there only when creating the file from nothing.
- **Decisions.** Test each settled decision — **all three or no ADR**: hard to reverse, surprising without context, a real trade-off. Say it as you apply it: _"Q2 is hard to reverse and a real trade-off, but nobody would be surprised — all three or no ADR, so it goes in the decision record."_ For a decision that passes, write the ADR now, while the Consequences are fresh, using `references/adr-template.md` from this skill's directory (file shape, numbering, supersede rule). Status `Accepted` when the user confirmed it, `Proposed` when they asked to record it without committing. Consequences with only upsides means the analysis is missing its cost.

## Exit — the empty frontier

The interview is done when the frontier is empty and the spec-ready test passes: every branch visited, every open question answered, an explicit assumption with a default, or descoped. If any angle still hides a decision, name it and ask it.

Close with a **decision record in the conversation**, each settled decision exactly once: decisions by angle; security answers; seams with their observable behaviors; assumptions with defaults; the explicit OUT list; ADRs written (number, title, path, status); glossary entries added or changed. This is what `to-prd` synthesizes from. Hand off with: "run `to-prd`".

**Acceptance contract:** the decision record exists in the conversation; `git status --short` shows changes only to `CONCEPTS.md` and under `docs/adr/`; every new ADR keeps the directory's naming shape, uses a fresh number, and carries Context, Decision, and Consequences with at least one cost.

## Gotchas

1. Do not ask what exploration could answer — read first, confirm second.
2. Do not put two interdependent questions in one round; the frontier is independent by construction.
3. Do not re-open ADRs or earlier answers without new evidence — **already decided**.
4. Do not leave the docs for the end — record on settle. A session that ends with "I'll write the ADRs now" has already lost the Consequences.
5. Do not write an ADR for a decision that fails any of the three tests, and do not skip one that passes because the feature felt small.
6. Do not copy the `security-gate` rows or the `test-lens` rules into the conversation — reference them, record only the answers.
7. Do not end without the decision record, and do not drift into file-level planning — that is `coding-design-plan`, after the spec.
8. Do not answer a prototype question by guessing, and do not prototype a question reading could answer — both tests in the detour rule, or no spike.

---

_The design-tree rounds and the three-test ADR bar are adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (`grilling`, `domain-modeling`; MIT). See NOTICE._
