---
name: grok-runner
description: Execute prompts using Grok CLI in headless print mode as the xAI seat (Grok 4.5). Use when users explicitly request Grok execution, when a multi-model workflow needs an xAI seat for provider diversity, or when a cross-runner workflow selects Grok as the preferred model.
---

# Grok Runner

Execute prompts via Grok CLI `-p` mode with role overlays, native structured output, and continuation support.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas are inline below.

## Runtime Compatibility

No fallback chain. If the `grok` CLI is missing, the seat fails fast with `return_code -2`, `status: seat_unavailable`, `fallback_reason: null` — no other installed CLI can produce a real Grok answer, so substituting one would violate **seat fidelity**. `--disable-fallback` is accepted as a no-op for cross-runner parity.

## Security Model

This skill invokes the local `grok` CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Grok reads during the run may be sent to xAI according to the local Grok CLI configuration. Sessions always persist under `~/.grok` — the CLI has no session-persistence opt-out. Analysis roles (every role except `implementer`) default to Grok plan mode (read-only, `--permission-mode plan`); pass `--allow-write` to opt out, or `--restrict-tools` to force it without a role.

## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Grok-specific envelope extensions:
- `agent_message` — the clean final answer. With `--output-format json` it is the payload's `text` field; with `stream-json` it is the concatenated `text` events; with `text` it is the trimmed stdout.
- `session_id` — the Grok session id (available with `json`/`stream-json` output), usable for `--resume <id>` follow-ups.
- `native_model_id` — the model that actually answered, harvested from grok's `modelUsage` (e.g. `grok-4.5-build`); also feeds `effective_model`.
- `reasoning_effort_forwarded` / `effort_clamped` — what `--effort` value was actually sent to grok, and whether the shared `xhigh`/`max` tiers were clamped to grok's `high`.
- `structured_output` — the schema-validated object grok returns when `--output-schema` is used.

## Usage

```bash
python3 .agents/skills/grok-runner/scripts/run_grok.py "your prompt here"
```

Use `--working-dir` when the prompt depends on package-local files or generated artifacts; relative `--prompt-file`/`--session-file`/`--output-schema` paths resolve against it (not the process cwd), with `~` expanded. Use repeated `--prompt-file` flags for longer prompts or council overlays. Combine `--output-file` with `--json` to write the full envelope to disk and print only a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}`, keeping large outputs out of the orchestrator's context while still showing which seat answered.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory (passed as subprocess cwd and grok `--cwd`) | Current dir |
| `--json`, `-j` | Wrap runner output in a JSON envelope | False |
| `--prompt-file` | Read prompt content from a file; may be repeated | None |
| `--model`, `-m` | Grok model id | CLI default (`grok-4.5`) |
| `--output-format`, `-o` | Headless output format `text`, `json`, or `stream-json`; forwarded to grok as `plain`/`json`/`streaming-json` | `text` |
| `--restrict-tools` | Use Grok plan mode (read-only) | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default plan mode | False |
| `--effort`, `-e` | Reasoning effort `low`, `medium`, `high`, `xhigh`, `max`; grok accepts low/medium/high, so `xhigh`/`max` clamp to `high` (recorded via `effort_clamped`) | CLI default (`high`) |
| `--output-schema FILE` | JSON Schema file forwarded to grok `--json-schema` for **native** structured-output enforcement; forces `--output-format json` | None |
| `--max-turns N` | Maximum agent turns for the headless run | CLI default |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Grok session by id | None |
| `--continue` | Natively resume the most recent Grok session for this directory | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior debate or workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Accepted for cross-runner parity; grok-runner never falls back (no-op) | False |
| `--output-file` | Write the full JSON envelope to this file atomically; with `--json`, stdout becomes the compact pointer | None |

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Grok, analysis roles default to plan mode (`--permission-mode plan`); pass `--allow-write` to opt out.

## Session Continuation

- `--resume <session-id>` / `--continue` — native Grok resume. Preferred for grok -> grok continuation; the session id comes from the `session_id` envelope field of the earlier run (requires `--output-format json` or `stream-json` on that run), or from `grok sessions`.
- `--session-file <file>` — prepends prior workflow context as text. Use only for cross-runner handoffs where no native session exists.

## Background Jobs

`--background` runs as a tracked job; manage it with the shared jobs CLI (`list --runner grok` / `status` / `result` / `cancel`) — see `../_shared/references/runner-common.md`.

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure) live in `../_shared/references/runner-common.md`.

## Examples

```bash
python3 .agents/skills/grok-runner/scripts/run_grok.py "Summarize the sync service"
python3 .agents/skills/grok-runner/scripts/run_grok.py --prompt-file /tmp/overlay.md --prompt-file /tmp/brief.md --role codereviewer --effort high
python3 .agents/skills/grok-runner/scripts/run_grok.py "Read-only architecture review" --restrict-tools --output-format json --json
python3 .agents/skills/grok-runner/scripts/run_grok.py "Continue from the accepted report" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/grok-runner/scripts/run_grok.py "Trace the failing execution path" --role codereviewer --effort high --output-format json --json --output-file /tmp/grok-review.json
python3 .agents/skills/grok-runner/scripts/run_grok.py --prompt-file /tmp/round1-brief.md --restrict-tools --effort high --json --disable-fallback --output-schema .agents/skills/models-consensus/schemas/opening-answer.schema.json --output-file /tmp/round1-grok.json
python3 .agents/skills/grok-runner/scripts/run_grok.py --resume 019fa905-2a08-7180-83fe-64b8bb369912 "Apply the top recommendation" --role implementer --allow-write
python3 .agents/skills/grok-runner/scripts/run_grok.py "Investigate the flaky test" --output-format json --background
```

## Behavior

1. Maps `--restrict-tools` to Grok `--permission-mode plan`; analysis roles get this by default.
2. Translates the shared output-format enum to grok's: `text` -> `plain`, `json` -> `json`, `stream-json` -> `streaming-json`, always passed explicitly. With json output the native payload stays in `stdout`; the wrapper extracts `agent_message`, `session_id`, `native_model_id`, and `structured_output` into the envelope.
3. Maps `--effort` to grok `--reasoning-effort`, clamping `xhigh`/`max` to `high` (envelope records `effort`, `reasoning_effort_forwarded`, `effort_clamped`).
4. `--output-schema FILE` reads the schema file and forwards its contents inline as grok `--json-schema`, so enforcement is native to the model, and forces json output (grok implies it). Very large schemas could approach argv limits; keep schemas file-sized, not megabytes.
5. Resolves relative `--prompt-file`/`--session-file`/`--output-schema` paths against `--working-dir` (not the process cwd), with `~` expanded; the working dir is also forwarded as grok `--cwd`.
6. Never falls back to another runner. A missing CLI blocks the seat explicitly (`status: seat_unavailable`, `return_code -2`) — **seat fidelity**: never substitute another model's answer for the Grok seat.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Grok CLI not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- `grok` CLI installed and in PATH
- `grok` CLI authenticated (`grok login`, grok.com account)

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat; do not remove it.
