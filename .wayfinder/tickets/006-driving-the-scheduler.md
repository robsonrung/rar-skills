---
id: "006"
title: Driving the scheduler from a board
type: grilling
status: open
parent: map
blocked_by: ["002"]
---

# Driving the scheduler from a board

## Question

Once the approval gate passes, the board hands off to `pipeline_scheduler.py` for phases 3–6. How, exactly?

To settle: does the board spawn the scheduler as a subprocess per board or import it directly; how a board scopes its cards so it shows only its own runs, given `collect_runs()` currently returns every run under the target flat; whether the scheduler needs a run-id prefix or a board id in its state to make that filtering honest; and how scheduler stdout, failures, and hard-blocks surface as board state rather than being swallowed.

Note the existing constraint: slice ledgers are siblings named `<run-id>-<slice>` precisely so the two-level board glob finds them. Any per-board scoping has to keep that working.

Blocked by Board lifecycle and storage layout, since where board state lives determines how runs are scoped to it.

### Sharpened by [Surviving a server restart](001-restart-durability.md)

The spawn question is **answered**: scheduler runs launch detached via `launch_background()`, in their own process session, so they outlive the server. The board is a window onto a run, never its owner — which rules out importing the scheduler in-process.

What that leaves for this ticket, harder than before: a detached run can die without telling anyone. So it must settle how the board distinguishes **still running** from **finished** from **died silently**, given `runner_jobs.py` already answers exactly this with a pid-liveness plus result-file check (`job_status()` returns `running` / `completed` / `failed` / `died` / `cancelled`). Decide whether that vocabulary is reused as-is or mapped onto run-state's `status` values, and what a board shows for a run whose process vanished with no result written.
