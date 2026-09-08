# Review dispatch

Read this before launching a review seat. The approved routing-plan JSON is authoritative. It supplies the exact seat, model, effort, execution path, and unavailable action for every route. Read
[`task-shaped-model-routing.md`](../../../../shared/references/task-shaped-model-routing.md),
[`model-roster.md`](../../../../shared/references/model-roster.md), and
[`host-model-execution.md`](../../../../shared/references/host-model-execution.md)
before resolving the route.

## Select the review shape

| Scope | Broad review route | Precision or analysis route |
| --- | --- | --- |
| `focused` | Astra at `high`; use Sol at `high` when Astra wrote the code. | None unless the plan names a precision pass. |
| `seam` | Astra at `high`, or `max` when the seam is difficult; use Sol at `high` when Astra wrote the code. | Opus at supported `xhigh` for subtle semantics or high-impact claims. |
| `deep` code, systems, security, data, diagnosis, or integration | Astra at `max`; use Sol at `high` for an independent broad pass when Astra wrote the code. | Opus at supported `xhigh`; add a selected security specialist when the scope needs it. |
| `deep` research, architecture, design, or trade-off analysis | Fable at `max` for the analysis, paired with the selected broad code-review route when code is in scope. | Opus at supported `xhigh` when a precision code pass is needed. |

Fable at `max` is a research and design route. It is not the generic reviewer
for code written by Astra. Terra is a routine implementation route and is not a
default review route. Use Astra at `ultra` only when the approved review plan
needs parallel exploration and records why.

Validate that the exact Opus model, selected host or runner, and `xhigh` effort
are supported before showing that route for approval. If they are not, report
the limitation and propose only an approved exact alternate. Do not infer a
route from an alias, a missing runner, or an old receipt.

## Dispatch rules

1. Select only routes present in the approved plan. The plan may include a specialist or an independent second reviewer; it does not imply a panel.
2. Resolve the selected model through native host delegation first. Use an isolated persistent subagent or supported task context when the exact route is native. Use a runner only for a foreign route or a native route that cannot meet the approved plan.
3. Preserve seat fidelity. Runner routes use fallback disabled and compare each receipt with the approved runner and model. Native routes check the approved host and transport.
4. If a required route is unavailable or returns a different receipt, follow its approved unavailable action. Without one, block that route and report the gap.
5. Give independent reviewers the same scope, diff, rules, and evidence contract. Give each a distinct lens only when the plan assigns one. Keep the same role context for later rechecks; do not share it with the writer or another reviewer.
6. Record selected routes, receipts, unavailable routes, and verification in the review report.
