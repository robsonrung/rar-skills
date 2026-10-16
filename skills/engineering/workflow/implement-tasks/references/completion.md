# Complete the Implementation Run

Read when the task results are ready for integration review and delivery.

## Verify the complete change

Read `shared/references/review-evidence.md`. For a bound feature policy, also
read `shared/references/feature-review.md` and use its final gate. Routine task
snapshots prove provisional dependency release only. Critical tasks need a current
independent review or valid scoped reuse under that policy. Batch refresh can
prepare their current evidence together; it cannot pass this final gate. Feature
acceptance needs the complete combined contract, checks, interaction evidence, an actual independent
review receipt, and a passing policy assessment.

Without a feature policy, each task must pass the launcher's `verify-review`
before integration. Final readiness needs a current structured
record for the combined source state and intended PR base. If integration makes
a task snapshot stale, use its report as context and assess affected interactions
against a new combined snapshot. Task completion labels alone are insufficient.

In task mode, the following carry forward and batch protocols can preserve valid task review evidence. Feature mode uses its bound policy gate.

A verified carry forward checkpoint can release task dependencies under the
original review's exact approved scope. It preserves that task's historical
review and current acceptance evidence, but cannot pass final combined `verify`.
Include its target changes and original findings in the final current combined
review. Do not require a duplicate task review solely because its checkpoint
already passed dependency release.

A current batch review can endorse several retained task contracts after ordinary
later edits. Reuse that one actual independent response when its exact task set,
canonical contracts, required current captures, prior findings, affected interactions, and
approved dispatch pass the shared batch protocol. It supplies final acceptance
only if its own approved contract and complete combined evidence also pass this
feature gate. Task endorsements cannot replace missing feature checks.

In feature mode, finish the combined simplification pass before the final
snapshot and combined check capture. Include every task contract, shared
interface, security decision, migration order, and required interaction in the
final review. A review of seams alone cannot accept deferred task behavior.

Capture the feature's acceptance results. Reuse task results only when the relevant code, dependencies, environment, and contract still match and no fresh run is required; run missing or affected checks on the combined state. For several tasks, call `full-review` once on the combined change. In task mode, focus on integration seams, shared contracts, migration order, and gaps in task reviews. In feature mode, cover the complete feature contract, all deferred task behavior, and those interactions. Use the approved integration route and its separate persistent context. In task mode, this supplements task review. In feature mode, it is the final acceptance review; earlier independent review covers only critical dependencies and named material risks. Use the approved reviewer plan and `security_focus=true` when a task has deep security exposure.

In task mode, a single task with a complete scoped review does not need a duplicate full panel. Reuse task evidence when the code and assumptions still match. After a fix, rerun affected checks and review changed paths; broaden only when the change or a failure requires it. Never weaken acceptance checks to obtain a pass.

Record unapplied findings using [residual-findings.md](residual-findings.md). A blocking defect stays blocked; recording it does not complete the feature.

Use the shared snapshot, required check plan, and structured response for the
combined review. Record the actual reviewer response and run the shared verifier.
In task mode, a single task can reuse its record when the verifier accepts its current source
and intended base. Feature mode reuses only a final record that passes its complete policy assessment. Link the snapshot, review record, check records, and verifier
output from the report. Only `ready` meets this gate; open P2 findings and skipped
required checks prevent completion.

## Deliver and report

Deliver the verified local diff by default. If the user authorized commit, push, or a PR, perform those actions; use `open-pr` for an authorized PR. A configured remote does not grant publication permission. Reuse prior authorization without asking again.

Write `report.md` in the run directory. Include:

1. Result: `complete`, `partial`, `failed`, or `ceiling_hit`; local diff or authorized delivery link.
2. Tasks: stable ID, status, dependency, integration result, and acceptance evidence.
3. Models: approved and configured models, native capability checks, transport, observed serving models when available, receipt limits, effort, and approved substitutions.
4. Role sessions: route IDs, host, native context or runner-session references, resumed or reconstructed turns, and any unavailable continuation capability.
5. Review: scope, reviewed revision, applied findings, residual record, and unverified checks.
6. Decisions: assumptions within scope, blocked decisions, and required next actions.
7. Cost evidence: measured usage, duration, reported cost, unknown-call counts, and repairs per accepted task. Keep failed attempts in these totals.

The queue is complete only when every task is accepted and final acceptance passes. In feature mode, promote provisional `implemented` tasks to accepted status and update their completion icons only after that gate returns ready. `partial` is a report outcome; run state uses the shared status enum. Use `capture-learning` for a reusable project finding or `session-handoff` when work must resume, within the original authorization.
