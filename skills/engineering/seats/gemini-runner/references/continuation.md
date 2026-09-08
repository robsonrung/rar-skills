# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- `--agy-continue` selects the latest shared Antigravity CLI conversation. It does not expose an exact session id, so it cannot preserve independent concurrent roles.
- Do not use `--agy-continue` for a multi-role workflow. Use proven isolated runtime state, or reconstruct the same authorized role from recorded artifacts and state the handoff limit.
- `--session-file <file>` prepends workflow context as text. It is a handoff, not native resumption.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `shared/references/runner-common.md`. `--background` requires the shared jobs module `shared/scripts/runner_jobs.py`. It ships in this source repo; if a slimmed install lacks `shared/`, `--background` exits with a clear error and the foreground modes are unaffected. (The shared launcher strips `--background`/`--json`/`--output-file` from the re-invoked argv, so the detached child runs in the foreground without recursing.)
