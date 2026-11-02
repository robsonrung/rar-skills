---
name: claude-runner
description: Run a prompt on a Claude model through the local Claude CLI. Use when the host cannot run the selected Claude model natively, or the user asks for the Claude CLI.
---

# Claude Runner

Run one prompt on a Claude model through the local `claude` CLI. A host that offers the model natively (a Claude Code subagent, a T3 Code provider) runs it there instead.

## Run

```bash
python3 <skill-dir>/scripts/run_claude.py "<prompt>" --model <model> --effort <effort> \
  --output-format json --disable-fallback --json
```

- `--prompt-file <file>` replaces the inline prompt for a long brief; `--working-dir <path>` sets the repository.
- `--role implementer`, or no role, can edit files; every other role runs read-only.
- `--background` returns a job id for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).
- `--help` lists the rest.

## Continue

The envelope's `session_id` (present with `--output-format json`) is that role's context. Send the role's next turn with `--resume <session_id>`; every role keeps its own session.

## Result

Read `agent_message`. `--disable-fallback` keeps **seat fidelity**: the answer comes from this seat, or `success` is false. On failure, report `status` and the telling stderr lines, and leave the seat unanswered.
