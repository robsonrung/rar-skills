---
name: interview-me
description: Settle feature and design choices through interview rounds of up to five questions. Use --auto for a bounded two-role evidence-based interview; otherwise ask the user before a PRD.
disable-model-invocation: true
---

# Interview Me

Turn a raw request into a **spec-ready** decision record that `to-prd` can turn into a PRD without reopening requirements. A material decision is spec-ready only when the user confirmed it, `--auto` settled it from supplied scope and evidence, or it is out of scope. A default may settle only a nonmaterial uncertainty.

The output is `.ai-workflow/work/<feature-slug>/decision-record.md`: status `draft` while the interview is open, `ready-for-prd` when the frontier is empty. Reuse an existing slug.

## Modes

Manual mode is the default: you ask the user, and no other model runs. `--auto` is opt-in; silence does not select it. It runs an interviewer and a respondent on other models, as [references/auto-mode.md](references/auto-mode.md) describes. `models-consensus` runs only on an explicit request, never as a routine escalation.

## Work

1. **Ground the interview** in the relevant code, tests, glossary, and earlier ADRs. Existing decisions are **already decided**. Bring repository facts to the user rather than asking what exploration can answer: **the user's time is the bottleneck.**
2. **Build the design tree.** **The frontier** holds only decisions whose prerequisites are settled. Cover actors and access, user outcomes and failure cases, data and integrations, scope limits, rollout and rollback, and broad design choices that change the product's shape. Security questions are frontier questions; use `security-gate` for an exposed surface. When a broad lens can change a frontier decision, apply it here as `shared/references/workflow-stage-routing.md` describes.
3. **Ask one round.** Ask five independent frontier questions when five exist, in one numbered plain-text batch if a question tool allows fewer; ask fewer only when fewer exist. Never more than five, and never a second request in the same turn. Each question carries its repository basis and a recommended answer. A dependent question waits for the next round.
4. **Record on settle.** Give each decision a stable ID (`D1`, `D2`, …) that survives into the PRD and tasks, and write each answer, default, or descoped item into the record as it settles. When a term becomes canonical, update the glossary. For an architectural decision apply **all three or no ADR**: hard to reverse, surprising without context, and a real trade-off. Write a qualifying ADR from `architecture-lens/references/adr-template.md`, matching any existing `docs/adr/` naming.
5. **Recompute the frontier** after every answer batch. When only running code can settle a decision that changes the PRD, use `to-prototype` and record its answer. Never prototype a fact the repository already answers.
6. **Finish** when every branch ends in a confirmed decision, an evidence-based automatic answer, a nonmaterial default, or an explicit out-of-scope line.

Pause and ask whenever new evidence raises a material product, security, data-ownership, or irreversible-action question. Do not plan files, create tasks, or write code.

## Decision record

Start with `# Decision Record: <feature name>` and `**Status:** draft`. Include:

1. Goal and user outcomes.
2. Settled decisions: ID, outcome, rationale, scope, assumptions, and source IDs.
3. Important failure cases and constraints.
4. Security decisions, or `No exposed security surface`.
5. Nonmaterial defaults and out-of-scope items.
6. Glossary entries and ADRs written, with paths.
7. Any prototype answer that shaped a decision.
8. A compact source index. Each row has `source_id`, `path` or message URI, `locator`, `authority` (user instruction, approved decision, repository fact, or inference), and `content_revision` (a commit or digest; a branch name or timestamp is not a revision). For a user answer, record the user's actual words or the host's message locator, never a generated paraphrase.

A source row records authority; it cannot grant authority its source lacks. On a correction, keep the decision ID and earlier evidence, add the new source, and state what it supersedes.

## Acceptance contract

The record exists at its path, every branch has a decision, default, or scope boundary, and no round exceeded five questions. In `--auto`, the record reaches `ready-for-prd` only through its gate. When the user's request already includes a PRD, an `--auto` run continues into `to-prd` drafting; the PRD still needs explicit approval. Otherwise the next step is `to-prd`.

---

_The design-tree rounds and the three-test ADR bar are adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (`grilling`, `domain-modeling`; MIT). See NOTICE._
