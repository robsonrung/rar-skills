---
name: pi-runner
description: Execute prompts using the Pi coding agent CLI in headless print mode, with the provider and model pinned per invocation (default provider openrouter). Use when users explicitly request Pi execution, when a workflow needs a seat on an arbitrary OpenRouter model without shared provider state, or when a workflow names the Kimi, GLM, Qwen, or Gemma seat — each is `--seat <name>` on this runner.
---

# Pi Runner

Execute prompts through the Pi coding agent CLI (`pi`) in non-interactive print mode. Pi pins the provider and model per invocation — `--provider openrouter --model vendor/model` with credentials resolved from the provider's env var or Pi's own auth store — so there is no shared mutable provider state between runs, no lane isolation to manage, and no fallback chain to disable. It also serves the collection's named OpenRouter seats through `--seat`.

## Named seats

| `--seat` | Pinned model | Envelope |
| --- | --- | --- |
| `kimi` | `moonshotai/kimi-k3` | `runner=kimi`, `effective_runner=pi`, `effective_provider=moonshotai` |
| `glm` | `z-ai/glm-5.3-flash` | `runner=glm`, `effective_provider=z-ai` |
| `qwen` | `qwen/qwen3.8-max` | `runner=qwen`, `effective_provider=qwen` |
| `gemma` | `google/gemma-4-31b-it` | `runner=gemma`, `effective_provider=google` |

`--seat` pins the seat's model and labels the envelope with the seat name; an explicit `--model` still wins, so a seat can be tried against a newer id without editing the table. The pins live in `PI_SEATS` in `scripts/run_pi.py`, mirrored by `shared/references/model-roster.md` and the seat table in `shared/scripts/discover_runners.py` — change all three together. A missing `pi` CLI or key reports `status: seat_unavailable` for the named seat; there is no fallback to another seat.

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

Supported options, roles, the `--json` output envelope key contract, return codes, and gotchas follow the shared wrapper family — read [`shared/references/runner-common.md`](../shared/references/runner-common.md). The envelope reports `runner=pi` (or the `--seat` name), `effective_runner=pi`, and `effective_provider` inferred from the model id's vendor prefix (`moonshotai/kimi-k3` → `moonshotai`); `native_provider` carries the serving gateway (`openrouter`) from the stream receipt.

## Usage

```bash
python3 .agents/skills/pi-runner/scripts/run_pi.py "your prompt here" --model moonshotai/kimi-k3
```

## Examples

```bash
python3 .agents/skills/pi-runner/scripts/run_pi.py "Summarize this module" --seat glm
python3 .agents/skills/pi-runner/scripts/run_pi.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer --seat kimi --json
python3 .agents/skills/pi-runner/scripts/run_pi.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer --model moonshotai/kimi-k3
python3 .agents/skills/pi-runner/scripts/run_pi.py "Answer from the brief only" --no-tools --json --model z-ai/glm-5.3-flash
```

## Gotchas

- **Missing credentials exit 0.** With no key for the selected provider, `pi` prints a "Use /login ..." hint and exits cleanly without producing agent events. The wrapper detects this and reports `success: false`, `status: auth_missing`, `auth_ok: false` — never trust Pi's bare exit code.
- **No native schema switch.** `--output-schema` appends the contract to the prompt and enforces it locally: the run fails with `status: malformed_output` unless the final answer is exactly one schema-valid JSON value.
- **Delta stream is compacted.** Pi's `--mode json` emits per-token `message_update` lines; the wrapper drops them from the stored `stdout` and keeps the terminal events, which carry the complete message and the serving receipt (provider, model, usage, stopReason). Read `agent_message`, not `stdout`.
- **No native timeout flag.** The wrapper's `--timeout` is enforced at the subprocess level and reports `return_code -1` on expiry.
- **Session resume** uses native `--session <id|path>`; `--no-session-persistence`/`--ephemeral` map to native `--no-session`. Pi's `--mode json` stream does not announce a session id, so the envelope's `session_id` only reflects what the caller passed in.
