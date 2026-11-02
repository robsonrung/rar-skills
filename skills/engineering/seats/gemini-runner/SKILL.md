---
name: gemini-runner
description: Run a prompt on a Gemini model through the local Antigravity CLI (`agy`). Use when the host cannot run the selected Gemini model natively, or the user asks for Antigravity.
---

# Gemini Runner

Run one prompt on Gemini with the local Antigravity CLI, `agy`. A host that offers the model natively (a T3 Code Antigravity provider) runs it there instead.

## Run

```bash
agy --print "<prompt>" --model <model> --effort <effort> --mode plan --output-format json
```

- Every role except the implementer keeps `--mode plan`; the implementer uses `--mode accept-edits`.
- `agy models` lists the model names it accepts; `--print-timeout <duration>` bounds a call.
- Run a long call in the host's background shell and read its output when it finishes.
- `agy --help` lists the rest.

## Continue

Send the role's next turn with `--conversation <id>` when the result carries its conversation ID. Without one, `--continue` resumes only the most recent conversation, which is the role's own only while it is the sole Gemini seat in flight; otherwise resend the role's earlier turns in the prompt.

## Result

Read the answer from the JSON result. Keep **seat fidelity**: the call must run the requested model. A failed or empty call means the seat is unanswered; report the telling stderr lines.
