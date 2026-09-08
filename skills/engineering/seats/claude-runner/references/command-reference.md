# Command Reference

Load the section needed for the selected operation. Prose paths resolve from the loaded skill root. Command examples using `.agents/skills/` assume a flat installation; substitute the actual loaded skill path in other layouts.

## Usage

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py "your prompt here"
```

Use `--working-dir` when the prompt depends on package-local files or generated artifacts; relative `--prompt-file`/`--session-file` paths resolve against it (not the process cwd), with `~` expanded. Use repeated `--prompt-file` flags for longer prompts or council overlays. Combine `--output-file` with `--json` to write the full envelope to disk and print only a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}`, keeping large outputs out of the orchestrator's context while still showing which seat (or labeled fallback) answered.


## Options

| Flag | Description | Default |
| --- | --- | --- |
| `--timeout`, `-t` | Timeout in seconds | 3600 |
| `--working-dir`, `-w` | Working directory | Current dir |
| `--json`, `-j` | Wrap runner output in a JSON envelope | False |
| `--prompt-file` | Read prompt content from a file; may be repeated | None |
| `--model`, `-m` | Claude model alias (`fable`, `opus`, `sonnet`) or a full model id. The canonical pins live in `shared/references/model-roster.md`. Approved routes use the pinned id so a model change cannot be silent. | CLI default |
| `--output-format`, `-o` | Claude print-mode output format: `text`, `json`, or `stream-json` | `text` |
| `--safe` | Informational no-op; permission checks are always enabled whether or not the flag is passed | True |
| `--bare` | Use Claude bare mode for faster startup and fewer implicit context sources | False |
| `--no-session-persistence` | Do not persist Claude session files to disk | False |
| `--restrict-tools` | Use Claude planning mode (read-only) | True for analysis roles |
| `--allow-write` | Opt an analysis role out of the default planning mode | False |
| `--effort`, `-e` | Claude effort level: `low`, `medium`, `high`, `xhigh`, `max` | CLI default |
| `--role` | Apply a role overlay | None |
| `--resume SESSION_ID` | Natively resume a Claude session by id | None |
| `--continue` | Resume the most recent Claude conversation; only safe for one non-concurrent role | False |
| `--background` | Run as a tracked background job and return a job id immediately | False |
| `--session-file` | Append prior debate or workflow context for cross-runner continuation | None |
| `--metadata-json` | Attach structured execution metadata to the prompt | None |
| `--disable-fallback` | Fail instead of routing to another runner | False |
| `--output-file` | Write the full JSON envelope to this file atomically; with `--json`, stdout becomes a compact pointer `{success, return_code, output_file, runner, effective_runner, effective_provider, fallback_from, status}` | None |


## Examples

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py "Summarize the sync service"
python3 .agents/skills/claude-runner/scripts/run_claude.py "Compare two implementation plans" --model sonnet
python3 .agents/skills/claude-runner/scripts/run_claude.py --prompt-file .ai-workflow/prompts/overlay.md --prompt-file .ai-workflow/prompts/brief.md --role codereviewer --model opus
python3 .agents/skills/claude-runner/scripts/run_claude.py "Read-only architecture review" --restrict-tools --bare --no-session-persistence
python3 .agents/skills/claude-runner/scripts/run_claude.py "Continue from the accepted report" --role implementer --session-file .ai-workflow/consensus/feature-x.md
python3 .agents/skills/claude-runner/scripts/run_claude.py "Deep audit of the auth module" --role codereviewer --effort high --output-format json --json
python3 .agents/skills/claude-runner/scripts/run_claude.py --resume 1f2e3d4c-... "Apply the top recommendation" --role implementer --allow-write
python3 .agents/skills/claude-runner/scripts/run_claude.py "Investigate the flaky test" --output-format json --background
```


## Behavior

1. Maps `--restrict-tools` to Claude `--permission-mode plan`; analysis roles get this by default.
2. When `--output-format json` or `stream-json` is used, the native Claude payload stays in `stdout`; the wrapper does not re-shape it, but it extracts `agent_message` and `session_id` into the envelope.
3. `--resume`/`--continue` map to the native Claude CLI flags; `--effort` maps to Claude `--effort`.
4. Resolves relative `--prompt-file`/`--session-file` paths against `--working-dir` (not the process cwd), with `~` expanded.


## Return Codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| -1 | Timeout exceeded |
| -2 | Claude CLI not found |
| -3 | Invalid input or unexpected error |
| -4 | Bare mode without `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (bare mode disables OAuth/keychain auth) |
