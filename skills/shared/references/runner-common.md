# Runner Common Reference

Canonical rules shared by the runner skills and their named seats. Use
[host-model-execution.md](host-model-execution.md) first: native model delegation
takes precedence over an external runner unless the user selected a transport.
This reference applies once a runner path is selected. Model identifiers live in
[model-roster.md](model-roster.md); `shared/scripts/discover_runners.py` checks
external transport presence and does not prove native capabilities or access.

## Iterative roles

Keep one explicit session per task and role when later turns are expected. Read
the runner's continuation reference before its first call so persistence is
enabled and the returned session ID is captured. Use that exact ID for follow-up
calls, never a shared last-session selector in a concurrent run. Pi needs an
explicit unique session path from the first call. Preserve approved model,
effort control, provider routing, model capabilities, tool policy, and counters
on resume. Copy them from the selected snapshot, not local preferences.
A transcript handoff is a disclosed reconstruction, not native resumption. See the host execution contract for
adapter limits, pending-call recovery, and role isolation.

## Seat fidelity

**Seat fidelity** — a seat's output is only ever that seat's, or the seat is reported absent (labeled via `fallback_from`).

This is the core invariant every runner upholds. A runner never silently substitutes another model's answer for the seat the caller asked for. When the requested CLI is missing, blocked, or fails, the runner either:

- routes to an explicit fallback runner and labels the substitution on the envelope (`fallback_from`, `fallback_reason`), so the caller always knows which seat actually answered; or
- reports the seat as unavailable (`success: false`, typically `status: seat_unavailable` with `return_code -2`) so councils and orchestrators account for the missing seat.

This is the one place the fallback split is defined; nothing else restates it.

| Runner | On a missing / failing CLI |
| --- | --- |
| `claude` | falls back → `codex` |
| `codex` | falls back → `claude` |
| `gemini` | falls back → `qwen`, `kimi`, `codex`, `claude` (in that order) |
| `dcode` | falls back → `claude`, `codex`, `qwen`, `kimi` (in that order) |
| `grok`, `cline`, `pi`, `kimi`, `glm`, `qwen`, `gemma`, `muse`, `minimax` | **block-and-report** — never substitutes |

A fallback is always labeled (`fallback_from`, `fallback_reason`), and every fallback chain passes `--disable-fallback` to the runner it delegates to so chains cannot loop. Either way the seat's identity is never faked.

## Approved-route execution

An implementation or council route selected by a user-approved routing plan is
stricter than an ad hoc runner call. It passes `--disable-fallback`, names its
model and effort explicitly, and accepts output only when the envelope's
`effective_runner` and `configured_model` match the approved route. It also
uses the route's `model_verification` policy. Carry selected provider routing and
required tool capabilities through initial calls, repairs, and resume. A privacy
or capability failure blocks the route; source sharing metadata alone does not
enforce request controls. The request policy digest does not prove serving identity.
`required` needs a matching verified serving-model receipt. `allow_unverified` is valid only when the user
approved it and the report labels the serving model unverified. A verified
receipt for a different model always blocks, including on an
`allow_unverified` route.

When an approved route is unavailable, block unless its `unavailable` field
contains one exact alternate route approved in the same plan. Invoke that
alternate as a new route with `--disable-fallback`; do not rely on a runner's
automatic fallback chain. A runtime-controlled effort is reported as such and
does not satisfy a route that promised a configured effort.

## Model provenance

Every envelope separates three model values:

- `requested_model` is what the caller asked for.
- `configured_model` is what the wrapper forwarded or set when known.
- `effective_model` is populated only when a native or provider event reports
  the serving model.

`model_receipt.status` is `verified` only for an observed native or provider
model. It is `unverified` when a wrapper has a configured label or no observed
model. Do not report `requested_model` or `configured_model` as confirmed
model access.

## Effort control

Adapters with a supported model specific effort use `effort_control: "runner"`.
Pi candidates without selectable effort use `effort_control: "runtime"` with a
null effort; preserve their observed runtime reasoning without inventing a level.
Gemini also uses runtime effort. Dcode is not eligible for approved implementation
or review routes because it cannot forward an exact model. Grok accepts at most `high`;
an approved route must select a supported effort rather than rely on a
direct-call clamp.

## Output envelope (required keys)

All `--json` responses conform to `shared/runner-envelope.schema.json` (bundled in this repo; installed at `.agents/skills/shared/runner-envelope.schema.json`).

Required top-level keys, always emitted on every exit path:

- `runner`
- `effective_runner`
- `effective_model`
- `requested_model`
- `configured_model`
- `model_receipt`
- `effective_provider`
- `auth_ok` (auth preflight result: `true` on a successful run; `null` when auth was never exercised — missing CLI, invalid input, or a failure before auth; `false` only when an authentication failure was actually detected)
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `stdout`, `stderr`, and execution metadata. The clean final answer is exposed as `agent_message`; orchestrators should read that field instead of parsing `stdout`. Individual runners extend this contract with their own keys such as `session_id`, `status`, `fallback_from`, and `fallback_attempts`; see each runner's SKILL.md for its extensions.

