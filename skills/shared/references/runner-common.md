# Runner Common Reference

Rules shared by the runner skills. Use [host-model-execution.md](host-model-execution.md) first: a host that runs the model natively takes precedence over a runner unless the user selected a transport. Model identifiers live in [model-roster.md](model-roster.md); `shared/scripts/discover_runners.py` checks which runner CLIs are present and does not prove access.

Two kinds of runner exist. `cli-runner` calls the Claude, Codex, Antigravity (`agy`), and Grok CLIs directly; its SKILL.md shows each command. `pi-runner` and `muse-runner` ship a wrapper script, because Pi enforces provider privacy routing and Muse checks workspace trust before any call.

In T3 Code, all model calls use internal subagents under [host-model-execution.md](host-model-execution.md). External runners and CLIs are unavailable as execution paths, including retries, except `muse-runner`, which runs every Muse route. Report a blocked route when the host cannot serve it.

## Seat fidelity

**Seat fidelity**: a seat's output is only ever that seat's, or the seat is reported absent.

No runner substitutes another model. Never pass a CLI's fallback option, such as Claude's `--fallback-model`. When the CLI is missing, fails, or reports a different model than the one requested, the seat is unanswered: report it, with the telling stderr lines, so councils and orchestrators account for the missing seat. An approved route may name one exact alternate in its `unavailable` field; run that alternate as a new route, never as a silent retry.

## Approved routes

A route from a user-approved plan names its model and effort explicitly, and its output counts only when the run used that model. Keep the requested model, the configured model, and any model the CLI or provider reports as separate facts: only a reported serving model is a verified receipt. A route marked `allow_unverified` may proceed on a configured label alone, and the report says so. A reported different model always blocks. Carry the route's provider routing and tool policy through every call, repair, and resume.

## Effort control

Pass the route's effort through the CLI's own flag. Grok accepts at most `high`. Pi models without selectable effort run at their runtime effort; report that rather than inventing a level.

## Roles and read-only mode

Every role except `implementer` is an analysis seat and runs read-only: Claude in plan mode with only Read, Glob, and Grep; Codex in its `read-only` sandbox; Gemini and Grok in plan mode; Pi with `--restrict-tools` or `--no-tools`. Tell read-only seats in the prompt to leave every file unchanged as well.

## Iterative roles

Keep one session per task and role when later turns are expected. Read the runner's Continue instructions before its first call so the session ID is captured, and use that exact ID for follow-ups; never a shared "most recent" selector while several roles run. Pi needs a unique session file from the first call; Muse keeps no session, so each turn resends the full context. A transcript handoff is a disclosed reconstruction, not resumption.

## Long calls

Run a direct CLI call in the host's background shell and read its output when it finishes. The Pi and Muse wrappers also accept `--background`, which returns a job ID for `shared/scripts/runner_jobs.py` (`status`, `wait-many`, `result`, `cancel`).

## Wrapper envelope

The Pi and Muse wrappers return the JSON envelope in `shared/runner-envelope.schema.json`. Read `agent_message` for the answer, `success` and `status` for the outcome, and `model_receipt` for the serving model. `--metadata-json` carries dispatch data; only its `prompt_context` field reaches the prompt.

## Presenting results

- Keep review findings in severity order, with file paths and line numbers exactly as reported.
- Keep the model's distinction between evidence, inference, and open questions.
- State whether the serving model was verified; never present a configured label as a served-model receipt.
- On failure, report the failure; never answer for the seat.

## Guardrails (opt-in command guard)

Runner CLIs run headless, sometimes with auto-approve flags. `shared/hooks/` ships a denylist of catastrophic commands (`dangerous-patterns.txt`), a PreToolUse guard (`deny-dangerous.sh`), and its test suite (`test-guard.sh`). It blocks only irreversible damage (rm on `/` or `~`, raw-disk writes, fork bombs, `curl | sh`, remote-history rewrites, repository deletion, token exfiltration). It is a seatbelt, not a sandbox: keep sandboxes and permission modes on.

Install is opt-in and user-driven; no skill wires it automatically. Copy the two files to `~/.agents/hooks/` and register the script per CLI:

- **Claude Code:** `~/.claude/settings.json`, a `PreToolUse` hook with matcher `Bash` (exit 2 blocks). Merge into any existing `hooks` object.
- **Codex CLI:** `~/.codex/hooks.json`, same shape. Codex pins hook-entry trust by hash; after editing the entry, re-trust it through `/hooks`.
- **Pi seats:** no hook system; their floor is the wrapper's tool modes. Note the gap rather than claiming coverage.

Use absolute paths in configs. After any pattern change, run `test-guard.sh` and confirm `failed: 0`.
