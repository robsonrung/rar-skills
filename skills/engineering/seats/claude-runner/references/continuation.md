# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- For an iterative role, capture its `session_id` from the earlier envelope with `--output-format json` or `stream-json`, then use `--resume <session-id>` for every later Claude turn. Keep `--no-session-persistence` off.
- `--continue` selects the most recent Claude conversation in the project. Use it only for one non-concurrent role when its identity is already certain. It cannot safely keep several roles separate.
- `--session-file <file>` prepends prior workflow context as text. It is a cross-runner handoff, not native resumption.


## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list --runner claude` / `status` / `result` / `cancel`) — see `shared/references/runner-common.md`.

## Durable streaming

For long iterative reviews, use `--output-format stream-json --event-log <unique-events.jsonl>`.
With `--output-file`, the stream log defaults beside that file. The wrapper flushes stdout events
and writes a checkpoint with session identity and available metrics. The event file is exclusive;
a retry uses a new file and resumes the recorded session. Partial usage stays marked incomplete.
A timeout preserves the observed session and available metrics but never reports success.

Keep findings in small checkpoints during a long review. The final structured result remains
required for acceptance. After interruption, inspect the captured events and actual process state
before resuming. Use `runner_jobs.py wait-many` for background jobs, not separate sleep loops.
