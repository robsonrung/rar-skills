# Roundtable Seat Invocations

Exact launch patterns for the four roundtable seats. Every seat is launched **read-only** and with **no role** — the two non-negotiables of this skill. Paths assume the installed `.agents/skills/` layout; when running from the source repo, drop the `.agents/skills/` prefix (skills live at the repo root).

## Table of Contents

1. [Shared flags](#shared-flags)
2. [Launching all seats concurrently](#launching-all-seats-concurrently)
3. [Per-seat commands](#per-seat-commands)
4. [Native Opus 4.8 subagent](#native-opus-48-subagent)
5. [Collecting results](#collecting-results)
6. [Host portability](#host-portability)

---

## Shared flags

Apply to every runner-backed seat (Codex, Gemini, Kimi), in both Round 0 and discussion rounds:

- `--restrict-tools` — forces read-only **without** assigning a role. Do **not** pass `--role`.
- `--disable-fallback` — fail a seat explicitly instead of borrowing another provider.
- `--json` — emit the wrapper envelope.
- `--timeout 600` — interpretation is short; 600s is ample.
- `--output-file <path>` — write the full envelope to disk; stdout becomes a tiny `{success, return_code, output_file}` pointer, keeping large outputs out of the moderator's context.
- `--output-schema <schema>` — enforce the round's JSON shape. **Supported only by Codex and Kimi.** Gemini and the Opus/Claude seat have no schema flag, so for them the JSON shape is enforced by the brief itself (the opening/discussion prompt already ends with the required shape).
- `--prompt-file <brief>` — the shared brief for the round (build it once, reuse for all seats).
- `--metadata-json '{"session":"<id>","round":<n>,"seat":"<seat>"}'`

Schemas live in this skill:
- Round 0: `.agents/skills/model-roundtable/schemas/opening-interpretation.schema.json`
- Discussion rounds: `.agents/skills/model-roundtable/schemas/discussion-round.schema.json`

## Launching all seats concurrently

Issue the three runner `Bash` calls **and** the Opus `Agent` call in a **single message** so they run in parallel. Each runner writes to its own `--output-file`; the moderator reads the files after the calls return. For very long runs, swap `--output-file` for `--background` and collect with `runner_jobs.py result` (see below).

Write the shared brief once per round, e.g. `.ai-workflow/roundtable/<id>/round<n>-brief.md`, then point every `--prompt-file` at it.

## Per-seat commands

Round 0 examples (`<id>` = session id, `<dir>` = `.ai-workflow/roundtable/<id>`). For discussion rounds, change `round0` → `round<n>` and swap the schema to `discussion-round.schema.json`.

### Codex

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file <dir>/round0-brief.md \
  --restrict-tools \
  --effort high \
  --timeout 600 \
  --json \
  --disable-fallback \
  --output-schema .agents/skills/model-roundtable/schemas/opening-interpretation.schema.json \
  --output-file <dir>/round0-codex.json \
  --metadata-json '{"session":"<id>","round":0,"seat":"codex"}'
```

### Gemini

```bash
python3 .agents/skills/gemini-runner/scripts/run_gemini.py \
  --prompt-file <dir>/round0-brief.md \
  --restrict-tools \
  --timeout 600 \
  --json \
  --disable-fallback \
  --output-file <dir>/round0-gemini.json \
  --metadata-json '{"session":"<id>","round":0,"seat":"gemini"}'
```

`gemini-runner` has no `--output-schema` flag and `agy` ignores `--model`/`--output-format` launch flags and exposes no session id — all expected. The JSON shape is enforced by the brief's trailing "Return ONLY JSON …" instruction.

### Kimi

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py \
  --prompt-file <dir>/round0-brief.md \
  --model kimi-code/kimi-for-coding \
  --restrict-tools \
  --output-format stream-json \
  --timeout 600 \
  --json \
  --disable-fallback \
  --output-schema .agents/skills/model-roundtable/schemas/opening-interpretation.schema.json \
  --output-file <dir>/round0-kimi.json \
  --metadata-json '{"session":"<id>","round":0,"seat":"kimi"}'
```

## Native Opus 4.8 subagent

On a Claude Code host, launch the Opus seat as a native subagent (not `claude-runner`). Spawn a **fresh** subagent each round — the moderator holds state, so seats stay stateless.

```text
Agent(
  subagent_type="general-purpose",
  description="Opus 4.8 roundtable seat — round <n>",
  model="opus",                       # resolves to Opus 4.8 (claude-opus-4-8)
  prompt="<round brief: opening or discussion seat prompt from SKILL.md>"
)
```

Keep it read-only by instruction (the brief says "do not solve, plan, or implement; only interpret") — optionally pass `mode: "plan"` to enforce read-only at the harness level. The subagent's final message is returned to the moderator directly; require it to return only the round's JSON shape so the output stays bounded.

Fallback (no `Agent` tool, e.g. non–Claude Code host): `claude-runner --model claude-opus-4-8 --restrict-tools --disable-fallback --output-format json --json --output-file <dir>/round0-opus.json` (claude-runner has no `--output-schema`; the brief enforces the JSON shape).

## Collecting results

- **`--output-file` path (default):** after the parallel calls return, `Read` each `round<n>-<seat>.json` and take `agent_message` (the clean final answer). Ignore raw `stdout`.
- **`--background` path (long runs):** each runner prints `{job_id, ...}`. Collect with the shared jobs CLI:
  ```bash
  python3 .agents/skills/_shared/scripts/runner_jobs.py result <job-id> --json   # prints stored agent_message + session_id
  python3 .agents/skills/_shared/scripts/runner_jobs.py status <job-id>          # running / completed / failed / died
  ```
- **Envelope contract:** every runner returns `runner`, `effective_runner`, `effective_model`, `effective_provider`, `auth_ok`, `fallback_reason`, `success`, `return_code`, plus `agent_message` and (when available) `session_id`. Treat any `success=false` or `return_code != 0` as a blocked seat — drop it, lower confidence, never substitute another model's answer. `return_code -2` means the CLI was not found (seat unavailable).

## Host portability

The roundtable logic is host-agnostic; only the launch mechanism differs.

| Capability | Claude Code | Codex host |
|------------|-------------|------------|
| Opus 4.8 seat | native `Agent`, `model:"opus"` | `claude-runner --model claude-opus-4-8` |
| Codex seat | `codex-runner --effort high` | native `spawn_agent` (`fork_context=false`) |
| Gemini seat | `gemini-runner` | `gemini-runner` |
| Kimi seat | `kimi-runner` | `kimi-runner` |
| Shell / read file | `Bash` / `Read` | `exec_command` |

On a Codex host, run the Codex seat as a native subagent and do not invoke `codex-runner` for it.
