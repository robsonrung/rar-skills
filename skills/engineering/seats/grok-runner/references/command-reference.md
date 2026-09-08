# Command Reference

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Usage

```bash
python3 .agents/skills/grok-runner/scripts/run_grok.py "your prompt here"
```

Use `--working-dir` when the prompt depends on package-local files or generated artifacts; relative `--prompt-file`/`--session-file`/`--output-schema` paths resolve against it (not the process cwd), with `~` expanded. Use repeated `--prompt-file` flags for longer prompts or council overlays. Combine `--output-file` with `--json` to write the full envelope to disk and print only a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}`, keeping large outputs out of the orchestrator's context while still showing which seat answered.


## Options

| Flag | Description | Default |
| --- | --- | --- |
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory (passed as subprocess cwd and grok `--cwd`) | Current dir |
| `--json`, `-j` | Wrap runner output in a JSON envelope | False |
| `--prompt-file` | Read prompt content from a file; may be repeated | None |
| `--model`, `-m` | Grok model id | CLI default (`grok-4.6`) |
| `--output-format`, `-o` | Headless output format `text`, `json`, or `stream-json`; forwarded to grok as `plain`/`json`/`streaming-json` | `text` |
| `--restrict-tools` | Use Grok plan mode (read-only) | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default plan mode | False |
| `--effort`, `-e` | Reasoning effort `low`, `medium`, `high`, `xhigh`, `max`; grok accepts low/medium/high, so `xhigh`/`max` clamp to `high` (recorded via `effort_clamped`) | CLI default (`high`) |
| `--output-schema FILE` | JSON Schema forwarded to grok `--json-schema`, then checked locally; forces `--output-format json` and rejects a non-schema-valid final answer | None |
| `--max-turns N` | Maximum agent turns for the headless run | CLI default |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Grok session by id | None |
| `--continue` | Natively resume the most recent Grok session for this directory | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior debate or workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Accepted for cross-runner parity; grok-runner never falls back (no-op) | False |
| `--output-file` | Write the full JSON envelope to this file atomically; with `--json`, stdout becomes the compact pointer | None |


## Examples

```bash
python3 .agents/skills/grok-runner/scripts/run_grok.py "Summarize the sync service"
python3 .agents/skills/grok-runner/scripts/run_grok.py --prompt-file .ai-workflow/prompts/overlay.md --prompt-file .ai-workflow/prompts/brief.md --role codereviewer --effort high
python3 .agents/skills/grok-runner/scripts/run_grok.py "Read-only architecture review" --restrict-tools --output-format json --json
python3 .agents/skills/grok-runner/scripts/run_grok.py "Continue from the accepted report" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/grok-runner/scripts/run_grok.py "Trace the failing execution path" --role codereviewer --effort high --output-format json --json --output-file .ai-workflow/runs/grok-review.json
python3 .agents/skills/grok-runner/scripts/run_grok.py --prompt-file .ai-workflow/prompts/round1-brief.md --restrict-tools --effort high --json --disable-fallback --output-schema .agents/skills/models-consensus/schemas/opening-answer.schema.json --output-file .ai-workflow/runs/round1-grok.json
python3 .agents/skills/grok-runner/scripts/run_grok.py --resume 019fa905-2a08-7180-83fe-64b8bb369912 "Apply the top recommendation" --role implementer --allow-write
python3 .agents/skills/grok-runner/scripts/run_grok.py "Investigate the flaky test" --output-format json --background
```


## Behavior

1. Maps `--restrict-tools` to Grok `--permission-mode plan`; analysis roles get this by default.
2. Translates the shared output-format enum to grok's: `text` -> `plain`, `json` -> `json`, `stream-json` -> `streaming-json`, always passed explicitly. With json output the native payload stays in `stdout`; the wrapper extracts `agent_message`, `session_id`, `native_model_id`, and `structured_output` into the envelope.
3. Maps `--effort` to grok `--reasoning-effort`, clamping `xhigh`/`max` to `high` (envelope records `effort`, `reasoning_effort_forwarded`, `effort_clamped`).
4. `--output-schema FILE` reads the schema file and forwards its contents inline as grok `--json-schema`, then independently verifies the returned final answer locally. A native exit code of zero alone is insufficient: the answer must be exactly one JSON value matching the schema. On failure the envelope has `success: false`, `status: malformed_output`, and `output_contract_error`. Very large schemas could approach argv limits; keep schemas file-sized, not megabytes.
5. Resolves relative `--prompt-file`/`--session-file`/`--output-schema` paths against `--working-dir` (not the process cwd), with `~` expanded; the working dir is also forwarded as grok `--cwd`.
6. Never falls back to another runner. A missing CLI blocks the seat explicitly (`status: seat_unavailable`, `return_code -2`) — **seat fidelity**: never substitute another model's answer for the Grok seat.


## Return Codes

| Code | Meaning                           |
| ---- | --------------------------------- |
| 0    | Success                           |
| -1   | Timeout exceeded                  |
| -2   | Grok CLI not found                |
| -3   | Invalid input or unexpected error |
