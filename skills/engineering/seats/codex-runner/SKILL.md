---
name: codex-runner
description: Run a prompt on a GPT model (Astra, Sol, Terra) through the local Codex CLI. Use when the host cannot run the selected GPT model natively, or the user asks for the Codex CLI.
---

# Codex Runner

Run one prompt on a GPT model through the local `codex` CLI. A host that offers the model natively (a Codex subagent, a T3 Code provider) runs it there instead.

## Run

```bash
python3 <skill-dir>/scripts/run_codex.py "<prompt>" --model <model> --effort <effort> \
  --disable-fallback --json
```

- `--prompt-file <file>` replaces the inline prompt for a long brief; `--working-dir <path>` sets the repository. Outside a Git repository, add `--skip-git-repo-check`.
- `--role implementer`, or no role, can edit files; every other role runs in a read-only sandbox.
- `--background` returns a job id for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).
- `--help` lists the rest.

## Continue

The envelope's `session_id` is that role's context. Send the role's next turn with `--resume <session_id>`; every role keeps its own session.

## Result

Read `agent_message`. `--disable-fallback` keeps **seat fidelity**: the answer comes from this seat, or `success` is false. On failure, report `status` and the telling stderr lines, and leave the seat unanswered.
