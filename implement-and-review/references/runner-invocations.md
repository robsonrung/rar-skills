# Seat Invocations

Exact launch patterns for the implement-and-review seats. Seat → model ids (and the alias-first policy: prefer `--model opus` over a pinned id) live in `shared/references/model-roster.md`. Paths assume the installed `.agents/skills/` layout; from the source repo, drop the `.agents/skills/` prefix. `<id>` = session id, `<base>` = the commit recorded at preflight, `<wt-fe>` / `<wt-be>` = the frontend/backend worktree paths (see [worktree-and-integration.md](worktree-and-integration.md)).

## Table of Contents

1. [Launcher script (one-call setup)](#launcher-script-one-call-setup)
2. [Shared rules](#shared-rules)
3. [Standard frontend implementer — Codex seat](#standard-frontend-implementer--codex-seat)
4. [Visual or creative frontend implementer — Opus seat](#visual-or-creative-frontend-implementer--opus-seat)
5. [Backend implementer — Codex seat](#backend-implementer--codex-seat)
6. [Cross-model review routing](#cross-model-review-routing)
7. [Collecting results](#collecting-results)
8. [Host portability](#host-portability)

## Launcher script (one-call setup)

`scripts/launch.py` collapses Phase 1's deterministic setup into one call: it creates the per-track git worktrees+branches off a clean base, fires the runner-backed implementer(s) as tracked background jobs, writes `launch-manifest.json`, and polls them. The default frontend route is the Codex seat for standard product UI. Visual reconstruction and highly creative work select the Opus seat.

```bash
L=.agents/skills/implement-and-review/scripts/launch.py

# default: standard product interface; fire both frontend and backend Codex jobs
python3 $L launch --session-id <id> --fe-brief <fe.md> --be-brief <be.md>

# visual reconstruction or highly creative work; leave frontend for native Opus
python3 $L launch --session-id <id> --fe-brief <fe.md> --be-brief <be.md> --fe-seat opus

# same visual route through claude-runner
python3 $L launch --session-id <id> --fe-brief <fe.md> --be-brief <be.md> --fe-seat opus --fe-mode runner

# single-track task:
python3 $L launch --session-id <id> --be-brief <be.md> --no-frontend

# one task of a parallel feature build — --slice namespaces worktrees/branches/artifacts
# (used by implement-feature to isolate per-task builds):
python3 $L launch --session-id <id> --slice <S> --be-brief <s-be.md> --fe-brief <s-fe.md>
python3 $L poll  --session-id <id> --slice <S> --wait

# poll to a consolidated status (optionally block until terminal):
python3 $L poll --session-id <id> --wait

# remove the session's worktrees when done (branches kept unless --delete-branches):
python3 $L cleanup --session-id <id> [--slice <S>]
```

Key flags: `--slice <S>` (per-task namespace for parallel feature builds: worktrees at `…/impl-review-<id>/<S>/{frontend,backend}`, branches `impl/<S>-<track>-<id>`, artifacts under `…/<id>/<S>/`), `--fe-seat {codex|opus}` (default `codex`), `--fe-mode {auto|subagent|runner}` (default `auto`), `--no-frontend`/`--no-backend`, `--no-full-auto` (Codex writes off), `--base <sha>` (branch off a given head, not stale base), `--worktrees-dir <dir>`, `--allow-dirty`, `--force` (recreate existing worktrees), `--dry-run`. The `launch`/`poll` output is JSON on stdout; `poll` exits non-zero if any runner track failed.

For a standalone single task, omit `--slice`. The `--slice` namespacing exists so **`implement-feature`** can run many per-task builds in parallel without collision; cross-task scheduling and integration live in that skill, not here.

- The manifest records each track's `worktree`, `branch`, `brief`, `job_id`, and `working_dir`. `poll` reuses `working_dir` to find each job under `<worktree>/.ai-workflow/runner-jobs/`, and on completion reports `success` and `runner_session_id` (use it for `--resume` fix rounds).
- Briefs must already exist (you write them in Phase 0/1); the launcher copies them into the artifact dir for provenance.
- The launcher only sets up and fires Phase 1 implement runs. Reviews, fix loops, integration, the `coding-review-simplify` pass, and the final `full-review` are driven by you — the review seats with the commands below, the two skills by invoking them directly.

When you want fine control, skip the launcher and use the per-seat commands directly.

## Shared rules

- **Writers vs. reviewers:** implementers get write access (only after the Phase 0 approval, or `--auto`); review seats are always read-only (`--restrict-tools`, no role that grants writes).
- **No silent swaps:** every runner gets `--disable-fallback`.
- **Keep transcripts out of context:** runners use `--output-file` (and `--background` for implementers); read `agent_message` from the file, not raw stdout.
- **Review contract:** reuse the bundled review schema `.agents/skills/codex-runner/schemas/review-output.schema.json` (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation, next_steps). Pass it via `--output-schema` to Codex/Kimi; embed the same shape in Opus-subagent reviewer prompts (subagents have no schema flag).
- **Briefs:** write each track's brief once under `.ai-workflow/impl-review/<id>/` — the task set + the shared contracts (API shapes/types both tracks must honor) — and reuse it across that track's cycles.

## Standard frontend implementer — Codex seat

Use the default Codex seat for product interfaces with an explicit component and
behavior contract. Omit `--model`; the roster-backed runner default selects the
current Codex seat.

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file .ai-workflow/impl-review/<id>/frontend-brief.md \
  --working-dir <wt-fe> \
  --role implementer \
  --full-auto \
  --effort high \
  --timeout 1800 \
  --json \
  --disable-fallback \
  --background \
  --metadata-json '{"session":"<id>","track":"frontend","phase":"implement","shape":"standard_product"}'
```

The brief carries the literal frontend scope, acceptance commands, shared
contracts, and the instruction to continue until the acceptance contract passes
or a configured exit fires. Keep the returned session id for fix rounds.

## Visual or creative frontend implementer — Opus seat

Spawn a **named** native subagent so fix rounds can continue the same context via `SendMessage`.

```text
Agent(
  name="fe-impl",
  subagent_type="general-purpose",
  description="Frontend implementer (Opus seat)",
  model="opus",
  mode="acceptEdits",                 # writes files unattended; use "auto" if it must also run build/test without prompts
  prompt="""
Operate ONLY inside this worktree; treat it as the repo root: <wt-fe>
Implement the FRONTEND task set below. Honor the SHARED CONTRACTS exactly so the
backend stays compatible. Do not touch files outside the frontend scope. Run the
frontend-local tests if present. Commit your work on this branch.

FRONTEND TASKS:
<fe task set>

SHARED CONTRACTS:
<api shapes / types>

UNCHANGED BEHAVIOR BOUNDARY:
<files / behavior that must not change>

ACCEPTANCE CONTRACT:
<exact commands and observable behavior>

Return a COMPACT summary only: files changed, how to test, and any risks you noted.
Do NOT paste full file contents or the full diff.
"""
)
```

**Fix round:** `SendMessage({to:"fe-impl", ...})` with the reviewer's findings; tell it to address them in the same worktree and re-commit. Re-spawning would lose its context.

## Backend implementer — Codex seat

Run in the backend worktree with write access and keep the `session_id` for fixes. Omit `--model`; the roster-backed runner default selects the current Codex seat.

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file .ai-workflow/impl-review/<id>/backend-brief.md \
  --working-dir <wt-be> \
  --role implementer \
  --full-auto \
  --effort high \
  --timeout 1800 \
  --json \
  --disable-fallback \
  --background \
  --metadata-json '{"session":"<id>","track":"backend","phase":"implement"}'
```

`--full-auto` is the user-approved unattended write+exec mode (gated by Phase 0). Collect the result and `session_id` via the jobs CLI (see below).

**Fix round:** resume the same Codex thread —

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --resume <session_id> \
  --working-dir <wt-be> \
  --role implementer --full-auto --effort high --timeout 1800 \
  --json --disable-fallback --output-file .ai-workflow/impl-review/<id>/be-fix-<cycle>.json \
  "Address these review findings and re-commit:\n<findings>"
```

## Cross-model review routing

Opus reviews work written by the Codex seat. Use a fresh native subagent when
available, or `claude-runner --model opus --role codereviewer --effort medium --restrict-tools --disable-fallback`.
Give it the complete task, the boundary around unchanged behavior, the diff,
and the review output contract.

The default Codex seat reviews work written by Opus:

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file .ai-workflow/impl-review/<id>/fe-review-brief.md \
  --working-dir <wt-fe> \
  --role codereviewer \
  --restrict-tools \
  --effort high \
  --timeout 900 \
  --json \
  --disable-fallback \
  --output-schema .agents/skills/codex-runner/schemas/review-output.schema.json \
  --output-file .ai-workflow/impl-review/<id>/fe-review-<cycle>.json \
  --metadata-json '{"session":"<id>","track":"frontend","phase":"review","cycle":<cycle>}'
```

Kimi is the first fallback for either reviewer role:

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py \
  --prompt-file .ai-workflow/impl-review/<id>/<track>-review-brief.md \
  --working-dir <worktree> \
  --role codereviewer \
  --restrict-tools \
  --output-format stream-json \
  --timeout 900 \
  --json \
  --disable-fallback \
  --output-schema .agents/skills/codex-runner/schemas/review-output.schema.json \
  --output-file .ai-workflow/impl-review/<id>/<track>-review-<cycle>.json
```

Every review prompt names the task, shared contracts, test evidence, and
unchanged-behavior boundary. An implementer never reviews its own work.

## Collecting results

- **`--output-file`:** `Read` the JSON and take `agent_message`.
- **`--background`:** each runner prints `{job_id,...}`; collect with the shared jobs CLI:
  ```bash
  python3 .agents/skills/shared/scripts/runner_jobs.py status <job-id>
  python3 .agents/skills/shared/scripts/runner_jobs.py result <job-id> --json   # agent_message + session_id
  ```
- **Subagents:** the `Agent`/`SendMessage` final message returns to the orchestrator directly — require the compact/JSON shape so it stays small.
- **Envelope:** runners return `success`, `return_code`, `effective_runner`, `effective_model`, `auth_ok`, `agent_message`, and `session_id` when available. Any `success=false` / `return_code!=0` is a blocked seat (`-2` = CLI not found) — degrade, never substitute.

## Host portability

| Capability | Claude Code | Codex host |
|------------|-------------|------------|
| Standard FE implementer | `codex-runner --role implementer --full-auto` | native Codex subagent or `codex-runner` |
| Visual/creative FE implementer | native `Agent`, `model:"opus"`, write mode | `claude-runner --model opus --allow-write` |
| BE implementer | `codex-runner --role implementer --full-auto` | native Codex subagent or `codex-runner` |
| Reviewer of Codex work | native `Agent`, `model:"opus"`, read-only | `claude-runner --model opus --restrict-tools` |
| Reviewer of Opus work | `codex-runner --role codereviewer --restrict-tools` | native Codex subagent or `codex-runner` |
| Fallback reviewer | `kimi-runner --role codereviewer` | `kimi-runner --role codereviewer` |
