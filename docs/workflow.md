# The development workflow

Use the feature path when the request needs discovery or several task slices:

`interview-me` → `to-prd` → `to-tasks` → `implement-tasks`

For one bounded, specified change with clear acceptance and no unresolved
product, security, public contract, data ownership, or dependency decision, use
`implement-and-review` directly. This path retains exact worker approval,
independent review, and captured acceptance evidence. It does not require a
feature PRD or task graph. A missing material decision returns to the relevant
earlier stage.

This guide describes the owning contracts. The
[stage routing](../skills/shared/references/workflow-stage-routing.md) reference
places engineering methods. The
[central configuration](../skills/shared/model-routing.json) owns models,
profiles, effort defaults, and council policy. The
[host execution](../skills/shared/references/host-model-execution.md) reference
owns native dispatch and role context reuse.

## Select the branch before the workers

Applying a method or lens in the current role does not dispatch a worker.
Coordinator work and deterministic tests, builds, hashes, status, evidence
assembly, and waits proceed through direct tools. These branches need no worker
table or model selection question.

Actual dispatch uses one [concrete preview](../skills/shared/references/model-preview.md).
Show the actual coordinator separately and only the required workers. Each row
names the scope, role, exact model and effort, transport, tools, isolation,
source sharing, provider controls, receipt policy, exact fallbacks, and limits.
Nested skills use that approved snapshot without another selection or extra
worker.

Resolve workflow routes with `model_routing.py resolve <route> --profile default`.
The central configuration selects the default. A validated local preference or
explicit override can change the preview. The approved snapshot controls dispatch,
repair, and resume even after preferences or central defaults change. Bare CLI
resolution keeps legacy family behavior, so it does not select the workflow
default.

A request to use defaults and run permits the unchanged concrete setup within
existing source sharing authority and accepted receipt limits. Silence does not
approve a route. An unavailable model, unsupported effort, failed privacy
control, or required missing receipt blocks its route. Only an exact approved
fallback can replace it without another decision.

## 1. `interview-me`

Use relevant repository facts, vocabulary, and existing decisions before asking.
Ask up to five independent questions in one turn. Resolve facts from source;
ask the user for material decisions that source cannot settle.

Record settled decisions, assumptions, exclusions, security choices, and
observable success conditions in
`.ai-workflow/work/<slug>/decision-record.md`. Give settled decisions stable IDs
and keep one source index with path, locator, authority, and content revision.
Capture each supplied answer when it settles a decision, following the
[answer evidence contract](../skills/shared/references/answer-evidence.md).
Keep its actual message locator when available. Otherwise retain the exact text
in an immutable artifact and state the locator limit. Reuse its source identity
through the PRD and tasks. A correction adds a linked record; it cannot replace
prior authority. It becomes `ready-for-prd` when the interview closes.

With `--auto`, resolve the product or technical interview roles from the central
configuration and retain two isolated contexts through the rounds. The
respondent can investigate evidence and propose alternatives. It cannot invent
a user preference or approval. Material decisions stay with the user unless
the user explicitly delegates them.

Use `security-gate` for a security surface and one broad inline lens when it can
change the next question. Use `to-prototype` only for a decision that requires
an experiment. Test mechanics belong in task design or implementation.

## 2. `to-prd`

Receive a `ready-for-prd` decision record and write
`.ai-workflow/work/<slug>/prd.md` as `draft`. Preserve settled behavior, scope,
design and security decisions, rollout limits, and observable outcomes. Link
those outcomes and constraints to decision IDs and the source index. Recheck
missing, changed, or disputed sources. Return a material conflict or missing
decision to the interview.

The user reviews the specification before it becomes `approved`. PRD approval
defines the product contract. It does not approve a task queue or worker routes.

## 3. `to-tasks`

Receive an approved PRD. Write each complete Slice Contract once in
`tasks/T<N>-<slug>.md`, initially as `draft`. Keep stable IDs, acceptance,
verified command definitions, gate findings, security classification, rollback,
review focus, dependencies, and write ownership in that file. Design lenses and
the gate use the canonical result schema in the task contract. Keep blocking
and advisory finding IDs, dispositions, and evidence through rechecks. Reuse
settled shared decisions; classify each slice's design and security risks.

