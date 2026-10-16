# Task Brief Methodology

Runner and native worker routes receive the task brief, not the skill library. Bind each brief to the existing approved route snapshot. Read the triggered methods and put their applicable constraints into the brief. Applying a practice or routine lens happens in that role. It does not select a route or launch a nested worker.

## Always Include

1. The accepted task scope and unchanged-behavior boundary.
2. The canonical acceptance contract path, required verification commands, and check IDs. The launcher inserts the full contract on first dispatch and reconstruction; derived notes add execution details without copying it.
3. The named task risk and any settled design constraint.
4. The evidence route from `evidence-strategy.md`.
5. The bound review mode, task classification, focused checks, dependency contract tests, and provisional result when feature mode applies.
6. The execution boundary: no commit, push, merge, pull request, deployment action, or external message.

Give the implementer the requirements file and shared capture instructions before
dispatch. After its final edit, it prepares a snapshot and captures the last green
required checks through `run-check`. It returns original snapshot, result, and log
paths. The coordinator selects reusable captures before independent review. For a deferred feature task, those captures prove provisional implementation only.

## Select by Trigger

| Trigger | Brief constraint |
| --- | --- |
| A behavior changes | Apply `tdd`: one failing check, minimal implementation, then refactor on green. |
| Untested legacy behavior | Apply `safe-incremental-coding`: make the **characterization test** before changing behavior. |
| Available failure evidence does not establish the cause | Apply `diagnose` before implementation. |
| Module or public boundary is unresolved | Apply `coding-design-plan`, then `design-gate` only if no selected lens exists. |
| Stored state, queue, migration, retry, or external API | Apply `data-systems-coding-lens`: name the source of truth and make writes idempotent. |
| Business rule, aggregate, or context boundary | Apply `domain-driven-design`. |
| Agent loop, durable state, tool retry, or human gate | Apply `agent-architecture-lens`. |
| Component composition, UI state, or UI fetch lifecycle | Apply `advanced-react` or `frontend-design`, when the matching framework is present. |
| New pattern, topology, or architecture boundary | Apply the selected lens conclusion as a fixed constraint. |

Apply `clean-code` when touched code has a concrete smell or needs refactoring. Apply `test-lens` when choosing tests needs judgment about real behavior, seams, mocks, or brittle coverage. Keep at most three selected lenses. Carry inherited findings into the brief, and recheck only a blocking lens after its design surface changes. Routine lenses are read only in the assigned role. A material risk or unresolved question can dispatch a selected independent specialist only through the approved snapshot. Reuse shared design, security, interface, and acceptance decisions from the feature policy. Reopen only a changed or unresolved boundary. The task should remain a **native diff**: change only what the acceptance contract needs.

## Review Brief

For an independent task or final feature review, read [review-brief.md](review-brief.md). Implementation-only roles stop before this section.
