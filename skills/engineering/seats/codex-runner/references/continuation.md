# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

Two mechanisms, with different purposes:

- For an iterative role, capture its returned `session_id` and use `--resume <session-id>` for every later Codex turn. This restores the full Codex-side thread state. Keep `--ephemeral` off. When resuming without a prompt, the wrapper sends its default continuation instruction.
- `--resume-last` selects the most recently recorded Codex session. Use it only for one non-concurrent role when its identity is already certain. It cannot safely keep several roles separate.
- `--session-file <file>` prepends prior workflow context as text. It is a cross-runner handoff, not native resumption.

`--resume` cannot fall back to another runner; if Codex CLI is missing the run fails with `return_code` -2.


## Background Jobs

`--background` runs as a tracked job (job dir holds the manifest, log, and final envelope as `result.json`); manage it with the shared jobs CLI (`list --runner codex` / `status` / `result` / `cancel`) — see `shared/references/runner-common.md`.
