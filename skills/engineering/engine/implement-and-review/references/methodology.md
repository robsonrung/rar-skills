# Task Brief Methodology

Runner and native worker routes receive the task brief, not the skill library. Bind each brief to the existing approved route snapshot. Put only the practices that the task actually triggers into that brief. Applying a practice or routine lens happens in that role. It does not select a route or launch a nested worker.

## Always Include

1. The accepted task scope and unchanged-behavior boundary.
2. The full acceptance contract on first dispatch, plus required verification commands and check IDs.
3. The named task risk and any settled design constraint.
4. The evidence route from `evidence-strategy.md`.
5. The execution boundary: no commit, push, merge, pull request, deployment action, or external message.

Give the implementer the requirements file and shared capture instructions before
dispatch. After its final edit, it prepares a snapshot and captures the last green
required checks through `run-check`. It returns original snapshot, result, and log
paths. The coordinator selects reusable captures before independent review.

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

Apply `clean-code` to touched code. Apply `test-lens` when choosing tests needs judgment about real behavior, seams, mocks, or brittle coverage. Keep at most three selected lenses. Carry inherited findings into the brief, and recheck only a blocking lens after its design surface changes. Routine lenses are read only in the assigned role. A material risk or unresolved question can dispatch a selected independent specialist only through the approved snapshot. The task should remain a **native diff**: change only what the acceptance contract needs.

## Review Brief

Give the approved reviewer:

1. The task and acceptance contract.
2. The changed paths and relevant diff.
3. Test evidence and any no-test exception.
4. The named task risk and triggered lens conclusions.
5. `shared/references/reviewer-response.md`, including its exact JSON fields, packet substitution, incremental responses, and conditional scope approval.

The reviewer is read only and independent from the implementer. It checks **observable behavior**, scope, evidence, and the named risk. It consumes the approved snapshot and does not choose a different model, effort, task scope, or worker.

For confirmed native continuation, send changed facts, finding IDs, evidence
locators, and the unchanged boundaries through the launcher. The launcher validates
the prior contract, route, context, receipt, and input before omitting repeated
contract text. It keeps the full rendering when it is smaller. Fresh or reconstructed roles receive the full contract. A compact
prompt does not reduce required review coverage or the approved call limits.
