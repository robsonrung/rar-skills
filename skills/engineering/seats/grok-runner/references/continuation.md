# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

- For an iterative role, capture its `session_id` from an earlier `json` or `stream-json` envelope, then use `--resume <session-id>` for every later Grok turn. Grok persists sessions under its own CLI controls.
- `--continue` selects the most recent Grok session for the directory. Use it only for one non-concurrent role when its identity is already certain. It cannot safely keep several roles separate.
- `--session-file <file>` prepends prior workflow context as text. It is a cross-runner handoff, not native resumption.


## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list --runner grok` / `status` / `result` / `cancel`) — see `shared/references/runner-common.md`.
