# Prepare and Approve the Model Plan

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Read before any implementation, reviewer, council, or model probe job. The preview is the concrete plan the user approves.

## Prepare the execution plan

1. Read the queue under `.ai-workflow/work/<feature-slug>/tasks/`, its `tasks-draft.md`, and its PRD. Verify that both approval records are present and still describe the queue; drafts cannot start implementation. For a bare plan, obtain an approved PRD through `to-prd`, then use `to-tasks`. For one complete task, keep the model approval below and skip graph scheduling.
2. Check stable task IDs, missing dependencies, cycles, acceptance commands, HITL decisions, and write conflicts. Resolve facts from the project before asking for a decision. Do not launch a task with unresolved requirements or missing access.
3. Read `shared/references/workflow-stage-routing.md`. Reuse earlier decisions and lens findings. Use `coding-design-plan` only when the implementation shape is unresolved; a complete Slice Contract already supplies the constraints. Call `design-gate` again only when new evidence changes the design surface; do not repeat an earlier architecture study.
4. Classify each task through `shared/references/task-shaped-model-routing.md`, then resolve roles through `shared/references/model-roster.md`. This distinguishes routine explicit functions, normal changes, TDD or difficult implementation, migration or branch exploration, ambiguous design or research, broad review, precision review, and defensive security without copying model choices here. If `.rar-skills/config.local.yaml` exists, read its advisory `seats` and `models` only while forming this preview, as `shared/references/local-config.md` defines. Validate every value against the roster and candidate transport, let direct user instructions win, and never reread it after approval. Select the strongest known suitable model for each implementation and review role, then the lowest sufficient supported effort. Separate task-fit recommendations from measured benchmark results.
5. Read `shared/references/host-model-execution.md` and preflight each chosen route without starting a model job. Check native capability before probing an external runner: exact model selection, supported effort, role isolation, tool policy, serving-model receipt, and follow-up or resume support. Prefer a native subagent or authorized task thread when it can meet the exact selected route. Probe and use an external runner only for a foreign model, an explicit user-requested transport, or a native route that lacks a required capability; name that reason in the preview. For an iterative runner role, check its documented persistent-session path. For a specialized defensive-security route, verify exact identity, entitlement, effort control, and tool limits. An ordinary general model cannot be presented as that specialized route; when it is unavailable, propose only the exact fallback defined in the shared route and approved in the plan.
6. Inspect git state and preserve unrelated edits. Record the base revision, acceptance commands, available native and runner transports, concurrency, and delivery authorization. Default to one sequential writer in the current working tree. Select isolation under `references/worktree-and-integration.md` from the loaded `implement-and-review` skill. Reversible worktree creation is within the implementation request; commit-based integration needs separate explicit authorization.
7. Save the human preview as `model-plan.md` and progress as `run-state.json`. Create the executable `routing-plan.json` only after approval. Keep these files under `.ai-workflow/impl-review/<session_id>/`. Use `shared/references/implementation-routing-plan.schema.json` for routing and `shared/references/run-state-contract.md` for progress. Include the PRD and every executable task in `scope.inputs` with their canonical `content_sha256`; bind each route to its task through `input_path`. Use the shared normalization rule so task status updates preserve approval, while changes to scope or acceptance invalidate it.

Resolve `shared/` from the installed skill library as the `shared` skill describes. Resolve worker skills from their loaded locations; never assume a `.agents/skills` installation path.

## Approve models before dispatch

Show this table with real resolved values, grouped only when tasks use the same route:

| Tasks or scope | Role | Exact model and transport | Effort | Native capability and role session | Model receipt | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| Task IDs | Implementation | Exact model, `native` subagent or thread, or named runner | Supported level | Preflight result; fresh task role and resume method | Required or unverified allowed | Task-specific fit |
| Same IDs | Independent review | Exact model, `native` subagent or thread, or named runner | Supported level | Preflight result; separate reviewer role and resume method | Required or unverified allowed | Main risk to inspect |
| Integration seams | Final review | Exact model, `native` subagent or thread, or named runner | Supported level | Preflight result; persistent integration role, separate from task roles | Required or unverified allowed | Cross-task coverage |

Also show the coordinator model, concurrency cap, review/fix limit, and proposed fallbacks. Use an independent review context whose model differs from its writer; prefer another model family when it meets the quality requirement. Include design-lens workers and specialist reviewers that will run, so no hidden panel follows approval. Represent these as reviewer routes with clear scope and track names. Give review-only passes their own scope IDs, so they do not appear as build tracks; name the integration scope explicitly. The coordinator is recorded in the human preview and run state.

For each native route, the machine plan records `mode: native`, its approved host and `subagent` or `thread` transport, the capability evidence, and supported efforts. For each runner route, it records `mode: runner` and the selected runner. The plan does not contain a future context ID. After dispatch, the task manifest records native context data under `native_contexts[route_id]`. Runner results supply `runner_session_id`, which the task manifest records under `runner_contexts[route_id]`. Link both from the feature run state with the last input revision, completed turn, pending call, and receipt. Session creation, resumption, or recovery under an unchanged approved route is execution state, not a new route.

Explain any receipt limit in plain terms: the runner may confirm the configured model without proving which model served the request. Record `model_verification: allow_unverified` only when the user approves that limit; otherwise use `required`. Show runtime-controlled effort as such, without inventing a fixed level.

Ask: **"Approve this model plan, including routes, transport, role-session strategy, effort, and receipt limits, or specify changes?"** Wait for the answer. Record the user response reference, approval time, and canonical scope and route digests in `routing-plan.json`. Save a matching `gates` entry with `gate: model_plan_approval`, `decision: approved`, and the approval time. The launcher verifies the fingerprints and input files before side effects; the host remains responsible for recording only actual user approval.

Task approval from `to-tasks` does not approve the model plan. `--auto`, a default selection, or silence cannot approve it. Reuse approval when the user already approved this exact scope, models, effort, receipt policy, mode, and transport. A dynamic session or context ID does not require a new approval. Do not start implementation, reviewer, council, or model probe jobs before this gate.

Carry the approved model and effort into every worker and runner call. Check configured values and serving-model receipts against the approved receipt policy. Any change to model, runner, mode, native transport, role, effort, or receipt policy requires approval of the changed rows unless that exact fallback was already approved. A missing model or unsupported effort blocks its route. Never silently use a cheaper model or the host model instead. On resume, compare saved scope and routes before reusing approval, then reconcile each pending context or runner call before sending its next turn.

## Select bounded routes

Resolve the task route from `shared/model-routing.json` with the shared
`model_routing.py resolve` command. Apply its risk triggers before selecting a
worker. Record the selected route key, family, and configuration digest beside
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
actual user approval `reference`. The route digest binds it. Reuse standing approval
within that scope; do not ask again on each task. Host approval review still applies.
Older approved plans remain valid under their recorded authority.

Select task review, targeted integration checks at changed boundaries, and one final
combined review. An earlier broad integration review needs a named unresolved risk.
Do not schedule a full repeated panel at every wave by default. Keep any review
sequence the user has already approved until an authorized plan change.

Record loaded skill and script revisions alongside the plan. Use the call ledger
and normalized per-call metrics from the shared run-state contract. The existing
model routing configuration remains the only source of model defaults.
