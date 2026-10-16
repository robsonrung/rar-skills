# Task shaped model routing

Use [`model-routing.json`](../model-routing.json) when selecting a worker's model
and effort. [model-roster.md](model-roster.md) explains its fields;
[host-model-execution.md](host-model-execution.md) controls native execution,
transport checks, and separate role contexts. This reference defines selection
and review procedure, not another table of model defaults.

## Select before approval

Use [model-preview.md](model-preview.md) to choose the branch first. Coordinator
work, applied methods and lenses, and deterministic commands need no model route.
For actual dispatch, consume an existing approved snapshot or resolve only the
roles needed for one concrete selection. The caller can combine this selection
with task approval; it does not need a second model question.

1. Match the work to a `routes` entry by its purpose and conditions. Use bounded
   exploration for evidence collection, isolated implementation for a small
   explicit function, and routine implementation for a feature with stable
   interfaces and meaningful checks. Use tools directly for deterministic work.
2. Select the `saver` profile unless user instructions or local preview
   preferences select another central profile. Resolve with
   `scripts/model_routing.py resolve <route> --profile default` from the shared
   skill, adding `--local-profile <name>` for a validated local preference.
   Explicit profiles and legacy family routes remain selectable. The
   output names the exact model and effort for each role and records a configuration digest. It starts no workers.
   `saver` preserves strong review roles; `economy` remains an explicit opt-in.
   Read exact seats and alternates from the configuration. First-pass diagnosis
   is bounded: an unresolved causal chain can justify a proposed `deep-analysis`
   or `difficult-implementation` route within the caller's change procedure.
3. Apply `policy.high_risk_triggers` to each task before editing. Record its risk
   level and evidence in `risk_reason`: affected behavior, invariants, and relevant
   acceptance checks. Resolve with `--risk high` when that task meets a trigger.
   One sensitive task does not promote every task in the feature. A task that
   shares the sensitive invariant remains high risk until its boundary is settled.
   A strong lead must settle requirements, interfaces, invariants, and critical
   acceptance cases before routine parts are delegated. Keep sensitive planning,
   implementation, and independent review on their selected strong routes.
4. Validate native or adapter support. Copy the exact selections and source
   digest into the proposed run plan. An alternate, a specialist, or a second
   review is a separate planned role, not an implicit extra call.
5. During execution, apply `policy.escalation_triggers`. Continue independent
   authorized work while the affected route follows the caller's change rules.
   Allow one initial attempt and one evidence based repair before considering
   a reasoning escalation. Use only a selected exact fallback within the original
   total budget. More thinking does not replace missing evidence, services,
   credentials, driver access, or an unclear contract.

Use the selected route's conditions and the configuration's policy fields.
Exceptional analysis routes require a recorded gap at the normal setting.
Effort labels do not imply parallel workers or equivalent reasoning across models.
Check a seat's `effort_scaling` field before raising effort: `flat` and
`flat-above-high` seats gain little above their routed level, and
`non-monotonic` seats can regress; only `monotonic` seats justify routine
escalation, and only with a recorded gap.

## Future task plans

Use `model_routing.py resolve-batch --tasks <task-risk.json> --profile default`
to resolve a future queue in one deterministic pass. Add a validated
`--local-profile` or an explicit profile as needed. Each input row has exactly
`task_id`, `route`, `risk`, and `risk_reason`. Task IDs use the queue's canonical
`T1`, `T2`, ... format. The helper sorts task numbers numerically,
requires an explicit risk decision for every task, and accepts no role overrides.
It applies each task's risk route independently and retains deterministic command
work without a model worker. An explicit role change uses the existing single
route preview and the caller's selection rules; it cannot be hidden in a batch.

```json
{"tasks": [
  {"task_id": "T1", "route": "routine-implementation", "risk": "normal", "risk_reason": "Formats settled fields; existing checks cover the result."},
  {"task_id": "T2", "route": "routine-implementation", "risk": "high", "risk_reason": "Changes endpoint authorization; review must cover denied access."}
]}
```

The batch also resolves the central `coordinator` route for future startup.
Pass `--coordinator-model <observed-model>` and `--coordinator-effort
<observed-effort>` only when the host exposes those facts. Its coordinator result
reports `match`, `mismatch`, or `unknown`. A mismatch or unknown value sets
`future_start_ready: false` and requires host selection before the future
coordinator starts. Plan preparation can continue in the current session.
A matching identity does not replace capability, authority, or usage checks.
The helper starts no model and never changes the current session.

Bind the task risk input and resolved preview as immutable `scope.inputs` for a
new plan. Keep the coordinator in this preview input, separate from executable
worker route rows. Existing approved snapshots, plan schema, and route digest
rules remain unchanged. On resume, consume the saved exact routes.

### Feature review preview

Add `--review-mode feature` for an explicit future feature preview. The default
`--review-mode task` returns the existing task routes unchanged. Feature mode
keeps early reviewers for high risk tasks, routes that are central risk targets,
and separately selected reviewer roles. Routine implementation rows keep only
their implementation role. Risk classification must follow behavior, invariants,
and acceptance evidence; disjoint paths alone do not prove low risk.

