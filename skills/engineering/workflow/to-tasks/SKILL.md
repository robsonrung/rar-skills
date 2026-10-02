---
name: to-tasks
description: Turn an approved PRD into canonical task drafts and an approved dependency queue. Use when planning implementation tasks; supports optional combined task and model approval.
---

# To Tasks

Draft with the current coordinator and direct repository tools. This work needs no full model preview or extra worker. Before dispatching a design or security worker, use `shared/references/model-preview.md` once for the required routes. Nested work uses the parent's immutable approved snapshot.

Turn one approved PRD into an executable queue. Each slice is small enough for one focused implementation run and has a checkable acceptance contract.

## Boundary

Receive `.ai-workflow/work/<feature-slug>/prd.md` with status `approved`. Write each canonical `tasks/T<N>-<slug>.md` once with status `draft`. Keep `tasks-draft.md` as the compact approval and dependency index. Approval promotes these same files to `ready-for-agent`; it does not create a second contract copy. Read [references/task-contract.md](references/task-contract.md) for the task fields, index, approval binding, and legacy queues.

Read `shared/references/workflow-stage-routing.md` before drafting. For each slice, call `design-gate` once for initial routing, then record its `lenses_run`, `required_changes`, and `verdict` in the Slice Contract. If it returns `revise`, ask only the lens with the blocking finding to recheck the fix. A nonempty `decision_required` result returns to the user before approval. A published slice has `verdict: proceed` and `decision_required: none`. Call `security-gate` to record `security: deep|standard`. Use `test-lens` only when the slice has a real test design decision, such as an integration boundary, mock boundary, concurrency case, or brittle existing test.

Do not call individual design lenses directly, a panel, a runner, or `models-consensus`. A `decision_required` result or an unanswered material requirement returns to the user before task approval. If the user explicitly wants extra opinions, direct them to invoke `models-consensus`; its own workflow presents the proposed seats for user approval before it runs.

Default to task-only approval. If the user requests combined task and model approval, prepare the concrete execution preview through `implement-tasks` before asking for one response that covers both decisions. Task-only approval never becomes model approval. Delivery and council authority remain separate.

## Work

1. Confirm that the PRD status is `approved`. A draft or bare plan returns to `to-prd`. Read the relevant code and identify the repository commands that can verify each slice. Never invent a command.

2. Draft vertical slices. Each slice provides one observable path through the needed layers. Prefer a **tracer bullet** that can be verified on its own. Keep a **behavior-preserving** prefactor first only when it removes a shared blocker, and record its characterization test or the existing suite that supplies the net. For a codebase-wide mechanical change, use expand, migrate, and contract slices instead of pretending it is vertical.

3. Assign stable IDs `T1`, `T2`, and onward. IDs never change after assignment because approval refers to them. A split gets a new ID, a deletion leaves a gap, and reordering keeps existing IDs. Dependencies name existing IDs; their graph defines order. Reject self blockers and cycles through the shared queue controller. Mark a slice `HITL` only when a remaining human authorization or decision is truly required. Mark all other slices `AFK`.

4. Attach the Slice Contract to each draft.

   1. Describe the end to end behavior without file paths.
   2. List verified commands and observable acceptance behavior. For stateful work, derive the meaningful failure sequences from its state machine and carry relevant defects from earlier slices. Identify which host adapters require realistic stored-value or integration checks; a synthetic happy-path fixture is insufficient. A feature slice must name behavior. A non feature slice may state `Test expectation: none; <reason>`. Never delete, skip, weaken, narrow, or mock away a test or acceptance check to make this contract pass. If the contract is wrong, return it before approval.
   3. Run `design-gate` and resolve its required changes before approval. If it returns `revise`, change the canonical draft and rerun only the lens that raised the blocking finding. Do not rerun the full lens set. Keep the finding and resolution in that task's Gates section. Carry the selected lens names, final verdict, and required changes. A nonempty `decision_required` result stops promotion until the user resolves it.
   4. Apply `security-gate` and carry its security flag with the matched trigger.
   5. Record a `test-lens` conclusion only when it resolved a real test design choice.
   6. State rollback, review focus, product blockers, and write conflicts separately. Name the owner of each shared contract and the condition that releases its consumers. Serialize slices that share a migration, contract, security surface, or likely write scope unless the draft names a merge plan. Settle a narrow shared interface first only when it removes a real blocker; do not invent a foundation phase merely to create parallel work.

5. Write the canonical task files and compact index using the reference. Keep machine scheduling inputs in `queue.json`. Record dependencies and ownership there, but retain complete acceptance and gate fields in each task. Validate the graph and binding with the read-only shared queue controller before approval.

6. Present each ID, title, canonical path, dependency, type, acceptance summary, gate result, security level, and ownership. Resolve material changes before asking for approval. For combined approval, include the exact resolved routes, source sharing, privacy, receipts, capabilities, tools, and budgets in this same preview. A coordinator-only draft does not need an execution preview until the user requests this option or later execution.

7. Record the actual response, timestamp, approved input identities, and decisions. Promote only the status of each approved canonical task to `ready-for-agent`; all gates must already have `verdict: proceed` and `decision_required: none`. Mark the index approved and link its immutable approval record. Do not rewrite the parent PRD. Never rewrite or delete a started, `done`, or `blocked` contract. A change to its scope, acceptance, gates, or ownership gets a new task ID and approval. Record progress in existing manifests and the ledger.

## Acceptance contract

Every ready task has an approved parent PRD, a stable ID, verified dependencies, a checkable acceptance contract, complete gate and security fields, rollback guidance, review focus, and explicit ownership. The index links the canonical tasks and actual approval. The next step is `implement-tasks`; it reuses exact combined approval or obtains model approval before dispatch. Existing legacy queues remain readable without rewriting started contracts.
