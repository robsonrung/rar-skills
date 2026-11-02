---
name: codex-runner
description: Run a prompt on a GPT model (Astra, Sol, Terra) through the local Codex CLI. Use when the host cannot run the selected GPT model natively, or the user asks for the Codex CLI.
---

# Codex Runner

Run one prompt on a GPT model with the local `codex` CLI. A host that offers the model natively (a Codex subagent, a T3 Code provider) runs it there instead.

## Run

```bash
codex exec --model <model> -c model_reasoning_effort='"<effort>"' --sandbox read-only \
  --json --output-last-message <answer-file> -C <repository> "<prompt>"
```

- The implementer uses `--sandbox workspace-write`; every other role keeps `--sandbox read-only`.
- Pass `-` as the prompt to read a long brief from stdin. Outside a Git repository, add `--skip-git-repo-check`.
- Run a long call in the host's background shell and read its output when it finishes.
- `codex exec --help` lists the rest.

## Continue

The `thread.started` event's `thread_id` is that role's context. Send the role's next turn with `codex exec resume <thread_id> "<prompt>"`, repeating the model, effort, and `-c sandbox_mode='"read-only"'`; every role keeps its own thread.

## Result

Read the answer file. Keep **seat fidelity**: the call must run the requested model and effort. A failed call or an empty answer means the seat is unanswered; report the telling stderr lines.
