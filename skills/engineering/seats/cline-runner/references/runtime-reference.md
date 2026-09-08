# Runtime and Result Contract

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Named seats

| `--seat` | Pinned model | Envelope |
| --- | --- | --- |
| `muse` | `meta/muse-spark-1.3` | `runner=muse`, `effective_runner=cline`, `effective_provider=meta` |
| `minimax` | `minimax/minimax-m2.7` | `runner=minimax`, `effective_provider=minimax` |

`--seat` pins the seat's model and labels the envelope with the seat name; an explicit `--model` still wins. The pins live in `CLINE_SEATS` in `scripts/run_cline.py`, mirrored by `shared/references/model-roster.md` and the seat table in `shared/scripts/discover_runners.py` — change all three together. Muse access on OpenRouter is limited to users in the United States. Two Cline-backed seats in the same run must each get their own `--data-dir` or `--lane`; Cline state is shared otherwise.


## Default Model

None forced. Cline uses whichever `provider/model` the local `cline auth` last configured (inspect with `cline config` interactively, or `cat ~/.cline/data/settings/providers.json`). Pass `--model provider/model-id` to pick a specific model for a run — e.g. `--model anthropic/claude-sonnet-5`, `--model openai/gpt-5.1`. Pass `--provider` to select an authenticated provider id (`cline`, `cline-pass`, `openrouter`, or whatever `cline auth` set up) independently of the model string.

**Model ids are catalog-specific per provider.** The vendor prefix in `vendor/model` is each provider's own catalog slug, and providers disagree: OpenRouter lists Z.AI's GLM as `z-ai/glm-5.3-flash`, while the cline gateway lists the same model as `zai/glm-5.3-flash`. An id from the wrong catalog fails the run with a native model-not-found error. Headless runs route through cline's persisted `lastUsedProvider` unless `--provider` overrides it — pick the id that matches the provider that will actually serve the run. Seat shims can pass `main()` a `default_model_by_provider` map to automate this.


## Security Model

This skill invokes the local Cline CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Cline reads or writes during the run may be sent to the configured provider. The wrapper exposes three tool modes (reported on the envelope as `tool_mode`):

- **`act`** — full toolset, auto-approved. The default with no role, for the `implementer` role, and with `--allow-write`.
- **`plan`** — Cline plan mode with tools auto-approved (`--plan --auto-approve true`): the **read-only analysis boundary** and the default for analysis roles (every role except `implementer`), also forced by `--restrict-tools`. Plan mode's toolset has no file-editing tool, and write actions (including shell redirection and file-creating commands) are blocked at the policy layer, while file reads, search, and read-only commands run headlessly (verified: a plan-mode seat asked to create files reported the edit tool absent and the writes blocked, and the target directory stayed empty). This is a real enforcement boundary, not a prompt overlay — and unlike the old `--auto-approve false` default, the seat can actually read code to verify claims.
- **`no_tools`** — native `--auto-approve false`, forced by `--no-tools`: every tool call (including reads) fails cleanly with an explicit approval error instead of running (verified — the model receives `"Tool approval requires an interactive session, but this session is non-interactive."` and continues without touching the filesystem). Use for clean-room seats that must answer from the prompt alone. Overrides `--restrict-tools`.

**`--model` mutates the user's persisted Cline config.** Passing `--model` (even an invalid one) rewrites the selected provider's `model` field in `~/.cline/data/settings/providers.json` as a side effect — the _next interactive_ `cline` session on this machine will pick up whatever model this runner last requested. For automated/scripted runs where that persistence is unwanted, pass `--data-dir <path>` to isolate state into a scratch directory instead of touching `~/.cline` (note: a fresh data dir has no authenticated providers, so auth must be provisioned there). The wrapper cannot auto-isolate without breaking auth, so when a run forwards `--model` without `--data-dir` it sets `provider_config_mutated: true` on the envelope to make the side effect visible.


## Concurrent Cline lanes

Two Cline-backed runs can execute concurrently **only** with separate authenticated state directories — a lane fixes provider/model/state and holds a bounded file-lock slot for the native call, avoiding both Cline's `lastUsedProvider` race and global model mutation. The built-in `kimi` and `glm` lane names remain provisionable (`cline auth --data-dir ~/.cline/lanes/kimi`, then `--lane kimi`) for anyone driving `cline` directly, but note the **Kimi and GLM seat shims no longer route through Cline** — they pin their models through `pi-runner` on OpenRouter and need no lanes.

