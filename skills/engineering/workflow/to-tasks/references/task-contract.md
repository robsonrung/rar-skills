# Task contracts

`brief.md` owns the task's full contract. `tasks.md` owns the queue, navigation, and approvals. `shared/references/work-state.md` owns the layout and the status rules.

## brief.md

```text
# T<N>: <title>
**Type:** HITL | AFK
**Parent:** <approved PRD path>
**Covers:** <PRD outcomes or user stories, by decision ID>

## What to build
<observable path through the required layers>

## Acceptance contract
<verified commands, observable behavior, and relevant failure sequences>

## Gates
Design: proceed, with the lenses run and the decision IDs relied on. Open decision: none.
Security: deep | standard, with the matched trigger.
Test lens: <conclusion when it resolved a real choice, otherwise none>

## Rollback note
<rollback path>

## Expected review focus
<risks, invariants, public contracts, and finding IDs to check>

## Parallelization
<owned paths, shared migrations, interfaces, or security surfaces, and the merge plan or serialization>

## Blocked by
<stable IDs or none; product blockers separate from write conflicts>
```

Keep `design-gate` finding IDs stable across rechecks, with each finding's resolution and evidence. When revising an unstarted draft, keep every field. Approval cannot clear an unresolved finding or decision by relabeling it.

## tasks.md before approval

Start with `# Tasks: <feature>`, `**Status:** draft`, and `**Parent:** <approved PRD path>`, then the queue table from work-state with every status `draft`. Acceptance text lives only in the briefs.

Recheck the briefs before promotion; a changed brief needs a fresh decision for what changed. A task-only response authorizes the queue, not worker models. Commits, push, merge, publication, deployment, external messages, and councils keep their own authority.

_Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`)._
