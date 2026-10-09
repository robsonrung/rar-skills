# Feature orchestration

Read after the model plan is approved. `implement-tasks` owns scheduling and integration; `implement-and-review` owns each task's build and review.

## Worker brief

Use a fresh implementer context and a separate independent reviewer context per task. For tasks with independently approved tracks, keep a separate pair per track. Supply these fields in the implementer's first message:

```text
Task: <stable T-ID and task file path>
Skill: implement-and-review
Scope: <allowed paths, interfaces, and exclusions>
Base: <current integration revision, or sequential working tree>
Inputs: <task acceptance contract, settled decisions, relevant file and evidence locators>
Models: <approved implementation/review models, native or runner transport, effort, and receipt policy>
Role session: <route id, context or runner-session reference when resumed, and manifest path>
Approval: <routing-plan.json, model-plan.md, and approval entry>
Authorization: <permitted local changes and authorized git/publication actions>
Acceptance: <exact commands and observable behaviors from the task>
Report: <unique task report and envelope paths>
Ceilings: <remaining review cycles, evidence recoveries, total calls, deadline, and context budget>
Return: complete, failed, ceiling_hit, or awaiting_human; evidence paths and remaining blockers
```

The acceptance contract is a completion condition, not a host `/goal` command. Do not use a user-owned task as a subagent unless requested. Start the worker with no parent conversation history. Send only the bound task packet. Use the host's explicit empty-history option; for a `fork_turns` host, use `none`. This does not authorize additional workers.

Workers load selected lenses and practices when their task needs them. They cannot select new models or add panels outside the approved plan. Reuse the task worker for a bounded correction; use a fresh context for the next task.

## Role-session lifecycle

Read `shared/references/host-model-execution.md` before dispatch. Use its native-first decision after the approved route and host capability check, not as a reason to replace the approved model or transport.

1. Before the first task call, write the brief and create the recorded implementer context. Create the reviewer context separately before its first review. Both are fresh for this task and track; neither receives another task's history.
2. Before dispatch, record the route ID, host, transport, task ID, role, input revision, pending call, and pending context entry in the feature ledger and task manifest. When the call returns, add its context or runner-session reference and receipt. Native task contexts live in `native_contexts[route_id]`; after polling, runner results supply `runner_session_id` and the manifest records it in `runner_contexts[route_id]`.
3. After a review finding, send the correction only to the same task's approved implementer context. Send the changed paths, evidence, and review report paths, not a copied transcript. Send the recheck to the same approved reviewer context. The approved cycle limit applies across these turns; it defaults to three.
4. Route an approved evidence recovery to the same task role that can recover the missing proof. It must not reimplement unrelated work, add a model, or reset the review cycle. Record the attempt before dispatch.
5. Keep a separate persistent integration context owned by the conductor for integration checks and seam review. It receives the current integration revision and task envelopes. It does not become a task implementer or reviewer, and task contexts do not become the integration context.
6. On resume, inspect a pending call before resending it. Resume the recorded native context through the engine's documented native continuation, or the recorded runner session through that runner's documented resume path. If the context is lost, reconstruct it only from the same role's artifacts and under the unchanged approved route. Record the loss and replacement reference. Never use a global latest-session selector.

Keep each context available until its role is complete and all required evidence is captured. Do not close a reviewer after its first pass when fixes or rechecks remain. Release only resources owned by this run and only through the host lifecycle and current authority.

## Scheduling

1. Use the shared read-only controller from [queue-controller.md](queue-controller.md) before each wave. It validates IDs, blockers, cycles, approved scope and route bindings, ownership, and concurrency. Preserve stable IDs. The canonical task file owns acceptance; the compact index owns references; manifests and the ledger own progress.
2. Select only returned `ready` tasks. Each dependency needs verified integration evidence bound to its contract and the current combined source state, a current carry forward checkpoint under its original approved scope, or an explicit current batch endorsement. A task or worker completion label alone cannot release a dependent. Finish returned `required_integration` work through the approved integration route or reuse an accepted shared checkpoint, then project readiness again.
3. Separate product blockers from write conflicts. Keep shared files, migrations, interfaces, and security surfaces serialized unless the approved queue input names an accepted merge plan with overlap and combined verification. An unresolved task or pending call keeps its write ownership until reconciliation and integration permit release.
4. Start at most the approved number of tasks. Use one writer without isolation. Each new worktree starts at the current integration revision. A running independent task can finish on its recorded base; after integration, check interactions and rerun affected acceptance. The scheduler only projects a wave; reserve its calls in the ledger before dispatch.
5. Record task role context IDs, runner-session IDs, pending calls, and task states before dispatch. Use the shared call-ledger helper to reserve and reconcile calls. Read compact status and result envelopes. Use cursor-based host waits or `runner_jobs.py wait-many` for explicit runner jobs. One bounded wait replaces alternating status and sleep calls. Do not load unchanged report bodies. Open report bodies for failures, changed results, and final synthesis, not repeated polling.

## Integration

