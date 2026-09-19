---
name: pi-runner
description: Execute an external Pi CLI prompt with a provider and model pinned per call. Use only for an explicit Pi CLI request, a selected Pi provider route unavailable as native host delegation, or an approved external fallback, including Kimi, GLM, Qwen, and Gemma seats.
---

# Pi Runner

Execute prompts through the Pi coding agent CLI (`pi`) in non-interactive print mode. Pi pins the provider and model per invocation — `--provider openrouter --model vendor/model` with credentials resolved from the provider's env var or Pi's own auth store — so there is no shared mutable provider state between runs, no lane isolation to manage, and no fallback chain to disable. It also serves the collection's named OpenRouter seats through `--seat`.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected provider model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. A host skill descriptor does not dispatch a native model.

## Named seats

Named seats and their exact model IDs live in `shared/model-routing.json`.
`--seat` reads those pins and labels the envelope with the seat name. An explicit
`--model` is a per-call selection and must match the approved plan when one
exists. Change maintained pins only in the central file. A missing CLI or key
reports `status: seat_unavailable`; there is no fallback to another seat.

## Default Provider

- `openrouter` — credentials from `OPENROUTER_API_KEY` (or Pi's auth store via an interactive `/login`). Override with `--provider`; Pi ships built-in catalogs for 15+ providers.
- Model ids absent from Pi's bundled catalog are passed through to the provider unchanged — a newer OpenRouter id than Pi's release knows about still works.

## Prerequisites

- `pi` CLI installed and in `PATH` (`npm install -g @mariozechner/pi-coding-agent`)
- The serving provider's API key in the environment (`OPENROUTER_API_KEY` for the default provider)

## Hermetic runs

Every run disables Pi's extension, skill, prompt-template, and theme discovery and its AGENTS.md/CLAUDE.md context-file loading. The prompt (plus `--prompt-file` material) is the seat's entire input surface; workspace context a seat should see must be passed in explicitly.

## Tool modes

- **act** (write roles, `--allow-write`, or no role): Pi's full built-in toolset (read, bash, edit, write).
- **restricted** (`--restrict-tools`, default for analysis roles): only the file-reading tool is enabled. Unlike Cline plan mode there is no search tool and no read-only shell in this mode.
- **no_tools** (`--no-tools`): native tool disable; the seat answers from the prompt alone. Strongest isolation; this is what poll-mode council seats use.

## Shared Wrapper Reference

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas follow `shared/references/runner-common.md`. The envelope reports `runner=pi` (or the `--seat` name), `effective_runner=pi`, and `effective_provider` inferred from the model id's vendor prefix (`vendor/model` gives `vendor`). Its terminal stream can supply `native_model_id`, which produces a verified model receipt.

## Usage

```bash
python3 .agents/skills/pi-runner/scripts/run_pi.py "your prompt here" --seat kimi
```

## Examples

```bash
python3 .agents/skills/pi-runner/scripts/run_pi.py "Summarize this module" --seat glm
python3 .agents/skills/pi-runner/scripts/run_pi.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer --seat kimi --json
python3 .agents/skills/pi-runner/scripts/run_pi.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer --seat kimi
python3 .agents/skills/pi-runner/scripts/run_pi.py "Answer from the brief only" --no-tools --json --seat glm
```

## Gotchas

- **Missing credentials exit 0.** With no key for the selected provider, `pi` prints a "Use /login ..." hint and exits cleanly without producing agent events. The wrapper detects this and reports `success: false`, `status: auth_missing`, `auth_ok: false` — never trust Pi's bare exit code.
- **No native schema switch.** `--output-schema` appends the contract to the prompt and enforces it locally: the run fails with `status: malformed_output` unless the final answer is exactly one schema-valid JSON value.
- **Delta stream is compacted.** Pi's `--mode json` emits per-token `message_update` lines; the wrapper drops them from the stored `stdout` and keeps the terminal events, which carry the complete message and the serving receipt (provider, model, usage, stopReason). Read `agent_message`, not `stdout`.
- **No native timeout flag.** The wrapper's `--timeout` is enforced at the subprocess level and reports `return_code -1` on expiry.
- **Session resume** uses native `--session <id|path>`; `--no-session-persistence`/`--ephemeral` map to native `--no-session`. Pi's `--mode json` stream does not announce a session id, so the envelope's `session_id` only reflects what the caller passed in.

## Load by need

- [references/continuation.md](references/continuation.md): when a role needs another Pi turn or a workflow needs a text handoff.
