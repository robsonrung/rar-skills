# Task shaped model routing

Read [`model-routing.json`](../model-routing.json) for every maintained model
and effort selection. [model-roster.md](model-roster.md) explains its fields;
[host-model-execution.md](host-model-execution.md) controls native execution,
transport checks, and separate role contexts. This reference defines selection
and review procedure, not another table of model defaults.

## Select before approval

Use [model-preview.md](model-preview.md) for the single direct invocation preview,
user overrides, and inherited selections. This procedure resolves only the roles
that preview needs.

1. Match the work to a `routes` entry by its purpose and conditions. Use bounded
   exploration for evidence collection, isolated implementation for a small
   explicit function, and routine implementation for a feature with stable
   interfaces and meaningful checks. Use tools directly for deterministic work.
2. Select the `economy` profile unless user instructions or local preview
   preferences select another central profile. Resolve with
   `scripts/model_routing.py resolve <route> --profile default` from the shared
   skill, adding `--local-profile <name>` for a validated local preference.
   Explicit profiles and legacy family routes remain selectable. The
   output names the exact model and effort for each role and records a configuration digest. It starts no workers.
3. Apply `policy.high_risk_triggers` before editing. Resolve with `--risk high`
   when a trigger applies. A strong lead must settle requirements, interfaces,
   invariants, and critical acceptance cases before routine parts are delegated.
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

## Review and verification

Implementation routes name a worker and a different review model. Keep separate
contexts and reuse each only for that role's repairs or rechecks. Give the reviewer
all `policy.review_inputs`, including the original requirement, actual diff,
relevant source, and captured checks. Permit further source inspection. Derive
expected behavior independently and check omissions, failure cases, and interfaces.
A summary from the implementer is not sufficient review evidence.

A `broad-review` role performs actual code review regardless of the selected
family. A `design-review` role assesses design and cannot substitute for code
review. Use `independent-review` when the usual reviewer wrote the code. Use a
separate integration review for the combined revision and task boundaries.

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

Every direct invocation follows [model-preview.md](model-preview.md). A request
to use defaults and run, or existing approval for the unchanged concrete setup,
permits the selected routes within authorized source sharing and receipt limits.
Otherwise obtain the caller's model plan decision; silence cannot provide it.
Nested skills reuse the selected snapshot. Save an implementation plan and
validate it against `implementation-routing-plan.schema.json`. Consensus keeps
its own explicit invocation and approval.

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
Do not reduce an explicitly selected model or effort. Select a cheaper future route only through
the selected plan. A performance claim needs a bounded comparison against the same
acceptance cases. Measure input,
cached input, output, failed attempts, execution time, approval wait time, and accepted outcomes.
Preserve independent security and transaction review. Missing usage remains unknown; fewer words
or lower nominal pricing alone do not prove lower cost per accepted result.
