# Prepare and Approve the Model Plan

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Use `shared/references/model-preview.md` once when an execution plan is needed. Coordinator-only validation and task drafting can proceed with direct tools under the current request. Nested workers use the immutable approved snapshot; they do not repeat selection or start unlisted workers. This workflow never invokes a council automatically.

## Prepare the execution plan

1. Read the canonical queue under `.ai-workflow/work/<feature-slug>/tasks/`, its compact `tasks-draft.md`, `queue.json`, and PRD. For normal execution, verify that the PRD and queue approvals still match. For an explicit combined decision, read the canonical drafts and prepare the execution plan without launching them. For a bare feature plan, obtain an approved PRD through `to-prd`, then use `to-tasks`. For one bounded, specified change with complete acceptance and settled product, security, public contract, data ownership, and dependency decisions, use standalone `implement-and-review` with the same model approval.
2. Use [queue-controller.md](queue-controller.md) to validate stable task IDs, blockers, cycles, ownership, and input hashes. Check acceptance commands and HITL decisions from the canonical contracts. Resolve facts from the project before asking for a decision. Unresolved requirements, missing access, or missing approved ownership block affected tasks.
3. Read `shared/references/workflow-stage-routing.md`. Reuse earlier decisions and lens findings. Use `coding-design-plan` only when the implementation shape is unresolved; a complete Slice Contract already supplies the constraints. Call `design-gate` again only when new evidence changes the design surface; do not repeat an earlier architecture study.
4. Classify each task through `shared/references/task-shaped-model-routing.md`, then resolve roles through `shared/references/model-roster.md`. This distinguishes routine explicit functions, normal changes, TDD or difficult implementation, migration or branch exploration, ambiguous design or research, broad review, precision review, and defensive security without copying model choices here. If `.rar-skills/config.local.yaml` exists, read its advisory `profile` and `seats` only while forming this preview, as `shared/references/local-config.md` defines. Validate every value against the roster and candidate transport, let direct user instructions win, and never reread it after approval. Select the central `saver` profile unless the user or local preference selects another. Preserve strong planning and risk roles; assign routine implementation and settled test cases through the selected profile. Keep independent review. Apply supported model specific effort without clamping it. Separate task fit policy from measured results.
5. Read `shared/references/host-model-execution.md` and preflight each chosen route without starting a model job. Check native capability before probing an external runner: exact model selection, supported effort, role isolation, tool policy, model and driver image capability when needed, provider request controls, serving-model receipt, and follow-up or resume support. Prefer a native subagent or authorized task thread when it can meet the exact selected route. Probe and use an external runner only for a foreign model, an explicit user-requested transport, or a native route that lacks a required capability; name that reason in the preview. For an iterative runner role, check its documented persistent-session path. For a specialized defensive-security route, verify exact identity, entitlement, effort control, and tool limits. An ordinary general model cannot be presented as that specialized route; when it is unavailable, propose only the exact fallback defined in the shared route and approved in the plan.
6. Inspect git state and preserve unrelated edits. Record the base revision, acceptance commands, available native and runner transports, concurrency, and delivery authorization. Default to one sequential writer in the current working tree. Select isolation under `references/worktree-and-integration.md` from the loaded `implement-and-review` skill. Reversible worktree creation is within the implementation request; commit-based integration needs separate explicit authorization.
7. Save the immutable human preview as `model-plan.md` and progress as `run-state.json`. Create the executable `routing-plan.json` only after approval. Keep these files under `.ai-workflow/impl-review/<session_id>/`. Use `shared/references/implementation-routing-plan.schema.json` for routing and `shared/references/run-state-contract.md` for progress. Include the PRD, stable queue configuration, every executable task, and any immutable policy file that carries tools, call/time budgets, or delivery limits in `scope.inputs` with their canonical `content_sha256`. Bind each route to its task through `input_path`. A policy file is an approved input, not another progress ledger. Use the shared normalization rule so execution status updates preserve approval, while scope, acceptance, ownership, and policy changes invalidate it. For drafts, record both current and prospective ready identities as described below.

Resolve `shared/` from the installed skill library as the `shared` skill describes. Resolve worker skills from their loaded locations; never assume a `.agents/skills` installation path.

## Approve models before dispatch

Show this table with real resolved values, grouped only when tasks use the same route:

