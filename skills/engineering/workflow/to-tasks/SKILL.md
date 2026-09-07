---
name: to-tasks
description: Turn an approved PRD into a reviewable queue of executable vertical slices, get task approval, and publish one task file per slice. Use when the user wants an approved PRD broken into implementation tasks. Each slice carries acceptance, gate, security, dependency, rollback, review, and parallelism details. Do not implement code, choose implementation models, or gather extra model opinions.
---

# To Tasks

Turn one approved PRD into an executable queue. Each slice is small enough for one focused implementation run and has a checkable acceptance contract.

## Boundary

Receive `.ai-workflow/work/<feature-slug>/prd.md` with status `approved`. Draft `.ai-workflow/work/<feature-slug>/tasks-draft.md`, get task approval, then publish one file named `T<N>-<slug>.md` per slice under `.ai-workflow/work/<feature-slug>/tasks/` with status `ready-for-agent`.

Read `shared/references/workflow-stage-routing.md` before drafting. For each slice, call `design-gate` once for initial routing, then record its `lenses_run`, `required_changes`, and `verdict` in the Slice Contract. If it returns `revise`, ask only the lens with the blocking finding to recheck the fix. A nonempty `decision_required` result returns to the user before approval. A published slice has `verdict: proceed` and `decision_required: none`. Call `security-gate` to record `security: deep|standard`. Use `test-lens` only when the slice has a real test design decision, such as an integration boundary, mock boundary, concurrency case, or brittle existing test.

Do not call individual design lenses directly, a panel, a runner, or `models-consensus`. A `decision_required` result or an unanswered material requirement returns to the user before task approval. If the user explicitly wants extra opinions, direct them to invoke `models-consensus`; its own workflow presents the proposed seats for user approval before it runs.

Task approval confirms the queue only. It does not approve implementation, external actions, or the build and review model and effort plan. `implement-tasks` presents that plan after the user invokes it.

## Work

1. Confirm that the PRD status is `approved`. A draft or bare plan returns to `to-prd`. Read the relevant code and identify the repository commands that can verify each slice. Never invent a command.

2. Draft vertical slices. Each slice provides one observable path through the needed layers. Prefer a **tracer bullet** that can be verified on its own. Keep a **behavior-preserving** prefactor first only when it removes a shared blocker, and record its characterization test or the existing suite that supplies the net. For a codebase-wide mechanical change, use expand, migrate, and contract slices instead of pretending it is vertical.

3. Assign stable IDs `T1`, `T2`, and onward in the draft. IDs never change after assignment because approval refers to them. A split gets a new ID, a deletion leaves a gap, and reordering keeps existing IDs. Confirm that every blocker names an existing earlier slice, no slice blocks itself, and the dependency graph has no cycle. Mark a slice `HITL` only when a remaining human authorization or decision is truly required. Mark all other slices `AFK`.

4. Attach the Slice Contract to each draft.

   1. Describe the end to end behavior without file paths.
   2. List verified commands and observable acceptance behavior. A feature slice must name behavior. A non feature slice may state `Test expectation: none — <reason>`. Never delete, skip, weaken, narrow, or mock away a test or acceptance check to make this contract pass. If the contract is wrong, return it before approval.
   3. Run `design-gate` and resolve its required changes before approval. If it returns `revise`, change the draft and rerun only the lens that raised the blocking finding. Do not rerun the full lens set. Keep the finding and resolution in `tasks-draft.md`. Carry the selected lens names, final verdict, and required changes. A nonempty `decision_required` result stops publication until the user resolves it.
   4. Apply `security-gate` and carry its security flag with the matched trigger.
   5. Record a `test-lens` conclusion only when it resolved a real test design choice.
   6. State rollback, review focus, blockers, and whether parallel work is safe. Serialize slices that share a migration, contract, security surface, or likely write scope unless the draft names a merge plan.

5. Write `tasks-draft.md` with status `draft`. Start it with `# Task Queue: <feature name>`, `**Status:** draft`, and `**Parent:** <approved PRD path>`. It contains every slice in dependency order and uses this shape:

   ```text
   # T<N>: <title>
   **Type:** HITL | AFK
   **Status:** draft
   **Parent:** <approved PRD path>
   **Covers:** <PRD outcomes or user stories>

   ## What to build
   ## Acceptance contract
   ## Gates
   1. Lenses run: <names or none>
   2. Verdict: <draft result; proceed when published>
   3. Required changes and resolved findings: <items or none>
   4. Decision required: <draft question; none when published>
   5. Security: deep | standard, with trigger
   ## Rollback note
   ## Expected review focus
   ## Parallelization
   ## Blocked by
   ```

6. Present the draft queue for approval. Show each ID, title, dependency, type, acceptance behavior, gate result, security level, and parallelization statement. Resolve material changes, then ask for task approval.

7. On approval, change `tasks-draft.md` to status `approved`. Publish one matching `T<N>-<slug>.md` task file per slice under `tasks/`, change each task status to `ready-for-agent`, set every gate verdict to `proceed` and every decision requirement to `none`, and preserve the stable IDs. Do not change the parent PRD. After publication, never rewrite or delete a task whose status is `in-progress`, `done`, or `blocked`; create a new task ID or return the change for user review.

## Acceptance contract

Every published task has an approved parent PRD, a stable ID, a dependency state, a checkable acceptance contract, `design-gate` fields with `verdict: proceed` and `decision_required: none`, a `security` level, rollback guidance, review focus, and a parallelization statement. `tasks-draft.md` records the approval and any resolved `revise` findings. The next step is `implement-tasks`, which separately presents the concrete model and effort plan for approval before dispatch.

---

_Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`)._
