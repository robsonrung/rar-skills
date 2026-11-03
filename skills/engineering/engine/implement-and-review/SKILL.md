---
name: implement-and-review
description: Implement one approved coding task, have a reviewer on a different model check it, and fix what the review confirms until the acceptance contract passes. Use for a scoped task with acceptance criteria; implement-tasks coordinates a queue.
---

# Implement And Review

Build one task to its **acceptance contract**. An implementer builds it, a reviewer on a different model checks it, and the implementer fixes what the review confirms. Worker success is evidence, not acceptance; you accept the task.

## Plan

1. Read the task, its acceptance contract, the code it touches, and the project's conventions. Settled design, security, and interface decisions are **already decided**; reopen only a boundary that changed.
2. Choose the roles. Use the routes in a plan you inherited from `implement-tasks`, or else the models the user names. Otherwise run `python3 shared/scripts/model_routing.py resolve <route> [--risk high]` with the route that fits the task's shape, for example `routine-implementation`, `hard-implementation`, or `migration` (`show` lists every route). The reviewer's model always differs from the implementer's.
3. Show the task, each role with its model, effort, and host route, and the limit of three review cycles. Ask: **"Approve this plan, or specify changes."** An inherited approved plan is already the approval.

## Roles

Give each role one persistent context for the whole task. Fixes go back to the same implementer and rechecks to the same reviewer. The reviewer never sees the implementer's transcript, only the contract, the diff, and the evidence.

Route each role by host:
- **T3 Code:** start it with `delegate_task` using the configured provider and model, and continue it with `t3_thread_send`.
- **Claude Code or Codex:** use a native subagent when the host has the model, and continue it by messaging that same subagent.
- **Model the host lacks:** use `cli-runner`, `pi-runner`, or `muse-runner`. An unavailable role blocks its work, and you report it; never swap in another model.

The implementer edits only within the task's scope. Neither role commits, pushes, merges, opens a pull request, deploys, or messages an outside service. Tell the reviewer to leave every file unchanged.

## Brief the implementer

Hand over the contract path rather than its text. Then give:
- the scope and the behavior that must stay unchanged;
- the named risk;
- the evidence route below;
- at most three methods picked by trigger;
- the boundary above.

| Trigger | Method |
| --- | --- |
| Behavior changes | `tdd`: one failing check, the minimal change, refactor on green. |
| Untested legacy behavior | `safe-incremental-coding`: a **characterization test** before the change. |
| The cause is not established | `diagnose` before any fix. |
| Unresolved module or public boundary | `coding-design-plan`, then `design-gate` if no lens has settled it. |
| Stored state, queue, migration, retry, or external API | `data-systems-coding-lens`. |
| Business rule or context boundary | `domain-driven-design`. |
| Agent loop, durable state, tool retry, or human gate | `agent-architecture-lens`. |
| UI composition, state, or fetch lifecycle | `advanced-react` or `frontend-design`. |
| Concrete smell, or test choice that needs judgment | `clean-code` or `test-lens`. |

Keep the change a **native diff**: touch only what the contract needs, in the house style.

## Evidence

| Situation | Required evidence |
| --- | --- |
| An existing test exposes the behavior | Its failing run before the change. |
| A nearby test asserts the old behavior | Its updated expectation, failing before the change. |
| Coverage misses the real path | The smallest new failing test. |
| Automated testing is not meaningful | The reason, and a direct replacement check. |

A behavior change reports the tests inspected, the tests added or changed, the red baseline, the verification commands, and their results. **Only captured command results count as evidence**: capture each check with `shared/scripts/capture_check.py run` into the task's `evidence/` folder (`shared/references/work-state.md`), and never claim a check ran that didn't. When the change crosses a callback, middleware, event, storage, external call, or second entry point, also prove the real path end to end. A mock alone cannot show that **observable behavior**.

Before review, rerun the required checks yourself on the final source, so the reviewer sees current evidence.

After the task is green, have the implementer run a **behavior-preserving** cleanup with `coding-review-simplify`. In feature mode, save broad cleanup for the combined pass.

## Review and repair

Give the reviewer the contract, the changed paths and diff, the captured evidence, the named risk, the conclusions of the methods used, and any earlier findings. The reviewer checks:
- observable behavior;
- scope;
- the evidence;
- the named risk;
- whether each cleanup preserved behavior, and whether a removed safeguard was required.

The reviewer returns `ready` or `changes required`. Each finding has a severity, a location, and its evidence.

Severity follows consequence. A P1 or P2 blocks acceptance. A confirmed P2 whose fix falls outside the scope stays blocking and goes to the user; never relabel it P3 to fit. For a seam, a public contract, or high residual risk, recommend `full-review`, and use it when the user selects it.

Send confirmed findings to the same implementer and capture fresh evidence. Then ask the same reviewer to recheck, giving it the finding IDs and what changed. Stop after three review cycles, counted in the report; the plan may set another limit. When the limit runs out, return `ceiling_hit` with the open findings.

## Feature policy

In task mode, run the task as above. In the feature mode that `implement-tasks` approves, the plan classifies each task:

- **Deferred:** implement it and capture its focused checks without a task reviewer. Return `implemented`, which is provisional.
- **Critical:** review it as above. The result stays provisional.
- **Final feature review,** once the combined work is ready:
  1. Run one combined cleanup pass through the original implementers.
  2. Run every required check on the final source.
  3. Have one reviewer, independent of every author, review the whole change with `full-review`, followed by the same repair loop.

  Only this gate accepts the feature and its tasks.

## Isolation

One track in the current working tree is the default: the **smallest reversible move**. Run tracks in parallel worktrees only when all of these hold:
- their files are disjoint;
- they share no type, API, migration, lockfile, generated artifact, or environment singleton;
- each track has its own implementer and reviewer.

If any of these is in doubt, work sequentially. Creating a worktree is within an implementation request. Committing or merging needs explicit authority. Remove worktrees only when asked. After integration, rerun the affected checks on the combined state.

## Report

Write the task's `report.md` in the layout of `shared/references/work-state.md` and **lead with the outcome**. The status is `accepted`, `implemented`, `blocked` (with its reason), or `ceiling_hit`. Then give:
- the acceptance evidence, as commands with their results;
- the roles, with model, effort, and route, and the model each call reported;
- the review verdict and the findings applied or declined;
- the changed paths;
- the residual risks;
- the one next action.
