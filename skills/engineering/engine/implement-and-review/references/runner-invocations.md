# Approved Route Launcher

Use this after the user approves the model summary. The routing plan is the
authority for the task, model, runner, effort, verification policy, and any
fallback. The launcher has no route default. Select models by
`shared/references/task-shaped-model-routing.md` and execution by
`shared/references/host-model-execution.md` before forming the plan.

## Prepare the plan

Each scope input has a `content_sha256`. It is the SHA-256 of UTF-8 task text
after line endings become LF and after removing only an exact standalone line
such as `**Status:** done`. A task status change does not invalidate approval.
An acceptance or requirement change does.

Write the proposed machine fields to `draft-model-plan.json`. Calculate the
canonical inputs and approval digests before recording approval:

```bash
SKILL_DIR="<absolute path of this skill directory>"
python3 "$SKILL_DIR/scripts/launch.py" plan-digests \
  --working-dir <project-root> \
  --routing-plan <draft-model-plan.json>
```

Copy the returned `scope.inputs` and digests into the draft. After actual user
approval, save `routing-plan.json` with its approval object. This command does
not approve, write, create a worktree, or dispatch a worker.

For a new native route, use `mode: native`, `effort_control: native`, and a
`native` object with `host`, `transport` (`subagent` or `thread`),
`capability_source`, and `supported_efforts`. Select an effort from the checked
host capability list. `runner` remains the model-family adapter key for schema
compatibility; a native route does not invoke its CLI. Legacy native rows with
runner effort control can still be read, but they do not prove native capability.

## Launch implementation

```bash
SKILL_DIR="<absolute path of this skill directory>"
python3 "$SKILL_DIR/scripts/launch.py" launch \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --routing-plan <routing-plan.json> \
  --track <track-name> <implementation-notes.md>
```

The implementation notes are derived notes. The launcher reads the route's
approved `input_path`, verifies its canonical content hash, and puts that task
contract before the notes. A note cannot replace the approved task contract.
The manifest records both source digests.

Before dispatch, discover the required commands and stable check IDs. Include the
requirements file, base, capture location, and shared `prepare` and `run-check`
instructions in the implementation notes as described in `evidence-strategy.md`.
The worker captures its last green checks after its final edit and returns original
snapshot and result paths with logs and required failing regression evidence.

A canonical task with a standalone `**Status:** draft` declaration cannot launch,
including spaces or tabs around the declaration or status value, even with an
approved routing plan. Promote the task before dispatch. A dry run can
preview a draft without writes. Legacy standalone contracts without a task
status line remain supported.

One sequential track works in a Git or non-Git directory. Independent tracks
use reversible isolation:

```bash
python3 "$SKILL_DIR/scripts/launch.py" launch \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --routing-plan <routing-plan.json> \
  --isolation worktree \
  --track <first-track> <first-notes.md> \
  --track <second-track> <second-notes.md>
```

`--dry-run` can preview a complete draft plan. Its output says
`unapproved_preview`; it cannot write, create a worktree, or start a job. A
non-dry launch rejects a plan without recorded approval.

## Launch review

The coordinator follows `shared/references/review-evidence.md`: confirm the worker's
final snapshot and environment, then run `select-checks` with its original captures
and `--from-snapshot <worker-snapshot>`. For an unchanged handoff, pass the same
worker snapshot to `--snapshot` and `--from-snapshot`.
If a selected fresh run or retry already has a result there, prepare a new target
snapshot and select again against the original worker snapshot before execution.
Keep reusable original captures and write fresh results only in the new directory.
Prepare a new snapshot when source or relevant context changed. Execute all affected,
fresh, missing, or invalid checks and assess explicit transfer candidates. Use the
task's recorded base and approved contract path. Exclude the launcher's generated artifact directory
when it is inside the worktree. The snapshot binds actual source and index
state; `input_revision` continues to identify the review brief.

Prepare the captured evidence packet with `review_evidence.py prepare-packet`. The launcher
requires and validates the complete packet before reserving a cycle when checks or observations are required. Intact failing captures remain reviewable. The explicit legacy `--direct-captures <json>` path accepts complete `checks` and `observations` with the same integrity validation. Missing or changed captures block before dispatch or cycle reservation. The response coverage includes all fields from the evidence contract.

