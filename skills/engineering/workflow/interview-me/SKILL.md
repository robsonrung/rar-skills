---
name: interview-me
description: Settle feature and design choices through interview rounds of up to five questions. Use --auto for a bounded two-role evidence-based interview; otherwise ask the user before a PRD.
disable-model-invocation: true
---

# Interview Me

For a direct invocation, use `shared/references/model-preview.md` to choose the branch first. Coordinator work and deterministic commands proceed within invocation authority. An actual worker branch uses one approved route snapshot. Nested calls reuse it without route selection or added workers.

Turn a raw request into a **spec-ready** decision record that `to-prd` can turn into a PRD without reopening requirements. A material decision is spec-ready only when it is confirmed, settled by supplied scope and evidence in `--auto` mode, or out of scope. An explicit default is allowed only for a nonmaterial uncertainty.

Use `shared/references/workflow-measurement.md` for the feature measurement record and capture API. Keep each stage's execution ledger and immutable plan intact. Create the feature measurement record with `start` and only known identity fields before the first round, then capture `stage-start` for `interview-me`. In `--auto`, import the reconciled completed role ledger through `stage-ledger` with its actual path and hash. Capture `stage-end` when the decision record is ready for the PRD, and pass the feature measurement path onward.

## Boundary

Receive a feature request, an earlier exploration, and repository facts. Produce `.ai-workflow/work/<feature-slug>/decision-record.md` with status `draft` while the interview is open and `ready-for-prd` when the frontier is empty.

Use `shared/references/workflow-stage-routing.md` when a broad lens can change a frontier decision. Apply the selected lens in this interview. Dispatch an independent specialist only for a material risk or unresolved question under its approved route. Use `security-gate` for an exposed security surface. Use `to-prototype` only when running code is the smallest reversible move that can settle a decision.

## Modes

Use a supplied or inherited mode. When no mode is supplied, manual mode is the safe scoped default. Ask only when a mode changes scope, cost, permitted effects, or an unresolved decision. Silence does not authorize `--auto`.

Manual mode asks the user the questions in this skill and creates no automatic roles or runner calls. `--auto` is an opt-in two-role interview. Read [references/auto-mode.md](references/auto-mode.md) before dispatch. The coordinator records one concrete route snapshot for its actual calls. Both roles consume that snapshot without re-resolving a route or adding a worker. `--auto` authorizes the selected default pair to make evidence-based answers within the supplied scope. A changed route, `models-consensus`, implementation, publication, or an irreversible external effect needs its own authority.

Use `models-consensus` only for an explicitly requested council with its separate approval. The interview does not use a council as a routine escalation.

This stage completes at the decision record. In `--auto` mode, when the user's existing request includes a PRD, continue into `to-prd` drafting without another command after the ready-for-PRD gate passes. Preserve the completed decision record and `ready-for-prd` status. Finish the interview ledger and capture its `stage-end`, then pass the same feature measurement path to `to-prd` for its separate `stage-start`. The user's existing PRD request authorizes drafting; explicit PRD approval remains required. An interview-only request stops at the decision record. Manual mode is unchanged. Do not plan files, create tasks, or implement code.

## Work

1. Ground the interview in the relevant code, tests, domain glossary, and earlier architecture decisions. Existing decisions are **already decided**. Bring repository facts to the user instead of asking questions that exploration can answer. **The user's time is the bottleneck.**

2. Build the **design tree**. The **frontier** contains only user decisions whose prerequisites are settled. Cover actors and access, user outcomes and failure cases, data and integrations, explicit scope limits, rollout or rollback, and broad design choices that change the product shape. Security questions count as frontier questions.

3. Run one round of independent questions.

   1. In manual mode:

      1. Ask exactly five when five independent frontier decisions exist and the current conversation can receive five questions in one response.
      2. When an interactive question tool has a lower limit but plain text is available, ask five in one numbered plain text batch. Otherwise ask fewer only when fewer independent decisions exist or the surface cannot receive more.
      3. Never ask more than five. Never send a second question request in the same turn to compensate for a tool limit.
      4. Give each question its repository basis and one recommended answer. A dependent question waits for the next round.

   2. In `--auto` mode, use the bounded round protocol in [references/auto-mode.md](references/auto-mode.md). Do not ask the user between automatic rounds unless only material unknowns remain.

4. **Record on settle.** Assign each frontier decision a stable ID (`D1`, `D2`, onward) and retain it through questions, answers, PRD outcomes, and task references. Write each answer, nonmaterial default, or descoped item into the decision record as it settles. Use the Decision record evidence fields below in both modes. Never use a default to bypass a material decision. In `--auto` mode, keep the provenance, evidence, assumptions, and role execution reference that [references/auto-mode.md](references/auto-mode.md) requires. When a term becomes canonical, update the glossary entry. For an architectural decision, apply **all three or no ADR**: it must be hard to reverse, surprising without context, and a real tradeoff. Write a qualifying ADR from `references/adr-template.md` when it settles.

5. Recompute the frontier after every user reply or automatic answer batch. If only a runnable experiment can settle a decision and that answer changes the PRD, use `to-prototype`, record its answer, and continue with independent questions in a later round. Do not prototype a fact the repository already answers.

6. Finish when the frontier is empty. A branch may end in a confirmed decision, an evidence-based automatic answer within the supplied scope, a nonmaterial assumption with a default, or an explicit out of scope statement. In `--auto` mode, apply its ready-for-PRD gate before changing the record status.

## Decision record

Write a short kebab case feature slug, reusing an existing one when present. Start with `# Decision Record: <feature name>` and `**Status:** draft`; change the status to `ready-for-prd` when the interview finishes. The decision record contains:

1. Goal and user outcomes.
2. Settled choices and their repository basis.
3. Important failure cases and constraints.
4. Security decisions from `security-gate`, or `No exposed security surface`.
5. Nonmaterial assumptions with defaults and explicit out of scope items.
6. Glossary entries and ADRs written, with their paths.
7. Any prototype answer that shaped a decision.
8. In `--auto` mode, a provenance entry for each automatic choice: its source category, evidence paths or locators, stated assumptions, and role execution reference. Include the active run ID and state path while the run is unfinished. Keep `awaiting-human` items open.

### Decision evidence

Use one compact source index in the decision record. Each source row contains `source_id`, `path` (or durable message/artifact URI), `locator` (section, symbol, range, or message ID), `authority` (user instruction, approved decision, repository fact, or inference), and `content_revision` (immutable revision or content digest). A branch name or timestamp alone is not a content revision. Record a captured result path and digest for command evidence. For a user answer, use `shared/references/answer-evidence.md`: retain an available native locator or an immutable capture of the actual answer with the missing-locator limit. Reuse its source ID and digest.

Each decision contains `decision_id`, outcome, status, rationale, applicable scope, source IDs, and explicit assumptions. Keep material unknowns open. Automatic choices also retain their source category and role execution reference. A source row describes authority; it cannot grant authority that the source lacks.

On correction or conflict, preserve the ID and earlier evidence, append the new source revision, and state which choice it supersedes. Reuse **already decided** choices while their scope, authority, and sources still match. Recheck missing, changed, or disputed evidence before using the affected decision. Interview lenses return decision fields in this record; they do not require separate briefs, code edits, or interface comments.

## Acceptance contract

The decision record exists at the stated path. Every open branch has a decision, nonmaterial default, or scope boundary. No question round exceeded five questions. An automatic record reaches `ready-for-prd` only through its evidence and material-unknown gate. The next step is `to-prd`.

---

_The design-tree rounds and the three-test ADR bar are adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (`grilling`, `domain-modeling`; MIT). See NOTICE._
