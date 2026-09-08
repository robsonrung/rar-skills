# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- `--resume <session-id>` / `--continue` — native Claude resume. Preferred for claude -> claude continuation; the session id comes from the `session_id` envelope field of the earlier run (requires `--output-format json` or `stream-json` on that run).
- `--session-file <file>` — prepends prior workflow context as text. Use only for cross-runner handoffs where no native session exists.


## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list --runner claude` / `status` / `result` / `cancel`) — see `shared/references/runner-common.md`.
