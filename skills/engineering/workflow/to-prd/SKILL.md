---
name: to-prd
description: Turn a settled decision record into a PRD for user approval. Use after interview-me or a settled product discussion; to-tasks consumes the approved PRD.
disable-model-invocation: true
---

# To PRD

Turn settled choices into one reviewable PRD. The result is an approved specification that `to-tasks` can translate into executable slices.

## Boundary

Receive `.ai-workflow/work/<feature-slug>/decision-record.md` with status `ready-for-prd`. Produce `.ai-workflow/work/<feature-slug>/prd.md` first with status `draft`, then with status `approved` after the user accepts it.

Read `shared/references/workflow-stage-routing.md` before writing. This step preserves settled choices. It does not open fresh architecture choices, prescribe test mechanics, select files, or decide an implementation model or effort level.

Do not call a panel, a runner, `models-consensus`, `design-gate`, `security-gate`, or `test-lens`. If the user explicitly wants additional opinions, direct them to invoke `models-consensus`. When the input has a material missing decision or a conflict with repository facts, return the exact question to `interview-me`. Do not guess or conduct a second interview here.

## Work

1. Confirm that the decision record status is `ready-for-prd`, then read it with the relevant code, domain glossary, and prior architecture decisions. A draft record returns to `interview-me`. Respect the **already decided** choices. If repository facts contradict a settled choice, describe the conflict and return it to `interview-me` before producing an approvable PRD.

2. Write the PRD draft at the stated path. Start it with `# PRD: <feature name>` and `**Status:** draft`.

3. Include these sections:

   1. Problem and goals.
   2. User stories or user journeys.
   3. Observable acceptance outcomes, including important failure behavior.
   4. Product, domain, integration, and data decisions that are already settled.
   5. Security decisions, or `No exposed security surface`.
   6. Rollout and rollback constraints.
   7. Out of scope items, assumptions, and remaining risks.

4. Use the current domain glossary and familiar user terms. Define a new term once; add a short scenario when a rule remains ambiguous, naming the actor, record, and outcome. Do not use a technical label as a substitute for its meaning. Keep the PRD at the decision level. Do not include file paths, code snippets, design patterns, or test mechanics. A prototype snippet belongs only when it is the decision itself and cannot be expressed precisely in prose.

5. Present the draft path and its material choices for review. Ask the user to approve it or request changes. Revise only from the settled record or user corrections.

6. On approval, change the PRD status to `approved`. The approved PRD is the only input `to-tasks` accepts. The next step is `to-tasks`.

## Acceptance contract

The PRD exists at `.ai-workflow/work/<feature-slug>/prd.md`. It has no unresolved decision that would force task planning to guess. Its status is `approved` before task planning begins.
