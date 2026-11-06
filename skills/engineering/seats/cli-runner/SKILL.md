---
name: cli-runner
description: "Run a prompt on a Claude, GPT (Astra, Sol, Terra), Gemini, or Grok model through its local CLI: claude, codex, agy (Antigravity), or grok. Use for an explicit Claude, Codex, Gemini, Antigravity, or Grok CLI request, a route whose model the host cannot run natively, or an approved external fallback."
---

# CLI Runner

In T3 Code, run all model calls as internal subagents under `shared/references/host-model-execution.md`. If the approved route is unavailable, report it. Do not execute this runner in T3 Code.


Run one prompt on one model through its vendor CLI. A host that runs the model natively takes precedence (`shared/references/host-model-execution.md`). Seat fidelity, read-only roles, session discipline, and long calls follow `shared/references/runner-common.md`. Run from the repository; `<cli> --help` lists the rest.

## Claude: `claude`

```bash
claude -p "<prompt>" --model <model> --effort <effort> --output-format json \
  --permission-mode plan --tools Read,Glob,Grep
```

- The implementer replaces the last line with `--permission-mode acceptEdits`.
- For a long brief, pipe it through stdin: `claude -p --model … < brief.md`.
- **Continue:** the result's `session_id` is the role's context; send its next turn with `--resume <session_id>`.
- **Result:** read `result`. Confirm `modelUsage` names the requested model, and never pass `--fallback-model`. `is_error: true` or another model leaves the seat unanswered.

## Codex: `codex`

```bash
codex exec --model <model> -c model_reasoning_effort='"<effort>"' --sandbox read-only \
  --json --output-last-message <answer-file> -C <repository> "<prompt>"
```

- The implementer uses `--sandbox workspace-write`.
- Pass `-` as the prompt to read a long brief from stdin. Outside a Git repository, add `--skip-git-repo-check`.
- **Continue:** the `thread.started` event's `thread_id` is the role's context; send its next turn with `codex exec resume <thread_id> "<prompt>"`, repeating the model, effort, and `-c sandbox_mode='"read-only"'`.
- **Result:** read the answer file. An empty answer leaves the seat unanswered.

## Gemini: `agy` (Antigravity)

```bash
agy --print "<prompt>" --model <model> [--effort <effort>] --mode plan --output-format json --print-timeout <duration>
```

- The implementer uses `--mode accept-edits`. Pass `--effort` only when the route sets one; `agy models` lists accepted names.
- **Result:** the JSON has `conversation_id`, `status`, `response`, and `error`. The exit code is 0 even on failure, so the call succeeded only when `status` is `SUCCESS` and `response` is non-empty.
- **Receipt:** the output names no serving model. `agy` rejects an unknown model instead of substituting one, so a Gemini result counts as configured, not verified. Report it that way, and never run a route that requires a verified receipt on `agy`.
- **Continue:** `--conversation <conversation_id>` from the first result. Never `--continue`, which picks the most recent conversation.

## Grok: `grok`

```bash
grok -p "<prompt>" --model <model> --reasoning-effort <effort> --output-format json \
  --permission-mode plan
```

- Effort goes up to `high`. The implementer uses `--permission-mode acceptEdits`.
- **Continue:** the result's `sessionId` is the role's context; send its next turn with `--resume <sessionId>`.
- **Result:** read `text`. Confirm `modelUsage` names the requested model.

A failed call, or a call that ran another model or effort, leaves the seat unanswered; report the telling stderr lines.
