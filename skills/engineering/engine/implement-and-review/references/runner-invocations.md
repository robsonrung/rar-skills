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

First follow `shared/references/review-evidence.md`: prepare a new snapshot and
requirements file, then capture required checks. Use the task's recorded base
and approved contract path. Exclude the launcher's generated artifact directory
when it is inside the worktree. The snapshot binds actual source and index
state; `input_revision` continues to identify the review brief.

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
  --review-snapshot <snapshot.json>
```

The manifest counts the review/fix attempt before dispatch. It permits three
cycles. Reserve the one allowed evidence recovery before asking the existing
route to recover missing evidence:

```bash
python3 "$SKILL_DIR/scripts/launch.py" evidence-recovery \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --reason "<missing evidence>"
```

## Receipts and native routes

The reviewer returns the shared evidence JSON contract. After its native receipt
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
to that call. Use observed serving-model values only when the host supplies them.

The launcher stores the receipt under the task's artifacts and records its path
and digest. `native_contexts[route_id]` keeps the role's context, configuration,
input revision, completed turn, and pending call. Another role cannot use that
context. Session identity does not verify serving-model identity.

## Continue the same role

After a completed native implementation needs an in-scope correction, prepare
the next turn in its recorded context:

```bash
python3 "$SKILL_DIR/scripts/launch.py" resume-native \
  --manifest <launch-manifest.json> \
  --track <track-name> \
  --follow-up <correction-notes.md>
```

Send the returned handoff through the host's follow-up tool, then use
`record-native --phase implementation` for the new result. Use `review` for each
reviewer recheck; it retains the reviewer session and counts the next review
cycle. Native follow-ups also have a hard bound; they do not extend the three
review cycles or the one evidence recovery.

If a native context is confirmed lost, use `--context-recovery-reason` on the
documented continuation or receipt command. Reconstruct only the same role from
its artifacts under the unchanged route. Record the previous and replacement
IDs. A recovery reason does not authorize a new model, scope, or tool policy.
An uncertain pending call must be reconciled before reconstruction.

`poll` captures successful runner `session_id` values in
`runner_contexts[route_id]`; reviewer rechecks use that exact session when the
adapter supports it. For an implementation fix through an external runner, pass
the recorded ID through that runner's continuation command with the exact
approved options and `--disable-fallback`, then capture its result in the task
ledger. Read the runner's continuation reference. Pi needs a unique session path
from the first call. A runner with no exact resume support needs a disclosed
same-role reconstruction; never use a global latest-session selector.

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
