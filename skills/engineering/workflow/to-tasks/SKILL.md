---
name: to-tasks
description: Turn an approved PRD into canonical task drafts and an approved dependency queue. Use when planning implementation tasks; supports optional combined task and model approval.
---

# To Tasks

Turn one approved PRD into an executable queue. Each slice fits one focused `implement-and-review` run and has a checkable acceptance contract. You draft the queue yourself with repository tools. One already accepted task with a complete contract goes straight to `implement-and-review`; do not manufacture a PRD and queue for it.

Read `.ai-workflow/work/<feature-slug>/prd.md`; a status other than `approved` goes back to `to-prd`. Write each task once as `tasks/T<N>-<slug>.md` with status `draft`, plus the `tasks-draft.md` index and `queue.json`, as [references/task-contract.md](references/task-contract.md) describes. Approval promotes those same files.

## Draft the slices

1. Read the relevant code and find the repository commands that can verify each slice. Never invent a command.
2. Cut vertical slices: each is one observable path through the layers it needs, ideally a **tracer bullet** that verifies on its own. Put a **behavior-preserving** prefactor first only when it removes a shared blocker, and name the characterization test or suite that protects it. A codebase-wide mechanical change uses expand, migrate, and contract slices.
3. Assign stable IDs `T1`, `T2`, …. IDs never change, because approval refers to them: a split gets a new ID, a deletion leaves a gap, and reordering keeps IDs. Dependencies name IDs; no self-blockers or cycles. Mark a slice `HITL` only when a human decision or authorization truly remains; otherwise `AFK`.
4. Write each slice's contract:
   1. The end-to-end behavior, without file paths.
   2. Verified commands and observable acceptance behavior. For stateful work, the meaningful failure sequences, and which adapters need realistic stored-value or integration checks. A non-feature slice may state `Test expectation: none; <reason>`. Never delete, skip, weaken, or mock away a check to make the contract pass; a wrong contract goes back before approval.
   3. Design: assess shared design, security, interface, and acceptance decisions once across the queue (`shared/references/workflow-stage-routing.md`), reuse them per task through `shared/references/planning-reuse.md`, and run `design-gate` only on an unresolved or changed boundary. Every published slice carries a gate result per `shared/references/gate-result.md` with `verdict: proceed` and `decision_required: none`.
   4. `security-gate` with its matched trigger. A `test-lens` conclusion only when it settled a real test-design choice.
   5. Rollback, review focus, product blockers, and write conflicts, kept separate. Name the owner of each shared contract and what releases its consumers. Serialize slices that share a migration, contract, security surface, or likely write scope unless a merge plan says otherwise. Do not invent a foundation phase just to create parallel work.
5. For a new feature, bind one central check plan and classify each task deferred or critical as `shared/references/feature-review.md` describes. Each task names its focused regression checks and dependency contract tests.
6. Validate each task with `shared/scripts/gate_contract.py <task.md>` and the queue with `shared/scripts/task_queue.py approval-inputs`.

Do not call design lenses directly, a panel, a runner, or `models-consensus`. A `decision_required` result or an unanswered material requirement goes to the user before approval.

## Approve

Present each ID, title, path, dependencies, type, acceptance summary, gate result, security level, and ownership. Resolve material changes first. Ask: **"Approve this task queue, or specify changes."** Silence or a generated sentence is not approval.

On approval, record the actual response with `shared/references/answer-evidence.md`, change only each task's status line to `ready-for-agent`, and mark the index approved with a link to the response. Never rewrite the PRD, or a started, `done`, or `blocked` task; a change to its scope, acceptance, gates, or ownership gets a new ID and approval.

Task approval is not model approval. When the request includes execution and the user wants one decision, have `implement-tasks` prepare its model plan and present both together; one explicit response then covers both.

The next step is `implement-tasks`.