## Roles

Supported roles:

- `planner`
- `codereviewer`
- `implementer`
- `synthesizer`
- `adversarial`
- `challenger`
- `researcher`

Every role except `implementer` is an analysis seat and defaults to read-only mode. The exact enforcement is runner specific: Claude planning mode, Codex read-only sandbox, Cline plan mode (read-only toolset with reads auto-approved; `--no-tools` forces a full tool block via `--auto-approve false`), Pi tool allowlisting (`--restrict-tools` enables only the file-reading tool; `--no-tools` disables all tools natively), or a prompt-level overlay. Pass `--allow-write` when an analysis role legitimately needs to write.

## Presenting results

- Prefer `agent_message` over `stdout`; the raw payload is for debugging.
- For reviews, keep findings ordered by severity and preserve file paths and line numbers exactly as reported.
- Preserve evidence boundaries: if the model marked something as an inference or open question, keep that distinction.
- State `model_receipt.status` when a result identifies its model. Never call an
  unverified configured label a served-model receipt.
- For a review-only request, return findings without editing. In an authorized
  implementation and review cycle, send supported in-scope findings to the
  recorded implementer session and verify the fixes. Reuse that authority;
  return only new material decisions to the user.
- If a run fails, report the failure with the most actionable stderr lines — do not silently substitute another model's answer (seat fidelity). Any fallback run is always labeled via `fallback_from`/`fallback_reason`.

## Guardrails (opt-in command guard)

Runner skills launch CLI seats headless with auto-approve flags — the guard puts a floor under that. `shared/hooks/` ships a denylist of catastrophic commands (`dangerous-patterns.txt`), a shared PreToolUse guard script (`deny-dangerous.sh`), and its test suite (`test-guard.sh`). The guard blocks only irreversible damage (rm on /|~, raw-disk writes, sudo rm, fork bombs, curl|sh, remote-history rewrites, gh repo delete, token exfil); recoverable commands stay allowed. It is a seatbelt against accidents, not a sandbox against a malicious agent — keep sandboxing and permission modes on regardless.

**Install is opt-in and user-driven; no skill ever wires it automatically.** Copy the two files to `~/.agents/hooks/` (or point configs at the repo checkout) and register the script per CLI:

- **Claude Code** — `~/.claude/settings.json`, `PreToolUse` hook with matcher `Bash` running the script (exit 2 blocks). Merge into any existing `hooks` object, never overwrite.
- **Codex CLI** — `~/.codex/hooks.json`, same `PreToolUse`/`Bash` shape. Gotcha: Codex pins hook-entry trust by hash — after editing the hook ENTRY (not the patterns file), re-trust via `/hooks` in Codex or it silently skips the guard.
- **Cline-backed seats (cline, muse, minimax)** — no user-global PreToolUse hook system as of 2026-08; their floor is native plan mode (no file-editing tool, write actions policy-blocked) for restricted runs, or `--auto-approve false` under `--no-tools`. Note the gap rather than pretending coverage.
- **Pi-backed seats (pi, kimi, glm, qwen, gemma)** — no PreToolUse hook system; their floor is the wrapper's tool modes (`--restrict-tools` enables only the file-reading tool; `--no-tools` disables all tools natively). Note the gap rather than pretending coverage.

Use absolute paths in configs (`~` expansion is inconsistent across hosts). After ANY pattern change run `test-guard.sh` (must end `failed: 0`). Known false-positive class: a harmless command whose argument text contains a dangerous-looking string can be blocked — put the text in a file and reference it.

## Background jobs

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs with the shared CLI (used by every runner skill):

```bash
python3 .agents/skills/shared/scripts/runner_jobs.py list [--runner <name>]
python3 .agents/skills/shared/scripts/runner_jobs.py status [job-id]
python3 .agents/skills/shared/scripts/runner_jobs.py result [job-id]
python3 .agents/skills/shared/scripts/runner_jobs.py cancel [job-id]
```

`job-id` defaults to the most recent job. All subcommands accept `--working-dir` and `--json`. `status` reports `running`, `completed`, `failed`, `cancelled`, or `died` plus a log tail; `result` prints the stored `agent_message` (or the full envelope with `--json`) and the session id for follow-up resumes; `cancel` terminates the job's process group.

## Wait for explicit jobs

Use `runner_jobs.py wait-many --targets <targets.json> --timeout 50 --json`.
The targets file is a list of `{working_dir, job_id}` entries. Store the returned `cursor` map
and pass its file with `--cursor` on the next wait. One wait checks all targets and returns
on a status change or the observation timeout. It does not start or cancel work. A timeout
is not a failed job. Resume the same handle. Read the result file only for changed terminal state.
The CLI accepts at most 60 seconds per wait so the caller can provide required progress updates.
