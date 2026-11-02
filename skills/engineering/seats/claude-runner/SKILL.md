---
name: claude-runner
description: Run a prompt on a Claude model through the local Claude CLI. Use when the host cannot run the selected Claude model natively, or the user asks for the Claude CLI.
---

# Claude Runner

Run one prompt on a Claude model with the local `claude` CLI. A host that offers the model natively (a Claude Code subagent, a T3 Code provider) runs it there instead.

## Run

```bash
claude -p "<prompt>" --model <model> --effort <effort> --output-format json
```

- Run it from the repository, or pass the brief through stdin for a long prompt: `claude -p --model … < brief.md`.
- The implementer adds `--permission-mode acceptEdits`. Every other role runs read-only: add `--permission-mode plan --tools Read,Glob,Grep`.
- Run a long call in the host's background shell and read its output when it finishes.
- `claude --help` lists the rest.

## Continue

The JSON result's `session_id` is that role's context. Send the role's next turn with `--resume <session_id>`; every role keeps its own session.

## Result

Read `result`. Keep **seat fidelity**: confirm `modelUsage` names the requested model, and never pass `--fallback-model`. A failed call, `is_error: true`, or another model means the seat is unanswered; report the telling stderr lines.
