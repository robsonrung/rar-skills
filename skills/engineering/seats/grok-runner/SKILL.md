---
name: grok-runner
description: Run a prompt on a Grok model through the local Grok CLI. Use when the host cannot run the selected Grok model natively, or the user asks for the Grok CLI.
---

# Grok Runner

Run one prompt on Grok through the local `grok` CLI. A host that offers the model natively runs it there instead.

## Run

```bash
python3 <skill-dir>/scripts/run_grok.py "<prompt>" --model <model> --effort <effort> \
  --output-format json --json
```

- Effort goes up to `high`.
- `--prompt-file <file>` replaces the inline prompt for a long brief; `--working-dir <path>` sets the repository.
- `--role implementer`, or no role, can edit files; every other role runs in read-only plan mode.
- `--background` returns a job id for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).
- `--help` lists the rest.

## Continue

The envelope's `session_id` (present with `--output-format json`) is that role's context. Send the role's next turn with `--resume <session_id>`; every role keeps its own session.

## Result

Read `agent_message`. This runner never falls back, which keeps **seat fidelity**: the answer comes from this seat, or `success` is false. On failure, report `status` and the telling stderr lines, and leave the seat unanswered.
