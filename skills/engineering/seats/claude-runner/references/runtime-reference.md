# Runtime and Result Contract

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Runtime Compatibility

Fallback: codex-runner only (invoked with `--disable-fallback`; the chain does not continue to qwen, kimi, or gemini). With `--disable-fallback`, fail fast with a prerequisite message instead of routing.

1. Check whether `claude` CLI is available.
2. If available, execute this skill normally.
3. If unavailable and `codex` is available, route to `$codex-runner` as fallback and report the provider switch (`fallback_from`). The fallback invocation always passes `--disable-fallback`, so the claude ⇄ codex pair can never loop.
4. If neither is available, stop with a clear prerequisite message.

This upholds **seat fidelity**: the Claude seat's output is only ever Claude's, or the seat is reported absent — a codex fallback is always labeled via `fallback_from`, never passed off as Claude.


## Security Model

This skill invokes the local Claude CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Claude reads during the run may be sent to Anthropic according to the local Claude CLI configuration. Permission checks stay enabled. Analysis roles (every role except `implementer`) default to Claude planning mode (read-only); pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role.


## Output Envelope

The required key contract is shared — see `shared/references/runner-common.md`. Claude-specific envelope extensions:

- `agent_message` — the clean final answer. With `--output-format json`/`stream-json` it is parsed from the result event; with `text` it is the trimmed stdout.
- `session_id` — the Claude session id (available with `--output-format json`/`stream-json`), usable for `--resume <id>` follow-ups.
- Current print-mode results do not expose a serving-model identifier. The wrapper records a forwarded model as `configured_model` and marks `model_receipt.status` `unverified` unless a future native receipt supplies the identifier.


## Prerequisites

- Claude CLI installed and in PATH
- Claude CLI authenticated
