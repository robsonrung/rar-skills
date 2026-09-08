# Runtime and Result Contract

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Runtime Compatibility

1. Check whether `codex` CLI is available.
2. If available, execute this skill normally.
3. If unavailable, the script automatically falls back to the claude-runner skill (`run_claude.py`) and reports the provider switch (`fallback_from`, `fallback_reason`); runner provenance fields stay mandatory in the envelope. The fallback invocation always passes `--disable-fallback`, so the codex ⇄ claude pair can never loop.
4. If `--disable-fallback` is set, `--resume`/`--resume-last` is requested (Codex sessions cannot be resumed by another runner), or no fallback runner is found, the script exits non-zero with `return_code` -2 and a clear prerequisite message.

This upholds **seat fidelity**: the Codex seat's output is only ever Codex's, or the seat is reported absent — a claude fallback is always labeled via `fallback_from`/`fallback_reason`, never passed off as Codex.

The broader cross-runner probe chain (codex -> qwen -> kimi -> gemini -> claude) is a contract owned by the runner skills that implement it (see the claude-runner skill's SKILL.md for its own fallback order); this wrapper implements only the codex -> claude leg.


## Security Model

This skill invokes the local Codex CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Codex reads during the run may be sent to OpenAI according to the local Codex CLI configuration. The wrapper never passes `--full-auto` unless the flag is explicitly given. Analysis roles (every role except `implementer`) default to the Codex read-only sandbox; pass `--allow-write`, an explicit `--sandbox`, or `--full-auto` to opt out. Use `--full-auto` only for a user approved unattended run.


## Output Envelope

The required key contract is shared — see `shared/references/runner-common.md`. Envelopes also include execution metadata (command, working directory, role, sandbox, and related fields). Codex-specific extensions:

- `agent_message` — the clean final answer from Codex (captured via `--output-last-message`), free of the activity transcript in `stdout`.
- `session_id` — the Codex session id when detectable, so the run can be continued with `--resume <id>` (or reopened interactively with `codex resume <id>`).
- Current headless output does not expose a serving-model identifier. The wrapper records a forwarded model as `configured_model` and marks `model_receipt.status` `unverified` unless a future native receipt supplies the identifier.


## Prerequisites

- Codex CLI installed and in PATH
- Codex CLI authenticated