The launcher starts review only after the implementation route has a terminal,
successful result with a valid receipt. It reloads the plan and compares the
saved reviewer route with it.

```bash
python3 "$SKILL_DIR/scripts/launch.py" review \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --review-brief <review-notes.md> \
  --review-snapshot <snapshot.json> \
  --evidence-packet <packet.json>
```

The manifest counts each review/fix attempt before dispatch. Reviewer routes can declare
`recovery.review_cycles` and `recovery.evidence_recoveries` in the approved plan. Defaults are
three cycles and one evidence recovery. Existing total call limits still apply. Reserve an
approved evidence recovery before asking the existing route to recover missing evidence:

```bash
python3 "$SKILL_DIR/scripts/launch.py" evidence-recovery \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --reason "<missing evidence>"
```

## Receipts and native routes

The launcher resolves the reviewer response contract to an absolute readable path.
External adapters use file reads. For a native host without verified shared-file
access, the brief embeds the contract so the role can use its exact schema.


The reviewer loads `shared/references/reviewer-response.md` and returns its exact
JSON contract after independently assessing source and evidence. The coordinator
keeps the full evidence operations manual. After the native receipt
is recorded, or its runner job completes, capture that exact response:

```bash
python3 "$SKILL_DIR/scripts/launch.py" record-review \
  --manifest <launch-manifest.json> --track <track-name> --cycle <number>
python3 "$SKILL_DIR/scripts/launch.py" verify-review \
  --manifest <launch-manifest.json> --track <track-name> --base <current-review-base>
```

`record-review` preserves valid results even when findings or failed checks
prevent readiness. `verify-review` uses the latest review cycle for the track.
Both return 0 for ready, 1 for remaining work, and 2 for missing, invalid,
or stale evidence. A fix requires a new snapshot and reviewer recheck. Preserve
earlier records and cycle limits. Non-Git implementation can still run, but the
source evidence gate requires Git.

For every runner call, forward the approved `provider_routing`, model capabilities,
effort control, and tool policy from its snapshot, including repairs and resume.
Retain the captured request policy digest and separate model author, gateway, and
observed inference provider. Reject a missing required request control or tool
capability; never relax privacy to recover availability. External browser workers
need their own checked driver and typed image path. A selected external Pi browser route
binds `browser: {mechanism, preflight: {path, sha256}}`. Pi receives
`--tool-policy browser`, `--browser-mechanism playwright-cli|agent-browser`, and
`--browser-preflight <file>` from that snapshot, with explicit image attachments
through `--image-file <path>` when needed. Shell scope is not a sandbox.

For every runner result, the effective runner and configured model must match
the approved route. A `required` route also needs a verified model receipt from
a native or provider event with the approved observed model. An
`allow_unverified` route may report an unverified receipt, which stays visible
in polling and the final report. A verified receipt is also valid when its
observed model matches. A different observed model blocks the route.

Native routes return a pending record. After the caller dispatches the exact
route, record its JSON receipt before polling or reviewing it:

```bash
python3 "$SKILL_DIR/scripts/launch.py" record-native \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --phase implementation \
  --receipt <receipt.json>
```

Use `--phase review --cycle <number>` for a native review receipt. Keep the
normal envelope model and receipt fields. Add `native_execution` with the actual
`host`, `transport`, `context_id`, `role`, `task_id`, `configured_model`,
`configured_effort`, `tool_policy`, and positive `completed_turn`. Copy
`call_id` and `input_revision` from the dispatched handoff so the receipt is bound
to that call. New handoffs also require `parent_history: none`: start with the host's supported
empty-history option and send the exact file at `input_path`, with no copied coordinator history.
For a `fork_turns` host, use `none` when creating the role. A resume uses the existing role context.
Record `native_execution.parent_history: none` only after that policy was applied. The recorder
rejects a missing or different value for these handoffs. Legacy handoffs keep their original fields.
This receipt is the host adapter's attestation, not independent inspection of hidden context.
Use observed serving-model values only when the host supplies them.

The launcher stores the receipt under the task's artifacts and records its path
and digest. `native_contexts[route_id]` keeps the role's context, configuration,
input revision, completed turn, and pending call. Another role cannot use that
context. Session identity does not verify serving-model identity.

## Continue the same role

