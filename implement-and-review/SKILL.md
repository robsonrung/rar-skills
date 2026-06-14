---
name: implement-and-review
description: Orchestrate a test-first, multi-model implementation that executes a whole task breakdown. Break the work into tracer-bullet vertical slices (via to-tasks), then build the slices — independent ones in parallel via subagents — each split across a frontend track (a native Opus 4.8 subagent implements, Kimi reviews) and a backend track (Codex implements, an Opus 4.8 subagent reviews) in isolated git worktrees, via TDD and the repo's lens skills; each slice loops implement→cross-review→fix (max 3), integrates, and must meet its acceptance contract. The orchestrator then runs the full-review skill on the result, applies findings, and leaves tests/build green. Opus orchestrates. Use to build/implement a feature with split frontend/backend work, TDD, cross-model review, and parallel task execution. Distinct from models-round-table (multi-model answer/decision, no code), collaborative_delivery (panel-gated TDD), and ship (single-model pipeline).
---

# Implement And Review

Execute a whole feature as a breakdown of **vertical slices**, building them with multiple models that review each other, and converge on one integrated, reviewed, tested solution. You (the main agent, Opus 4.8) are the **orchestrator**: you plan, decompose, schedule, dispatch seats, gate writes, run the fix loops, integrate, and run the final review. You never implement a slice yourself — you delegate and coordinate.

Two nested structures:
- **Slices are the unit of value and parallelism.** Each slice is a tracer-bullet vertical cut through all layers, carrying a machine-checkable **acceptance contract**. Independent slices run **in parallel**; dependent ones wait.
- **Tracks split each slice across models.** Within a slice, a frontend track and a backend track build their layers and **review each other** — the model that writes a track never reviews its own track.

| Track (within a slice) | Implementer | Reviewer |
|------------------------|-------------|----------|
| Frontend | native Opus 4.8 subagent (`Agent`, `model:"opus"`, write-enabled) | Kimi (`kimi-runner --role codereviewer`, read-only) |
| Backend | Codex (`codex-runner --role implementer`, write-enabled) | native Opus 4.8 subagent (read-only) |
| Final review (whole change) | the **`full-review`** skill (multi-model: Codex + Claude + bug finders + verification), then apply findings | — |

Several independent Opus contexts exist (orchestrator, FE implementers, BE reviewers). Keep them separate; never let one act as another.

Exact launch commands and the worktree/integration git flow live in
[references/runner-invocations.md](references/runner-invocations.md) and
[references/worktree-and-integration.md](references/worktree-and-integration.md); per-track methodology and skill snippets in
[references/methodology.md](references/methodology.md). Read them before Phase 1.

## Hard Rules

