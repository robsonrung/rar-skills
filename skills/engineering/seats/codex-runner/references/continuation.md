# Session Continuation and Background Jobs

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Session Continuation

Two mechanisms, with different purposes:

- `--resume <session-id>` / `--resume-last` — native Codex resume (`codex exec resume`). Preferred for codex -> codex continuation: it restores the full Codex-side thread state without re-sending prior text. The session id comes from the `session_id` envelope field of the earlier run. When resuming without a prompt, a default "continue from the current thread state" instruction is sent.
- `--session-file <file>` — prepends prior workflow context as text. Use only for cross-runner handoffs (e.g. continuing a Claude or Gemini thread in Codex), where no native session exists.

`--resume` cannot fall back to another runner; if Codex CLI is missing the run fails with `return_code` -2.


## Background Jobs

`--background` runs as a tracked job (job dir holds the manifest, log, and final envelope as `result.json`); manage it with the shared jobs CLI (`list --runner codex` / `status` / `result` / `cancel`) — see `shared/references/runner-common.md`.
