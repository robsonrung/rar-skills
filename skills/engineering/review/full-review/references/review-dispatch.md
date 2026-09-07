# Review dispatch

Read this before launching a review seat. The approved routing-plan JSON is authoritative. It supplies the exact seat, runner, model, effort, mode, and unavailable action for every route.

## Select the review shape

| Scope | Primary review route | Independent route |
| --- | --- | --- |
| `focused` | The approved reviewer for the task track | None unless the plan names one. |
| `seam` | Astra at high effort for final reconciliation, with a brief that covers logic and state plus root-cause precision | Fable at high effort only when the plan requests an independent second review. |
| `deep` for systems, security, data, diagnosis, or integration | Astra at high effort | Fable at high effort. |
| `deep` for repository-scale work, interface fidelity, performance, or long-running code | Fable at high effort | Astra at high effort. |

For a bounded task, the reviewer is the opposite frontier route from the approved implementer: Astra implementation is reviewed by Fable, and Fable implementation is reviewed by Astra. Use medium effort unless the approved risk needs high effort.

`codex` remains a compatibility alias for an older caller. New plans use `astra`. Do not infer a route from an alias, a missing runner, or an old receipt.

## Dispatch rules

1. Select only routes present in the approved plan. The plan may include a specialist or an independent second reviewer; it does not imply a panel.
2. Preserve seat fidelity. Launch with fallback disabled and compare each receipt with the approved runner and model.
3. If a required route is unavailable or returns a different receipt, follow its approved unavailable action. Without one, block that route and report the gap.
4. Give independent reviewers the same scope, diff, rules, and evidence contract. Give each a distinct lens only when the plan assigns one.
5. Record selected routes, receipts, unavailable routes, and verification in the review report.
