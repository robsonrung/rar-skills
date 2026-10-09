# Canonical task contracts

Use this reference when drafting, approving, or reading an existing queue. A task file owns its full Slice Contract. The index owns navigation and the approval reference. The existing task manifest and call ledger own execution progress.

## Canonical task

Write `tasks/T<N>-<slug>.md` before approval:

```text
# T<N>: <title>
**Type:** HITL | AFK
**Status:** draft
**Parent:** <approved PRD path>
**Covers:** <PRD outcomes or user stories>

## What to build
<observable path through the required layers>

## Acceptance contract
<verified commands, observable behavior, and relevant failure sequences>

## Gates
Verdict: proceed | revise
Decision required: none | <decision ID>
<one versioned gate-result JSON block from shared/references/gate-result.md>
Security: deep | standard; trigger: <matched trigger>
Test lens: <conclusion when it resolved a real choice, otherwise none>

## Rollback note
<rollback path>

## Expected review focus
<risks and affected contracts>

## Parallelization
<owned paths, shared migrations/interfaces/security surfaces, and merge plan or serialization>

## Blocked by
<stable IDs or none; distinguish product blockers from write conflicts>
```

Use a new ID for a split or a replacement. Deletion leaves an ID gap. Keep every acceptance, gate, security, rollback, review, and ownership field when revising an unstarted draft. Approval cannot clear an unresolved finding or decision by changing its label.

## Canonical gate result

Read `shared/references/gate-result.md` for the canonical fields and finding contract. Use the task Markdown labels shown above; the queue controller requires the exact `Verdict:`, `Decision required:`, and `Security:` labels. The versioned JSON holds the complete gate record; these labels must agree with it. Run `shared/scripts/gate_contract.py <task.md>` before approval.

Carry the gate's `review_focus` into Expected review focus by reference and add only task-specific risks there. Legacy task fields remain readable; fill missing fields when revising an unstarted draft, without rewriting a started contract.

## Compact index

Write `tasks-draft.md` with `# Task Queue: <feature>`, `**Status:** draft`, and `**Parent:** <approved PRD path>`. Follow them with a dependency table:

| ID and task path | Title | Blocked by | Type | Contract reference | Gates and security | Ownership |
| --- | --- | --- | --- | --- | --- | --- |
| T1; tasks/T1-example.md | Concrete behavior | none | AFK | Task's Acceptance contract section | proceed; standard | Named scope |

The table links canonical contracts and scheduling metadata. Keep acceptance text only in each task file; read it there when presenting the human preview. Link `queue.json` and its validation result. Use `shared/scripts/task_queue.py --help` for the scheduling input shape; `approval-inputs --queue <queue.json> --root <project-root>` checks drafts without dispatch. After approval, add the actual response reference, decision time, immutable approval record, and whether the response covered `task_queue` only or both `task_queue` and `model_plan`.

## Approval binding

Before presenting the queue, capture the current PRD, index, queue configuration, and task identities in an immutable preview. Capture the proposed execution routes only for combined approval. Retain the actual response with `shared/references/answer-evidence.md`; a generated approval sentence, preference, or silence is not a response.

Bind each draft's current hash and its prospective ready-state content hash. The prospective text differs only by replacing its exact `**Status:** draft` line with `**Status:** ready-for-agent`. Use the launcher's content normalization for the prospective hash. The launcher excludes an exact ready, in-progress, done, or blocked status line; it retains all acceptance and gate content. Do not change the shared normalization rule to exclude arbitrary status prose.

Recheck the draft identities before promotion. If any input changed, update the concrete preview and get a decision for the changed scope. On approval, change only the task status. Verify the resulting task content hashes against the prospective hashes, then build the standard approved routing scope from those hashes when models were approved. Keep the original preview and response unchanged. Index status and added approval links are administrative changes; retain the exact reviewed index as evidence rather than treating the live index as immutable scope.

A task-only response authorizes the queue, not worker models. A combined response must explicitly cover both decisions and bind all preview inputs. `implement-tasks` owns its model plan and records separate gate entries for the two decisions using that one response. Commits, push, merge, publication, deployment, external messages, and council execution keep their own authority.

## Existing queues

Read published `T<N>-<slug>.md` files from a legacy queue as canonical. The old `tasks-draft.md` can retain its copied contracts and approval history. Do not require its rewrite to execute an approved queue. If only a legacy draft index exists, derive each task once before approval, compare every field with the source, and record the derivation. No draft can run.

The controller can read legacy task Markdown and dependencies. Supply approved ownership and manifest locators when a legacy queue lacks machine scheduling inputs. Add these as a separate routing scope input before dispatch. This new binding does not grant model approval or change an existing started contract. Missing ownership, approval, or integration evidence blocks only the work that needs it.

_Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`)._
