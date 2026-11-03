# Task shaped model routing

How to match work to a route in [`model-routing.json`](../model-routing.json). [model-roster.md](model-roster.md) explains its fields, [model-preview.md](model-preview.md) owns approval, and [host-model-execution.md](host-model-execution.md) runs the approved route. This reference holds no model defaults.

## Pick the route

1. Match the work's purpose to a `routes` entry: bounded exploration to collect evidence, isolated implementation for a small explicit function, routine implementation for a feature with stable interfaces and meaningful checks. Deterministic work needs no route.
2. Apply `policy.high_risk_triggers` to each task before editing, and record the affected behavior, invariants, and acceptance checks in `risk_reason`. Resolve a triggered task with `--risk high`. A task that shares a sensitive invariant stays high risk until its boundary is settled. A strong lead settles requirements, interfaces, invariants, and critical acceptance cases before routine parts are delegated; a routine author implements settled cases and does not decide product policy.
3. First-pass diagnosis is bounded. An unresolved causal chain can justify proposing `deep-analysis` or `difficult-implementation`.
4. During execution, apply `policy.escalation_triggers`. Allow one attempt and one evidence-based repair before raising effort, and check the seat's `effort_scaling` first: `flat` and `flat-above-high` seats gain little above their routed level, `non-monotonic` seats can regress, and only `monotonic` seats justify escalation, with a recorded gap. More thinking does not replace missing evidence, services, credentials, or an unclear contract.

## Future task plans

`model_routing.py resolve-batch --tasks <task-risk.json> --profile default` resolves a future queue in one pass. Each row has exactly `task_id` (`T1`, `T2`, ...), `route`, `risk`, and `risk_reason`; the helper requires a risk decision for every task and accepts no role overrides. An explicit role change goes through a single-route preview instead.

```json
{"tasks": [
  {"task_id": "T1", "route": "routine-implementation", "risk": "normal", "risk_reason": "Formats settled fields; existing checks cover the result."},
  {"task_id": "T2", "route": "routine-implementation", "risk": "high", "risk_reason": "Changes endpoint authorization; review must cover denied access."}
]}
```

The batch also resolves the central `coordinator` route for the future session. Pass `--coordinator-model` and `--coordinator-effort` only when the host exposes them. A `mismatch` or `unknown` result sets `future_start_ready: false`: the user selects the coordinator in the host before the future session starts, while this session can finish the plan. Bind the task-risk input and the resolved preview as immutable `scope.inputs` of the new plan, keeping the coordinator out of the worker route rows.

### Feature review preview

`--review-mode feature` keeps early reviewers only for high-risk tasks, central risk targets, and separately selected reviewer roles; routine rows keep only their implementer. The result adds `review_mode`, `execution_authorized: false`, and `final_review`, which uses the central `broad-review` route (with its risk route when a critical task exists). A final reviewer whose model matches any author returns `status: blocked` with the conflicts; resolve it with an explicit replacement preview. Bind the policy through [feature-review.md](feature-review.md) before execution. A preview never removes reviews from an approved plan.

## Review

In task mode every implementation route names a reviewer on a different model. Give the reviewer all `policy.review_inputs`: the original requirement, the actual diff, relevant source, and the captured checks. It derives expected behavior independently; an implementer's summary is not review evidence. A `broad-review` role does code review, a `design-review` role does not substitute for it, and `independent-review` applies when the usual reviewer wrote the code. Integration review covers the combined revision; in feature mode the final review covers the whole feature, including deferred tasks. Review opinions never replace deterministic checks.

## Interview and council roles

Resolve `interview-product` or `interview-technical` with the selected family; the mixed family keeps interviewer and respondent on different models. Councils live under `councils`; resolve one with `model_routing.py council <name>` only to prepare the approval preview for `models-consensus`.

## Approved routes

Validate a saved implementation plan against `implementation-routing-plan.schema.json`. Each route records task, track, role, seat, model, mode, transport, effort and its control, provider routing, tool policy, receipt policy, fallback, limits, `unavailable` action, and source artifact. Context IDs and iteration results go in run state, never into approved rows.

`unavailable` is `block` unless the user approved one exact alternate. An unexpected runner or configured model blocks the route; for native routes, so does a different host or transport. `model_verification: required` blocks without a verified matching receipt; `allow_unverified` proceeds on the recorded approval and the report says so. A verified mismatch always blocks.

The approval binds canonical SHA-256 values of the task and PRD inputs and a digest of the normalized routes. `shared/scripts/routing_plan.py` computes both: inputs sorted by `path`, routes by `id` then `task_id`, sorted-key compact UTF-8 JSON, LF line endings, and only an exact `**Status:** ready-for-agent|in-progress|done|blocked` line ignored. A status change keeps the approval; a scope or acceptance edit does not.
