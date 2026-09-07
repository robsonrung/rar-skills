# Feature orchestration

Read after the model plan is approved. `implement-tasks` owns scheduling and integration; `implement-and-review` owns each task's build and review.

## Worker brief

Use a fresh native subagent or runner context per task. Supply these fields in its first message:

```text
Task: <stable T-ID and task file path>
Skill: implement-and-review
Scope: <allowed paths, interfaces, and exclusions>
Base: <current integration revision, or sequential working tree>
Inputs: <PRD, task, decisions, and relevant evidence paths>
Models: <approved implementation/review models, runners, effort, and receipt policy>
Approval: <routing-plan.json, model-plan.md, and approval entry>
Authorization: <permitted local changes and authorized git/publication actions>
Acceptance: <exact commands and observable behaviors from the task>
Report: <unique task report and envelope paths>
Ceilings: three review/fix cycles; one evidence recovery
Return: complete, failed, ceiling_hit, or awaiting_human; evidence paths and remaining blockers
```

The acceptance contract is a completion condition, not a host `/goal` command. Do not use a user-owned task as a subagent unless requested. Do not fork unrelated conversation history into a worker.

Workers load selected lenses and practices when their task needs them. They cannot select new models or add panels outside the approved plan. Reuse the task worker for a bounded correction; use a fresh context for the next task.

## Scheduling

1. Validate the graph before starting. Reject unknown IDs, self-dependencies, and cycles. Preserve stable task IDs.
2. A task is ready when every blocker is `done` and its changes passed acceptance on the integration state.
3. Honor the queue's parallelization constraints. Serialize shared files, migrations, interfaces, and security-sensitive paths unless there is an explicit merge plan.
4. Start at most the approved number of tasks. Each new worktree starts at the current integration revision. A running independent task can finish on its recorded base; check its result again after integration.
5. Record worker IDs and task states. Read compact status and result envelopes. Open report bodies for failures and final synthesis, not repeated polling.

## Integration

Use the project's branch convention and preserve unrelated changes. Use commit-based worktree integration only when commits are authorized. Otherwise run tasks sequentially in the working tree and record acceptance after each task.

Before an authorized merge, record a pending effect with task ID, source revision, and target revision. Merge, verify ancestry and acceptance, then confirm the effect. After a crash, inspect the repository before retrying a pending merge.

Do not mark a task done on worker completion alone. Review conflict resolutions, capture checks on the combined state, then release dependents. A failed task blocks descendants, not unrelated tasks.

## Per-task launcher

Use the launcher bundled with the loaded `implement-and-review` skill when it supports the approved plan. Read its documented flags; do not construct a second frontend/backend workflow here. Pass `--routing-plan`, `--task-id`, the task namespace, base, and named task briefs through the documented `--track` arguments. Launcher defaults cannot override approval.

If a launcher cannot represent a model, effort, or execution mode, report the mismatch before dispatch. Use an already approved adapter or ask for a route change. Report configured and observed models separately. A route without an observed serving-model receipt can continue only under its approved `allow_unverified` policy.

## Completion

Keep task reports after workers finish. Close native workers through the host lifecycle when needed. Leave user-owned tasks, branches, and worktrees intact unless cleanup is authorized.

Run combined acceptance and the approved seam review. Report blocked tasks and missing evidence. Resume from the ledger and repository state; a report path alone does not prove its revision is current.
