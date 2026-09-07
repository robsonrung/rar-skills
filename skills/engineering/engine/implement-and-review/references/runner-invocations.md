# Approved Route Launcher

Use this after the user approves the model summary. The routing plan is the
authority for the task, model, runner, effort, verification policy, and any
fallback. The launcher has no route default.

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

The launcher starts review only after the implementation route has a terminal,
successful result with a valid receipt. It reloads the plan and compares the
saved reviewer route with it.

```bash
python3 "$SKILL_DIR/scripts/launch.py" review \
  --working-dir <project-root> \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --review-brief <review-notes.md>
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

Use `--phase review --cycle <number>` for a native review receipt.

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
