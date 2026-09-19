# Command Reference

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

Model and reasoning defaults are read from `shared/model-routing.json`.
Use the approved route values in placeholders below; `--help` shows the current
adapter choices.

## Usage

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "your prompt here"
```

Paths in the examples use the installed `.agents/skills/` layout. In this
source checkout, invoke
`skills/engineering/seats/gemini-runner/scripts/run_gemini.py` instead.


## Options

| Flag | Description | Default |
| --- | --- | --- |
| `--timeout`, `-t` | Maximum execution time in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current directory |
| `--json`, `-j` | Wrap runner output in JSON | False |
| `--model`, `-m` | Compatibility request label from the central configuration. The adapter uses its own model settings and does not forward this flag. | Configured adapter default |
| `--output-format`, `-o` | Response format hint: `text`, `json`, or `stream-json`. **Advisory only** — `agy` print mode has no output-format launch flag, so the wrapper just asks the model for the format in the prompt. For `json` it does a best-effort fence-strip and reports `output_json_valid`; it does not guarantee or re-shape the output. | `text` |
| `--prompt-file` | Read the prompt from a file (repeatable; files are concatenated in order) | None |
| `--role` | Apply a role overlay | None |
| `--restrict-tools` | Add a read-only analysis overlay to the prompt | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default read-only overlay | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior workflow context for cross-runner continuation | None |
| `--agy-continue` | Resume the latest shared Antigravity CLI conversation; unsafe for concurrent roles | False |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope atomically to this path; with `--json`, stdout becomes a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` | None |


## Examples

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Explain this code"
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Analyze this file" --output-format json
python3 .agents/skills/gemini-runner/scripts/run_gemini.py --prompt-file .ai-workflow/prompts/review.md --role codereviewer
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Implement the accepted recommendation" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/gemini-runner/scripts/run_gemini.py "Continue the previous analysis" --agy-continue
```


## Behavior

1. Executes `agy [--continue] --print-timeout <Ns> --print "<prompt>"`. The `--print-timeout` is set slightly below the wrapper's `--timeout` so `agy` self-terminates (and returns its own exit code) before the hard subprocess timeout would kill it; a genuine wrapper timeout still reports `return_code -1` / `status: timeout`.
2. Does not request a permission bypass.
3. Keeps `runner=gemini` for workflow compatibility and sets `effective_runner=agy` when Antigravity CLI produced the output.
4. Does not pass unsupported Gemini CLI flags such as `--model`, `--output-format`, `--thinking-budget`, or a read-only convenience mode to `agy`. `--model` is a request label only; the envelope records `model_receipt.status: unverified` unless a native receipt identifies the serving model. Configure agy's `/model` picker to Gemini 3.8 Flash (High) when that route is selected.
5. Resolves relative `--prompt-file`/`--session-file` paths against `--working-dir` (not the process cwd).

### Continuation caveat

`agy` exposes no session id, so `--agy-continue` resumes **the most recent** Antigravity CLI conversation in the shared `agy` home — it cannot target a specific session and `session_id` stays null. Avoid running two `--agy-continue` invocations concurrently against the same `agy` home; they can cross-contaminate.


## Return Codes

| Code | Meaning                                     |
| ---- | ------------------------------------------- |
| 0    | Success                                     |
| 1+   | Antigravity CLI (`agy`) error (passthrough) |
| -1   | Timeout expired                             |
| -2   | Antigravity CLI (`agy`) not found           |
| -3   | Invalid input or unexpected error           |
