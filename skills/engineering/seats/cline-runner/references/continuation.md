# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- For an iterative role, pass its recorded Cline id as `--session <session-id>` on every later turn. The wrapper can recover an id after a run through `cline history`, but that recovery is best effort and can be ambiguous under concurrent work.
- Give concurrent roles separate `--data-dir` values or authenticated lanes before creating their sessions. Record the explicit id returned or selected for each role. Cline always writes its session history, so `--no-session-persistence` does not provide isolation.
- `--session-file <file>` prepends workflow context as text. It is a handoff, not native resumption.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `shared/references/runner-common.md`.
