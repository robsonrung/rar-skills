---
name: muse-runner
description: Run a prompt on Muse Wonder Full through the local Muse CLI. Use when the host cannot run Muse natively, or for an approved optional implementation route.
---

# Muse Runner

Run one bounded turn on Muse Wonder Full through the local `muse` CLI. A host that offers the model natively (a T3 Code Muse provider) runs it there instead.

## Run

First run `--preflight --json`: it checks the workspace configuration and resolves the model profile without a model call.

```bash
python3 <skill-dir>/scripts/run_muse.py "<prompt>" --effort <effort> --json
```

- Muse Wonder Full is the default model; effort defaults to `high`.
- The turn reads files only. `--allow-write` lets it edit; `--allow-shell` adds sandboxed commands, such as tests, on top of `--allow-write`. With shell allowed, tell Muse in the prompt to stay a single worker.
- `--timeout` (default 300 seconds) and `--max-steps` (default 20) bound the turn; running out of steps is a failed result.
- `--background` returns a job id for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).
- On 16 October 2026 the user confirmed zero data retention for their current Muse Code subscription; another account needs its own confirmation. Share source only within the user's approved scope.

## Continue

Muse keeps no session, so every turn starts fresh. Give each later turn the full task context plus what the earlier turns produced.

## Result

Read `agent_message`. This runner never falls back, which keeps **seat fidelity**: the answer comes from this seat, or `success` is false. A finished turn does not mean its tests passed. On failure, report `status` and the telling stderr lines, and leave the seat unanswered.
