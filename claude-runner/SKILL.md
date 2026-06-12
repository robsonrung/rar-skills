---
name: claude-runner
description: Execute prompts using Claude CLI in headless print mode from the current workspace. Use when users explicitly request Claude execution, when a cross-runner workflow selects Claude as the preferred model, or when repo automation needs a Claude CLI seat alongside Codex, Gemini, GLM, or Qwen.
---

# Claude Runner

Execute prompts via Claude CLI `-p` mode with role overlays and continuation support.

## Runtime Compatibility
Fallback: codex-runner only (invoked with `--disable-fallback`; the chain does not continue to qwen, kimi, or gemini).
With `--disable-fallback`, fail fast with a prerequisite message instead of routing.

1. Check whether `claude` CLI is available.
2. If available, execute this skill normally.
3. If unavailable and `codex` is available, route to `$codex-runner` as fallback and report the provider switch.
4. If neither is available, stop with a clear prerequisite message.

## Security Model

This skill invokes the local Claude CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Claude reads during the run may be sent to Anthropic according to the local Claude CLI configuration. Permission checks stay enabled. Analysis roles (every role except `implementer`) default to Claude planning mode (read-only); pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role.


## Output Envelope

All `--json` responses must conform to `.agents/skills/_shared/runner-envelope.schema.json` (provisioned at install time; when that schema file is absent, the required-keys list below is the authoritative contract).
Required top-level keys, always emitted:
- `runner`
- `effective_runner`
- `effective_model`
- `effective_provider`
- `auth_ok` (auth preflight result)
- `fallback_reason`
- `success`
- `return_code`

The envelope also carries `stdout`, `stderr`, and execution metadata, plus:
- `agent_message` — the clean final answer. With `--output-format json`/`stream-json` it is parsed from the result event; with `text` it is the trimmed stdout.
- `session_id` — the Claude session id (available with `--output-format json`/`stream-json`), usable for `--resume <id>` follow-ups.

## Usage

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py "your prompt here"
```

Use `--working-dir` when the prompt depends on package-local files or generated artifacts. Use repeated `--prompt-file` flags for longer prompts or council overlays. Combine `--output-file` with `--json` to write the full envelope to disk and print only a compact `{success, return_code, output_file}` stub, keeping large outputs out of the orchestrator's context.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in a JSON envelope | False |
| `--prompt-file` | Read prompt content from a file; may be repeated | None |
| `--model`, `-m` | Claude model alias or full model name such as `claude-sonnet-4-6` or `claude-opus-4-7` | CLI default |
| `--output-format`, `-o` | Claude print-mode output format: `text`, `json`, or `stream-json` | `text` |
| `--safe` | Informational no-op; permission checks are always enabled whether or not the flag is passed | True |
| `--bare` | Use Claude bare mode for faster startup and fewer implicit context sources | False |
| `--no-session-persistence` | Do not persist Claude session files to disk | False |
| `--restrict-tools` | Use Claude planning mode (read-only) | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default planning mode | False |
| `--effort`, `-e` | Claude effort level: `low`, `medium`, `high`, `xhigh`, `max` | CLI default |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Claude session by id | None |
| `--continue` | Natively resume the most recent Claude conversation in this project | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior debate or workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope to this file atomically; with `--json`, stdout becomes a compact `{success, return_code, output_file}` stub | None |

## Roles

Supported roles:
- `planner`
- `codereviewer`
- `implementer`
- `synthesizer`
- `adversarial`
- `challenger`
- `researcher`

Every role except `implementer` is an analysis seat and defaults to Claude planning mode (read-only). Pass `--allow-write` when an analysis role legitimately needs to write.

## Session Continuation

- `--resume <session-id>` / `--continue` — native Claude resume. Preferred for claude -> claude continuation; the session id comes from the `session_id` envelope field of the earlier run (requires `--output-format json` or `stream-json` on that run).
- `--session-file <file>` — prepends prior workflow context as text. Use only for cross-runner handoffs where no native session exists.

## Background Jobs

`--background` detaches the run as a tracked job under `<working-dir>/.ai-workflow/runner-jobs/<job-id>/` and immediately prints `{success, job_id, pid, job_dir, ...}`. Manage jobs with the shared CLI:

```bash
python3 .agents/skills/_shared/scripts/runner_jobs.py list [--runner claude]
python3 .agents/skills/_shared/scripts/runner_jobs.py status [job-id]
python3 .agents/skills/_shared/scripts/runner_jobs.py result [job-id]
python3 .agents/skills/_shared/scripts/runner_jobs.py cancel [job-id]
```

## Presenting Results

- Prefer `agent_message` over `stdout`; the raw payload is for debugging.
- For reviews, keep findings ordered by severity and preserve file paths and line numbers exactly as reported.
- Preserve evidence boundaries: if the model marked something as an inference or open question, keep that distinction.
- Never auto-apply review findings; present them and ask which to fix.
- If a run fails, report the failure with the most actionable stderr lines — do not silently substitute another model's answer.

## Examples

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py "Summarize the sync service"
python3 .agents/skills/claude-runner/scripts/run_claude.py "Compare two implementation plans" --model claude-sonnet-4-6
python3 .agents/skills/claude-runner/scripts/run_claude.py --prompt-file /tmp/overlay.md --prompt-file /tmp/brief.md --role codereviewer --model claude-opus-4-7
python3 .agents/skills/claude-runner/scripts/run_claude.py "Read-only architecture review" --restrict-tools --bare --no-session-persistence
python3 .agents/skills/claude-runner/scripts/run_claude.py "Continue from the accepted report" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/claude-runner/scripts/run_claude.py "Deep audit of the auth module" --role codereviewer --effort xhigh --output-format json --json
python3 .agents/skills/claude-runner/scripts/run_claude.py --resume 1f2e3d4c-... "Apply the top recommendation" --role implementer --allow-write
python3 .agents/skills/claude-runner/scripts/run_claude.py "Investigate the flaky test" --output-format json --background
```

## Behavior

1. Maps `--restrict-tools` to Claude `--permission-mode plan`; analysis roles get this by default.
2. When `--output-format json` or `stream-json` is used, the native Claude payload stays in `stdout`; the wrapper does not re-shape it, but it extracts `agent_message` and `session_id` into the envelope.
3. `--resume`/`--continue` map to the native Claude CLI flags; `--effort` maps to Claude `--effort`.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Claude CLI not found |
| -3 | Invalid input or unexpected error |
| -4 | Bare mode without `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (bare mode disables OAuth/keychain auth) |

## Prerequisites

- Claude CLI installed and in PATH
- Claude CLI authenticated

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat; do not remove it.
