# Canonical task contracts

The task file owns its full slice contract. `tasks-draft.md` owns navigation and the approval link. `queue.json` owns scheduling inputs. The run ledger owns execution progress.

## Task file

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
<the gate's review_focus by reference, plus task-specific risks>

## Parallelization
<owned paths, shared migrations/interfaces/security surfaces, and merge plan or serialization>

## Blocked by
<stable IDs or none; product blockers separate from write conflicts>
```

The queue controller parses the exact `Verdict:`, `Decision required:`, and `Security:` labels, and they must agree with the JSON gate record. When rendering gates from shared conclusions, keep the full rendered gate in the task as `shared/references/planning-reuse.md` describes; the renderer grants no approval and does not carry security over between tasks. When revising an unstarted draft, keep every field. Approval cannot clear an unresolved finding or decision by relabeling it.

## Index

`tasks-draft.md` starts with `# Task Queue: <feature>`, `**Status:** draft`, and `**Parent:** <approved PRD path>`, then a dependency table:

| ID and task path | Title | Blocked by | Type | Contract reference | Gates and security | Ownership |
| --- | --- | --- | --- | --- | --- | --- |
| T1; tasks/T1-example.md | Concrete behavior | none | AFK | Task's Acceptance contract section | proceed; standard | Named scope |

Acceptance text lives only in the task files. Link `queue.json` and its validation result. After approval, add the response reference, decision time, and whether it covered the task queue alone or the queue and model plan.

## Queue and approval binding

`shared/scripts/task_queue.py --help` documents the `queue.json` shape. `task_queue.py approval-inputs --queue <queue.json> --root <project-root>` checks the drafts without dispatch and reports each task's current and prospective ready-state hashes; `shared/scripts/routing_plan.py --help` covers the digests for a combined approval. The scripts own the hashing and normalization rules.

Capture the queue's state before presenting it, and recheck it before promotion; a changed input needs a fresh decision for what changed. Promotion changes only the `**Status:**` line. A task-only response authorizes the queue, not worker models. Commits, push, merge, publication, deployment, external messages, and councils keep their own authority.

_Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`)._
