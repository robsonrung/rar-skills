# Review dispatch

The approved routing plan supplies the exact seat, model, effort, execution path,
and unavailable action. Before approval, resolve defaults from
[`model-routing.json`](../../../../shared/model-routing.json) through
[`task-shaped-model-routing.md`](../../../../shared/references/task-shaped-model-routing.md).
Apply [`host-model-execution.md`](../../../../shared/references/host-model-execution.md)
before dispatch. Do not select a new default while resuming an approved review.

## Select the review shape

| Scope | Route reference | Additional work |
| --- | --- | --- |
| `focused` | `broad-review`; `independent-review` if the usual reviewer wrote the code | Relevant deterministic checks |
| `seam` | `broad-review`, or `deep-review` when the boundary is difficult | `precision-review` only for an exposed semantic risk |
| `deep` code or integration | `deep-review` with a model distinct from the writer | Selected security, data, or compatibility checks |
| Research, architecture, or design | `design-review` | Add actual code review when code is in scope |
| Defensive security | `security-review` | Verify specialist access before proposing any conditional model |

Resolve family and effort from the configuration, then verify support in the
selected host or adapter. The review role defines its job: a code reviewer checks
requirements, full diff, relevant surrounding code, missing cases, and captured
checks. Design analysis alone cannot approve code. After the initial review, use
[Incremental review responses](../../../../shared/references/incremental-review.md)
for changed and affected paths. Retain earlier coverage through the verified
record; do not repeat a full review for a prose correction.

## Dispatch rules

1. Select only routes present in the approved plan. A specialist or second pass
   must be named there; a review request does not imply a panel.
2. Prefer supported native delegation. Use a separate persistent reviewer context
   and retain it for later rechecks. Never share it with the implementer.
3. Preserve seat fidelity, exact effort, and the plan's receipt policy. Disable
   runner fallback and compare each result with the approved route.
4. Follow the approved unavailable action on a mismatch or missing capability.
   Without an approved alternate, report the affected route as blocked.
5. Supply `policy.review_inputs` from the central configuration. Inspect additional
   source when needed and assess expected behavior independently of the author's
   explanation. Verify actionable findings before recommending changes.
6. Record routes, receipts, captured checks, and coverage limits. Review/fix cycles
   retain the caller's bounds and cannot silently expand scope or model effort.
