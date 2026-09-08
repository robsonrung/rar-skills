# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- Use `--resume <session-id>` only when the caller already has a specific dcode session id. The wrapper does not receive a session id from dcode output, so it cannot create an exact per-role resume record itself.
- `--dcode-continue` selects dcode's shared most recent session. Do not use it for concurrent roles.
- `--session-file <file>` prepends workflow context as text. It is a handoff, not native resumption.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `shared/references/runner-common.md`. `--background` requires the shared jobs module `shared/scripts/runner_jobs.py`. It ships in this source repo; if a slimmed install lacks `shared/`, `--background` exits with a clear error and the foreground modes are unaffected. (The shared launcher strips `--background`/`--json`/`--output-file` from the re-invoked argv, so the detached child runs in the foreground without recursing.)
