---
name: to-prd
description: Turn a settled decision record into a PRD for user approval. Use after interview-me or a settled product discussion; to-tasks consumes the approved PRD.
disable-model-invocation: true
---

# To PRD

Turn `.ai-workflow/work/<feature-slug>/decision-record.md`, status `ready-for-prd`, into `.ai-workflow/work/<feature-slug>/prd.md`. You draft it yourself. The PRD stays at the decision level: no fresh architecture choices, files, code, patterns, or test mechanics.

1. Reuse the record's decision IDs and source index, and respect **already decided** choices. Recheck a source only when its locator or revision is missing, or a fact changed or is disputed. A missing material decision or a conflict goes back to `interview-me` with the exact question and the conflicting sources; never write an approvable PRD from a guess.
2. Write the draft with `# PRD: <feature name>` and `**Status:** draft`, and these sections:
   1. Problem and goals.
   2. User stories or journeys.
   3. Observable acceptance outcomes, including important failure behavior.
   4. Settled product, domain, integration, and data decisions.
   5. Security decisions, or `No exposed security surface`.
   6. Rollout and rollback constraints.
   7. Out of scope, assumptions, and remaining risks.
   8. Decision IDs for each outcome and constraint, linked to the record rather than copied.
3. Use the glossary's terms and define any new one once. Where a rule stays ambiguous, add a short scenario naming the actor, record, and outcome.
4. Present the path and the material choices. Revise from user corrections. Mark it `approved` only on explicit acceptance, recording the user's actual words or the host's message locator; silence does not approve it. An `--auto` handoff from `interview-me` still needs this approval.

The approved PRD is the only input `to-tasks` accepts.
