---
name: codex-runner
description: Execute prompts using Codex CLI in non-interactive exec mode. Use when users explicitly request Codex execution, when a workflow needs a Codex CLI run inside this repository, or when a cross-runner workflow selects Codex as the preferred model and native Codex subagents are unavailable.
---

# Codex Runner

Execute prompts via Codex CLI `exec` mode with role overlays, native session resume, background jobs, and continuation support.

Roles, the output-envelope key contract, presenting-results rules, the background-jobs CLI, and the **seat fidelity** invariant are shared across runners — see `../_shared/references/runner-common.md`. Only this runner's deltas are inline below.

## Runtime Compatibility

1. Check whether `codex` CLI is available.
2. If available, execute this skill normally.
3. If unavailable, the script automatically falls back to the claude-runner skill (`run_claude.py`) and reports the provider switch (`fallback_from`, `fallback_reason`); runner provenance fields stay mandatory in the envelope.
4. If `--disable-fallback` is set, `--resume`/`--resume-last` is requested (Codex sessions cannot be resumed by another runner), or no fallback runner is found, the script exits non-zero with `return_code` -2 and a clear prerequisite message.

This upholds **seat fidelity**: the Codex seat's output is only ever Codex's, or the seat is reported absent — a claude fallback is always labeled via `fallback_from`/`fallback_reason`, never passed off as Codex.

