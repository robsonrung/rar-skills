---
name: to-prd
description: Turn a settled decision record into a PRD for user approval. Use after interview-me or a settled product discussion; to-tasks consumes the approved PRD.
disable-model-invocation: true
---

# To PRD

For a direct invocation, use `shared/references/model-preview.md` to choose the branch first. Coordinator work and deterministic commands proceed within invocation authority. An actual worker branch uses one approved route snapshot. Nested calls reuse it without route selection or added workers.

Turn settled choices into one reviewable PRD. The result is an approved specification that `to-tasks` can translate into executable slices.

Use `shared/references/workflow-measurement.md` for the feature measurement record and capture API. Keep each stage's execution ledger and immutable plan intact. Capture `stage-start` for `to-prd` before drafting, the actual approval wait at request and response, and `stage-end` after approval. Bind the approved requirements identity once it is known through `identity`; preserve earlier observations.

## Boundary

Receive `.ai-workflow/work/<feature-slug>/decision-record.md` with status `ready-for-prd`. Produce `.ai-workflow/work/<feature-slug>/prd.md` first with status `draft`, then with status `approved` after the user accepts it.

Accept the authorized handoff from `interview-me --auto` when the user's existing request includes a PRD. Reuse its completed decision record and feature measurement path. Start this stage separately and retain explicit user approval of the draft.

The coordinator alone drafts this PRD. It preserves settled choices and does not select a model, resolve a route, or dispatch a worker. Keep the PRD at the decision level. It does not open fresh architecture choices or prescribe files, code, design patterns, or test mechanics. A council needs an explicit user request and its separate approval. A missing material decision or a conflict returns to `interview-me`.

## Work

1. Confirm that the decision record status is `ready-for-prd`. Read the record and reuse its stable decision IDs and compact source index, including authority, locators, and content revisions. Respect **already decided** choices. Recheck an original source only when the record lacks a locator or revision, or when a fact has changed or is disputed.

2. Return a material missing decision or source conflict to `interview-me`. State the exact question, conflicting evidence, and source locators. Do not create an approvable PRD from a guess.

3. Write the PRD draft at the stated path. Start it with `# PRD: <feature name>` and `**Status:** draft`. Include these sections:

   1. Problem and goals.
   2. User stories or user journeys.
   3. Observable acceptance outcomes, including important failure behavior.
   4. Settled product, domain, integration, and data decisions.
   5. Security decisions, or `No exposed security surface`.
   6. Rollout and rollback constraints.
   7. Out of scope items, assumptions, and remaining risks.
   8. Decision IDs for the outcomes and constraints, linked to the decision record and its source index. Keep the index in that record rather than copying source content into the PRD.

4. Use the domain glossary and familiar user terms from the decision record. Define a new term once. When a rule remains ambiguous, add a short scenario that names the actor, record, and outcome. Include a prototype snippet only when it is the decision and prose cannot state it precisely.

5. Present the draft path and material choices for review. Revise from the settled record or user corrections. Capture the actual acceptance or correction through `shared/references/answer-evidence.md` and reuse its source ID. Mark the PRD `approved` only after explicit user acceptance. Silence does not approve it.

6. The approved PRD is the only input `to-tasks` accepts. The next step is `to-tasks`.

## Acceptance contract

The PRD exists at `.ai-workflow/work/<feature-slug>/prd.md`. Its settled facts trace to decision record locators and revisions, or to rechecked changed or disputed sources. It has no unresolved decision that would force task planning to guess. Its status is `approved` before task planning begins.