Use the project's branch convention and preserve unrelated changes. Default to one sequential writer in the selected workspace and record acceptance after each task. Follow `references/worktree-and-integration.md` from the loaded `implement-and-review` skill for isolation and integration. Perform commit-based integration only when its required git actions are explicitly authorized.

Reuse a launcher-managed independent review when its exact approved route, contract, acceptance, and snapshot already match the current combined source. Its immutable manifest links must pass the shared verifier. Do not repeat that review only to release a dependency. Changed source or uncovered interactions require current integration evidence.

Before the original review, an optional bounded `review_scope` can declare the
complete dependency closure and exact prospective independent content. Use the
carry forward protocol in `shared/references/review-evidence.md` only after the
original reviewer explicitly approves it. A later checkpoint captures current
source, environment evidence, and required checks without a second broad review.
Keep unknown dependencies and affected shared boundaries on ordinary integration
review. Never infer independence from disjoint paths, create a scope after the
review, or use a task checkpoint as final feature acceptance.

For ordinary later changes, group affected retained tasks into one current batch
review through `shared/references/review-evidence.md`. Preserve each **acceptance
contract**, prior findings, required current captures, and named interactions. Reserve one
approved independent reviewer call bound to the batch contract and snapshot.
Link that snapshot as `batch_review` from every endorsed integration entry.
This avoids a separate reviewer call per retained task. The exact legacy path,
independence, pending ownership, route limits, and final feature gate still apply.

Represent an additional integration review as an approved `role: reviewer` route with its own scope ID and canonical `input_path`, such as `integration-T1` bound to the T1 task contract for dependency release. Keep its context separate from both task roles. Reserve the call through the shared run-state helper with the combined `review_snapshot`, dispatch through the selected native host or runner, and record the actual receipt with `complete`. This review-only scope uses the shared ledger lifecycle; the per-task launcher still owns implementation/review pairs. Link the resulting immutable snapshot from the ledger's `integration_evidence[T1]`. A final feature review can bind the PRD as its canonical input.

Before an authorized merge, record a pending effect with task ID, source revision, and target revision. Merge, verify ancestry and acceptance, then confirm the effect. After a crash, inspect the repository before retrying a pending merge.

Do not mark a task done on worker completion alone. Review conflict resolutions and capture applicable acceptance on the combined state before releasing dependents. Reuse a captured task result only when the relevant code, dependencies, environment, and acceptance contract still match and the caller does not require a fresh run. A failed task blocks descendants, not unrelated tasks.

## Per-task launcher

Use the launcher bundled with the loaded `implement-and-review` skill when it supports the approved plan. Read its documented flags; do not construct a second frontend/backend workflow here. Pass `--routing-plan`, `--task-id`, the task namespace, base, and named task briefs through the documented `--track` arguments. Launcher defaults cannot override approval. For a native route, use the engine's documented native receipt and continuation flow with the same `native_contexts[route_id]` record. For a runner route, resume only its recorded session through that runner's documented adapter. Do not create a fresh role context for a review, correction, or evidence retry when the recorded context remains usable.

If a launcher cannot represent a model, effort, or execution mode, report the mismatch before dispatch. Use an already approved adapter or ask for a route change. Report configured and observed models separately. A route without an observed serving-model receipt can continue only under its approved `allow_unverified` policy.

## Completion

Keep task reports and role-session records after workers finish. Do not close a task role before its review, correction, and evidence obligations end; keep the integration context until the feature report is complete. Close native workers only through the host lifecycle when needed. Leave user-owned tasks, branches, and worktrees intact unless cleanup is authorized.

Capture combined acceptance and the approved seam review using [completion.md](completion.md). Report blocked tasks and missing evidence. Resume from the ledger and repository state; a report path alone does not prove its revision is current.

## Context packet before dispatch

Use `shared/scripts/context_packet.py` to bind the derived brief to current decisions
and selected evidence. The launcher checks the complete final input against a 24,000-byte
UTF-8 limit, including the full task contract and appended review instructions. Link source
sections instead of embedding reports. A larger limit needs `context_budget` and a reason in
the approved route; a packet's derived-note limit cannot override it.
The packet must identify current decisions, evidence, and superseded material.
Save it beside the brief as `<brief-name>.md.packet.json`; the launcher verifies it
before dispatch. Missing packets remain compatible with older runs, but new runs
use them. See `shared/references/context-packets.md` for the input contract.

A changed decision invalidates affected derived notes and prototypes. Rebuild the
brief from current decisions before dispatch; do not ask the worker to choose
between conflicting instructions. Keep the original sources available for inspection.

## Completion and compact recovery

For new ledger-managed reviews, bind `--review-snapshot` during reservation and use the shared
`complete` command with the actual receipt. Keep the task launcher's route checks where it owns
the task manifest. Do not reconstruct a successful receipt by scanning transcripts or editing
metadata. A source or evidence mismatch blocks acceptance before another model is needed.
Save the exact failed field, current contract, and prepared packet for any authorized recovery.
