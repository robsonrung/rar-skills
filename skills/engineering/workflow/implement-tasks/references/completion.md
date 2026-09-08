# Complete the Implementation Run

Read when the task results are ready for integration review and delivery.

## Verify the complete change

Capture the feature's acceptance results. Reuse task results only when the relevant code, dependencies, environment, and contract still match and no fresh run is required; run missing or affected checks on the combined state. For several tasks, call `full-review` once on the combined change, focused on integration seams, shared contracts, migration order, and gaps in task reviews. Use the approved integration route and its separate persistent context; it does not replace task-level independent review. Use the approved reviewer plan and `security_focus=true` when a task has deep security exposure.

A single task with a complete scoped review does not need a duplicate full panel. Reuse task evidence when the code and assumptions still match. After a fix, rerun affected checks and review changed paths; broaden only when the change or a failure requires it. Never weaken acceptance checks to obtain a pass.

Record unapplied findings using [residual-findings.md](residual-findings.md). A blocking defect stays blocked; recording it does not complete the feature.

## Deliver and report

Deliver the verified local diff by default. If the user authorized commit, push, or a PR, perform those actions; use `open-pr` for an authorized PR. A configured remote does not grant publication permission. Reuse prior authorization without asking again.

Write `report.md` in the run directory. Include:

1. Result: `complete`, `partial`, `failed`, or `ceiling_hit`; local diff or authorized delivery link.
2. Tasks: stable ID, status, dependency, integration result, and acceptance evidence.
3. Models: approved and configured models, native capability checks, transport, observed serving models when available, receipt limits, effort, and approved substitutions.
4. Role sessions: route IDs, host, native context or runner-session references, resumed or reconstructed turns, and any unavailable continuation capability.
5. Review: scope, reviewed revision, applied findings, residual record, and unverified checks.
6. Decisions: assumptions within scope, blocked decisions, and required next actions.

The queue is complete only when every task is done and final acceptance passes. `partial` is a report outcome; run state uses the shared status enum. Use `capture-learning` for a reusable project finding or `session-handoff` when work must resume, within the original authorization.