1. **Orchestrator coordinates, never implements.** Delegate FE to Opus subagents and BE to Codex.
2. **Cross-model review is mandatory.** Within every slice, Kimi reviews FE (Opus's work); Opus reviews BE (Codex's work). An implementer never reviews its own track.
3. **Test-first (TDD).** Every track builds via red-green-refactor — a failing test before the code that passes it, one test → one minimal change, refactor only on green. No implementation without a test first.
4. **Good code, boy-scout rule.** Produce clean code (clear names, small focused units, no duplication/dead code) and leave touched files cleaner than found — but scope improvements to what the slice changes; never rewrite unrelated areas or change behavior beyond the slice.
5. **Apply the repo's lens skills.** Each track works through the relevant quality/architecture skills (see [Methodology & Per-Track Skills](#methodology--per-track-skills)) — narrowed by each slice's `gates`; the final review uses **`full-review`**.
6. **Acceptance is the per-slice gate.** A slice is done only when its acceptance contract (real repo commands + named behaviors) passes. Never mark a slice done on "tests pass" when its acceptance names a behavior.
7. **Writes are gated.** No code until the user approves the slice breakdown in Phase 0 (skip only when `--auto`). Implementers run unattended-write only after that approval.
8. **Isolated parallelism.** Each slice builds in its own git worktree off the current integration head; within a slice the two tracks use disjoint file scopes. Slices integrate in dependency order. Fall back to sequential when the project is not a git repo.
9. **Bounded fix loop.** At most **3** review→fix cycles per track per slice. Still blocking after 3 → stop that slice and escalate with the open findings; let independent slices continue.
10. **Definition of done = green.** Each slice meets its acceptance, and the final integrated solution — after applying full-review findings — passes the project's tests/build (including the new test-first tests). If none exist, say so; never claim "tests pass" when none ran.
11. **Never fabricate or silently swap a seat.** Pass `--disable-fallback` to every runner. Missing seat → degrade per [Degrade Gracefully](#degrade-gracefully) and say so.

## Methodology & Per-Track Skills

These are Claude Code skills. The **orchestrator** invokes them directly — in Phase 0 (decompose with **`to-tasks`**, design with the lenses) and for the final `full-review`. Runner/subagent implementers (Codex, Opus FE subagents, Kimi) **cannot load skills**, so **embed each track's methodology into its brief** using the ready-made snippets in [references/methodology.md](references/methodology.md).

| Scope | Skills to apply |
|-------|-----------------|
| Decompose | **`to-tasks`** (preferred for autonomous execution — vertical slices + acceptance + gates); `to-issues` only for human-tracked tickets |
| Both tracks | `tdd` (+ `small-steps`), `clean-code`, `refactor-to-testability` (untested/legacy code → characterization-test net first), `coding-design-plan`, `coding-implementation-guard`, `test-lens` |
| Frontend | `frontend-design`, `react-performance` (when React — 17 + MUI + Redux Toolkit: re-renders, memo, context, stale closures, fetch races), `ui-ux-pro-max` |
| Backend | `data-systems-coding-lens` (stored state, transactions, idempotency/retries, concurrency, migrations, observability), `ddd-tactical` (business-logic pattern + aggregate invariants), `ddd-strategic` / `architect-lens` (when crossing a service/context boundary) |
| Final review | `full-review`; `security-gate` / full-review `security_focus=true` for slices flagged `security: deep` |

Per slice, apply only the lenses its `to-tasks` `gates` selected — don't force every skill onto every slice. Detailed checklists + paste-in snippets: [references/methodology.md](references/methodology.md).

## Preflight

1. **Host & git.** Confirm the `Agent` tool exists (native Opus subagents). Confirm `git rev-parse --is-inside-work-tree`. No git → sequential fallback (worktree reference).
2. **Seats.** `codex` in `PATH` (BE implementer + a full-review external runner); `kimi-cli` in `PATH` (FE reviewer). Mark missing seats and degrade.
3. **Verification commands.** Detect how this project tests/builds and runs a *single* test (TDD needs a fast inner loop). These also back the slices' acceptance contracts — `to-tasks` must use commands that actually exist.
4. **Concurrency cap.** Default **3 slices in flight** (each uses FE+BE seats); lower it when seats/cost are tight or seats are scarce.
5. **Base & artifacts.** Record `HEAD` as `<base>`. When `.ai-workflow/` is writable, use `.ai-workflow/impl-review/<session_id>/` (per-slice subdirs); else keep state inline and return paths as `null`.

## Phase 0 — Plan & Decompose Into Slices (gate)

**Intake A — from `models-round-table`.** If the task came through `models-round-table` (`--from-roundtable <path>`, or `.ai-workflow/roundtable/<session_id>/report.md`), take its *Consensus answer* as the settled task per the **Handoff contract**. **Gate:** resolve any *Open caveats* (low-confidence or orchestrator-decided points) with the user before code; in `--auto`, record an assumption per caveat and proceed.

**Intake B — from `to-tasks`.** If a breakdown already exists (a `TASKS.md` or tracker issues with `acceptance`, `gates`, `blocked_by`), use it as the slice list. Otherwise:
- **Non-trivial feature →** run **`to-tasks`** to produce tracer-bullet vertical slices, each with an acceptance contract, gate flags (lenses + `security`), and `blocked_by` deps. (`to-tasks` is preferred over `to-issues` for autonomous execution.)
- **Small / single-layer change →** skip `to-tasks`; treat the whole change as **one implicit slice** and proceed.

Then, for the breakdown:
1. **Design pass** (lightweight) with the planning/architecture lenses as warranted — `coding-design-plan`, `design-gate`, `ddd-tactical` (BE business-logic pattern). Informs the briefs, not a deliverable.
2. **Per slice, plan the FE/BE split:** disjoint file scopes (e.g. `client/**` vs `server/**`), the behaviors to test first, and the shared contracts (API shapes, types) both tracks must honor. A slice may be single-track (pure-FE or pure-BE).
3. **Present** the slice list (titles, deps, acceptance, gates, HITL/AFK, FE/BE split) and the verification commands. **Get approval before any code is written**, unless `--auto`.

## Phase 1 — Schedule (DAG + parallelism)

Build the dependency graph from `blocked_by`. Then:
- Schedule **HITL** slices first so human touchpoints cluster early; run **AFK** slices unattended.
- Launch all currently-unblocked slices **concurrently, up to the concurrency cap**, each via Phase 2 in its own worktree off the **current integration head**.
- As each slice integrates (Phase 2c), unblock its dependents and pull the next ready slices into flight.
- Continue until every slice is done or escalated. An escalated slice blocks only its dependents; independent slices keep going.
- If you `log`/report progress, say how many slices are done / in flight / blocked. Never silently drop a slice.

The launcher fires a slice's runner-backed seats and polls them in one call — `launch.py launch --session-id <id> --slice <S> ...` then `poll --session-id <id> --slice <S> --wait` (see [the launcher section](references/runner-invocations.md#launcher-script-one-call-setup)). Manual git is the fallback.

## Phase 2 — Build a Slice (repeat per slice)

### 2a. Implement (FE + BE, test-first)

Create the slice's worktree(s) off the current integration head. Build the tracks **concurrently** (issue the Codex `Bash` call and the Opus `Agent` call in one message). Every brief embeds the track methodology from [references/methodology.md](references/methodology.md): the **TDD loop**, the **good-code / boy-scout** rule, and the track's **lens checklist** (narrowed by the slice's gates).

- **Frontend:** spawn a named Opus subagent (`Agent`, `model:"opus"`, write-enabled, addressable for fix rounds via `SendMessage`). It works only in the slice's FE scope, implements test-first, honors the shared contracts, applies the FE lenses, runs FE-local tests after each step, and returns a compact summary (files, tests added, how to test, risks) — not its full diff.
- **Backend:** run `codex-runner --role implementer` (write access) in the slice's BE scope; brief = BE work + behaviors-to-test + shared contracts + embedded TDD/boy-scout/BE-lens snippets. Use `--background`/`--output-file`; keep the `session_id` for `--resume` fixes.

Commit tests and code interleaved (not all tests then all code).

### 2b. Cross-review + fix (≤3 cycles per track)

For each track, each cycle:
1. **Review the diff** with the cross-model reviewer, read-only, against the slice's task + acceptance + shared contracts, **through the track's lens checklist**. The reviewer also checks that changed behavior is covered by test-first tests and that touched code was left clean. Require the review-output contract (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation): reuse `.agents/skills/codex-runner/schemas/review-output.schema.json` for Kimi (`--output-schema`); embed the same shape in the Opus reviewer's prompt.
2. **Stop** when the reviewer returns `approve` with no high-severity findings.
3. **Else fix** via the **same implementer** (FE → `SendMessage`; BE → `codex-runner --resume <session_id>`); re-review.
4. After **3** cycles without approval, stop the slice and escalate its open findings.

Never apply review findings yourself; the implementer fixes its own track. Never auto-accept — the reviewer re-checks after each fix.

### 2c. Integrate the slice + acceptance

1. Merge the slice's track work, then merge the slice into the **integration branch** in dependency order (commands in the worktree reference). Resolve conflicts using both diffs; disjoint scopes should make this rare.
2. Run the slice's **acceptance contract** (its commands + named behaviors) — must pass. If `gates.security: deep`, run `full-review security_focus=true` scoped to the slice now (not just at the end).
3. Red → bounded slice-fix loop (≤3): route the failure to the responsible track, re-merge, re-test. Green → mark the slice **done** and unblock dependents.

## Phase 3 — Final Review (full-review) & Apply

After all slices are integrated, run the **`full-review`** skill on the whole change — it is multi-model (Codex + Claude + Gemini external runners, bug finders, personas, specialists, execution-based verification, structural-maintainability), so it fulfills "Opus and Codex review together" and goes further than per-slice review.

1. **Invoke** `full-review` against the integration branch (local diff vs `<base>`, or range `<base>..<integration>`). `security_focus=true` if any slice was security-sensitive. full-review is **read-only**.
2. **Triage:** fix every CRITICAL/HIGH; apply safe, behavior-preserving MEDIUM simplification/maintainability findings; record deferrals with a reason. The machine JSON is the source of truth.
3. **Apply** via the responsible implementer (BE → Codex `--resume`; FE → `SendMessage`), preserving TDD — add/adjust a test for any behavioral fix.
4. **Re-verify:** full suite **green**; re-run `full-review` (or `quick_mode`) when CRITICAL/HIGH were fixed, until `APPROVE` or only accepted findings remain.

## Phase 4 — Report & Handoff

Deliver inline and write `.ai-workflow/impl-review/<session_id>/report.md` (persisted mode):

1. **Task** and final status (`done` / `partial` / `escalated`).
2. **Slices** — a table: slice, deps, FE/BE seats, review cycles, acceptance result, status; note which ran in parallel.
3. **Seats** used and any degraded/unavailable seats with reasons.
4. **Integration** — order merged, conflicts resolved.
5. **Final review (full-review)** — verdict, findings by severity, what was fixed/simplified, deferrals with reasons.
6. **Verification** — exact commands run and results (green/red); confirm the new test-first tests pass; state plainly if no tests existed.
7. **Branch/worktrees** — the integration branch name and how to inspect/land it. Do not push, open a PR, or delete worktrees unless asked.
8. **Escalations** — any slice stopped at the 3-cycle cap, with open findings.

## Degrade Gracefully

- **No breakdown wanted / small change:** run as a single implicit slice (today's one-pass FE/BE build) — skip the DAG and parallelism.
- **Kimi missing (FE reviewer):** use Codex as the FE reviewer (still cross-model, since FE is Opus's work); note the substitution.
- **Codex missing (BE implementer):** with approval, have an Opus subagent implement BE and a *different* model review it; flag lost cross-vendor diversity. If no write-capable seat + distinct reviewer remain for a non-empty track, stop and report.
- **Not a git repo:** run slices **sequentially** in the working tree (no per-slice worktrees, no parallelism); full-review runs against the local diff.
- **Few seats / tight cost:** lower the concurrency cap (down to 1 = sequential slices); say so.
- **No tests/build found:** TDD still drives design where a harness can be introduced; if truly none exists, build + review + `full-review`, and report that verification could not run — never imply it passed.
- **full-review external runners unavailable:** it degrades itself (lowers its confidence cap, notes lost triangulation) — apply its findings anyway; don't skip it.
- Lower overall confidence one band per degradation and surface it.

## Output Contract

Return:
1. `report_path` (or `null`)
2. final status + the slice table (slice → status / cycles / acceptance)
3. integration branch name and final verification result
4. a concise inline rendering of the report

## Gotchas

- BE implementer needs write + command execution; pass the write flag only after Phase 0 approval (or `--auto`). Reviewers and `full-review` are always read-only (`--restrict-tools`, no write-granting role).
- **Skills don't load inside runner/subagent seats.** The orchestrator invokes skills it can (`to-tasks`, `full-review`, lenses); for implementer seats, embed the methodology from `references/methodology.md` into the brief.
- **Vertical vs horizontal:** `to-tasks` slices are vertical (all layers); tracks are horizontal (FE/BE). The slice is the outer unit; the FE/BE split is *inside* each slice. Don't confuse a track for a task.
- **`full-review` is read-only** — applying findings is a separate implementer step, then re-verify.
- Parallel slices each branch off the **current integration head**, not stale `<base>` mid-run, so later slices build on already-integrated work; respect `blocked_by`.
- Read seat results from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript). Keep state in the orchestrator — read diffs from worktrees, not full transcripts.
- `--resume <session_id>` continues the *same* Codex thread; `SendMessage` continues the *same* Opus subagent. Re-spawning loses context.
- Fixes/simplifications must not regress behavior; TDD still applies — add/adjust a test per behavioral fix and re-verify.
- Two-plus Opus instances is intended. A reviewer Opus must be a separate subagent from any implementer, and the orchestrator never reviews or writes a slice itself.
- **Handoff contract with `models-round-table`** (answer → build): its *Consensus answer* is your settled task; its *Open caveats* are a hard gate — resolve before code. `models-round-table` is read-only and never builds; `feature-models-round-table` chains the two.
