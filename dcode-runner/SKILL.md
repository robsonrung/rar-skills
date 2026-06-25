---
name: dcode-runner
description: Execute prompts using DeepAgents CLI (`dcode`) non-interactive mode with the user's already-configured model and credentials. Use when users explicitly request dcode or DeepAgents execution, when a workflow needs a DeepAgents/LangChain seat, or when a cross-runner workflow selects dcode as the preferred provider.
---

# Dcode Runner

Execute prompts via DeepAgents CLI (`dcode`) non-interactive mode with role overlays and continuation support. The CLI's pre-configured model and credentials are used as-is — the runner never selects a model or touches `~/.deepagents/`.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas (including its extended envelope keys and `auth_ok` semantics) are inline below.

## Runtime Compatibility

When `dcode` is missing and fallback is disabled (or all fallbacks are unavailable), the envelope carries `status: seat_unavailable` and `return_code` -2; council orchestrators must treat that seat as absent. When a fallback runner does produce the output, unavailable fallback seats attempted before it are listed in `fallback_attempts` on the returned envelope.

1. Check whether DeepAgents CLI (`dcode`) is available.
2. If available, run this skill.
3. If unavailable, route through the fallback order `$claude-runner`, `$codex-runner`, `$qwen-runner`, then `$kimi-runner`, and report the fallback.
4. Never claim the dcode/DeepAgents seat participated when a fallback provider produced the output.

This is **seat fidelity**: the dcode seat's output is only ever that seat's, or the seat is reported absent — a fallback provider's answer is always labeled via `fallback_from`/`fallback_attempts`, never passed off as dcode.

## Configuration Model

The runner deliberately **does not** select a model, configure providers, or write to `~/.deepagents/`. `dcode` uses whatever default model and credentials the user has already wired up via `/model`, `/auth`, `~/.deepagents/config.toml`, `~/.deepagents/.env`, or a project-local `.env`. `--model` on this wrapper is metadata only and is **not** forwarded to `dcode`; it surfaces in `effective_model` for logs and is otherwise ignored. To change which model dcode uses, change it in dcode itself.

## Security Model

This skill invokes the local DeepAgents CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files dcode reads during the run may be sent to whichever provider dcode is configured to use. Permission checks stay enabled by default; pass `--auto-approve` to forward `dcode -y` and skip human-in-the-loop prompts. Analysis roles (every role except `implementer`) default to a read-only prompt overlay; pass `--allow-write` to opt out.

**The read-only overlay is a soft constraint, not a sandbox.** `dcode` exposes no read-only launch flag, so `--restrict-tools` only *instructs* the model to stay read-only via prompt text — it is not enforced. A seat fed untrusted input (e.g. an `adversarial`/`codereviewer` reviewing an attacker-influenced diff) could be prompt-injected into ignoring the overlay and taking write actions. Do not rely on `--restrict-tools` as a security boundary for untrusted content; isolate the working directory instead.

Precedence when both overlay flags are passed: an explicit `--restrict-tools` always wins (read-only), then `--allow-write` opts out, otherwise analysis roles default to read-only and a bare role-less prompt does not.

## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Every exit path (success, timeout, input error, missing CLI, fallback) is normalized — the same keys are present whether the wrapper is invoked via the CLI or imported and called programmatically. `agent_message` holds the trimmed `dcode -n -q --no-stream` response; `dcode` does not print a session id to stdout, so `session_id` stays null.

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

## Usage

```bash
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. When running from this source repo, skills live at the repo root, so invoke `dcode-runner/scripts/run_dcode.py` instead.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Maximum execution time in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current directory |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Compatibility metadata label. `dcode` uses its configured model — this is **not** forwarded. | `dcode-configured-model` |
| `--output-format`, `-o` | Response format hint: `text`, `json`, or `stream-json`. **Advisory only** — `dcode -n` emits plain text, so the wrapper just asks the model for the format in the prompt. For `json` it does a best-effort fence-strip and reports `output_json_valid`; it does not guarantee or re-shape the output. | `text` |
| `--prompt-file` | Read the prompt from a file (repeatable; files are concatenated in order) | None |
| `--role` | Apply a role overlay | None |
| `--restrict-tools` | Add a read-only analysis overlay to the prompt | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default read-only overlay | False |
| `--auto-approve` | Forward `dcode -y` to skip human-in-the-loop permission prompts | False |
| `--max-turns` | Cap dcode's agentic turns (forwarded as `--max-turns`; dcode exits 124 when exceeded) | None |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior workflow context for cross-runner continuation | None |
| `--dcode-continue` | Resume the most recent dcode session via native `dcode -r` | False |
| `--resume SESSION_ID` | Resume a specific dcode session via native `dcode -r SESSION_ID` | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope atomically to this path; with `--json`, stdout becomes a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` | None |

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For dcode, analysis roles default to a read-only prompt overlay (a soft constraint, not a sandbox — see Security Model); pass `--allow-write` to opt out.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `../_shared/references/runner-common.md`. `--background` requires the shared jobs module `_shared/scripts/runner_jobs.py`. It ships in this source repo; if a slimmed install lacks `_shared/`, `--background` exits with a clear error and the foreground modes are unaffected. (The shared launcher strips `--background`/`--json`/`--output-file` from the re-invoked argv, so the detached child runs in the foreground without recursing.)

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure — fallback runs labeled via `fallback_from`/`fallback_reason`) live in `../_shared/references/runner-common.md`.

## Examples

```bash
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Explain this code"
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Analyze this file" --output-format json
python3 .agents/skills/dcode-runner/scripts/run_dcode.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Apply the accepted recommendation" --role implementer --auto-approve --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Continue the previous analysis" --dcode-continue
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Tight loop cap" --max-turns 8
```

## Behavior

1. Executes `dcode -n -q --no-stream --timeout <Ns> [-y] [--max-turns N] [-r [ID]] "<prompt>"`. The dcode `--timeout` is set slightly below the wrapper's `--timeout` so `dcode` self-terminates (and returns its own 124 exit code) before the hard subprocess timeout would kill it; a genuine wrapper timeout still reports `return_code -1` / `status: timeout`. A `dcode` 124 with `--max-turns` set is annotated `max_turns_exceeded: true`.
2. Does not request a permission bypass unless `--auto-approve` is passed (which forwards `-y`).
3. Keeps `runner=dcode` for workflow compatibility and sets `effective_runner=dcode` when the CLI produced the output.
4. Does not pass unsupported flags such as `--model`, `--output-format`, or a read-only convenience mode to `dcode`. `--model` is metadata only; when supplied it is reflected in `effective_model`, otherwise `effective_model` is the `dcode-configured-model` placeholder.
5. Resolves relative `--prompt-file`/`--session-file` paths against `--working-dir` (not the process cwd).

### Continuation caveat

`dcode -r` without an ID resumes **the most recent** dcode session in the shared `~/.deepagents/` home — it cannot target a specific session and `session_id` stays null. Use `--resume SESSION_ID` to target a specific session by id when you have one. Avoid running two `--dcode-continue` invocations concurrently against the same `~/.deepagents/` home; they can cross-contaminate.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1+ | DeepAgents CLI (`dcode`) error (passthrough; `124` = dcode's own timeout or `--max-turns` cap) |
| -1 | Wrapper timeout expired |
| -2 | DeepAgents CLI (`dcode`) not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- DeepAgents CLI (`dcode`) installed and available in PATH (`curl -LsSf https://langch.in/dcode | bash`)
- A model and credentials configured in dcode via `/auth`, `/model`, `~/.deepagents/config.toml`, `~/.deepagents/.env`, or a project-local `.env`

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat; do not remove it.
