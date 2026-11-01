---
name: eco-use
description: Coordinate economical delegation from the current session with a medium-effort classifier, bounded independent workers, durable state, and independent review. Use when the user asks to minimize coordinator work while other models execute.
---

# Eco Use

Stay a **thin conductor** in the invoking session: specify acceptance, dispatch, wait, and report evidence. Delegate implementation, research, and verification. Do not turn a blocked worker into inline execution by the expensive coordinator.

## Bind the existing engine

Use `shared/model-routing.json` as the only model registry. Read `shared/references/model-preview.md` and `shared/references/task-shaped-model-routing.md`. For a bounded task use `implement-and-review`; for an approved queue use `implement-tasks`. Missing material decisions follow the existing interview/PRD/task workflow. This skill adds an execution policy, not a second scheduler or a replacement harness.

Before dispatch, obtain or reuse an approved exact snapshot covering classifier, workers, independent reviewers, integration, transport, source-sharing authority and fallback triggers. An economy profile is a starting point for resolution, not evidence of equivalent quality or lower measured cost. Preserve already approved snapshots; do not silently replace routes.

## Classify once, briefly

Dispatch a separate read-only classifier at **medium** effort with no inherited conversation. Send one batch containing task IDs, short descriptions, acceptance summaries and required capabilities. Request only `id`, `complexity` (`low`, `medium`, `high`) and a one-sentence `reason` per task. Reject missing/duplicate IDs or unknown labels before scheduling.

Use low for mechanical closed transformations, medium for bounded implementation or investigation, and high for substantial dependency or diagnostic uncertainty. Resolve the approved task-shaped routes from the central registry; complexity does not authorize new models or more reasoning. If no eligible medium-effort classifier is configured, report a blocked classifier instead of substituting the conductor.

## Economy policy

Bind these limits explicitly in the engine's approved plan:

- At most two independent tasks in flight; one writer when isolation is unavailable. Retain ownership through review and integration; overlapping writes never run concurrently.
- One review-directed correction per task, followed by one recheck. Preserve counters on resume. Exhaustion blocks the task without automatic model escalation.
- Separate reviewer context and a different model from each author in scope, as required by the engine.
- No automatic metered-API fallback. A fallback must be explicitly approved with its trigger, capabilities and payment policy; subscription access is not unlimited capacity.
- Prefer an eligible configured local-machine route. Bound its availability probe to three seconds, record timeout/unavailability/capability mismatch, then use only a preapproved alternative. Local execution and native host dispatch are different concepts. Without a configured bounded local probe, disclose that local-first is unverified and block local-first-required dispatch; never invent an endpoint or claim it was checked.

Antigravity is an optional adapter, not a bundled dependency. This library does not ship personal credential switching scripts or a verified Antigravity adapter. Use it only after registering a compatible route and validating its output, privacy, locking, timeout and receipt contract. Otherwise select a supported approved route or report the gap.

## Wait, recover, report

Use `implement-tasks/references/queue-controller.md` and `shared/references/workflow-controller.md` for readiness and changed-event waits; `shared/references/host-model-execution.md` governs native dispatch. Keep **the ledger, not the transcript**: canonical run state, pending call reservations, role session IDs, attempts and evidence remain under the engine's `.ai-workflow` session directory. Do not introduce a parallel database.

While workers run, wait through host events or bounded process waits. Wake for completion, blocking evidence or a required decision, not repeated model-generated status checks. Reconcile pending calls and actual effects before resuming; uncertain partial writes block replay. Cancellation uses the engine/runner's owned-job cancellation only, never unrelated user processes. Closing the application does not promise background persistence.

Report task acceptance, review evidence, exact routes/receipts, fallback reasons and pending work. Use the shared usage ledger; missing provider token counts are unavailable, never zero. Claim savings only with comparable observed measurements.

## Maintenance and compatibility

This is the rar-skills adaptation of the eco-use policy, version 1. It reuses this repository's routing, approval, ledger, scheduling and runner contracts. It intentionally does not copy a personal helper, machine paths, local model IDs or authentication. It has no standalone `iniciar/status/retomar/cancelar` CLI: use the engine's lifecycle commands. Keep policy variants versioned; their files are not byte-identical mirrors. Changing shared contracts requires checking this policy and its execution limits.