The result adds `review_mode`, `execution_authorized: false`, and `final_review`.
The final selection uses the central `broad-review` route, with its central risk
route when a critical task exists. It is separate from task rows. A final
reviewer that matches any implementer or worker model produces `status: blocked`
and exact task, role, and model conflicts. The helper does not select a fallback.
Use an explicit replacement preview to resolve the conflict under the caller's
existing authority. No model default lives in this procedure.

This output prepares a plan only. Bind a feature policy through
[feature-review.md](feature-review.md) before execution. Existing approved
snapshots retain all their saved roles. A preview never removes reviews from a
running or previously approved plan.

## Review and verification

Task mode implementation routes name a worker and a different review model. Feature mode keeps critical task reviews and a separate final reviewer independent from every author. Keep separate
contexts and reuse each only for that role's repairs or rechecks. Give the reviewer
all `policy.review_inputs`, including the original requirement, actual diff,
relevant source, and captured checks. Permit further source inspection. Derive
expected behavior independently and check omissions, failure cases, and interfaces.
A summary from the implementer is not sufficient review evidence.

A `broad-review` role performs actual code review regardless of the selected
family. A `design-review` role assesses design and cannot substitute for code
review. Use `independent-review` when the usual reviewer wrote the code. Use a
separate integration review for the combined revision and task boundaries. In feature mode, this final review covers the complete feature behavior, including deferred task scopes.

Run the compiler, tests, lint, types, or security checks applicable to the change.
Capture a failing regression before a bug fix where applicable. Do not weaken
checks to make a patch pass. Review opinions do not replace deterministic evidence.

## Efficiency and comparison

Apply `policy.efficiency` and `policy.evaluation`. Keep worker briefs narrow,
return evidence paths, and reuse role context. Compare total work per accepted
result, including exploration, review, repairs, tokens, elapsed time, and cost.
A cheaper model can use more tokens; parallel workers can increase total usage.
Pilot candidate routes on representative tasks by class and retain them only
where observed acceptance and independent review hold. Do not claim equivalence
from the configuration or a small trial.

## Interview and council roles

Resolve `interview-product` or `interview-technical` with the selected family.
The mixed family keeps distinct interviewer and respondent models. A restricted
host can use an explicitly selected family route. The auto interview's own
mandate, role separation, and round limits still apply.

Council assignments are in `councils` in the same configuration. Resolve them
with `model_routing.py council <name>` only to prepare the approval preview.
`models-consensus` remains user invoked and deliberation only.

## Approval and exact routes

Only actual worker dispatch requires a concrete model selection under
[model-preview.md](model-preview.md). A request to use defaults and run, an exact
model request, or approval for the unchanged concrete setup permits those routes
within source sharing authority and receipt limits. Otherwise obtain the caller's
model plan decision; silence cannot provide it. Nested skills and runners consume
the approved snapshot without route resolution or extra workers. Save the
implementation plan and validate it against `implementation-routing-plan.schema.json`.
Consensus keeps its own explicit invocation and approval.

Each route records task, track, role, seat, model, execution mode, transport,
effort and control, provider routing, capabilities and tool policy, receipt
policy, exact fallback triggers, limits, unavailable action, and source artifact.
Resolve native capabilities before probing external CLIs. Keep context IDs and
iteration results in mutable run state rather than changing approved rows.

Use `--disable-fallback` for every approved runner route. `unavailable` is `block`
unless the user approved one exact alternate. An unexpected runner or configured model blocks the route.
For native routes, check the approved host and native transport as well.
`model_verification: required` blocks without a verified matching receipt.
`allow_unverified` permits execution only under the workflow's recorded approval,
with that limit in the report. A verified observed-model mismatch always blocks.
Do not silently change a model, effort, mode, role, receipt policy, or transport.

The approval record binds canonical content SHA-256 values for task and PRD
inputs and a digest of normalized routes. Reject duplicate paths and route IDs.
Sort inputs by `path` and routes by `id`, then `task_id`. Serialize with sorted
object keys, UTF-8, `ensure_ascii=false`, and compact JSON separators before
hashing. Normalize text line endings to LF and omit only a line exactly equal to
`**Status:** ready-for-agent`, `**Status:** in-progress`, `**Status:** done`, or
`**Status:** blocked`. A status transition can reuse approval; scope or acceptance
edits cannot. The launcher recomputes both digests before side effects.

Reuse approval while scope and routes match. When a route fails, continue
independent authorized work and report the affected row. A new model, unsupported
effort, or changed transport needs the calling workflow's change decision.

## Cost and acceptance

Use scripts for status waits, hashes, evidence assembly, and receipt normalization. These jobs
need no model route. Keep the coordinator brief limited to changed facts and unresolved decisions.
Reserve each model call against the existing ledger before dispatch, including repairs,
fallbacks, specialists, and review rechecks. Recovery preserves counters and total ceilings.
Do not reduce an explicitly selected model or effort. Select a cheaper future route only through
the selected plan. A performance claim needs a bounded comparison against the same
acceptance cases. Measure input,
cached input, output, failed attempts, execution time, approval wait time, and accepted outcomes.
Preserve independent security and transaction review. Missing usage remains unknown; fewer words
or lower nominal pricing alone do not prove lower cost per accepted result.
