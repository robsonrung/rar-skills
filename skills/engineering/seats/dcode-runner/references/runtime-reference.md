# Runtime and Result Contract

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Runtime Compatibility

When `dcode` is missing and fallback is disabled (or all fallbacks are unavailable), the envelope carries `status: seat_unavailable` and `return_code` -2; council orchestrators must treat that seat as absent. When a fallback runner does produce the output, unavailable fallback seats attempted before it are listed in `fallback_attempts` on the returned envelope.

1. Check whether DeepAgents CLI (`dcode`) is available.
2. If available, run this skill.
3. If unavailable, route through the fallback order `$claude-runner`, `$codex-runner`, `pi-runner --seat qwen`, then `pi-runner --seat kimi`, and report the fallback.
4. Never claim the dcode/DeepAgents seat participated when a fallback provider produced the output.

This is **seat fidelity**: the dcode seat's output is only ever that seat's, or the seat is reported absent — a fallback provider's answer is always labeled via `fallback_from`/`fallback_attempts`, never passed off as dcode.


## Configuration Model

The runner deliberately **does not** select a model, configure providers, or write to `~/.deepagents/`. `dcode` uses whatever default model and credentials the user has already wired up via `/model`, `/auth`, `~/.deepagents/config.toml`, `~/.deepagents/.env`, or a project-local `.env`. `--model` on this wrapper is a request label only and is **not** forwarded to `dcode`. The envelope marks that label unverified unless a native receipt identifies the serving model. To change which model dcode uses, change it in dcode itself.


## Routing limit

Do not place dcode in an approved implementation or review routing plan. The
wrapper cannot forward or bind an exact model, so even an unverified route
cannot prove that it used the user-approved configured model. Use it only for
a manual, explicitly requested run, and report that the serving model is not
verified.


## Security Model

This skill invokes the local DeepAgents CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files dcode reads during the run may be sent to whichever provider dcode is configured to use. Permission checks stay enabled by default; pass `--auto-approve` to forward `dcode -y` and skip human-in-the-loop prompts. Analysis roles (every role except `implementer`) default to a read-only prompt overlay; pass `--allow-write` to opt out.

**The read-only overlay is a soft constraint, not a sandbox.** `dcode` exposes no read-only launch flag, so `--restrict-tools` only _instructs_ the model to stay read-only via prompt text — it is not enforced. A seat fed untrusted input (e.g. an `adversarial`/`codereviewer` reviewing an attacker-influenced diff) could be prompt-injected into ignoring the overlay and taking write actions. Do not rely on `--restrict-tools` as a security boundary for untrusted content; isolate the working directory instead.

Precedence when both overlay flags are passed: an explicit `--restrict-tools` always wins (read-only), then `--allow-write` opts out, otherwise analysis roles default to read-only and a bare role-less prompt does not.


## Output Envelope

The required key contract is shared — see `shared/references/runner-common.md`. Every exit path (success, timeout, input error, missing CLI, fallback) is normalized — the same keys are present whether the wrapper is invoked via the CLI or imported and called programmatically. `agent_message` holds the trimmed `dcode -n -q --no-stream` response; `dcode` does not print a session id to stdout, so `session_id` stays null.

Dcode-specific extended keys that may appear:

- `status` — set to `seat_unavailable` (`-2`), `timeout` (`-1` from the wrapper or `124` from `dcode --timeout`/`--max-turns`), or `auth_failed` when relevant.
- `fallback_from` / `fallback_reason` — present when a fallback runner produced the output (`fallback_from: dcode`).
- `fallback_attempts` — the siblings tried and skipped before the returned result (including `not_installed` siblings), so the attempt log is always complete, even when every fallback was unavailable.
- `output_json_valid` — for `--output-format json`, whether the (fence-stripped) `agent_message` parsed as JSON.
- `max_turns_exceeded` — `true` when `dcode` exited 124 and `--max-turns` was set, so a caller can distinguish a turn-cap exit from a wall-clock timeout.

With `--output-file` set, the `--json` stdout pointer is `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` so an orchestrator can see which seat/fallback answered without opening the file.

### `auth_ok` semantics

- A successful run (`return_code 0`) → `auth_ok: true`.
- A **missing CLI** (`return_code -2`) → `auth_ok: null` (**untested** — no authentication was ever attempted; it is not reported as `false`).
- A detected authentication failure → `auth_ok: false`, and the run is **forced to `success: false`** (with `status: auth_failed`) even if `dcode` exited 0, so the envelope is never self-contradictory. Auth-failure detection is a heuristic scanned on `stderr` (and on `stdout` only when the run already failed) to avoid false positives from answers that merely mention authentication; treat it as best-effort.


## Prerequisites

- DeepAgents CLI (`dcode`) installed and available in PATH (`curl -LsSf https://langch.in/dcode | bash`)
- A model and credentials configured in dcode via `/auth`, `/model`, `~/.deepagents/config.toml`, `~/.deepagents/.env`, or a project-local `.env`
