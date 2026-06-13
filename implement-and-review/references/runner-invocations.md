# Seat Invocations

Exact launch patterns for the implement-and-review seats. Paths assume the installed `.agents/skills/` layout; from the source repo, drop the `.agents/skills/` prefix. `<id>` = session id, `<base>` = the commit recorded at preflight, `<wt-fe>` / `<wt-be>` = the frontend/backend worktree paths (see [worktree-and-integration.md](worktree-and-integration.md)).

## Table of Contents

1. [Launcher script (one-call setup)](#launcher-script-one-call-setup)
2. [Shared rules](#shared-rules)
3. [Frontend implementer — Opus subagent](#frontend-implementer--opus-subagent)
4. [Backend implementer — Codex](#backend-implementer--codex)
5. [Frontend reviewer — Kimi](#frontend-reviewer--kimi)
6. [Backend reviewer — Opus subagent](#backend-reviewer--opus-subagent)
7. [Joint review & simplify — Opus + Codex](#joint-review--simplify--opus--codex)
8. [Collecting results](#collecting-results)
9. [Host portability](#host-portability)

## Launcher script (one-call setup)

`scripts/launch.py` collapses Phase 1's deterministic setup into one call: it creates the per-track git worktrees+branches off a clean base, fires the runner-backed implementer(s) as tracked background jobs, writes `launch-manifest.json`, and polls them. It **cannot** spawn a native Opus `Agent` subagent (an in-process orchestrator tool), so the frontend has two modes.

```bash
L=.agents/skills/implement-and-review/scripts/launch.py

# default: set up both worktrees + briefs, fire ONLY the backend (Codex) job;
# you then spawn the native Opus FE subagent in the printed frontend worktree.
python3 $L launch --session-id <id> --fe-brief <fe.md> --be-brief <be.md>

# fire BOTH implementers as background jobs (frontend via claude-runner):
python3 $L launch --session-id <id> --fe-brief <fe.md> --be-brief <be.md> --fe-mode runner

# single-track task:
python3 $L launch --session-id <id> --be-brief <be.md> --no-frontend

# poll to a consolidated status (optionally block until terminal):
python3 $L poll --session-id <id> --wait

# remove the session's worktrees when done (branches kept unless --delete-branches):
python3 $L cleanup --session-id <id>
```

Key flags: `--fe-mode {subagent|runner}` (default `subagent`), `--no-frontend`/`--no-backend`, `--no-full-auto` (Codex writes off), `--base <sha>`, `--worktrees-dir <dir>`, `--allow-dirty`, `--force` (recreate existing worktrees), `--dry-run`. The `launch`/`poll` output is JSON on stdout; `poll` exits non-zero if any runner track failed.

- The manifest records each track's `worktree`, `branch`, `brief`, `job_id`, and `working_dir`. `poll` reuses `working_dir` to find each job under `<worktree>/.ai-workflow/runner-jobs/`, and on completion reports `success` and `runner_session_id` (use it for `--resume` fix rounds).
- Briefs must already exist (you write them in Phase 0/1); the launcher copies them into the artifact dir for provenance.
- The launcher only sets up and fires Phase 1 implement runs. Reviews, fix loops, integration, and the joint pass are driven by you using the commands below.

When you want fine control, skip the launcher and use the per-seat commands directly.

## Shared rules

- **Writers vs. reviewers:** implementers get write access (only after the Phase 0 approval, or `--auto`); reviewers and the joint analysis pass are always read-only (`--restrict-tools`, no role that grants writes).
- **No silent swaps:** every runner gets `--disable-fallback`.
- **Keep transcripts out of context:** runners use `--output-file` (and `--background` for implementers); read `agent_message` from the file, not raw stdout.
- **Review contract:** reuse the bundled review schema `.agents/skills/codex-runner/schemas/review-output.schema.json` (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation, next_steps). Pass it via `--output-schema` to Codex/Kimi; embed the same shape in Opus-subagent reviewer prompts (subagents have no schema flag).
- **Briefs:** write each track's brief once under `.ai-workflow/impl-review/<id>/` — the task set + the shared contracts (API shapes/types both tracks must honor) — and reuse it across that track's cycles.

## Frontend implementer — Opus subagent

Spawn a **named** native subagent so fix rounds can continue the same context via `SendMessage`.

```text
Agent(
  name="fe-impl",
  subagent_type="general-purpose",
  description="Frontend implementer (Opus 4.8)",
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

Return a COMPACT summary only: files changed, how to test, and any risks you noted.
Do NOT paste full file contents or the full diff.
"""
)
```

**Fix round:** `SendMessage({to:"fe-impl", ...})` with the reviewer's findings; tell it to address them in the same worktree and re-commit. Re-spawning would lose its context.

## Backend implementer — Codex

Run in the backend worktree with write access; keep the `session_id` for fixes.

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

## Frontend reviewer — Kimi

Read-only review of the FE worktree diff (cross-model: Opus wrote it, Kimi reviews).

```bash
python3 .agents/skills/kimi-runner/scripts/run_kimi.py \
  --prompt-file .ai-workflow/impl-review/<id>/fe-review-brief.md \
  --working-dir <wt-fe> \
  --model kimi-code/kimi-for-coding \
  --role codereviewer \
  --restrict-tools \
  --output-format stream-json \
  --timeout 900 \
  --json \
  --disable-fallback \
  --output-schema .agents/skills/codex-runner/schemas/review-output.schema.json \
  --output-file .ai-workflow/impl-review/<id>/fe-review-<cycle>.json \
  --metadata-json '{"session":"<id>","track":"frontend","phase":"review","cycle":<cycle>}'
```

The review brief instructs Kimi to review `git diff <base>..HEAD` in the worktree against the FE task set + shared contracts, return the review-output shape, and not modify anything.

## Backend reviewer — Opus subagent

Read-only review of the BE worktree diff (cross-model: Codex wrote it, Opus reviews). Spawn a fresh subagent each cycle.

```text
Agent(
  subagent_type="general-purpose",
  description="Backend reviewer (Opus 4.8) — cycle <cycle>",
  model="opus",
  mode="plan",                         # read-only
  prompt="""
Review (read-only) the backend changes in this worktree: <wt-be>
Run: git diff <base>..HEAD
Judge against the BACKEND task set and SHARED CONTRACTS below. Do not edit anything.

Return ONLY JSON: {verdict:"approve"|"needs-attention", summary, findings:[{severity,file,line,recommendation,confidence}], next_steps}

BACKEND TASKS: <be task set>
SHARED CONTRACTS: <api shapes / types>
"""
)
```

## Joint review & simplify — Opus + Codex

Both review the **integrated** diff read-only and propose behavior-preserving simplifications (reuse, dedupe, dead code, the FE/BE seam).

Codex:

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file .ai-workflow/impl-review/<id>/joint-brief.md \
  --working-dir <integration-worktree-or-repo> \
  --role codereviewer \
  --restrict-tools \
  --effort high --timeout 900 \
  --json --disable-fallback \
  --output-schema .agents/skills/codex-runner/schemas/review-output.schema.json \
  --output-file .ai-workflow/impl-review/<id>/joint-codex.json
```

Opus: a `mode:"plan"` subagent with the joint brief and the same JSON shape. The brief gives both `git diff <base>..<integration>` and asks for simplifications that **do not change behavior**.

**Apply step:** the orchestrator reconciles both lists (apply agreed/safe items, drop behavior-changing ones), then applies via one implementer — Codex `--resume <session_id> --full-auto` or a write-enabled Opus subagent — and re-runs verification.

## Collecting results

- **`--output-file`:** `Read` the JSON and take `agent_message`.
- **`--background`:** each runner prints `{job_id,...}`; collect with the shared jobs CLI:
  ```bash
  python3 .agents/skills/_shared/scripts/runner_jobs.py status <job-id>
  python3 .agents/skills/_shared/scripts/runner_jobs.py result <job-id> --json   # agent_message + session_id
  ```
- **Subagents:** the `Agent`/`SendMessage` final message returns to the orchestrator directly — require the compact/JSON shape so it stays small.
- **Envelope:** runners return `success`, `return_code`, `effective_runner`, `effective_model`, `auth_ok`, `agent_message`, and `session_id` when available. Any `success=false` / `return_code!=0` is a blocked seat (`-2` = CLI not found) — degrade, never substitute.

## Host portability

| Capability | Claude Code | Codex host |
|------------|-------------|------------|
| FE implementer (Opus) | native `Agent`, `model:"opus"`, write mode | `claude-runner --model claude-opus-4-8 --allow-write` |
| BE implementer (Codex) | `codex-runner --role implementer --full-auto` | native `spawn_agent` (`fork_context=false`), write-enabled |
| FE reviewer (Kimi) | `kimi-runner --role codereviewer` | `kimi-runner --role codereviewer` |
| BE reviewer (Opus) | native `Agent`, `mode:"plan"` | `claude-runner --model claude-opus-4-8 --restrict-tools` |
| Joint pass | Opus subagent + `codex-runner` | native Codex subagent + `claude-runner` |
