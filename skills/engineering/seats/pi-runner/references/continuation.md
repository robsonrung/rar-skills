# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- Allocate one durable session file path for each iterative role. Pass that exact path with `--session <role-session-file>` on the first Pi call and every later turn. Record the path in workflow state before the first call.
- Pi's stream does not report a new session id. The envelope can only repeat the `--session` value supplied by the caller, so do not wait for the wrapper to discover a role session.
- Keep `--ephemeral` and `--no-session-persistence` off for an iterative role. `--session-file <file>` is a text handoff, not the native Pi session argument.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `shared/references/runner-common.md`.
