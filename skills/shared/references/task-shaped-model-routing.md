# Task shaped model routing

How to match work to a route in [`model-routing.json`](../model-routing.json). [model-roster.md](model-roster.md) explains its fields, [model-preview.md](model-preview.md) owns approval, and [host-model-execution.md](host-model-execution.md) runs the approved route. This reference holds no model defaults.

## Pick the route

1. Match the work to a `routes` entry by its `use_when` line (`model_routing.py routes` prints them). Pick the lightest route that fits: `lookup` when a mistake is cheap to spot, `routine-code` when tests or a diff decide correctness, `standard-code` when the change needs judgment the checks do not cover, `hard-code` when an early mistake compounds, and `analysis` when the cause is unknown or nobody checks the judgment. Deterministic work needs no route.
2. Apply `policy.high_risk_triggers` to each task before editing, and record the affected behavior, invariants, and acceptance checks as the task's risk reason. Resolve a triggered task with `--risk high`. A task that shares a sensitive invariant stays high risk until its boundary is settled. A strong lead settles requirements, interfaces, invariants, and critical acceptance cases before routine parts are delegated; a routine author implements settled cases and does not decide product policy.
3. First-pass diagnosis is bounded. An unresolved causal chain can justify proposing `deep-analysis` or `hard-code`.
4. During execution, apply `policy.escalation_triggers`. Allow one attempt and one evidence-based repair before raising effort, and check the seat's `effort_scaling` first: `flat` and `flat-above-high` seats gain little above their routed level, `non-monotonic` seats can regress, and only `monotonic` seats justify escalation, with a recorded gap. More thinking does not replace missing evidence, services, credentials, or an unclear contract.

## Review

In task mode every implementation route seats its reviewer on another provider than the implementer. In feature mode only `critical` tasks keep one, and the final `review` reviewer differs from every author. Give the reviewer all `policy.review_inputs`: the original requirement, the actual diff, relevant source, and the captured checks. It derives expected behavior independently; an implementer's summary is not review evidence. A review of the design does not substitute for a review of the code. Integration review covers the combined revision; in feature mode the final review covers the whole feature, including deferred tasks. Review opinions never replace deterministic checks.

## Interview and council roles

Resolve `interview`; the interviewer runs on the host's provider and the respondent on the other. Councils live under `councils`; resolve one with `model_routing.py council <name>` only to prepare the approval preview for `models-consensus`.

## Approved routes

The approved plan lives at the top of the feature's `tasks.md` ([work-state.md](work-state.md)): for each task and role, the model, effort, and host route, plus the limits. Context IDs and iteration results go in the task reports, never into the plan.

An unavailable route blocks its tasks unless the user approved one exact alternate. A reported model that differs from the approved one always blocks; [runner-common.md](runner-common.md#approved-routes) owns the rest of the receipt rules.
