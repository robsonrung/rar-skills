---
name: gemini-runner
description: Execute prompts using Antigravity CLI (`agy`) headless print mode for a Gemini/Google seat. Use when users request Gemini execution, Antigravity CLI execution, or when a consensus workflow needs a Gemini seat and local `agy` is installed.
---

# Gemini Runner

Execute prompts via Antigravity CLI (`agy`) headless print mode with role overlays and continuation support.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas (including its extended envelope keys and `auth_ok` semantics) are inline below.

## Runtime Compatibility
When `agy` is missing and fallback is disabled (or all fallbacks are unavailable), the envelope carries `status: seat_unavailable` and `return_code` -2; council orchestrators must treat that seat as absent. When a fallback runner does produce the output, unavailable fallback seats attempted before it are listed in `fallback_attempts` on the returned envelope.

1. Check whether Antigravity CLI (`agy`) is available.
2. If available, run this skill.
3. If unavailable, route through the fallback order `$qwen-runner`, `$kimi-runner`, `$codex-runner`, then `$claude-runner`, and report the fallback.
4. Never claim the Gemini/Google seat participated when a fallback provider produced the output.

This is **seat fidelity**: the Gemini/Google seat's output is only ever that seat's, or the seat is reported absent — a fallback provider's answer is always labeled via `fallback_from`/`fallback_attempts`, never passed off as Gemini.

## Security Model

This skill invokes the local Antigravity CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Antigravity reads during the run may be sent to the configured Google model. Permission checks stay enabled through the local Antigravity configuration. Analysis roles (every role except `implementer`) default to a read-only prompt overlay; pass `--allow-write` to opt out.

**The read-only overlay is a soft constraint, not a sandbox.** `agy` has no sandbox/read-only launch flag, so `--restrict-tools` only *instructs* the model to stay read-only via prompt text — it is not enforced. A seat fed untrusted input (e.g. an `adversarial`/`codereviewer` reviewing an attacker-influenced diff) could be prompt-injected into ignoring the overlay and taking write actions. Do not rely on `--restrict-tools` as a security boundary for untrusted content; isolate the working directory instead.

Precedence when both overlay flags are passed: an explicit `--restrict-tools` always wins (read-only), then `--allow-write` opts out, otherwise analysis roles default to read-only and a bare role-less prompt does not.

## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Every exit path (success, timeout, input error, missing CLI, fallback) is normalized — the same keys are present whether the wrapper is invoked via the CLI or imported and called programmatically. `agent_message` holds the trimmed `agy` print-mode response; `agy` exposes no session id, so `session_id` stays null.

Gemini-specific extended keys that may appear:
- `status` — set to `seat_unavailable` (`-2`), `timeout` (`-1`), or `auth_failed` when relevant.
- `fallback_from` / `fallback_reason` — present when a fallback runner produced the output (`fallback_from: gemini`).
- `fallback_attempts` — the siblings tried and skipped before the returned result (including `not_installed` siblings), so the attempt log is always complete, even when every fallback was unavailable.
- `output_json_valid` — for `--output-format json`, whether the (fence-stripped) `agent_message` parsed as JSON.

### `auth_ok` semantics

- A successful run (`return_code 0`) → `auth_ok: true`.
- A **missing CLI** (`return_code -2`) → `auth_ok: null` (**untested** — no authentication was ever attempted; it is not reported as `false`).
- A detected authentication failure → `auth_ok: false`, and the run is **forced to `success: false`** (with `status: auth_failed`) even if `agy` exited 0, so the envelope is never self-contradictory. Auth-failure detection is a heuristic scanned on `stderr` (and on `stdout` only when the run already failed) to avoid false positives from answers that merely mention authentication; treat it as best-effort.

With `--output-file` set, the `--json` stdout pointer is `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` so an orchestrator can see which seat/fallback answered without opening the file.

