# Runner Invocation Reference

Complete invocation patterns for every council seat, organized by host capability.

## Table of Contents

1. [Host Tool Mapping](#host-tool-mapping)
2. [Native Seat Patterns](#native-seat-patterns)
3. [Runner Fallback Patterns](#runner-fallback-patterns)
4. [Auth and Transport Rules](#auth-and-transport-rules)
5. [Runner Output Contract](#runner-output-contract)

---

## Host Tool Mapping

Treat host tooling as a compatibility layer. Council logic stays the same; concrete tools differ by platform.

| Capability | Claude Code | Codex |
|------------|-------------|-------|
| Native Claude seat | `Agent` | unavailable |
| Native Codex seat | unavailable | `spawn_agent` + `wait_agent` |
| Interactive question UI | `AskUserQuestion` | `request_user_input` when available, otherwise any equivalent host-native interactive input tool before plain-text fallback |
| Shell execution | `Bash` / `Shell` | `exec_command` |
| Read persisted output | `Read` / `ReadFile` | `exec_command` (`sed`, `cat`, `python3 -m json.tool`) |

Never refer to Claude-only tool names as if they are universal. Branch all seat launch instructions by host capability.
When the workflow needs user input, use the Interactive Questions protocol in SKILL.md.

---

## Native Seat Patterns

### Claude Opus 4.8 (Claude Code host)

```text
Agent(
  subagent_type="general-purpose",
  description="Claude Opus 4.8 council seat — round {n}",
  model="claude-opus-4-8",
  prompt="<stance overlay>\n\n---\n\n<shared brief>",
  run_in_background=true
)
```

Use `model="claude-sonnet-5-0"` for the Sonnet 5.0 seat.

### Codex (Codex host)

```text
spawn_agent(
  fork_context=false,
  model="gpt-5.5",
  reasoning_effort="medium",
  message="<stance overlay>\n\n---\n\n<shared brief>"
)
```

For adversarial or research-heavy rounds, raise `reasoning_effort` to `high`.

If full-history context inheritance is needed, either spawn without explicit `model` and `reasoning_effort` overrides, or keep `fork_context=false` and pass the task-local brief directly.

**Critical**: On a Codex host, do not invoke `codex-runner` or `codex exec` for the Codex seat.

---

## Runner Fallback Patterns

Use runner scripts only when the native seat path is unavailable. Pass `--disable-fallback` so councils fail a seat explicitly instead of silently borrowing another provider.

### Claude Opus 4.8 / Sonnet 5.0 (runner fallback)

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-stance-claude-opus.md \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-brief.md \
  --timeout 900 \
  --role planner \
  --model claude-opus-4-8 \
  --output-format json \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-claude-opus-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"claude-opus","stance":"supportive_with_integrity"}'
```

Use `--model claude-sonnet-5-0` for the Sonnet 5.0 seat.

In `inline` artifact mode, combine the prompt and pass it as a single positional prompt instead of `--prompt-file` flags.

### Codex (runner fallback — non-Codex hosts only)

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-codex.md \
  --timeout 900 \
  --role challenger \
  --model gpt-5.5 \
  --effort high \
  --json \
  --ephemeral \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-codex-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"codex","stance":"devils_advocate"}'
```

`codex-runner` supports `--effort none|minimal|low|medium|high|xhigh`. Use `high` for adversarial or research-heavy rounds, mirroring the native Codex seat guidance.

### Gemini

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-gemini.md \
  --timeout 900 \
  --role synthesizer \
  --json \
  --output-format json \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-gemini-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"gemini","stance":"balanced_synthesis"}'
```

Do not depend on speculative Gemini-only flags such as `--thinking-budget` or a read-only convenience mode.

### Kimi

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-kimi.md \
  --timeout 900 \
  --role implementer \
  --model kimi-code/kimi-for-coding \
  --output-format stream-json \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-kimi-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"kimi","stance":"pragmatic_engineering"}'
```

### GLM

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-glm.md \
  --timeout 900 \
  --role implementer \
  --json \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-glm-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"glm","stance":"pragmatic_engineering"}'
```

`glm-runner` delegates to `dcode-runner`; the GLM identity is a seat label and the underlying model is whichever one `dcode` is configured with. `--model` is metadata only and is not forwarded — to make the GLM seat actually run GLM, configure `dcode` itself to point at a GLM provider (`~/.deepagents/config.toml` or `dcode --default-model openrouter:z-ai/glm-5.2`). The seat has no `--output-schema` flag; rely on the brief's trailing `Return ONLY JSON …` line to enforce shape.

---

## Auth and Transport Rules

### `--disable-fallback`

Always pass `--disable-fallback` to runner-backed seats. Councils must fail a seat explicitly instead of silently borrowing another provider.

### Claude `--bare` rule

Do not use `--bare` for Claude runner seats when relying on Claude OAuth or keychain-backed login. Claude's own help states that `--bare` disables OAuth and keychain auth, so a logged-in terminal can still fail with `Not logged in` in headless mode if `--bare` is passed. Only use `--bare` when `ANTHROPIC_API_KEY` or an explicit `apiKeyHelper`-based configuration is the intended auth path.

### GLM / dcode transport rule

`glm-runner` delegates to `dcode-runner`; the GLM identity is a seat *label* in the envelope and dcode answers with whichever model it has been configured with. To preserve true GLM semantics, the user must point `dcode` at a GLM provider (`~/.deepagents/config.toml` or `~/.deepagents/.env`) — the runner deliberately never forwards `--model` to dcode. Treat the GLM seat as a single seat; do not pair it with another dcode-backed seat under a different label and call it diversity.

---

## Runner Output Contract

All runner-script paths return a wrapper envelope with fields such as:
- `success`
- `stdout`
- `stderr`
- `return_code`
- `runner`
- `effective_runner`
- `role`
- `prompt_file` or `prompt_files` when applicable
- `session_file` when applicable

Important:
- `--json` controls the wrapper envelope.
- Native CLI JSON or JSONL output stays in `stdout`.
- Every runner skill in this repo emits `agent_message` (the clean final answer) when it can extract one, and `session_id` when the underlying CLI reports it — prefer `agent_message` over parsing `stdout`. For the Claude seat this requires `--output-format json` or `stream-json`. Do not assume `usage` or token-cost fields exist unless the specific runner emitted them.
- When `--output-file` is used, treat the file as the source of truth. Stdout may be only a small acknowledgment payload.

Normalize native-seat output into the same envelope shape before comparing seats.
