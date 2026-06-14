# Roundtable Seat & Judge Invocations

Exact launch patterns for the five seats and two judges. Everything here is launched **read-only** and with **no role/stance** — the non-negotiables of this skill. Paths assume the installed `.agents/skills/` layout; from the source repo, drop the `.agents/skills/` prefix.

## Table of Contents

1. [Shared rules](#shared-rules)
2. [Launching concurrently](#launching-concurrently)
3. [Seats](#seats)
4. [Disagreement round](#disagreement-round)
5. [Judges](#judges)
6. [Collecting results](#collecting-results)
7. [Host portability](#host-portability)

## Shared rules

- **Read-only, no role:** pass `--restrict-tools` and **no** `--role` to every runner seat/judge (they answer/opine; they never write).
- **No silent swaps:** `--disable-fallback` on every runner.
- **Keep transcripts out of context:** use `--output-file`; read `agent_message` from the file, not raw stdout.
- **Timeout:** `--timeout 600` is ample for answering.
- **Schema enforcement:** `--output-schema` is supported only by **Codex and Kimi**. Gemini and the Opus/Sonnet (native or claude-runner) seats have no schema flag — for them the JSON shape is enforced by the brief's trailing `Return ONLY JSON …` line.

Schemas:
- opening: `.agents/skills/models-round-table/schemas/opening-answer.schema.json`
- disagreement round: `.agents/skills/models-round-table/schemas/disagreement-round.schema.json`
- judge: `.agents/skills/models-round-table/schemas/judge.schema.json`

## Launching concurrently

Issue the three runner `Bash` calls (Codex, Gemini, Kimi) **and** the two `Agent` calls (Opus, Sonnet) in a **single message** so all five run in parallel. Write the round's brief once (e.g. `.ai-workflow/roundtable/<id>/round1-brief.md`) and point every `--prompt-file` at it.

## Seats

Phase 1 (opening) examples; `<id>` = session id, `<dir>` = `.ai-workflow/roundtable/<id>`. For the disagreement round, change `round1` → `round2` and swap the schema to `disagreement-round.schema.json`.

### Codex

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file <dir>/round1-brief.md \
  --restrict-tools --effort high --timeout 600 \
  --json --disable-fallback \
  --output-schema .agents/skills/models-round-table/schemas/opening-answer.schema.json \
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
  --output-schema .agents/skills/models-round-table/schemas/opening-answer.schema.json \
  --output-file <dir>/round1-kimi.json \
  --metadata-json '{"session":"<id>","round":1,"seat":"kimi"}'
```

### Opus 4.8 and Sonnet 4.6 (native subagents)

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

Require the round's exact JSON shape in the prompt so output stays bounded. Fallback (no `Agent` tool): `claude-runner --model claude-opus-4-8` (or `--model claude-sonnet-4-6`) `--restrict-tools --disable-fallback --output-format json --json --output-file <dir>/round1-opus.json` (claude-runner has no `--output-schema`; the brief enforces the shape).

## Disagreement round

Same five seats, `round2` brief = the open `D#` points + every seat's position + "give your final opinion on each," with `--output-schema …/disagreement-round.schema.json` (Codex/Kimi). One round only.

## Judges

After the disagreement round, run **two** judges on the still-open points — read-only, fresh, no role.

- **Opus judge** — native subagent, `model:"opus"`, `mode:"plan"`, given the open `D#` set + every seat's final position; return the judge JSON shape (must be a *different* subagent than the Opus seat).
- **Codex judge** —

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file <dir>/judges-brief.md \
  --restrict-tools --effort high --timeout 600 \
  --json --disable-fallback \
  --output-schema .agents/skills/models-round-table/schemas/judge.schema.json \
  --output-file <dir>/judge-codex.json \
  --metadata-json '{"session":"<id>","role":"judge","judge":"codex"}'
```

A point is resolved when both judges' `ruling` agrees; otherwise the orchestrator makes the final call.

## Collecting results

- `--output-file`: `Read` the JSON and take `agent_message`.
- Native subagents: the `Agent` final message returns to the orchestrator — require the JSON shape so it stays small.
- Envelope: runners return `success`, `return_code`, `effective_runner`, `effective_model`, `auth_ok`, `agent_message`. Any `success=false` / `return_code != 0` is a blocked seat (`-2` = CLI not found) — drop it, lower confidence, never substitute.

## Host portability

| Capability | Claude Code | Codex host |
|------------|-------------|------------|
| Opus / Sonnet seats & Opus judge | native `Agent`, `model:"opus"`/`"sonnet"` | `claude-runner --model claude-opus-4-8` / `--model claude-sonnet-4-6` |
| Codex seat & Codex judge | `codex-runner --effort high` | native `spawn_agent` (`fork_context=false`) |
| Gemini seat | `gemini-runner` | `gemini-runner` |
| Kimi seat | `kimi-runner` | `kimi-runner` |