| Tasks or scope | Role | Exact model and transport | Effort | Native capability and role session | Model receipt | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| Task IDs | Implementation | Exact model, `native` subagent or thread, or named runner | Supported level | Preflight result; fresh task role and resume method | Required or unverified allowed | Task-specific fit |
| Same IDs | Independent review | Exact model, `native` subagent or thread, or named runner | Supported level | Preflight result; separate reviewer role and resume method | Required or unverified allowed | Main risk to inspect |
| Integration seams | Final review | Exact model, `native` subagent or thread, or named runner | Supported level | Preflight result; persistent integration role, separate from task roles | Required or unverified allowed | Cross-task coverage |

Also show the actual coordinator model and effort when exposed, selected profile, total call and time ceilings, concurrency cap, review/fix limit, exact fallback triggers, and driver readiness. Include provider routing, source sharing scope, allowed tools, model capabilities, and runtime effort where applicable. These controls belong in the selected route snapshot and its digest. Use an independent review context whose model differs from its writer; prefer another model family when it meets the quality requirement. Include design-lens workers and specialist reviewers that will run, so no hidden panel follows approval. Represent these as reviewer routes with clear scope and track names. Give review-only passes their own scope IDs, so they do not appear as build tracks; name the integration scope explicitly. The coordinator is recorded in the human preview and run state.

For each native route, the machine plan records `mode: native`, its approved host and `subagent` or `thread` transport, the capability evidence, and supported efforts. For each runner route, it records `mode: runner` and the selected runner. The plan does not contain a future context ID. After dispatch, the task manifest records native context data under `native_contexts[route_id]`. Runner results supply `runner_session_id`, which the task manifest records under `runner_contexts[route_id]`. Link both from the feature run state with the last input revision, completed turn, pending call, and receipt. Session creation, resumption, or recovery under an unchanged approved route is execution state, not a new route.

Explain any receipt limit in plain terms: the runner may confirm the configured model without proving which model served the request. Record `model_verification: allow_unverified` only when the user approves that limit; otherwise use `required`. Show runtime-controlled effort as such, without inventing a fixed level.

For a requested combined decision, use the section below instead of a separate model approval prompt. Otherwise offer **Keep defaults**, **Change selected roles**, or **Use another profile**. A direct request to “use defaults and run” permits the unchanged resolved setup within existing source sharing authority and accepted receipt limits; show the concrete plan and proceed. Reuse actual approval for the unchanged setup. Otherwise ask for the concrete model plan decision and wait. Record the actual user response reference, approval time, and canonical scope and route digests in `routing-plan.json`. Save a matching `gates` entry with `gate: model_plan_approval`, `decision: approved`, and the approval time. The launcher verifies the fingerprints and input files before side effects; the host remains responsible for recording only actual user approval.

Task approval from `to-tasks` does not approve the model plan. `--auto`, a saved preference alone, or silence cannot approve it. An explicit instruction to use defaults and run can approve the unchanged resolved selection as described above. Reuse approval when the user already approved this exact scope, models, effort, receipt policy, mode, and transport. A dynamic session or context ID does not require a new approval. Do not start implementation, reviewer, or model probe jobs before this gate.

## Combined task and model approval

Use this option only when the user requests both decisions together. It presents one concrete queue and its complete execution preview. It does not infer model approval from an earlier task-only response.

1. Keep the canonical task files in `draft`. Validate their gates, acceptance, dependencies, and ownership. Use `task_queue.py approval-inputs` to capture their current file hashes and prospective ready content hashes. Keep `queue.json` stable. Preserve the exact reviewed index as immutable evidence; its later status and approval links are administrative metadata.
2. Resolve all execution rows and controls before presenting the decision. Show task IDs and paths, dependencies, acceptance summaries, gate/security results, ownership and merge plans beside the exact model routes. Show source sharing, privacy, receipt limits, capabilities, transport, allowed tools, independent review, fallback triggers, concurrency, recovery, and total call/time budgets. Keep the actual coordinator separate. No worker runs during preview.
3. Bind the immutable preview to the current PRD, queue configuration, task drafts, prospective ready inputs, resolved routes, and policy files. Run `task_queue.py approval-inputs --routing-plan <draft-routing-plan.json>` to emit the prospective scope inputs and launch-compatible scope/route digests without promotion. A draft status is not excluded by the existing canonical rule; retain its hash as evidence instead of weakening normalization. Set the queue's `approval_record` locator before preview; preserve the resulting saved preview.
4. Request one actual response that explicitly covers both decisions: “Approve this task queue and the exact execution plan shown here?” Record its durable reference, decision time, and distinct approved decisions `task_queue` and `model_plan`. A response that covers only one decision satisfies only that gate. Source sharing and unverified receipts must be within actual authority shown in the preview.
5. Recheck every reviewed input before promotion. Write the immutable combined decision envelope from [queue-controller.md](queue-controller.md) using the actual response reference and time. Promote only each task's exact status line to `ready-for-agent`, then verify its prospective hash. Write the standard approved routing plan with those scope inputs and the recorded digests. Its approval reference and time must match the decision envelope. Use the engine's read-only `plan-digests` command to confirm the resulting scope and route digests match the preview. Preserve the original preview and response.
6. Append separate `task_queue_approval` and `model_plan_approval` entries to the existing `gates` list. Both cite the same actual response and timestamp; each records its scope. The model gate also records `scope_digest` and `routes_digest`. Link the task gate from the compact index. Use one immutable approved route snapshot for dispatch, repair, and resume.

