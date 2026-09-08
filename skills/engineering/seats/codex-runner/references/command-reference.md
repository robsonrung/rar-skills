# Command Reference

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Usage

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. In this
source checkout, invoke
`skills/engineering/seats/codex-runner/scripts/run_codex.py` instead.

For repository-aware tasks, prefer `--working-dir` set to the repository root so Codex picks up the applicable local instructions.

Before composing non-trivial prompts (reviews, implementations, research seats), read `references/prompting.md` for task-type XML recipes and anti-patterns.


## Options

| Flag | Description | Default |
| --- | --- | --- |
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Model. Default `gpt-6-astra`. Aliases: `astra`/`codex` -> `gpt-6-astra`; `sol` -> `gpt-5.6-sol`; `terra`/`codex-code` -> `gpt-5.6-terra`; `luna` -> `gpt-5.6-luna`; `spark` -> `gpt-5.3-codex-spark`. | `gpt-6-astra` |
| `--effort`, `-e` | Reasoning effort: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, or `ultra`. Direct calls clamp an unsupported known value and report `requested_effort`, `effort`, and `effort_clamped`. Approved routing plans validate instead of clamping. | CLI default |
| `--sandbox`, `-s` | Codex sandbox mode override | CLI default |
| `--restrict-tools` | Force `--sandbox read-only` | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the read-only default | False |
| `--full-auto` | Pass Codex full auto mode for an explicitly approved unattended run | False |
| `--approval-policy`, `-a` | Codex approval policy override | None |
| `--skip-git-repo-check` | Allow runs outside a Git repo | False |
| `--prompt-file` | Read the prompt from a file (repeatable; files are concatenated in order) | None |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Codex session by id | None |
| `--resume-last` | Resume the most recent Codex session; only safe for one non-concurrent role | False |
| `--session-file` | Append prior workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--ephemeral` | Run without persisting session files to disk | False |
| `--output-schema` | Path to a JSON Schema file for the final response shape | None |
| `--add-dir` | Additional writable directory (repeatable; not valid with `--resume`) | None |
| `--image`, `-i` | Attach an image file to the prompt (repeatable) | None |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--output-file` | Write the full wrapper JSON result atomically to this file | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |

When `--json` and `--output-file` are combined, stdout becomes a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}`, keeping large Codex outputs out of an orchestrating agent's context window while still showing which seat (or labeled fallback) answered.


## Examples

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "Explain this module"
python3 .agents/skills/codex-runner/scripts/run_codex.py "Review the staged diff" --role codereviewer
python3 .agents/skills/codex-runner/scripts/run_codex.py --prompt-file .ai-workflow/prompts/review.md --role challenger --ephemeral
python3 .agents/skills/codex-runner/scripts/run_codex.py "Audit the auth module" --effort high --json --output-file .ai-workflow/runs/codex-audit.json
python3 .agents/skills/codex-runner/scripts/run_codex.py "Fix it quickly" --model spark --role implementer
python3 .agents/skills/codex-runner/scripts/run_codex.py --resume-last "Apply the top recommendation" --role implementer --full-auto
python3 .agents/skills/codex-runner/scripts/run_codex.py "Investigate the flaky integration test" --background
python3 .agents/skills/codex-runner/scripts/run_codex.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
```


## Behavior

1. Executes `codex exec` (or `codex exec resume` when `--resume`/`--resume-last` is given).
2. Supports role overlays, `--prompt-file`, native resume, and `--session-file` continuation. Relative `--prompt-file`/`--session-file`/`--output-schema`/`--image` paths resolve against `--working-dir` (not the process cwd), with `~` expanded.
3. Always captures the final agent message via `--output-last-message` into the `agent_message` envelope field, and surfaces the Codex `session_id` when detectable.
4. When Codex CLI is invoked with `--json`, the native Codex JSONL event stream remains in `stdout`; the wrapper does not re-shape it.


## Return Codes

| Code | Meaning                           |
| ---- | --------------------------------- |
| 0    | Success                           |
| -1   | Timeout exceeded                  |
| -2   | Codex CLI not found               |
| -3   | Invalid input or unexpected error |


## Structured Review Output

A review output schema is bundled at `schemas/review-output.schema.json` (verdict `approve`/`needs-attention`, summary, findings with severity/file/line range/confidence/recommendation, next_steps — the same contract as the official OpenAI Codex plugin). Pair it with a review role so findings are machine-parseable from `agent_message`:

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py "Review the staged diff" \
  --role codereviewer \
  --output-schema .agents/skills/codex-runner/schemas/review-output.schema.json --json
```
