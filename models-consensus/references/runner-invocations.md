# Runner Invocation Reference

This reference is for `transport: headless`. The interactive cmux transport has separate command shapes and an artifact relay in [cmux-transport.md](cmux-transport.md).

Complete invocation patterns for every council seat, organized by host capability.

Model selection is not pinned here: pass the roster's alias (`--model opus`) or rely on the runner's default, and read `shared/references/model-roster.md` for the seat → model mapping. The only id that still appears below is Gemini's, where `--model` is a metadata label rather than a model switch.

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

`--output-schema` is natively validated by Codex; for rounds after the first, swap in `schemas/later-round-response.schema.json`. Pi-backed and Cline-backed seats receive the schema in their prompt **and are locally post-validated**: only exactly one JSON value that matches the schema is a successful vote. Gemini and Claude seats have no schema flag — for them the brief's trailing `Return ONLY JSON …` line holds the shape (see [operations.md#response-schema-validation](operations.md#response-schema-validation)).

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

The Grok seat runs **Grok 4.6** (the `grok` CLI default) at reasoning-effort high — an independent xAI lineage whose strength is execution-grounded, agentic reasoning, which is why its scheduled stances are `pragmatic_engineering`/`devils_advocate` rather than synthesis. Auth smoke test: `grok -p "Reply with the single word: ready" --output-format json` — a nonzero exit or `{"type":"error",...}` payload blocks the seat. Pass `--restrict-tools` explicitly when overriding the role to `implementer` for a stance: consensus seats never write, and only the `implementer` role escapes the read-only default.

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

`kimi-runner` pins its default Moonshot model per invocation through `pi` on OpenRouter — omit `--model` rather than pinning the id here. The only credential is `OPENROUTER_API_KEY`; there is no lane provisioning, no shared provider state, and Kimi/GLM rounds launch in parallel safely.

### GLM

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-glm.md \
  --timeout 900 \
  --role implementer \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-glm-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"glm","stance":"pragmatic_engineering"}'
```

`glm-runner` delegates to `pi-runner` and pins a **real** GLM model per invocation — `--provider openrouter --model z-ai/glm-5.3-flash` (`runner=glm`, `effective_runner=pi`, `effective_provider=z-ai`). Omit `--model`; the old cline-gateway slug `zai/glm-5.3-flash` is retired along with the per-catalog resolution. `--output-schema` is prompt-guided and then locally enforced; a response outside the contract returns `status: malformed_output` and cannot be counted as a GLM vote.

### Qwen

```bash
python3 .agents/skills/qwen-runner/scripts/run_qwen.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-qwen.md \
  --timeout 900 \
  --role implementer \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-qwen-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"qwen","stance":"pragmatic_engineering"}'
```

`qwen-runner` delegates to `pi-runner` and pins `--provider openrouter --model qwen/qwen3.8-max` per invocation (`runner=qwen`, `effective_runner=pi`, `effective_provider=qwen`) — omit `--model`. The seat is Qwen3.8 Max, the dense open-weight VLM of the Qwen3.8 Max family: the council's coding-first, long-horizon agentic-feasibility voice. Shares the OpenRouter transport and key with Kimi, GLM, and Gemma ([Kimi / GLM / Qwen / Gemma transport rule](#kimi--glm--qwen--gemma-transport-rule-pi-on-openrouter)).

### Gemma

```bash
python3 .agents/skills/gemma-runner/scripts/run_gemma.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-gemma.md \
  --timeout 900 \
  --role implementer \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-gemma-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"gemma","stance":"supportive_with_integrity"}'
```

`gemma-runner` delegates to `pi-runner` and pins `--provider openrouter --model google/gemma-4-31b-it` per invocation — omit `--model`. The seat is Gemma 4 31B (Google DeepMind, 140+ languages, multimodal, LiveCodeBench v6 80) — the cheapest roster seat and the council's grounded, mid-tier, multilingual voice. Shares the OpenRouter transport and key with Kimi, GLM, and Qwen.

### Muse

```bash
python3 .agents/skills/muse-runner/scripts/run_muse.py \
  --prompt-file .ai-workflow/consensus/{session_id}-round-{n}-muse.md \
  --timeout 900 \
  --role implementer \
  --json \
  --no-session-persistence \
  --restrict-tools \
  --disable-fallback \
  --output-file .ai-workflow/consensus/{session_id}-round-{n}-muse-output.json \
  --metadata-json '{"session":"{session_id}","round":{n},"seat":"muse","stance":"pragmatic_engineering"}'