New task contracts use one versioned `gate-result` block. Validate it with the
[gate contract](../skills/shared/references/gate-result.md) before approval.
The queue repeats this consistency check before promotion or dispatch. Keep
closed findings and their resolution evidence. A valid record does not prove
its evidence or grant approval. Started legacy contracts retain their format.

`tasks-draft.md` is a compact index with task links and scheduling metadata.
`queue.json` provides machine-readable dependencies, ownership, concurrency,
and any approved merge plan. It does not duplicate acceptance or execution
state. Read the [task contract](../skills/engineering/workflow/to-tasks/references/task-contract.md)
for the fields and approval binding.

Task-only approval is the default. When execution is requested, the preview can
include the exact model plan. One actual response can then explicitly approve
both decisions. Record separate task and model gates with that response. Bind
the reviewed PRD, index, queue, task identities, and routes when applicable.
Keep the immutable preview and actual response as evidence.

After approval, promote only the exact task status to `ready-for-agent` and
verify the prospective content hashes. Drafts cannot dispatch. A task-only
response cannot satisfy the model gate. A change to acceptance, dependencies,
ownership, or routes needs a revised binding and the applicable decision.

Published task files in legacy queues remain canonical. Keep their approval
history and execution records. Supply and bind missing machine scheduling
metadata before the work that needs it; a legacy queue does not require a
cosmetic rewrite.

## 4. `implement-tasks`

Validate the approved queue and reuse a matching combined approval when present.
Otherwise prepare the exact implementation, independent review, and integration
routes before dispatch. Task approval, `--auto`, a saved preference, or silence
does not approve worker routes.

Bind canonical inputs by content hash. The launcher's normalization excludes
only recognized standalone progress status lines. It preserves acceptance and
gate content. Local preferences inform the preview once and do not change an
approved plan during execution.

Check exact native capability before external runner availability. Use an
isolated native context when it meets the selected model, effort, tools,
receipt, and follow-up requirements. Use an approved runner for a foreign or
unsupported route. Keep implementer, reviewer, and integration contexts
separate. Reuse each context only for its own task and role.

First calls and context reconstruction receive the full accepted contract.
Confirmed native and supported runner continuations can receive the contract
identity, changed facts, findings, and evidence locators. The launcher validates
the prior input, receipt, completed turn, task, role, route, and contract before
omitting repeated text. It uses the full rendering when that is smaller.
Missing proof requires full reconstruction in a fresh role context. Conflicting
proof blocks dispatch. Recovery keeps the approved route and consumed limits.

Runner dispatch records retain provenance, receipts, hashes, and counters outside
the role prompt. Explicit `prompt_context` selects required role context. The
adapter measures the final rendered UTF-8 input and enforces its approved byte
budget before execution. This measurement excludes host instructions, tool schemas,
history, later reads, and images; it is not a token count.

Use the [read-only queue controller](../skills/engineering/workflow/implement-tasks/references/queue-controller.md)
to project `ready`, `blocked`, and `required_integration` work from bound
contracts, task manifests, the call ledger, and verified integration evidence.
Its `approval-inputs` and `schedule` commands write no state, start no worker,
and run no acceptance command. Consult its current `--help` for arguments.

The conductor reserves selected calls and inputs in the existing ledger before
dispatch. The projection itself reserves nothing. Retain ownership through
pending calls and required integration. Independent tasks can run within the
approved concurrency cap. Without isolation, use one sequential writer. Shared
files and migration, interface, or security surfaces serialize tasks unless an
approved merge plan permits overlap.

Worker completion does not release dependents. Verify the combined source state,
acceptance, interactions, and findings first. A complete single-task review does
not require a duplicate panel. A current launcher review can supply matching
combined-state evidence. An extra integration reviewer call needs its separately
approved scope and reserved allowance. Use the engine's
[isolation and integration contract](../skills/engineering/engine/implement-and-review/references/worktree-and-integration.md)
for workspaces and integration authority.

For dependency release, the queue can use an immutable `carry_forward` link to
the original independent review. Its declared dependency inputs must remain
unchanged, and later content must exactly match prospective changes that reviewer
approved. A current target snapshot, environment assessment, and passing evidence
packet bind the new state. Unknown dependencies, changed acceptance, unapproved
content, or failed evidence block reuse. This proof releases dependencies only;
final delivery still requires review of the current combined source.