After a completed implementation needs an in-scope correction, prepare
the next turn in its recorded context:

```bash
python3 "$SKILL_DIR/scripts/launch.py" resume \
  --manifest <launch-manifest.json> \
  --track <track-name> \
  --follow-up <correction-notes.md>
```

For native routes, send the returned handoff through the host's follow-up tool, then use
`record-native --phase implementation` for the new result. Use `review` for each
reviewer recheck; it retains the reviewer session and counts the next review
cycle. External routes dispatch through the same command; `resume-native` remains a compatible alias. Followups have a hard bound; they do not extend the approved
review cycle or evidence recovery allowances.

Compact followups send changed facts, findings, evidence locators, and the execution
boundary. The ledger retains the canonical contract identity, exact approved route,
completed context, receipt hash, and prior bound input. External proof also binds
request policy, tool policy, isolated history, and the actual saved session. A context
ID alone cannot authorize compact input. Native and runner contexts remain separate.
After proof validation, the launcher uses the smaller full or compact rendering and
records `input_kind`. First calls and reconstructed contexts receive the full contract.
Missing proof starts fresh full reconstruction under the original route and remaining counters.
Altered receipt, session, route, policy, contract, or prior input blocks for reconciliation.
An uncertain outcome must be reconciled before another dispatch.

The implementation followup limit is the approved reviewer route's
`recovery.review_cycles` plus `recovery.evidence_recoveries`. Plans without
`recovery` keep the limit of four followups. The manifest saves `resume_attempts`
before external dispatch or returning a handoff for host dispatch. The count persists across resume
and context reconstruction. A retry while a call is pending cannot reserve
another followup. Review cycles and evidence recoveries retain their separate
counts and limits; the followup bound does not grant either reservation.

If a native context is confirmed lost, use `--context-recovery-reason` on
`resume-native` or `review` before dispatch. The handoff requests reconstruction
with the full contract. Record the replacement through `record-native`, which
retains that recovery reason. Reconstruct only the same role from
its artifacts under the unchanged route. Record the previous and replacement
IDs. A recovery reason does not authorize a new model, scope, or tool policy.
An uncertain pending call must be reconciled before reconstruction.

`poll` captures successful runner `session_id` values in
`runner_contexts[route_id]`; reviewer rechecks and implementation repairs use that
exact session when the adapter supports it. Use the launcher for both roles so
input binding, receipts, and counters remain intact. A runner with no exact resume
support uses full reconstruction with a recorded reason. Global latest-session
selectors cannot identify independent roles. The file-based adapter must retain
its allocated session file before compact continuation is eligible.

## Poll and cleanup

```bash
python3 "$SKILL_DIR/scripts/launch.py" poll \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --wait
```

`died`, `cancelled`, malformed, and receipt-mismatched jobs are terminal
failures. The launcher writes the manifest before and after every dispatch.
The first write is exclusive. If the session and task already have a manifest,
`launch` stops before dispatch or artifact replacement. Use the existing manifest
to resume or reconcile the task. A dry run remains a preview and writes no files.

Polling reads runner jobs in one process and checks each distinct job once per
poll. It does not read runner logs. Parsed results can be reused within one wait
only after their content hash matches. The cache holds at most 32 results of at
most 256 KiB each and is discarded when the command exits. Receipt checks still
run on each observation. Missing and corrupt jobs are terminal failures; native
tasks remain pending until their receipts are recorded.

The standalone runner status command reads at most the final 4 KiB of a log and
returns at most five nonempty lines. `log_tail_truncated` reports omitted bytes or
lines. Read the stored log directly when more detail is required.

Cleanup accepts only its own manifest path, repository root, worktree path, and
branch shape. Dry runs report `planned_worktrees`; they do not claim removal.

## Structured rechecks and receipts

The launcher requests structured Claude output so a resumable role returns its
session ID. Malformed or missing terminal output is a receipt failure, not a pass.
Use the wrapper's normalized metrics; keep its raw stdout for evidence. Do not
recover a session by scanning an unrelated or global latest transcript.

For source rechecks use the shared incremental-review contract. For a prose-only
correction use its addendum mode. Both remain reviewer calls under the approved
ceilings. They do not authorize extra cycles. The evidence helper expands and
validates the response; never rewrite the reviewer's response before recording it.
