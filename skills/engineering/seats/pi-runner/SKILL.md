---
name: pi-runner
description: Execute an external Pi CLI prompt with a provider and model pinned per call. Use only for an explicit Pi CLI request, a selected Pi provider route unavailable as native host delegation, or an approved external fallback, including Kimi, GLM, Qwen, and Gemma seats.
---

# Pi Runner

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Execute prompts through Pi (`pi`) in non-interactive mode. Strict request controls use RPC with a startup handshake; legacy calls retain print mode. Pin the gateway and model per invocation with `--provider` and `--model`, or select a central named seat with `--seat`. Credentials come from the gateway environment or Pi auth store. An exact model selection does not constrain inference provider fallback; carry that separate policy through `--provider-routing`.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected provider model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. A host skill descriptor does not dispatch a native model.

## Named seats

Named seats and their exact model IDs live in `shared/model-routing.json`.
`--seat` reads those pins and labels the envelope with the seat name. An explicit
`--model` is a per-call selection and must match the approved plan when one
exists. Change maintained pins only in the central file. A missing CLI or key
reports `status: seat_unavailable`; there is no fallback to another seat.

## Gateway and capabilities

The central runner configuration selects the default gateway. OpenRouter uses
`OPENROUTER_API_KEY` or Pi's auth store. Use `--provider` for an explicitly
selected gateway. A model ID absent from the bundled catalog needs verified
capability metadata; passing the string alone does not prove model access, image
support, tools, or effort control.

Read supported effort and runtime effort from the central model entry. Pass the
selected controllable effort explicitly. GLM accepts `low`, `high`, and `max`;
omission or an unrecognized native value can select `max`. Reject unsupported
values instead of mapping generic `medium` or `xhigh` to it. Models without
selectable reasoning effort keep runtime controlled effort and no invented
level. Capture the serialized setting before using a new route.

## Provider request policy

An approved `provider_routing` object is passed as compact JSON through
`--provider-routing`. For strict OpenRouter routes it contains
`gateway: openrouter`, `zdr: true`, `data_collection: deny`, and
`require_parameters: true`. Include `only` for a selected inference provider
allowlist and `allow_fallbacks` when the plan specifies it. Provider fallback
inside an approved set is separate from fallback to another model. Never remove
privacy controls to recover availability. Strict calls bind the gateway URL
independently of the model registry. A provider label pointed at another URL is
rejected before task content is released.

Use the packaged request enforcement path with configuration scoped to the run.
It must preserve the exact selected policy through every initial, tool, repair,
and resumed request. Unrelated extension discovery stays disabled; do not depend
on a mutable global model registry. Missing enforcement or a wrong gateway blocks
the strict route before repository content is sent. Source sharing metadata alone
is not an enforced request policy.

Strict execution requires the minimum stable Pi version declared by the runtime
adapter or a newer stable release. The request hook must confirm readiness
before task content is sent. The installed
runtime compacts sessions outside its request hook, so strict runs stop before
compaction and wait for the settled event before accepting completion. A full
context needs an approved fresh context packet; it cannot silently summarize
through an unprotected request.

Retain `provider_policy_receipt` with `status: enforced`, `gateway`,
`policy_sha256`, and positive `request_count` only after request enforcement is
observed. Capture synthetic local requests to verify the exact model, reasoning,
provider controls, tools, and image payloads without logging source or secrets.
A missing receipt cannot establish strict route acceptance. Omitted policy keeps
legacy behavior and cannot be reported as strict privacy.

## Prerequisites

- `pi` CLI already installed and in `PATH`; a missing installation is a preparation gap, not permission for a global install
- The serving provider's API key in the environment (`OPENROUTER_API_KEY` for the default provider)

## Hermetic runs

Every run disables unrelated extension, skill, prompt-template, theme, and project instruction discovery. An explicitly packaged request hook for the selected policy is the controlled exception. Pass the role brief, permitted files, driver instructions, and image artifacts explicitly. Tool reads and permitted attachments can extend the input; do not describe the prompt as the entire input when tools are enabled.

## Tool modes

- **act** (write roles, `--allow-write`, or no role): Pi's full built-in toolset (read, bash, edit, write).
- **restricted** (`--restrict-tools`, default for analysis roles): only the file-reading tool is enabled. Unlike Cline plan mode there is no search tool and no read-only shell in this mode.
- **no_tools** (`--no-tools`): native tool disable; the seat answers from the supplied input. This is what poll-mode council seats use.
- **browser** (`--tool-policy browser`): file/image reads and shell access for the selected driver. Pass `--browser-mechanism playwright-cli` or `agent-browser` and `--browser-preflight <file>` with captured readiness evidence. Shell access does not enforce a browser-only sandbox or authorize product repair.

External Pi workers do not inherit host browser tools. For visual work, preflight
model image support, the driver's artifact path, and typed image content through
the adapter with a synthetic image. Use `--image-file <path>` for an explicit
attachment; repeat it for multiple permitted images. A screenshot path in text
is insufficient.
Keep one driver per journey and one isolated session per role. Missing driver,
tool, image, or privacy capability blocks that route.

## Shared Wrapper Reference

Supported options, roles, the `--json` envelope, and return codes follow `shared/references/runner-common.md`. The envelope reports `runner=pi` or the seat name and `effective_runner=pi`. `model_author` describes the vendor; `gateway` describes the API route. `inference_provider` needs actual upstream evidence and remains unknown when absent. The legacy `effective_provider` vendor field does not identify an inference host. A terminal `native_model_id` can produce a client reported model receipt; it is not independent proof of the inference provider. Keep request policy receipts separate from model receipts.

## Usage

Resolve `SKILL_DIR` from the loaded skill and copy exact selections from the run
snapshot. For a model with selectable effort:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_pi.py" --prompt-file <role-brief.md> \
  --seat <selected-seat> --thinking <selected-effort> \
  --session <unique-role-session-file> \
  --provider-routing '<approved-provider-routing-json>' --disable-fallback --json
```

For runtime controlled effort, use the selected model's supported runtime path;
do not invent a `high` value. Omit `--provider-routing` only when the selected
route has no provider policy. Use `--no-tools` for a brief-only role or the
explicitly selected tool policy for file or browser work.

## Gotchas

- **Missing credentials exit 0.** With no key for the selected provider, `pi` prints a "Use /login ..." hint and exits cleanly without producing agent events. The wrapper detects this and reports `success: false`, `status: auth_missing`, `auth_ok: false` — never trust Pi's bare exit code.
- **No native schema switch.** `--output-schema` appends the contract to the prompt and enforces it locally: the run fails with `status: malformed_output` unless the final answer is exactly one schema-valid JSON value.
- **Delta stream is compacted.** Pi's `--mode json` emits per-token `message_update` lines; the wrapper drops them from the stored `stdout` and keeps the terminal events, which carry the complete message and the serving receipt (provider, model, usage, stopReason). Read `agent_message`, not `stdout`.
- **No native timeout flag.** The wrapper's `--timeout` is enforced at the subprocess level and reports `return_code -1` on expiry.
- **Session resume** uses native `--session <id|path>`; `--no-session-persistence`/`--ephemeral` map to native `--no-session`. Pi's `--mode json` stream does not announce a session id, so the envelope's `session_id` only reflects what the caller passed in.

## Load by need

- [references/continuation.md](references/continuation.md): when a role needs another Pi turn or a workflow needs a text handoff.