```

`muse-runner` delegates to `cline-runner` and forwards `meta/muse-spark-1.1` on every run — omit `--model`. The seat is Meta's multimodal agentic-reasoning model (1M context): the council's agent-orchestration, tool-use, and computer-use design voice. OpenRouter limits the model to users in the United States — the smoke test blocks the seat elsewhere. It is a Cline-backed seat: if another Cline-backed seat (minimax) runs in the same council, isolate each with its own `--data-dir` or `--lane` — Cline-backed seats that share state must not launch in parallel.

---

## Poll-Mode Deltas

The command shapes above are written for `debate` (stance overlay + `--role` + a per-round stance in `--metadata-json`). In `mode: poll` the same commands apply with these differences — see [poll-protocol.md](poll-protocol.md):

- **No `--role`, no stance.** Poll seats answer the raw prompt; under the default `no_tools` profile pass `--restrict-tools` (for pi-backed seats — kimi, glm, qwen, gemma — and cline-backed seats — muse, minimax — pass `--no-tools` instead, since their `--restrict-tools` means read-only analysis mode rather than a full tool block) and no role at all. Drop `stance` from `--metadata-json` and keep `{"session":…,"round":…,"seat":…}` (plus `"sample":n` when self-paired).
- **Schemas.** Point `--output-schema` at the poll schema for the stage: `schemas/opening-answer.schema.json` (Phase 1), `schemas/disagreement-round.schema.json` (Phase 3), `schemas/judge.schema.json` (Phase 4 judges), `schemas/organizer-analysis.schema.json` (organizer), `schemas/synthesis.schema.json` (synthesizer). Full mapping: [operations.md#response-schema-validation](operations.md#response-schema-validation).
- **Validation receipt.** `--output-schema` is natively constrained by **Codex and Grok** (`grok-runner` forwards it to grok's own `--json-schema` and forces JSON output for the run). Grok, Pi-backed, and Cline-backed seats also validate the final answer locally, so an exit code of zero is insufficient: a vote requires exactly one schema-valid JSON value. Gemini and the Claude seats have no schema flag and rely on the brief's trailing `Return ONLY JSON …` line.
- **Timeout.** `--timeout 600` is ample for a single answering pass; keep 900 for debate rounds that carry a digest.
- **Artifact paths.** Write one brief per phase and point every `--prompt-file` at it; per-seat outputs follow the artifact policy naming (`{session_id}-round-{n}-{seat}-output.json`).
- **Self-pairing.** Launch duplicates with distinct labels (`"seat":"opus#1"`) and distinct `--output-file`s, vary the brief with a `SAMPLE: n` line, and mark `is_duplicate: true` in the seat table.
- **Organizer / judges / synthesizer.** Same runner shapes, always read-only, no role, each a fresh context. For `quality` and `research`, use native `Agent` (`model: "opus"`, `mode: "plan"`) when available or `claude-runner --model opus --effort high --restrict-tools --disable-fallback` elsewhere. For `budget`, use `codex-runner --restrict-tools --effort high --disable-fallback --output-schema <stage schema>`. Judges remain one fresh Opus context and one fresh Codex context.

## Auth and Transport Rules

### `--disable-fallback`

Always pass `--disable-fallback` to runner-backed seats. Councils must fail a seat explicitly instead of silently borrowing another provider.

### Claude `--bare` rule

Do not use `--bare` for Claude runner seats when relying on Claude OAuth or keychain-backed login. Claude's own help states that `--bare` disables OAuth and keychain auth, so a logged-in terminal can still fail with `Not logged in` in headless mode if `--bare` is passed. Only use `--bare` when `ANTHROPIC_API_KEY` or an explicit `apiKeyHelper`-based configuration is the intended auth path.

### Kimi / GLM / Qwen / Gemma transport rule (Pi on OpenRouter)

`kimi-runner`, `glm-runner`, `qwen-runner`, and `gemma-runner` delegate to `pi-runner` and pin their real models per invocation (`moonshotai/kimi-k3`, `z-ai/glm-5.3-flash`, `qwen/qwen3.8-max`, `google/gemma-4-31b-it`, all `--provider openrouter`), so each seat genuinely runs its named model — there is no mutable provider state that can silently reroute it. They require the `pi` CLI (`npm install -g @mariozechner/pi-coding-agent`) and `OPENROUTER_API_KEY`. Note the correlated dependency: all four seats share one serving gateway and one key, so an OpenRouter outage or key problem drops them together — account for that in diversity confidence, and treat each as a single seat (model-lineage diversity still holds: Moonshot, Z.AI, Qwen, and Google are distinct labs, but do not pair any of them with another OpenRouter-served seat under a different label and call it transport diversity).

---

## Runner Output Contract

The envelope is **not** defined here. Every `--json` runner response conforms to the shared contract in **`shared/references/runner-common.md`** (schema: `shared/runner-envelope.schema.json`) — read that for the full required-key list, the seat-fidelity invariant, and the roles table. This section names only what the council does with it.

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
