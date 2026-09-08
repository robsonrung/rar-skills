# Command Reference

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Usage

```bash
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. In this
source checkout, invoke
`skills/engineering/seats/dcode-runner/scripts/run_dcode.py` instead.


## Options

| Flag | Description | Default |
| --- | --- | --- |
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


## Examples

```bash
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Explain this code"
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Analyze this file" --output-format json
python3 .agents/skills/dcode-runner/scripts/run_dcode.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Apply the accepted recommendation" --role implementer --auto-approve --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Continue the previous analysis" --dcode-continue
python3 .agents/skills/dcode-runner/scripts/run_dcode.py "Tight loop cap" --max-turns 8
```


## Behavior

1. Executes `dcode -n -q --no-stream --timeout <Ns> [-y] [--max-turns N] [-r [ID]] "<prompt>"`. The dcode `--timeout` is set slightly below the wrapper's `--timeout` so `dcode` self-terminates (and returns its own 124 exit code) before the hard subprocess timeout would kill it; a genuine wrapper timeout still reports `return_code -1` / `status: timeout`. A `dcode` 124 with `--max-turns` set is annotated `max_turns_exceeded: true`.
2. Does not request a permission bypass unless `--auto-approve` is passed (which forwards `-y`).
3. Keeps `runner=dcode` for workflow compatibility and sets `effective_runner=dcode` when the CLI produced the output.
4. Does not pass unsupported flags such as `--model`, `--output-format`, or a read-only convenience mode to `dcode`. `--model` is a request label only. The envelope keeps `effective_model` null and marks the route unverified unless dcode exposes a native serving-model receipt.
5. Resolves relative `--prompt-file`/`--session-file` paths against `--working-dir` (not the process cwd).

### Continuation caveat

`dcode -r` without an ID resumes **the most recent** dcode session in the shared `~/.deepagents/` home — it cannot target a specific session and `session_id` stays null. Use `--resume SESSION_ID` to target a specific session by id when you have one. Avoid running two `--dcode-continue` invocations concurrently against the same `~/.deepagents/` home; they can cross-contaminate.


## Return Codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1+ | DeepAgents CLI (`dcode`) error (passthrough; `124` = dcode's own timeout or `--max-turns` cap) |
| -1 | Wrapper timeout expired |
| -2 | DeepAgents CLI (`dcode`) not found |
| -3 | Invalid input or unexpected error |
