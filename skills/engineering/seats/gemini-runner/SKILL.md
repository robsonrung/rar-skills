---
name: gemini-runner
description: Run a prompt on a Gemini model through the local Antigravity CLI (`agy`). Use when the host cannot run the selected Gemini model natively, or the user asks for Antigravity.
---

# Gemini Runner

Run one prompt on Gemini through the local Antigravity CLI, `agy`. A host that offers the model natively (a T3 Code Antigravity provider) runs it there instead.

## Run

```bash
python3 <skill-dir>/scripts/run_gemini.py "<prompt>" --model <model> --disable-fallback --json
```

- `agy` serves the model chosen in its own settings; `--model` only labels the envelope. Select the seat's model in `agy` before the run. Effort is not selectable.
- `--prompt-file <file>` replaces the inline prompt for a long brief; `--working-dir <path>` sets the repository.
- `--role implementer`, or no role, can edit files; every other role is told to stay read-only.
- `--background` returns a job id for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).
- `--help` lists the rest.

## Continue

`agy` exposes no session id. `--agy-continue` resumes its most recent conversation, so it holds a role's context only while that role is the sole Gemini seat in flight. Otherwise, hand the role its earlier turns as text with `--session-file <file>`.

## Result

Read `agent_message`. `--disable-fallback` keeps **seat fidelity**: the answer comes from this seat, or `success` is false. On failure, report `status` and the telling stderr lines, and leave the seat unanswered.
