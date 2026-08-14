# Runner Invocation Reference

This reference is for `transport: headless`. The interactive cmux transport has separate command shapes and an artifact relay in [cmux-transport.md](cmux-transport.md).

Complete invocation patterns for every council seat, organized by host capability.

Model selection is not pinned here: pass the roster's alias (`--model opus`) or rely on the runner's default, and read `_shared/references/model-roster.md` for the seat → model mapping. The only id that still appears below is Gemini's, where `--model` is a metadata label rather than a model switch.

## Table of Contents

1. [Host Tool Mapping](#host-tool-mapping)
2. [Native Seat Patterns](#native-seat-patterns)
3. [Runner Fallback Patterns](#runner-fallback-patterns)
4. [Poll-Mode Deltas](#poll-mode-deltas)
5. [Auth and Transport Rules](#auth-and-transport-rules)
6. [Runner Output Contract](#runner-output-contract)

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

### Claude Opus (Claude Code host)

```text
Agent(
  subagent_type="general-purpose",
  description="Claude Opus council seat — round {n}",
  model="opus",
  mode="plan",
  prompt="<stance overlay>\n\n---\n\n<shared brief>",
  run_in_background=true
)
```

Use `model="sonnet"` for the Sonnet seat. Aliases, not pinned ids — the alias resolves to whatever the roster currently pins, and the `effective_model` receipt records what actually served.

### Codex (Codex host)

```text
spawn_agent(
  fork_context=false,
  reasoning_effort="medium",
  message="<stance overlay>\n\n---\n\n<shared brief>"
)
```

Omitting `model` uses the host's Codex model; pass one explicitly only to pin the roster's `codex` seat model deliberately (read the id from the roster, never from this file).

For adversarial or research-heavy rounds, raise `reasoning_effort` to `high`.

If full-history context inheritance is needed, either spawn without explicit `model` and `reasoning_effort` overrides, or keep `fork_context=false` and pass the task-local brief directly.

**Critical**: On a Codex host, do not invoke `codex-runner` or `codex exec` for the Codex seat.

---

## Runner Fallback Patterns

Use runner scripts only when the native seat path is unavailable. Pass `--disable-fallback` so councils fail a seat explicitly instead of silently borrowing another provider.

### Claude Opus / Sonnet (runner fallback)

```bash
python3 .agents/skills/claude-runner/scripts/run_claude.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-stance-claude-opus.md \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-brief.md \
  --timeout 900 \
  --role planner \
  --model opus \
  --output-format json \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-claude-opus-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"claude-opus","stance":"supportive_with_integrity"}'
```

Use `--model sonnet` for the Sonnet seat.

In `inline` artifact mode, combine the prompt and pass it as a single positional prompt instead of `--prompt-file` flags.

### Codex (runner fallback — non-Codex hosts only)

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-codex.md \
  --timeout 900 \
  --role challenger \
  --effort high \
  --json \
  --ephemeral \
  --restrict-tools \
  --disable-fallback \
  --output-schema .agents/skills/models-consensus/schemas/round1-response.schema.json \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-codex-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"codex","stance":"devils_advocate"}'
```

The Codex seat runs `codex-runner`'s default model (the roster's `codex` seat) — omit `--model` rather than pinning an id. `codex-runner` supports `--effort none|minimal|low|medium|high|xhigh`; use `high` for adversarial or research-heavy rounds, mirroring the native Codex seat guidance.

`--output-schema` is natively validated by Codex; for rounds after the first, swap in `schemas/later-round-response.schema.json`. Cline-backed seats accept the same flag (prompt-enforced, not natively validated). Gemini and Claude seats have no schema flag — for them the brief's trailing `Return ONLY JSON …` line holds the shape (see [operations.md#response-schema-validation](operations.md#response-schema-validation)).

### Gemini

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-gemini.md \
  --timeout 900 \
  --role synthesizer \
  --model gemini-3.7-flash \
  --json \
  --output-format json \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-gemini-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"gemini","stance":"balanced_synthesis"}'
```

The consensus Gemini seat does architecture/synthesis reasoning, so it runs **Gemini 3.7 Flash (High)** (`--model` is a metadata label — set agy's own model picker to match). Do not depend on speculative Gemini-only flags such as `--thinking-budget` or a read-only convenience mode.

### Grok

```bash
python3 .agents/skills/grok-runner/scripts/run_grok.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-grok.md \
  --timeout 900 \
  --role implementer --restrict-tools \
  --effort high \
  --json \
  --output-format json \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-grok-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"grok","stance":"pragmatic_engineering"}'
```

The Grok seat runs **Grok 4.5** (the `grok` CLI default) at reasoning-effort high — an independent xAI lineage whose strength is execution-grounded, agentic reasoning, which is why its scheduled stances are `pragmatic_engineering`/`devils_advocate` rather than synthesis. Auth smoke test: `grok -p "Reply with the single word: ready" --output-format json` — a nonzero exit or `{"type":"error",...}` payload blocks the seat. Pass `--restrict-tools` explicitly when overriding the role to `implementer` for a stance: consensus seats never write, and only the `implementer` role escapes the read-only default.

### Kimi

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-kimi.md \
  --timeout 900 \
  --role implementer \
  --output-format stream-json \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-kimi-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"kimi","stance":"pragmatic_engineering"}'
```

`kimi-runner` forwards its default Moonshot model through `cline` — omit `--model` rather than pinning the id here.

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

`glm-runner` delegates to `cline-runner` and forwards a **real** GLM model — omit `--model` and the shim resolves the id per the serving provider, because Z.AI's slug differs by catalog: `z-ai/glm-5.2` on OpenRouter, `zai/glm-5.2` on the cline gateway (`runner=glm`, `effective_runner=cline`, `effective_provider=z-ai` or `zai` accordingly). Never pin a GLM id by hand in council commands — the wrong catalog's slug fails the seat with a native model-not-found error. `--output-schema` is accepted but **prompt-enforced** (not natively validated), so the brief's trailing `Return ONLY JSON …` line is what actually holds the shape.

---

## Poll-Mode Deltas

The command shapes above are written for `debate` (stance overlay + `--role` + a per-round stance in `--metadata-json`). In `mode: poll` the same commands apply with these differences — see [poll-protocol.md](poll-protocol.md):

- **No `--role`, no stance.** Poll seats answer the raw prompt; under the default `no_tools` profile pass `--restrict-tools` (for cline-backed seats — kimi, glm, qwen, muse, gemma, minimax — pass `--no-tools` instead, since their `--restrict-tools` now means read-only plan mode rather than a full tool block) and no role at all. Drop `stance` from `--metadata-json` and keep `{"session":…,"round":…,"seat":…}` (plus `"sample":n` when self-paired).
- **Schemas.** Point `--output-schema` at the poll schema for the stage: `schemas/opening-answer.schema.json` (Phase 1), `schemas/disagreement-round.schema.json` (Phase 3), `schemas/judge.schema.json` (Phase 4 judges), `schemas/organizer-analysis.schema.json` (organizer), `schemas/synthesis.schema.json` (synthesizer). Full mapping: [operations.md#response-schema-validation](operations.md#response-schema-validation).
- **Native validation.** `--output-schema` is natively validated by **Codex and Grok** (`grok-runner` forwards it to grok's own `--json-schema` and forces JSON output for the run). Cline-backed seats accept the flag but enforce it by prompt; Gemini and the Claude seats have no schema flag and rely on the brief's trailing `Return ONLY JSON …` line.
- **Timeout.** `--timeout 600` is ample for a single answering pass; keep 900 for debate rounds that carry a digest.
- **Artifact paths.** Write one brief per phase and point every `--prompt-file` at it; per-seat outputs follow the artifact policy naming (`{session_id}-round-{n}-{seat}-output.json`).
- **Self-pairing.** Launch duplicates with distinct labels (`"seat":"opus#1"`) and distinct `--output-file`s, vary the brief with a `SAMPLE: n` line, and mark `is_duplicate: true` in the seat table.
- **Organizer / judges / synthesizer.** Same runner shapes, always read-only, no role, each a fresh context. For `quality` and `research`, use native `Agent` (`model: "opus"`, `mode: "plan"`) when available or `claude-runner --model opus --effort high --restrict-tools --disable-fallback` elsewhere. For `budget`, use `codex-runner --restrict-tools --effort high --disable-fallback --output-schema <stage schema>`. Judges remain one fresh Opus context and one fresh Codex context.

## Auth and Transport Rules

### `--disable-fallback`

Always pass `--disable-fallback` to runner-backed seats. Councils must fail a seat explicitly instead of silently borrowing another provider.

### Claude `--bare` rule

Do not use `--bare` for Claude runner seats when relying on Claude OAuth or keychain-backed login. Claude's own help states that `--bare` disables OAuth and keychain auth, so a logged-in terminal can still fail with `Not logged in` in headless mode if `--bare` is passed. Only use `--bare` when `ANTHROPIC_API_KEY` or an explicit `apiKeyHelper`-based configuration is the intended auth path.

### GLM / cline transport rule

`glm-runner` delegates to `cline-runner` and forwards a **real** GLM model, resolving the id per the serving provider (`z-ai/glm-5.2` on OpenRouter, `zai/glm-5.2` on the cline gateway — same model, per-catalog slugs), so the seat genuinely runs GLM (not a relabeled other model). It requires the `cline` CLI (`npm install -g cline`) and a Cline provider authenticated via `cline auth` that carries a GLM model. Passing `--model` mutates that provider's persisted default in `~/.cline/data/settings/providers.json`; pass `--data-dir` for automated runs to isolate the side effect. Treat the GLM seat as a single seat; do not pair it with another cline-backed seat under a different label and call it diversity.

---

## Runner Output Contract

The envelope is **not** defined here. Every `--json` runner response conforms to the shared contract in **`_shared/references/runner-common.md`** (schema: `_shared/runner-envelope.schema.json`) — read that for the full required-key list, the seat-fidelity invariant, and the roles table. This section names only what the council does with it.

Three keys carry the council's independence accounting and MUST be recorded in the seat table for every runner-backed seat:

- **`effective_model` — the independence receipt.** The model the backend reports it actually served. Cross-seat agreement counts as independent corroboration **only** when this field confirms the serving model — never the requested model, never a self-claim. An unverified seat's agreement weighs as if it came from the host model, and two seats reporting the same `effective_model` collapse to one independent source.
- **`auth_ok`** — the auth preflight result: `true` on a successful run, `null` when auth was never exercised (missing CLI, invalid input, or a failure before auth), `false` only when an authentication failure was actually detected. Treat anything other than `true` on a launched seat as a blocker, not a warning.
- **`fallback_reason`** — non-null means the runner substituted another path. Any labeled substitution (paired with `fallback_from`) is a **loss of seat independence**: mark the original seat unavailable for independence accounting even when the substitute answered successfully. This is also why `--disable-fallback` is mandatory on every council call — it turns a silent substitution into an explicit seat failure.

Alongside those, the envelope always carries `runner`, `effective_runner`, `effective_provider`, `success`, and `return_code`.

Reading results:
- `--json` controls the wrapper envelope; native CLI JSON or JSONL output stays in `stdout`.
- Prefer `agent_message` (the clean final answer) over parsing `stdout`; `session_id` appears when the underlying CLI reports it. For the Claude seat, `agent_message` requires `--output-format json` or `stream-json`.
- When `--output-file` is used, treat the file as the source of truth — stdout may be only a small acknowledgment payload.
- Do not assume `usage` or token-cost fields exist unless the specific runner emitted them (cost tracking degrades to the round counter, see [operations.md#cost-governance](operations.md#cost-governance)).

Normalize native-seat output into the same envelope shape before comparing seats — including a synthetic `effective_model` for native seats, so the independence rule applies uniformly.
