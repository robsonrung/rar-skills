---
name: implement-and-review
description: Implement and review one approved coding task through exact model routes and persistent role contexts. Use for a scoped task with an acceptance contract; use implement-tasks to coordinate a queue.
---

# Implement And Review

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Build one task to its **acceptance contract** with the exact approved implementation and review routes. The next consumer is `implement-tasks` or the user. A worker result is evidence for integration. It must not mark a task queue complete. The parent marks a task complete only after integration checks pass with no unresolved acceptance or blocking defect.

The routing plan is a binding record, not a suggestion. It selects the implementation and independent review model, effort, native or runner execution, and any approved fallback. Read `shared/references/implementation-routing-plan.schema.json`, `shared/references/task-shaped-model-routing.md`, and `shared/references/host-model-execution.md` before dispatching work. Use the task defaults in the central configuration; do not infer model quality from the current host or an old implementation/review pair.

## Authority

The user request to implement authorizes edits inside the accepted task, its stated verification, and reversible worktree isolation. It does not authorize a commit, push, merge, pull request, deployment, external message, or destructive cleanup. A routing-plan approval authorizes only the recorded routes. Commit-based integration needs separate explicit authority.

## Before Writing Code

1. Read the task, acceptance contract, and active project conventions. Inspect the relevant code and tests.
2. Confirm the task input files still match the routing plan hashes. The launcher enforces this before it writes files, creates worktrees, or starts a worker.
3. If the task came from `implement-tasks`, use its approved plan. For a standalone task, prepare the same model summary, show it to the user, and wait for approval or changes before starting a worker. Reuse existing approval for the exact scope and routes. Include the host capability check, independent reviewer, session strategy, effort, receipt limits, and allowed fallbacks.
4. Start with one track. Add a second track only when their scopes and contracts are independent. Worktree isolation is reversible and needs no separate approval. Commit-based integration remains separately authorized.

Never call `models-consensus` from this skill. A user who wants more opinions invokes that workflow separately.

## Apply Engineering Practices at Their Trigger

1. Use `coding-design-plan` when the implementation shape or boundary is still unresolved. Use the task's settled decisions as inputs.
2. Use `design-gate` only for a nonlocal boundary that has no selected lens conclusions already.
3. Use `diagnose` before implementation when the available failure evidence does not establish the cause.
4. Use `tdd` for a behavior change. For untested legacy behavior, use `safe-incremental-coding` to make a **characterization test** before changing it.
5. Use `clean-code` when touched code has a concrete smell or needs refactoring. Use `test-lens` when a test choice needs judgment about real behavior, seams, mocks, or brittle coverage. Apply a domain lens only when the task triggers it: data paths, interfaces, distributed systems, domain logic, agent control flow, or a framework-specific UI concern.
6. Use `coding-review-simplify` after the task is green when a behavior-preserving simplification would help the next reader.

The implementation brief must state the task scope, acceptance contract, relevant lens conclusions, and that no git or external action is allowed. The launcher prepends the approved task contract to derived implementation and review notes. Derived notes cannot replace it.

## Launch the Approved Routes

Use the launcher from this skill's directory. It requires an approved plan, validates canonical task content hashes and route digests, and records the approved reviewer in the manifest. A dry run can preview a complete draft plan but never writes, creates a worktree, or starts a worker.

Prefer native delegation when the host exposes the exact model, effort, isolation,
and tools. Use an external runner for a foreign model, an unsupported native
capability, or an explicit transport request. Start a separate context per task,
track, and role; keep it for that role's later turns. A reviewer uses a different
model and a separate context from the implementer.

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/launch.py" launch \
  --session-id <session-id> \
  --task-id <task-id> \
  --routing-plan <routing-plan.json> \
  --track <track-name> <implementation-brief.md>
```

The default is one sequential working-tree track. For independent tracks, add `--isolation worktree` and one `--track` pair for each track. `task-id` is the stable per-task namespace formerly carried by a slice identifier. Commit-based integration remains a separate authorized action.

A native launch returns an exact `native_dispatch` handoff. The host starts or
resumes that role, then records its actual receipt with `record-native`. A handoff
is not execution. Read [references/runner-invocations.md](references/runner-invocations.md)
for native capabilities, receipt fields, `resume-native`, and runner continuation.

When implementation finishes, read `shared/references/review-evidence.md`. Prepare the source snapshot and required check plan, then capture the selected checks. Prepare a focused review brief with the acceptance contract, snapshot, check result paths, and the task's named risk. Launch the exact reviewer recorded in the plan:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/launch.py" review \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --review-brief <review-brief.md> \
  --review-snapshot <snapshot.json>
```

The review command reloads the approved plan, verifies the saved route still matches it, and uses a read-only reviewer. It does not accept a route from the mutable manifest alone. Rechecks reuse the recorded reviewer context. Keep native contexts in `native_contexts[route_id]` and runner sessions in `runner_contexts[route_id]`; do not use a global latest-session selector.

## Review and Finish

After recording the execution receipt, run `record-review` with the same manifest,
track, and cycle. It stores the structured reviewer response and rejects missing
coverage or evidence. For later turns, use the incremental recheck or prose addendum
in `shared/references/incremental-review.md`; the expanded record still needs complete coverage. Before completion, run `verify-review --manifest
<launch-manifest.json> --track <track-name> --base <current-review-base>`.
Only `ready` meets the review acceptance contract. A successful `poll` reports
execution status only. Link the snapshot, review record, and verifier result
from `report.md`. Legacy reviews without these records cannot establish readiness.

1. Apply valid findings through the same approved implementer route and its recorded context. Persist each review/fix cycle before dispatch. The maximum is three cycles. If evidence is missing, reserve one evidence recovery before dispatching it. A second missing-evidence result or an exhausted cycle ceiling stops the task. Retain the implementer and reviewer until their fixes, rechecks, and evidence work are complete.
2. Use `full-review` only when the user selected it in the reviewer plan. Recommend it when the change crosses a seam, carries high risk, or needs feature-level reconciliation. Its scope and routes must remain proportional to the task.
3. Capture the required task acceptance results. Reuse earlier passing results only when the relevant code, dependencies, environment, and acceptance contract still match and the caller permits reuse. Run missing or affected checks after changes. **Only captured command results count as evidence.**
4. Write a short report under `.ai-workflow/impl-review/<session-id>/<task-id>/report.md` when that directory is available. Include acceptance, implementation and reviewer receipts, role context references, any context loss or reconstruction, changed paths, and unresolved risks. Reconcile a pending call before retrying; context loss never resets counters or changes the approved model.

## Output Contract

Return:

1. `status`: `complete`, `failed`, `ceiling_hit`, or `awaiting_human`.
2. `acceptance`: each required behavior and captured check result.
3. `routes_used`: approved route ids, effective receipts, and an explicitly approved fallback if used.
4. `review`: findings applied, findings declined with evidence, and remaining risks.
5. `changed_paths`: files changed within the task scope.
6. `next_action`: only a necessary user decision, parent integration, or separate authorized delivery action.
