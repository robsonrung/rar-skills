# Runtime and Result Contract

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Runtime Compatibility

No fallback chain. If the `grok` CLI is missing, the seat fails fast with `return_code -2`, `status: seat_unavailable`, `fallback_reason: null` — no other installed CLI can produce a real Grok answer, so substituting one would violate **seat fidelity**. `--disable-fallback` is accepted as a no-op for cross-runner parity.


## Security Model

This skill invokes the local `grok` CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Grok reads during the run may be sent to xAI according to the local Grok CLI configuration. Sessions always persist under `~/.grok` — the CLI has no session-persistence opt-out. Analysis roles (every role except `implementer`) default to Grok plan mode (read-only, `--permission-mode plan`); pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role.


## Output Envelope

The required key contract is shared — see `shared/references/runner-common.md`. Grok-specific envelope extensions:

- `agent_message` — the clean final answer. With `--output-format json` it is the payload's `text` field; with `stream-json` it is the concatenated `text` events; with `text` it is the trimmed stdout.
- `session_id` — the Grok session id (available with `json`/`stream-json` output), usable for `--resume <id>` follow-ups.
- `native_model_id` — the model that actually answered, harvested from grok's `modelUsage`. It produces `model_receipt.status: verified` and feeds `effective_model`.
- `reasoning_effort_forwarded` / `effort_clamped` — what `--effort` value was actually sent to grok, and whether the requested level was clamped to the configured adapter limit.
- `structured_output` — the final schema-valid object when `--output-schema` is used. The wrapper checks it locally after Grok's native constraint.


## Prerequisites

- `grok` CLI installed and in PATH
- `grok` CLI authenticated (`grok login`, grok.com account)
