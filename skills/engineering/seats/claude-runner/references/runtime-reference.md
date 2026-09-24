# Runtime and Result Contract

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Runtime Compatibility

Fallback: codex-runner only (invoked with `--disable-fallback`; the chain does not continue to qwen, kimi, or gemini). With `--disable-fallback`, fail fast with a prerequisite message instead of routing. Restricted profiles, any explicit tool profile, explicit write permission, and native turn or cost limits also block fallback because the sibling runner has no equivalent contract. The elapsed time limit is forwarded on permitted fallbacks.

1. Check whether `claude` CLI is available.
2. If available, run local preflight with the resolved CLI, working directory, and child environment after token injection. Record the safe report in `preflight` on both success and failure. A blocked report stops before a print request and cannot trigger fallback. Unknown authentication visibility stays unknown. The local check does not prove live authentication or model entitlement.
3. If unavailable and `codex` is available, route to `$codex-runner` as fallback and report the provider switch (`fallback_from`). The fallback invocation always passes `--disable-fallback`, so the claude ⇄ codex pair can never loop.
4. If neither is available, stop with a clear prerequisite message.

This upholds **seat fidelity**: the Claude seat's output is only ever Claude's, or the seat is reported absent — a codex fallback is always labeled via `fallback_from`, never passed off as Claude.


Direct calls may omit model or effort and use CLI runtime defaults. The wrapper does not fill either omission. Preflight leaves omitted controls unknown; an explicit model still receives its recorded version check. Approved workflows must supply their exact selected model and effort.

## Security Model

This skill invokes the local Claude CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Claude reads during the run may be sent to Anthropic according to the local Claude CLI configuration. Permission checks stay enabled. Analysis roles (every role except `implementer`) default to `repo_read_only`, which allows only Read, Glob, and Grep. Restricted profiles disable customizations and use strict empty MCP configuration. `no_tools` removes all tools. Pass `--allow-write` or `--tool-profile write` for normal write permissions, or `--restrict-tools` to force read tools without a role. These profiles control available tools; they do not provide an operating system filesystem sandbox.


## Output Envelope

The required key contract is shared — see `shared/references/runner-common.md`. Claude-specific envelope extensions:

- `agent_message` — the clean final answer. With `--output-format json`/`stream-json` it is parsed from the result event; with `text` it is the trimmed stdout.
- `session_id` — the Claude session id (available with `--output-format json`/`stream-json`), usable for `--resume <id>` follow-ups.
Primary `assistant.message.model` events in JSON arrays or streams supply serving evidence. Events with `parent_tool_use_id` identify auxiliary work. Synthetic model IDs, initialization model labels, requested labels, and `modelUsage` alone supply no serving proof. Missing evidence keeps `effective_model` null. One observed primary ID gives a verified serving receipt; `model_matches_requested` separately compares an exact `claude-...` request. Alias matches stay unknown. An exact mismatch or multiple primary IDs fails the result.

| Field | Meaning |
| --- | --- |
| `primary_model_ids` | Unique observed primary serving IDs |
| `auxiliary_model_ids` | Serving IDs observed in child assistant events |
| `model_matches_requested` | Exact match, mismatch, or null when not established |
| `model_identity_error` | Mismatch or multiple primary IDs, otherwise null |
| `model_usage` | Raw native per-model usage breakdown |
| `auxiliary_model_usage` | Usage labels outside the observed primary ID set; not independent serving proof |
| `preflight` | Safe local compatibility, configuration, installation, and auth visibility evidence |
| `print_invocation_started` | False before any print launch attempt; true immediately before the print subprocess or capture call |
| `tool_profile` | Selected tool authority |
| `tool_profile_receipt` | Startup tool and MCP evidence; verified only when both are reported and satisfy the profile |
| `limits` | Elapsed time, native turns, reported USD cap, and advisory response length |

The cost limit is a threshold for CLI reported spend, not a guaranteed invoice ceiling. The terminal `total_cost_usd` supplies the total cost once. Do not add the per-model usage breakdown to that total. Missing measurements stay unknown. Startup tools outside the allowlist or nonempty MCP servers fail the result. Missing startup evidence stays unverified. `stdout` and any event log retain the raw events.

Prompts remain command arguments. Stdin transport requires a shared capture API change and is deferred.

For a confirmed `preflight_blocked` result, `print_invocation_started` is false, `session_id` is null, and `stdout` is empty. When the local preflight report confirms zero provider calls, token, cache, reasoning, and reported cost metrics are zero; `duration_ms` measures the elapsed preflight time and `metrics_complete` is true. A preflight exception without that evidence leaves usage unknown.

`preflight.evidence.provider_calls` covers only local preflight checks. A normal model call can have that value set to zero and `print_invocation_started` set to true. The latter stays true on an uncertain launch, timeout, or process error. Missing usage after such a failure is never replaced with zeros. Fallback results without the print marker remain unknown.


## Prerequisites

- Claude CLI installed and in PATH
- Claude CLI authenticated
