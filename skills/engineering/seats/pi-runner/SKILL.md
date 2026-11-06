---
name: pi-runner
description: Run a prompt on a gateway model (Kimi, GLM, Qwen, Gemma, Minimax, Mistral, DeepSeek) through the local Pi CLI. Use when the host cannot run the selected model natively, or the user asks for Pi.
---

# Pi Runner

In T3 Code, run all model calls as internal subagents under `shared/references/host-model-execution.md`. If the approved route is unavailable, report it. Do not execute this runner in T3 Code.


Run one prompt through the local `pi` CLI, which reaches models behind a gateway such as OpenRouter. A host that offers the model natively (a T3 Code Pi provider) runs it there instead.

## Run

```bash
python3 <skill-dir>/scripts/run_pi.py "<prompt>" --seat <seat> --thinking <effort> \
  --session <role-session-file> --json
```

- `--seat` pins a named seat's model from `shared/model-routing.json`; for any other model, pass `--provider <gateway> --model <model>`. Omit `--thinking` for a model without selectable effort.
- Seats marked zero-retention in `shared/model-routing.json` get strict privacy routing automatically; `--provider-routing '<json>'` sets it explicitly.
- `--no-tools` answers from the prompt alone; `--restrict-tools` reads files only and is the default for analysis roles; `--role implementer`, or no role, gets full tools.
- `--prompt-file <file>` replaces the inline prompt for a long brief; `--working-dir <path>` sets the repository.
- Credentials come from `OPENROUTER_API_KEY` or Pi's auth store; missing ones return `status: auth_missing`.
- `--background` returns a job id for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).
- `--help` lists the rest, including browser work (`--tool-policy browser`) and images (`--image-file`).

## Continue

Pi returns no session id: the file passed to `--session` is the role's context. Give every role its own file from its first call, and pass that same file on each later turn.

## Result

Read `agent_message`. This runner never falls back, which keeps **seat fidelity**: the answer comes from this seat, or `success` is false. On failure, report `status` and the telling stderr lines, and leave the seat unanswered.