For ordinary later changes, one current batch review can endorse several
canonical task contracts. Preserve each task's acceptance, prior findings,
review links, and complete current evidence. Bind the batch's own approved
contract, exact task membership, environment assessment, and affected
interactions. Use one separate independent integration route and one reserved
call. Valid check transfers and observation reuse follow the existing evidence
rules; affected and required fresh checks still run.

The queue validates both original task execution and the current batch review.
Pending calls keep ownership. Within one projection, immutable batch evidence is
validated once and reused. Before returning, the queue rechecks source, base,
index, and linked file hashes. No cache carries into the next projection.
A batch releases dependencies only. It also satisfies final review only when its
approved scope and full current evidence meet the complete feature gate.

## Engineering methods and review

| Moment | Applicable method |
| --- | --- |
| Design a slice | Apply `design-gate` once with at most three relevant inline lenses; classify security with `security-gate`. |
| Resolve implementation shape | Apply `coding-design-plan` for an unresolved shape. Reuse inherited constraints unless the surface changed. |
| Build behavior | Use `tdd` when test-first verification adds value; use `test-lens` for a real test-design choice. |
| Change untested legacy behavior | Use `safe-incremental-coding` before a risky edit. |
| Investigate an unexplained failure | Use `diagnose` to prove its cause. |
| Improve a verified change | Use `clean-code` or `coding-review-simplify` for a concrete local need. |
| Review completion | Use the approved independent reviewer; use `full-review` for integration seams or named risks and `browser-smoke` for affected interface flows. |

Routine lenses are read-only procedures in the assigned role. A material risk
or unresolved question can require an independent specialist with its own
approved route and reserved budget. Final code review remains independent.
Resolve blocking gate findings before task approval. Recheck the lens that
raised the finding instead of replaying the full gate. Routine reviews do not
start a council. Framework lenses apply only when that framework is present.

Keep every confirmed finding in the durable review record. A human summary may
limit displayed findings, but must link the full record and identify omitted
IDs. A summary limit cannot remove a P2 from the final gate. Review ancestry
retains finding identity and history; timestamps and list order cannot select
between conflicting conclusions.

## Capture and reuse verification

Discover check IDs and capture commands before implementation. The implementer
captures the last passing required checks against the final unchanged source and
returns the original snapshot and result paths. The coordinator uses those
captures with `select-checks` before running further verification.

The [shared evidence contract](../skills/shared/references/review-evidence.md)
binds source, requirements, dependencies, environment, command definitions,
coverage, and findings in immutable records. `verify-changes` executes the
selected repository commands directly. It inherits the caller or approved
snapshot base, rejects a conflict, and discovers a default only when neither
supplies one. Captured scope includes committed, staged, and unstaged changes. The shared `select-checks` helper returns
`run`, `reuse`, or a candidate `transfer` from declared inputs and changed paths.

Run affected checks and every declared or requested fresh check. Retain matching
passing captures. A transfer needs the explicit runtime, dependency, external
state, and base interaction assessment. Unknown dependencies use whole-source
scope. A changed commit alone does not require every command to run again;
unchanged file hashes alone do not prove semantic independence.

`validate-e2e` binds required units to the shared snapshot, reserves attempts
before execution, and captures command results and browser observations in the
shared evidence shape. Its `evidence-packet` export rechecks source and capture
integrity. All required units must reference one current compatible snapshot.
Repair can replace the snapshot within the same approved contract while keeping
consumed limits.

Before reserving a reviewer cycle, the launcher validates the complete evidence
packet or explicit direct captures. Missing or changed captures block dispatch.
Failed checks and observations remain review evidence and cannot satisfy
readiness. Each reviewer brief includes the absolute response contract path and
the snapshot's required fields, including on continuation.

Give that packet and the focused [reviewer response contract](../skills/shared/references/reviewer-response.md)
to the independent reviewer. It owns source coverage, findings, observations,
and retained conclusions. The coordinator owns evidence preparation, capture,
transfer, and verification. Preserve the actual response and run the shared
verifier before claiming readiness. `pre-pr-review` uses the same
verifier to reuse valid coverage and close only the remaining gaps. A status map,
prose pass, worker success, or council recommendation is insufficient. Required
runtime gates remain separate from business behavior. Missing browser evidence
remains a gap.