A lane with missing provider state fails explicitly as `status: lane_unavailable`; it never falls back to the shared `~/.cline` state. Built-ins that select the same provider share a two-slot credential pool, so a lane pair can run in parallel but the runner cannot fan out without bound. `--lane-file` remains available for custom names, nonstandard state paths, or a stricter `credential_pool`/rate limit; the JSON contains paths and pool names, never keys. Lanes are opt-in for backward compatibility: runs without `--lane` retain the existing behavior and must not be launched in parallel when they share Cline state.


## Output Envelope

The required key contract is shared — see `shared/references/runner-common.md`. Cline-specific extensions: `agent_message` (the final answer text, extracted from the terminal `run_result` event, or trimmed stdout in `text` mode), `finish_reason` (Cline's native `completed`/`error`/etc.), `native_model_id`/`native_provider` (the model that actually answered, read back from the stream — useful when `--model` was omitted and produces a verified model receipt), `native_return_code` (the raw process exit code before return-code normalization), `tool_mode` (`act`/`plan`/`no_tools` — see Security Model; `restrict_tools` stays as the boolean `tool_mode != "act"` for backward compatibility), `thinking` (the reasoning-effort level forwarded, when set), `provider_config_mutated` (true when `--model` was forwarded without `--data-dir` — see Security Model), and `session_id` (recovered best-effort from `cline history`, not from the stream itself; can be null under concurrent use — see Gotchas).

With `--output-file` set, the `--json` stdout pointer is `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` so an orchestrator can see which seat answered without opening the file.


## Gotchas

- **`--model` persists globally.** See Security Model — every `--model` invocation rewrites `~/.cline/data/settings/providers.json` for the requested provider, including on a failed run with an invalid model string. Use `--data-dir` for automated runs to avoid surprising the user's next interactive `cline` session.
- **Do not share an unisolated Cline state.** Parallel Kimi/GLM calls without lanes can race on provider/model selection. Configure separate, authenticated lane state directories and an appropriate pool limit before parallelizing them.
- **No session id in the stream.** Cline's `--json` output never includes a `sessionId`/`session_id` field (the `agentId`/`taskId` in `hook_event` lines are different, per-run identifiers, not the resumable session id). The wrapper cross-references `cline history --json` by cwd + start time; this is best-effort and can miss under heavy concurrent use of the same working directory.
- **Model ids don't transfer between providers.** `z-ai/glm-5.3-flash` (OpenRouter) and `zai/glm-5.3-flash` (cline gateway) are the same model under different catalog slugs; the wrong one fails the run with a native model-not-found error against the serving provider. Check `lastUsedProvider` in `~/.cline/data/settings/providers.json` when a "valid" id mysteriously fails.
- **`--no-tools` fails tool calls, it doesn't skip them.** The model sees an explicit approval error and keeps reasoning — expect it to explain what it couldn't do rather than silently omitting the attempt. This is a real boundary (verified: no hang, no silent bypass). The injected constraint text tells the seat tool calls will fail so it answers from the prompt instead of burning its retry budget hunting for a working tool path — keep prompts for `--no-tools` runs self-contained.
- **`--output-schema` has two layers.** Cline receives the schema as a prompt because it has no native schema switch; afterward this wrapper validates the final terminal response locally. The model's native exit code alone never makes a schema-invalid answer successful.
- Cline's non-JSON native error lines (e.g. `hook dispatch failed: ...`) can appear on stderr even for a run whose `agent_message` and `finishReason` are otherwise fine — treat `success`/`finish_reason` as authoritative over stray stderr noise.


## Prerequisites

- `cline` CLI installed and in `PATH` (`npm install -g cline`)
- At least one provider authenticated via `cline auth`

This is **seat fidelity** for a no-fallback runner: if `cline` is missing or auth fails, the seat is blocked and reported absent, never substituted by another model. The envelope returns `success=false` with remediation guidance in `stderr`. A missing CLI maps to `return_code=-2` and `status=seat_unavailable`; auth or model failures surface as Cline's own nonzero exit with `finish_reason` set to the native reason — treat any `success=false` as a blocked seat.
