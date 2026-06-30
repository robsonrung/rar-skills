# Roundtable Seat, Organizer, Judge & Synthesizer Invocations

Exact launch patterns for the seats, the organizer, the two judges, and the synthesizer. Everything here is launched **read-only** (no write/exec) and with **no role/stance** — the non-negotiables of this skill. Paths assume the installed `.agents/skills/` layout; from the source repo, drop the `.agents/skills/` prefix.

## Table of Contents

1. [Shared rules](#shared-rules)
2. [Tool profiles](#tool-profiles)
3. [Self-pairing (duplicate seats)](#self-pairing-duplicate-seats)
4. [Launching concurrently](#launching-concurrently)
5. [Seats](#seats)
6. [Organizer](#organizer)
7. [Gap-repair round](#gap-repair-round)
8. [Judges](#judges)
9. [Synthesizer](#synthesizer)
10. [Collecting results](#collecting-results)
11. [Host portability](#host-portability)

## Shared rules

- **No mutation, no role:** pass `--restrict-tools` and **no** `--role` to every runner seat/organizer/judge/synthesizer under the default `no_tools` profile (they answer/opine; they never write/exec). See **Tool profiles** for the read-only-tools exception.
- **No silent swaps:** `--disable-fallback` on every runner.
- **Keep transcripts out of context:** use `--output-file`; read `agent_message` from the file, not raw stdout.
- **Timeout:** `--timeout 600` is ample for answering.
- **Schema enforcement:** `--output-schema` is supported by **Codex and Kimi only**. GLM (via dcode-runner), Gemini, and the Opus/Sonnet (native or claude-runner) seats have no schema flag — for them the JSON shape is enforced by the brief's trailing `Return ONLY JSON …` line.
- **Transient retry:** a runner returning `success=false` with no output file (e.g. `return_code -3` on a busy concurrent launch) may be **retried once sequentially** before the seat is dropped — concurrent back-to-back launches occasionally trip this and a lone retry clears it.

Schemas:
- opening: `.agents/skills/models-roundtable/schemas/opening-answer.schema.json`
- organizer analysis: `.agents/skills/models-roundtable/schemas/organizer-analysis.schema.json`
- gap-repair round: `.agents/skills/models-roundtable/schemas/disagreement-round.schema.json`
- judge: `.agents/skills/models-roundtable/schemas/judge.schema.json`
- synthesis: `.agents/skills/models-roundtable/schemas/synthesis.schema.json`

## Tool profiles

Apply the **same** profile to every active seat (identical conditions — Hard Rule 5):

- `no_tools` (default) — keep `--restrict-tools` on every runner; native seats run `mode:"plan"`, read-only by instruction. Best for repo/code decisions.
- `repo_read_only` — allow read-only repo reads; the brief lists the paths. No web, no writes.
- `research_read_only` — enable read-only web for runners that support it (Codex/Gemini/Kimi web search/fetch; native Claude seats via their web tools) and require each seat to return `sources_used[]` + `failed_lookups[]`. No repo, no writes.
- `repo_plus_research` — both of the above, read-only.

Never pass write/exec tools. If a seat's host cannot honor the chosen read-only profile, **drop that seat** rather than run it with a different toolset.
For GLM, use research profiles only after confirming dcode is configured with `TAVILY_API_KEY` (in `~/.deepagents/.env` or the environment) so it exposes the same read-only web behavior as the other active seats; otherwise drop that seat for the run.

## Self-pairing (duplicate seats)

When self-pairing (auto-fallback to reach quorum, or a deliberate preset), launch the same model more than once with **distinct labels** in `--metadata-json` (`"seat":"opus#1"`, `"seat":"opus#2"`) and distinct `--output-file`s. Vary the brief trivially per sample (e.g. a `SAMPLE: n` line) so the runs are independent. Mark every duplicate `is_duplicate:true` in the seat table and lower **diversity confidence** in the report; never report duplicates as distinct models.

## Launching concurrently

Issue all available runner `Bash` calls (normally four) **and** the two `Agent` calls (Opus, Sonnet) in a **single message** so all seats run in parallel. Write the round's brief once (e.g. `.ai-workflow/roundtable/<id>/round1-brief.md`) and point every `--prompt-file` at it.

## Seats

Phase 1 (opening) examples; `<id>` = session id, `<dir>` = `.ai-workflow/roundtable/<id>`. For the gap-repair round, change `round1` → `round2` and swap the schema to `disagreement-round.schema.json`. Under a non-default tool profile, also relax `--restrict-tools` per [Tool profiles](#tool-profiles) — identically across all seats.

### Codex

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file <dir>/round1-brief.md \
  --restrict-tools --effort high --timeout 600 \
  --json --disable-fallback \
  --output-schema .agents/skills/models-roundtable/schemas/opening-answer.schema.json \
  --output-file <dir>/round1-codex.json \
  --metadata-json '{"session":"<id>","round":1,"seat":"codex"}'
```

### Gemini

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py \
  --prompt-file <dir>/round1-brief.md \
  --restrict-tools --timeout 600 \
  --json --disable-fallback \
  --output-file <dir>/round1-gemini.json \
  --metadata-json '{"session":"<id>","round":1,"seat":"gemini"}'
```

`gemini-runner` has no `--output-schema`; the brief enforces the shape.

### Kimi

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py \
  --prompt-file <dir>/round1-brief.md \
  --model kimi-code/kimi-for-coding \
  --restrict-tools --output-format stream-json --timeout 600 \
  --json --disable-fallback \
  --output-schema .agents/skills/models-roundtable/schemas/opening-answer.schema.json \
  --output-file <dir>/round1-kimi.json \
  --metadata-json '{"session":"<id>","round":1,"seat":"kimi"}'
```

### GLM

```bash
python3 .agents/skills/glm-runner/scripts/run_glm.py \
  --prompt-file <dir>/round1-brief.md \
  --restrict-tools --timeout 600 \
  --json --disable-fallback \
  --output-file <dir>/round1-glm.json \
  --metadata-json '{"session":"<id>","round":1,"seat":"glm"}'
```

`glm-runner` delegates to `dcode-runner`; the GLM identity is a seat label and the underlying model is whichever one `dcode` is configured with. `--model` is metadata only and is not forwarded — to make the GLM seat actually run GLM, configure `dcode` itself (`~/.deepagents/config.toml` or `dcode --default-model openrouter:z-ai/glm-5.2`). There is no `--output-schema` flag; the brief's trailing `Return ONLY JSON …` line enforces the shape. For the gap-repair round, change `round1` → `round2` and write to `round2-glm.json`.

### Opus 4.8 and Sonnet 5.0 (native subagents)

On a Claude Code host, launch these as native subagents (read-only by instruction; optionally `mode: "plan"`). Spawn fresh each round — the orchestrator holds state.

```text
Agent(
  subagent_type="general-purpose",
  description="Opus 4.8 roundtable seat — round <n>",
  model="opus",                 # Sonnet seat: model="sonnet"
  mode="plan",
  prompt="<round brief: opening or disagreement seat prompt from SKILL.md>"
)
```

Require the round's exact JSON shape in the prompt so output stays bounded. Fallback (no `Agent` tool): `claude-runner --model claude-opus-4-8` (or `--model claude-sonnet-5-0`) `--restrict-tools --disable-fallback --output-format json --json --output-file <dir>/round1-opus.json` (claude-runner has no `--output-schema`; the brief enforces the shape).

## Organizer

After Phase 1, run **one** organizer over **all** seat answers — read-only, fresh, no role — to emit the five-dimension structured analysis. Default Opus 4.8 (native subagent, `model:"opus"`, `mode:"plan"`, a *different* subagent than the Opus seat); fall back to the strongest available seat model. The brief = every seat's answer + "produce the organizer analysis". Native seats enforce the shape via the brief; on a Codex host use `--output-schema …/organizer-analysis.schema.json`. The organizer's `material_gaps` flag gates Phase 3 (skip the gap-repair round when `false`).

## Gap-repair round

Run only when the organizer set `material_gaps:true`. Same seats, `round2` brief = the open `C#`/`B#`/`U#` points (+ each seat's position + the organizer analysis) and "resolve the contradiction / fill the blind spot / defend or refute the unique insight, **with evidence** — this is targeted repair, not re-voting." Use `--output-schema …/disagreement-round.schema.json` for runner seats that support schema output (Codex and Kimi); GLM, Gemini, and Claude seats rely on the brief's `Return ONLY JSON …` line. One round only.

## Judges

After the gap-repair round, run **two** judges on the still-open points — read-only, fresh, no role. Each judge receives the open points + every seat's final position + **the organizer analysis** (which it validates/challenges, not re-derives) and must fill `sensitivity_note` per verdict.

- **Opus judge** — native subagent, `model:"opus"`, `mode:"plan"`, given the open points + every seat's final position + the organizer analysis; return the judge JSON shape (must be a *different* subagent than the Opus seat).
- **Codex judge** —

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file <dir>/judges-brief.md \
  --restrict-tools --effort high --timeout 600 \
  --json --disable-fallback \
  --output-schema .agents/skills/models-roundtable/schemas/judge.schema.json \
  --output-file <dir>/judge-codex.json \
  --metadata-json '{"session":"<id>","role":"judge","judge":"codex"}'
```

A point is resolved when both judges' `ruling` agrees; otherwise the orchestrator makes the final call. Carry every `sensitivity_note` into the report as confidence-drag.

## Synthesizer

After judging + the orchestrator's final calls, run **one** synthesizer — read-only, fresh, no role — to write the consensus answer. Default Opus 4.8 (native subagent, `model:"opus"`, `mode:"plan"`; a *different* context than the Opus seat/organizer/judge). The brief = the full record (organizer analysis + locked consensus + resolved/open points with rulings + every seat answer) and "write the consensus answer with an attribution map." Native seats enforce the shape via the brief; on a Codex host use `--output-schema …/synthesis.schema.json`. The orchestrator then **validates** every claim's attribution against the record before adopting the answer (send back once if it drifts).

## Collecting results

- `--output-file`: `Read` the JSON and take `agent_message`.
- Native subagents: the `Agent` final message returns to the orchestrator — require the JSON shape so it stays small.
- Envelope: runners return `success`, `return_code`, `effective_runner`, `effective_model`, `auth_ok`, `agent_message`. Any `success=false` / `return_code != 0` is a blocked seat (`-2` = CLI not found) — drop it, lower confidence, never substitute.

## Host portability

| Capability | Claude Code | Codex host |
|------------|-------------|------------|
| Opus / Sonnet seats & Opus judge | native `Agent`, `model:"opus"`/`"sonnet"` | `claude-runner --model claude-opus-4-8` / `--model claude-sonnet-5-0` |
| Organizer & synthesizer (default Opus) | native `Agent`, `model:"opus"`, `mode:"plan"` | `claude-runner --model claude-opus-4-8` (schema via `--output-schema`) |
| Codex seat & Codex judge | `codex-runner --effort high` | native `spawn_agent` (`fork_context=false`) |
| Gemini seat | `gemini-runner` | `gemini-runner` |
| Kimi seat | `kimi-runner` | `kimi-runner` |
| GLM seat | `glm-runner` (via `dcode-runner`) | `glm-runner` (via `dcode-runner`) |