## Preflight and recovery

Claude preflight caches stable transport, compatibility, and effort capabilities.
The cache uses a current fingerprint of CLI identity and version, routing and
preflight code, configuration, policy, launch context, model, and effort, with a 24-hour limit. A mismatch,
expiry, or corrupt entry requires a fresh capability check. Each launch still
checks authentication visibility and installation drift. Local login metadata
does not prove live account entitlement. Serving receipts, quota, per-request
privacy, and tool permissions remain current-run facts.

Before each native or runner call, reserve its approved allowance and pending
state. Reconcile an uncertain completion before retrying. Keep raw output,
receipt limits, input identity, and role context references. Defaults are three
task review/fix cycles and one evidence recovery. Validation and other callers
can define their own bounded allowances. Starting a new stage or resuming a
context does not reset consumed call, attempt, or time limits. Exhaustion stops
the affected work while independent authorized work can continue.

## Optional discovery and council

`brainstorm` can clarify a broad idea before the interview. When its territory
gate applies, the user chooses whether to receive a decision map. Then batch up
to five independent decisions. A declined map or silence does not settle a
material choice.

`to-prototype` answers one runnable uncertainty with the smallest useful
experiment. A visual question can start with one fixture or static screen and
use two alternatives when comparison matters. Add a host page only when real
application context changes the observation. Record actual observations and
limits. Prototype code never becomes production code.

`models-consensus` runs only on an explicit user request for extra opinions.
Its council approval remains separate from implementation approval. The current
modes are `poll`, `debate`, and `personas`. A poll defaults to `standard`.
Explicit `lean` is limited to low-risk questions and `per_call` transport;
`cmux` rejects it. Security, money, migrations, public contracts, data loss,
deep review, and high risk require standard.

Lean retains three blind opening seats, organizer, and synthesis. Both judge
routes and conditional gap repairs appear in the approved budget. Judges run
when validated organizer evidence shows material gaps, contradictions,
confidence below the central threshold, or high risk. Otherwise immutable
organizer evidence establishes `conditional-not-needed`. A caller's reason
alone cannot skip a judge. Report answer confidence and verified diversity
confidence separately. The council remains read-only and cannot implement or
approve its recommendation.

## Measure the complete workflow

Choose one feature measurement state before the first stage. Use the
[measurement capture hook](../skills/shared/references/workflow-measurement.md)
at stage, wait, command, repair, and terminal boundaries. Start with known
identity fields and bind remaining fields once when they become fixed. Later
route initialization preserves these early observations.

Keep a separate automatic interview route ledger under its own authority.
After its calls resolve and its owner records terminal status, import its
completed ledger by hash into the feature state. The import retains the source
plan and counters. Comparison counts each receipt hash once. Record full
coverage only when every relevant call and event is captured. Measurement
completion does not grant acceptance or change execution authority.

Compare recorded runs with the read-only `shared/scripts/workflow_comparison.py`
helper and the [run-state measurement contract](../skills/shared/references/run-state-contract.md#compare-workflow-cost).
Use the same source start revision, acceptance cases, requirements, and runtime
identity. Keep workflow elapsed time separate from summed worker duration,
approval waiting, and coordinator usage. Include failures, repairs, repeated
commands, token categories, actual reported cost, and missed defects. Unknown
measurements stay unknown; cached input is not free.

Cost deltas require passed acceptance and equal observed defect counts under
matching identities and the same defect observation protocol. Missing
observations block comparison. Lower cost does not establish equivalent quality. The [measurement report](workflow-measurement.md)
records the source baseline, deterministic checks, and limits. The
[local runtime validation](workflow-runtime-validation.md) exercises capture
across separate interview and implementation stages with synthetic receipts.
Invocation totals take precedence over message subtotals. A missing usage field
in any counted request stays unknown in the total. No full workflow
provider performance benchmark was run for these changes, and route defaults
remain unchanged.

## Delivery boundary and limits

The default result is a verified local diff. Commit, push, pull request, tracker,
external message, publication, and deployment actions each retain their own
authority. Routine execution does not create user-owned chats or sidebar changes.

Installed names and public compatibility remain intact. Static and offline
contract checks establish only the contracts they exercise. They do not prove
model quality, production readiness, measured latency, or cost savings.
