# Task Brief Methodology

Runner and native worker routes receive the task brief, not the skill library. Put only the practices that the task actually triggers into that brief.

## Always Include

1. The accepted task scope and unchanged-behavior boundary.
2. The acceptance contract and commands to run.
3. The named task risk and any settled design constraint.
4. The evidence route from `evidence-strategy.md`.
5. The execution boundary: no commit, push, merge, pull request, deployment action, or external message.

## Select by Trigger

| Trigger | Brief constraint or orchestration skill |
| --- | --- |
| A behavior changes | `tdd`: one failing check, minimal implementation, then refactor on green. |
| Untested legacy behavior | `safe-incremental-coding`: make the **characterization test** before changing behavior. |
| Available failure evidence does not establish the cause | `diagnose` before implementation. |
| Module or public boundary is unresolved | `coding-design-plan`, then `design-gate` only if no selected lens exists. |
| Stored state, queue, migration, retry, or external API | `data-systems-coding-lens`: name the source of truth and make writes idempotent. |
| Business rule, aggregate, or context boundary | `domain-driven-design`. |
| Agent loop, durable state, tool retry, or human gate | `agent-architecture-lens`. |
| Component composition, UI state, or UI fetch lifecycle | `advanced-react` or `frontend-design`, when the matching framework is present. |
| New pattern, topology, or architecture boundary | Use the selected lens conclusion as a fixed constraint. |

Apply `clean-code` to touched code. Use `test-lens` when choosing tests needs judgment about real behavior, seams, mocks, or brittle coverage. The task should remain a **native diff**: change only what the acceptance contract needs.

## Review Brief

Give the approved reviewer:

1. The task and acceptance contract.
2. The changed paths and relevant diff.
3. Test evidence and any no-test exception.
4. The named task risk and triggered lens conclusions.
5. This output shape: `approve` or `needs-attention`; severity-ordered findings with file, line, mechanism, and recommended correction; then remaining risk.

The reviewer is read-only. It checks **observable behavior**, scope, evidence, and the named risk. It does not choose a different model, effort, or task scope.