## Usage

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. When running from this source repo, skills live at the repo root, so invoke `gemini-runner/scripts/run_gemini.py` instead.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Maximum execution time in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current directory |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Compatibility metadata label. `agy` uses its configured model from `/model` or settings — this label is reflected in `effective_model` but not forwarded. Premium seat: `gemini-3.1-pro` (product discovery / product thinking); for broad independent perspective and cross-file consistency, pass `gemini-3.5-flash`. | `gemini-3.1-pro` |
| `--output-format`, `-o` | Response format hint: `text`, `json`, or `stream-json`. **Advisory only** — `agy` print mode has no output-format launch flag, so the wrapper just asks the model for the format in the prompt. For `json` it does a best-effort fence-strip and reports `output_json_valid`; it does not guarantee or re-shape the output. | `text` |
| `--prompt-file` | Read the prompt from a file (repeatable; files are concatenated in order) | None |
| `--role` | Apply a role overlay | None |
| `--restrict-tools` | Add a read-only analysis overlay to the prompt | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default read-only overlay | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior workflow context for cross-runner continuation | None |
| `--agy-continue` | Resume the most recent Antigravity CLI conversation with native `agy --continue` | False |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope atomically to this path; with `--json`, stdout becomes a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` | None |

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Gemini, analysis roles default to a read-only prompt overlay (a soft constraint, not a sandbox — see Security Model); pass `--allow-write` to opt out.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list`/`status`/`result`/`cancel`) — see `../_shared/references/runner-common.md`. `--background` requires the shared jobs module `_shared/scripts/runner_jobs.py`. It ships in this source repo; if a slimmed install lacks `_shared/`, `--background` exits with a clear error and the foreground modes are unaffected. (The shared launcher strips `--background`/`--json`/`--output-file` from the re-invoked argv, so the detached child runs in the foreground without recursing.)

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure — fallback runs labeled via `fallback_from`/`fallback_reason`) live in `../_shared/references/runner-common.md`.

## Examples

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Explain this code"
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Analyze this file" --output-format json
python3 .agents/skills/gemini-runner/scripts/run_gemini.py --prompt-file /tmp/review.md --role codereviewer
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Continue the previous analysis" --agy-continue
```

## Behavior

1. Executes `agy [--continue] --print-timeout <Ns> --print "<prompt>"`. The `--print-timeout` is set slightly below the wrapper's `--timeout` so `agy` self-terminates (and returns its own exit code) before the hard subprocess timeout would kill it; a genuine wrapper timeout still reports `return_code -1` / `status: timeout`.
2. Does not request a permission bypass.
3. Keeps `runner=gemini` for workflow compatibility and sets `effective_runner=agy` when Antigravity CLI produced the output.
4. Does not pass unsupported Gemini CLI flags such as `--model`, `--output-format`, `--thinking-budget`, or a read-only convenience mode to `agy`. `--model` is metadata only; when supplied it is reflected in `effective_model`, otherwise `effective_model` is the `gemini-3.1-pro` premium-seat label (agy uses its own configured model — set its `/model` picker to Gemini 3.1 Pro, or Gemini 3.5 Flash for broad-perspective seats).
5. Resolves relative `--prompt-file`/`--session-file` paths against `--working-dir` (not the process cwd).

### Continuation caveat

`agy` exposes no session id, so `--agy-continue` resumes **the most recent** Antigravity CLI conversation in the shared `agy` home — it cannot target a specific session and `session_id` stays null. Avoid running two `--agy-continue` invocations concurrently against the same `agy` home; they can cross-contaminate.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1+ | Antigravity CLI (`agy`) error (passthrough) |
| -1 | Timeout expired |
| -2 | Antigravity CLI (`agy`) not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Antigravity CLI (`agy`) installed and available in PATH
- Authentication configured for Antigravity CLI
- Model selection configured in `agy` itself (the wrapper's `--model` is a non-forwarded label). List the models `agy` accepts with `agy models`; the two premium Gemini seats are named **`Gemini 3.1 Pro (High)`** (product discovery / architecture reasoning) and **`Gemini 3.5 Flash (High)`** (broad independent perspective / cross-file). Select one via `/model` in an interactive `agy` session or in `~/.gemini/antigravity-cli/settings.json` — the wrapper's `--model gemini-3.1-pro` / `--model gemini-3.5-flash` only sets the `effective_model` label.
