# Command Reference

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

Model and reasoning defaults are read from `shared/model-routing.json`.
Use the approved route values in placeholders below; `--help` shows the current
adapter choices.

## Usage

```bash
python3 .agents/skills/cline-runner/scripts/run_cline.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. In this
source checkout, invoke
`skills/engineering/seats/cline-runner/scripts/run_cline.py` instead.


## Supported Options

| Flag | Description | Default |
| --- | --- | --- |
| `--timeout`, `-t` | Maximum execution time in seconds; also passed to native `--timeout` (minus a 5s margin) so Cline self-terminates cleanly first | `3600` |
| `--working-dir`, `-w` | Working directory for execution | Current dir |
| `--json`, `-j` | Output wrapper results in JSON format | `False` |
| `--prompt-file` | Read prompt content from a file; repeatable | None |
| `--model`, `-m` | Exact approved model or supported alias from the central configuration. | Configured adapter default |
| `--provider`, `-P` | Cline provider id (native `-P`) | Locally configured default |
| `--output-format`, `-o` | `text` or `stream-json` (native `--json` on/off) | `stream-json` |
| `--thinking` | Reasoning selection from the central configuration; `--help` lists accepted values. Approved routes reject unsupported selections. | Configured adapter default |
| `--session` | Resume a specific Cline session by id (native `--id`) | None |
| `--worktree` | Auto-create a detached git worktree under `~/.cline/worktrees/` and run there (native `--worktree`) | `False` |
| `--data-dir` | Isolated local state directory (native `--data-dir`) — use for automated runs to avoid mutating `~/.cline` | None |
| `--lane` | Named isolated lane, fixing provider/model/state and acquiring a bounded credential-pool slot | None |
| `--lane-file` | Optional local JSON override for custom lanes (shape: `references/cline-lanes.example.json`); built-in `kimi`/`glm` lanes need no file | None |
| `--lane-wait-timeout` | Seconds to wait for a lane credential-pool slot | `30` |
| `--config` | Configuration directory (native `--config`) | None |
| `--system` | Override the default Cline system prompt (native `--system`) | None |
| `--restrict-tools` | Force read-only plan mode (native `--plan`, tools auto-approved) | `True` for analysis roles |
| `--no-tools` | Force native `--auto-approve false`: every tool call fails, seat answers from the prompt alone | `False` |
| `--allow-write` | Opt an analysis role out of the read-only plan-mode default | `False` |
| `--background` | Run as a tracked background job and return a job id immediately | `False` |
| `--role` | Apply a role overlay | None |
| `--session-file` | Append prior workflow context from a file | None |
| `--metadata-json` | JSON string to embed as execution metadata | None |
| `--output-schema` | Path to a JSON Schema final-response contract; the prompt instructs Cline and the wrapper rejects non-JSON, concatenated JSON, and schema-invalid terminal answers | None |
| `--ephemeral`, `--no-session-persistence`, `--safe`, `--bare`, `--disable-fallback` | Accepted for cross-runner parity; no effect on Cline CLI | `False` |
| `--output-file` | Write the wrapper JSON result to this file atomically | None |


## Examples

```bash
python3 .agents/skills/cline-runner/scripts/run_cline.py "Summarize the core module architecture"
python3 .agents/skills/cline-runner/scripts/run_cline.py "Explain this module" --model '<approved-model>'
python3 .agents/skills/cline-runner/scripts/run_cline.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer
python3 .agents/skills/cline-runner/scripts/run_cline.py "Implement the accepted fix" --role implementer --model '<approved-model>'
python3 .agents/skills/cline-runner/scripts/run_cline.py "Resume and continue" --session 1782865158637_s2n62
python3 .agents/skills/cline-runner/scripts/run_cline.py "Run this in CI" --model '<approved-model>' --data-dir .ai-workflow/cline-state/ci
python3 .agents/skills/cline-runner/scripts/run_cline.py --seat muse "Review this change" --restrict-tools --json
```


## Behavior

1. Runs `cline <prompt> --cwd <dir> --auto-approve <bool>` directly for non-interactive execution, appending native `--plan` in the read-only `plan` tool mode. Relative `--prompt-file`/`--session-file`/`--output-schema` paths resolve against `--working-dir` (not the process cwd), with `~` expanded.
2. Defaults to native `--json` (NDJSON event stream) so callers can consume streaming output; the wrapper parses the terminal `run_result` line for the final text, `finishReason`, and resolved model.
3. Returns a wrapper envelope with `success`, `stdout`, `stderr`, `return_code`, `runner`, `effective_runner`.
4. Keeps native Cline output in `stdout`; the wrapper `--json` flag only controls the outer envelope.
5. Never falls back to another provider. Missing CLI or auth failures block the seat explicitly.
6. Trusts the process exit code for `success`, but overrides to failure if the stream's `finishReason` disagrees (e.g. a native agent error reported with an unexpectedly clean exit), so `success` is never self-contradictory with `finish_reason`.
7. `session_id` is recovered with a best-effort `cline history --json` lookup by working directory and start time immediately after the run, since Cline's own stream never reports one.
8. A lane records `lane`, `credential_pool`, `lane_max_concurrency`, `lane_slot`, and `state_isolated: true` on its envelope. The provider/model receipt from Cline remains authoritative for independence accounting.
9. With `--output-schema`, parses exactly one terminal JSON value (a single JSON code fence is accepted), validates the repository's supported Draft-7 subset locally, then emits the canonical JSON in `agent_message` and `structured_output`. Invalid output returns `success: false`, `status: malformed_output`, and `output_contract_error`.


## Return Codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Cline CLI not found |
| -3 | Invalid input, native agent error (non-`completed` `finishReason`), or unexpected error |