Task promotion is within the approved decision. Commits, push, merge, publication, deployment, external messages, and council execution retain separate authority. A council is never included by implication. If inputs or controls change, retain completed evidence and get a decision only for the affected scope or rows.

Carry the approved model and effort into every worker and runner call. Check configured values and serving-model receipts against the approved receipt policy. A user override before dispatch wins and creates a replacement snapshot for unresolved rows. Any change to model, runner, mode, native transport, role, effort, provider routing, capabilities, tool policy, limits, or receipt policy needs the changed rows selected again unless that exact fallback was already approved. Keep completed evidence intact. A missing model or unsupported effort blocks its route. Never silently use a cheaper model or the host model instead. On resume, compare saved scope and routes before reusing approval, then reconcile each pending context or runner call before sending its next turn.

## Select bounded routes

Resolve the task route from `shared/model-routing.json` with the shared
`model_routing.py resolve <route> --profile default` command, adding the validated
`--local-profile` when present, or pass the explicit user profile. Explicit legacy `--family` routes remain available. Apply its risk
triggers before selecting a worker. Record the selected route key, profile or
family, and configuration digest beside
the exact proposed rows. The resolver does not grant approval or start workers.

For a difficult design with routine implementation, name a strong design role
before the bounded implementation roles and retain integration review. Separate
test design from test implementation when expected behavior is uncertain.
Exceptional effort requires a recorded reason. Apply the configuration's
escalation triggers through the existing approval boundary, never an automatic
model change. Record total usage, elapsed time, and repair cycles when available;
unavailable metrics remain unknown.

## Source sharing and review checkpoints

For an external route, the concrete preview names the provider, source and evidence
scope, allowed follow-up reviews, and exclusions. Save this in the route's optional
`source_sharing` object with `provider`, `scope`, `follow_ups`, `exclusions`, and the
actual user approval `reference`. The route digest binds it. Source sharing is
authority, not a provider request control. Save the selected `provider_routing`
separately, including its gateway, privacy requirements, and any provider allowlist.
Carry the same policy through initial calls, repairs, and resume. A request policy
digest proves the locally captured fields; it does not prove inference host
identity. Reuse standing approval within that scope; do not ask again on each task. Host approval review still applies.
Older approved plans remain valid under their recorded authority.

Select task review, targeted integration checks at changed boundaries, and one final
combined review. An earlier broad integration review needs a named unresolved risk.
Do not schedule a full repeated panel at every wave by default. Keep any review
sequence the user has already approved until an authorized plan change.

Set any complete worker input limit in the route's optional `context_budget` object.
The default is 24,000 UTF-8 bytes, including the task contract and appended review instructions.
A higher `max_bytes` needs a `reason` and is included in the approved route digest. Record that
new task roles start without parent history and repairs resume the same recorded role context.

Record loaded skill and script revisions alongside the plan. Use the call ledger
and normalized per-call metrics from the shared run-state contract. The existing
model routing configuration remains the only source of model defaults.

## Recovery allowance

The reviewer route can include `recovery: {"review_cycles": 3, "evidence_recoveries": 2}`.
These exact limits are included in the route approval digest. Omission preserves the legacy
three-cycle and one-recovery limits. The launcher reads the approved route, not editable
manifest ceilings. Choose the allowance with the total call and time budget; it does not
increase those totals. Routine evidence repair within this scope requires no new decision.
A changed model, product requirement, authority, or exhausted total still needs a decision.
