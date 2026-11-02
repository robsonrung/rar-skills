---
name: grok-runner
description: Run a prompt on a Grok model through the local Grok CLI. Use when the host cannot run the selected Grok model natively, or the user asks for the Grok CLI.
---

# Grok Runner

Run one prompt on Grok with the local `grok` CLI. A host that offers the model natively runs it there instead.

## Run

```bash
grok -p "<prompt>" --model <model> --reasoning-effort <effort> --output-format json \
  --permission-mode plan
```

- Effort goes up to `high`. The implementer drops `--permission-mode plan` and uses `acceptEdits`; every other role stays in plan mode.
- Run it from the repository. Run a long call in the host's background shell and read its output when it finishes.
- `grok --help` lists the rest.

## Continue

The JSON result's `sessionId` is that role's context. Send the role's next turn with `--resume <sessionId>`; every role keeps its own session.

## Result

Read `text`. Keep **seat fidelity**: confirm `modelUsage` names the requested model. A failed call or another model means the seat is unanswered; report the telling stderr lines.