The broader cross-runner probe chain (codex -> qwen -> kimi -> gemini -> claude) is a contract owned by the runner skills that implement it (see the claude-runner skill's SKILL.md for its own fallback order); this wrapper implements only the codex -> claude leg.

## Security Model

This skill invokes the local Codex CLI from the current machine. Prompt text, prompt files, session files, metadata, and any files Codex reads during the run may be sent to OpenAI according to the local Codex CLI configuration. The wrapper no longer passes `--full-auto` by default. Analysis roles (every role except `implementer`) default to the Codex read-only sandbox; pass `--allow-write`, an explicit `--sandbox`, or `--full-auto` to opt out. Use `--full-auto` only for a user approved unattended run.

## Output Envelope

The required key contract is shared — see `../_shared/references/runner-common.md`. Envelopes also include execution metadata (command, working directory, role, sandbox, and related fields). Codex-specific extensions:
- `agent_message` — the clean final answer from Codex (captured via `--output-last-message`), free of the activity transcript in `stdout`.
- `session_id` — the Codex session id when detectable, so the run can be continued with `--resume <id>` (or reopened interactively with `codex resume <id>`).

## Usage

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout; when running from this source repo, skills live at the repo root, so invoke `codex-runner/scripts/run_codex.py` instead.

For repository-aware tasks, prefer `--working-dir` set to the repository root so Codex picks up the applicable local instructions.

Before composing non-trivial prompts (reviews, implementations, research seats), read `references/prompting.md` for task-type XML recipes and anti-patterns.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Codex model. Default `gpt-5.5` (best all-around: architecture, coding, synthesis, adversarial reasoning). Alias `codex` -> `gpt-5.3-codex` (code-specialized: agentic coding, regression, security review); `spark` -> `gpt-5.3-codex-spark` | `gpt-5.5` |
| `--effort`, `-e` | Reasoning effort: `none`, `minimal`, `low`, `medium`, `high`, `xhigh` | CLI default |
| `--sandbox`, `-s` | Codex sandbox mode override | CLI default |
| `--restrict-tools` | Force `--sandbox read-only` | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the read-only default | False |
| `--full-auto` | Pass Codex full auto mode for an explicitly approved unattended run | False |
| `--approval-policy`, `-a` | Codex approval policy override | None |
| `--skip-git-repo-check` | Allow runs outside a Git repo | False |
| `--prompt-file` | Read the prompt from a file (repeatable; files are concatenated in order) | None |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Codex session by id | None |
| `--resume-last` | Natively resume the most recent Codex session | False |
| `--session-file` | Append prior workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--ephemeral` | Run without persisting session files to disk | False |
| `--output-schema` | Path to a JSON Schema file for the final response shape | None |
| `--add-dir` | Additional writable directory (repeatable; not valid with `--resume`) | None |
| `--image`, `-i` | Attach an image file to the prompt (repeatable) | None |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--output-file` | Write the full wrapper JSON result atomically to this file | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |

When `--json` and `--output-file` are combined, stdout becomes a compact `{success, return_code, output_file}` summary, keeping large Codex outputs out of an orchestrating agent's context window.

## Roles

The role list and the analysis-seat read-only default are shared — see `../_shared/references/runner-common.md`. For Codex, analysis roles default to the Codex read-only sandbox; pass `--allow-write` (or an explicit `--sandbox`/`--full-auto`) to opt out.

## Session Continuation

Two mechanisms, with different purposes:

- `--resume <session-id>` / `--resume-last` — native Codex resume (`codex exec resume`). Preferred for codex -> codex continuation: it restores the full Codex-side thread state without re-sending prior text. The session id comes from the `session_id` envelope field of the earlier run. When resuming without a prompt, a default "continue from the current thread state" instruction is sent.
- `--session-file <file>` — prepends prior workflow context as text. Use only for cross-runner handoffs (e.g. continuing a Claude or Gemini thread in Codex), where no native session exists.

`--resume` cannot fall back to another runner; if Codex CLI is missing the run fails with `return_code` -2.

## Structured Review Output

A review output schema is bundled at `schemas/review-output.schema.json` (verdict `approve`/`needs-attention`, summary, findings with severity/file/line range/confidence/recommendation, next_steps — the same contract as the official OpenAI Codex plugin). Pair it with a review role so findings are machine-parseable from `agent_message`:

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "Review the staged diff" \
  --role codereviewer \
  --output-schema .agents/skills/codex-runner/schemas/review-output.schema.json --json
```

## Background Jobs

`--background` runs as a tracked job (job dir holds the manifest, log, and final envelope as `result.json`); manage it with the shared jobs CLI (`list --runner codex` / `status` / `result` / `cancel`) — see `../_shared/references/runner-common.md`.

## Presenting Results

Shared rules (prefer `agent_message`, severity-ordered findings, evidence boundaries, never auto-apply, **seat fidelity** on failure) live in `../_shared/references/runner-common.md`. Codex-specific additions:

- If Codex made edits, say so explicitly and list the touched files.
- Fallback applies only when the Codex CLI is missing, and it is always labeled via `fallback_from`/`fallback_reason`.

## Examples

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "Explain this module"
python3 .agents/skills/codex-runner/scripts/run_codex.py "Review the staged diff" --role codereviewer
python3 .agents/skills/codex-runner/scripts/run_codex.py --prompt-file /tmp/review.md --role challenger --ephemeral
python3 .agents/skills/codex-runner/scripts/run_codex.py "Audit the auth module" --effort high --json --output-file /tmp/codex-audit.json
python3 .agents/skills/codex-runner/scripts/run_codex.py "Fix it quickly" --model spark --role implementer
python3 .agents/skills/codex-runner/scripts/run_codex.py --resume-last "Apply the top recommendation" --role implementer --full-auto
python3 .agents/skills/codex-runner/scripts/run_codex.py "Investigate the flaky integration test" --background
python3 .agents/skills/codex-runner/scripts/run_codex.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
```

## Behavior

1. Executes `codex exec` (or `codex exec resume` when `--resume`/`--resume-last` is given).
2. Supports role overlays, `--prompt-file`, native resume, and `--session-file` continuation.
3. Always captures the final agent message via `--output-last-message` into the `agent_message` envelope field, and surfaces the Codex `session_id` when detectable.
4. When Codex CLI is invoked with `--json`, the native Codex JSONL event stream remains in `stdout`; the wrapper does not re-shape it.

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Codex CLI not found |
| -3 | Invalid input or unexpected error |

## Prerequisites

- Codex CLI installed and in PATH
- Codex CLI authenticated
