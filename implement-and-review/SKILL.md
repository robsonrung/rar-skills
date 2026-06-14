---
name: implement-and-review
description: Implement ONE scoped task end-to-end with cross-model review. Given a task prompt, decide the frontend/backend split and which model does what, build it test-first — a frontend track (a native Opus 4.8 subagent implements, Kimi reviews) and a backend track (Codex implements, an Opus 4.8 subagent reviews) in parallel isolated git worktrees, applying the repo's lens skills — loop implement→cross-review→fix (max 3) per track, integrate the two tracks, run the full-review skill, and leave tests/build green. Opus orchestrates. Use to implement/build/fix a single scoped task with split frontend/backend work, TDD, and cross-model review. For a whole feature (many tasks), use implement-feature, which calls this per task. Distinct from models-roundtable (answer only, no code) and ship (single-model pipeline).
---

# Implement And Review

Implement **one scoped task** with two model tracks that build in parallel and review each other's work, then converge on one integrated, reviewed, tested change. You (the main agent, Opus 4.8) are the **orchestrator**: you decide the split, dispatch seats, gate writes, run the fix loops, integrate, and run the final review. You never implement a track yourself — you delegate and coordinate.

This skill builds **one task**. To break a plan into many tasks and build them all, use **`implement-feature`**, which calls this skill per task. Keep this skill simple and self-contained.

Both tracks are **test-first (TDD)** and follow the **boy-scout rule** — leave touched code cleaner than found. The defining shape is **cross-model review**: the model that writes a track never reviews its own track.

| Track | Implementer | Reviewer |
|-------|-------------|----------|
| Frontend | native Opus 4.8 subagent (`Agent`, `model:"opus"`, write-enabled) | Kimi (`kimi-runner --role codereviewer`, read-only) |
| Backend | Codex (`codex-runner --role implementer`, write-enabled) | native Opus 4.8 subagent (read-only) |
| Final review | the **`full-review`** skill on the task's diff (multi-model: Codex + Claude + bug finders + verification), then apply findings | — |

Several independent Opus contexts exist (orchestrator, FE implementer, BE reviewer). Keep them separate.

Exact launch commands and the worktree/integration git flow are in
[references/runner-invocations.md](references/runner-invocations.md) and
[references/worktree-and-integration.md](references/worktree-and-integration.md); per-track methodology + skill snippets in
[references/methodology.md](references/methodology.md). Read them before Phase 1.

## Hard Rules

1. **Orchestrator coordinates, never implements.** Delegate FE to the Opus subagent and BE to Codex.
2. **Cross-model review is mandatory.** Kimi reviews FE (Opus's work); Opus reviews BE (Codex's work). An implementer never reviews its own track.
3. **Test-first (TDD).** Both tracks build via red-green-refactor — a failing test before the code that passes it, one test → one minimal change, refactor only on green.
4. **Good code, boy-scout rule.** Produce clean code (clear names, small focused units, no duplication/dead code) and leave touched files cleaner than found — but scope improvements to what the task changes; never rewrite unrelated areas or change behavior beyond the task.
5. **Apply the repo's lens skills.** Each track works through the relevant quality/architecture skills (see [Methodology & Per-Track Skills](#methodology--per-track-skills)); the final review uses **`full-review`**.
6. **Writes are gated.** No code until the user approves the plan + FE/BE split in Phase 0 (skip only when `--auto`). Implementers run unattended-write only after that approval.
7. **Isolated parallelism.** Each track builds in its own git worktree/branch so they cannot clobber each other. Fall back to sequential same-tree execution when the project is not a git repo.
8. **Bounded fix loop.** At most **3** review→fix cycles per track. Still blocking after 3 → stop and escalate with the open findings.
9. **Definition of done = green.** The integrated task — after applying full-review findings — passes the project's tests/build (including the new test-first tests). If none exist, say so; never claim "tests pass" when none ran.
10. **Never fabricate or silently swap a seat.** Pass `--disable-fallback` to every runner. Missing seat → degrade per [Degrade Gracefully](#degrade-gracefully) and say so.

## Methodology & Per-Track Skills

These are Claude Code skills. The **orchestrator** invokes them directly — in Phase 0 (design with the lenses) and for the final `full-review`. Runner/subagent implementers (Codex, the Opus FE subagent, Kimi) **cannot load skills**, so **embed each track's methodology into its brief** using the ready-made snippets in [references/methodology.md](references/methodology.md).

| Scope | Skills to apply |
|-------|-----------------|
| Both tracks | `tdd` (+ `small-steps`), `clean-code`, `refactor-to-testability` (untested/legacy code → characterization-test net first), `coding-design-plan`, `coding-implementation-guard`, `test-lens` |
| Frontend | `frontend-design`, `react-performance` (when React — 17 + MUI + Redux Toolkit: re-renders, memo, context, stale closures, fetch races), `ui-ux-pro-max` |
| Backend | `data-systems-coding-lens` (stored state, transactions, idempotency/retries, concurrency, migrations, observability), `ddd-tactical` (business-logic pattern + aggregate invariants), `ddd-strategic` / `architect-lens` (when crossing a service/context boundary) |
| Final review | `full-review`; `security-gate` / full-review `security_focus=true` when the change is security-sensitive |

Apply only the lenses that fit the task; don't force every skill onto every change. Checklists + paste-in snippets: [references/methodology.md](references/methodology.md).

## Preflight

1. **Host & git.** Confirm the `Agent` tool exists (native Opus subagents). Confirm `git rev-parse --is-inside-work-tree`. No git → sequential fallback (worktree reference).
2. **Seats.** `codex` in `PATH` (BE implementer + a full-review external runner); `kimi-cli` in `PATH` (FE reviewer). Mark missing seats and degrade.
3. **Verification commands.** Detect how this project tests/builds and runs a *single* test (TDD needs a fast inner loop). These also back the done gate.
4. **Base & artifacts.** Record the current head as `<base>` (when called by `implement-feature`, this is the task's assigned base). When `.ai-workflow/` is writable, use `.ai-workflow/impl-review/<session_id>/`; else keep state inline.

## Phase 0 — Plan the Task (gate)

1. **Understand the task.** If it is ambiguous, clarify first.
2. **Design pass** (lightweight) with the planning/architecture lenses as warranted — `coding-design-plan`, `design-gate`, `ddd-tactical` (BE business-logic pattern). Informs the briefs, not a deliverable.
3. **Split the task** into a **frontend** part and a **backend** part with **disjoint file scopes** (e.g. `client/**` vs `server/**`), the **behaviors to test first**, and the **shared contracts** (API shapes, types) both tracks must honor. A task may be single-track (pure-FE or pure-BE).
4. **Present** the split, which model does what, the behaviors-to-test, the shared contracts, and the verification commands. **Get approval before any code is written**, unless `--auto`.

## Phase 1 — Implement (FE + BE, test-first, parallel)

Fast path: the bundled launcher creates the worktrees, fires the runner-backed implementer(s), and polls — `python3 .agents/skills/implement-and-review/scripts/launch.py launch --session-id <id> --fe-brief <f> --be-brief <f>` (default `--fe-mode subagent` fires only the Codex BE job and leaves the FE worktree for a native Opus subagent; `--fe-mode runner` fires both). See [the launcher section](references/runner-invocations.md#launcher-script-one-call-setup). Manual git is the fallback.

Create one worktree+branch per non-empty track off `<base>`, then build both tracks **concurrently** (issue the Codex `Bash` call and the Opus `Agent` call in one message). Every brief embeds the track methodology from [references/methodology.md](references/methodology.md): the **TDD loop**, the **good-code / boy-scout** rule, and the track's **lens checklist**.

- **Frontend:** spawn a named Opus subagent (`Agent`, `model:"opus"`, write-enabled, addressable for fix rounds via `SendMessage`). It works only in the FE scope, implements test-first, honors the shared contracts, applies the FE lenses, runs FE-local tests after each step, and returns a compact summary (files, tests added, how to test, risks) — not its full diff.
- **Backend:** run `codex-runner --role implementer` (write access) in the BE scope; brief = BE work + behaviors-to-test + shared contracts + embedded TDD/boy-scout/BE-lens snippets. Use `--background`/`--output-file`; keep the `session_id` for `--resume` fixes.

Commit tests and code interleaved (not all tests then all code).

## Phase 2 — Cross-review + Fix (≤3 cycles per track)

For each track, each cycle:
1. **Review the diff** (`git -C <worktree> diff <base>..HEAD`) with the cross-model reviewer, read-only, against the task + shared contracts, **through the track's lens checklist**. The reviewer also checks that changed behavior is covered by test-first tests and that touched code was left clean. Require the review-output contract (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation): reuse `.agents/skills/codex-runner/schemas/review-output.schema.json` for Kimi (`--output-schema`); embed the same shape in the Opus reviewer's prompt.
2. **Stop** when the reviewer returns `approve` with no high-severity findings.
3. **Else fix** via the **same implementer** (FE → `SendMessage`; BE → `codex-runner --resume <session_id>`); re-review.
4. After **3** cycles without approval, stop and escalate the open findings.

Never apply review findings yourself; the implementer fixes its own track. Never auto-accept — the reviewer re-checks after each fix.

## Phase 3 — Integrate the Two Tracks

1. Merge both track branches into an integration branch off `<base>` (commands in the worktree reference). Disjoint scopes should make this clean; resolve any conflict using both diffs, preserving each track's intent and the shared contracts.
2. Run the full verification commands. Red → bounded integration-fix loop (≤3): route the failure to the responsible track, re-merge, re-test.
3. Proceed only when **green** (or escalate).

## Phase 4 — Final Review (full-review) & Apply

Run the **`full-review`** skill on the task's integrated diff — it is multi-model (Codex + Claude + Gemini external runners, bug finders, personas, specialists, execution-based verification, structural-maintainability), so it fulfills "Opus and Codex review together" and goes further than the per-track review.

1. **Invoke** `full-review` (local diff vs `<base>`, or range `<base>..<integration>`). `security_focus=true` when security-sensitive. It is **read-only**.
2. **Triage:** fix every CRITICAL/HIGH; apply safe, behavior-preserving MEDIUM simplification/maintainability findings; record deferrals with a reason. The machine JSON is the source of truth.
3. **Apply** via the responsible implementer (BE → Codex `--resume`; FE → `SendMessage`), preserving TDD — add/adjust a test for any behavioral fix.
4. **Re-verify:** **green**; re-run `full-review` (or `quick_mode`) when CRITICAL/HIGH were fixed, until `APPROVE` or only accepted findings remain.

## Phase 5 — Report

Deliver inline and write `.ai-workflow/impl-review/<session_id>/report.md` (persisted mode):

1. **Task** and final status (`done` / `escalated`).
2. **Seats** used and any degraded/unavailable seats with reasons.
3. **Frontend** — what was built, tests added (test-first), lenses applied, review cycles, findings resolved vs. outstanding.
4. **Backend** — same.
5. **Integration** — merge notes, conflicts resolved.
6. **Final review (full-review)** — verdict, findings by severity, what was fixed/simplified, deferrals with reasons.
7. **Verification** — exact commands run and results (green/red); confirm the new test-first tests pass; state plainly if none existed.
8. **Branch/worktrees** — the integration branch name and how to inspect/land it. Do not push, open a PR, or delete worktrees unless asked.
9. **Escalations** — any track stopped at the 3-cycle cap, with open findings.

When called by `implement-feature`, return this report compactly so the orchestrator can integrate the task and move on.

## Degrade Gracefully

- **Kimi missing (FE reviewer):** use Codex as the FE reviewer (still cross-model, since FE is Opus's work); note the substitution.
- **Codex missing (BE implementer):** with approval, have an Opus subagent implement BE and a *different* model review it; flag lost cross-vendor diversity. If no write-capable seat + distinct reviewer remain for a non-empty track, stop and report.
- **Not a git repo:** run the tracks **sequentially** in the working tree (backend first so the FE builds against settled contracts), no worktrees; full-review against the local diff.
- **No tests/build found:** TDD still drives design where a harness can be introduced; if truly none exists, build + review + `full-review`, and report that verification could not run — never imply it passed.
- **full-review external runners unavailable:** it degrades itself (lowers its confidence cap, notes lost triangulation) — apply its findings anyway; don't skip it.
- Lower overall confidence one band per degradation and surface it.

## Output Contract

Return:
1. `report_path` (or `null`)
2. final status + per-track summary (built / cycles / outstanding)
3. integration branch name and verification result
4. a concise inline rendering of the report

## Gotchas

- BE implementer needs write + command execution; pass the write flag only after Phase 0 approval (or `--auto`). Reviewers and `full-review` are always read-only.
- **Skills don't load inside runner/subagent seats.** The orchestrator invokes skills it can (`full-review`, lenses); for implementer seats, embed the methodology from `references/methodology.md` into the brief.
- **`full-review` is read-only** — applying findings is a separate implementer step, then re-verify.
- Read seat results from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript). Keep state in the orchestrator — read diffs from worktrees, not full transcripts.
- `--resume <session_id>` continues the *same* Codex thread; `SendMessage` continues the *same* Opus subagent. Re-spawning loses context.
- Fixes/simplifications must not regress behavior; TDD still applies — add/adjust a test per behavioral fix and re-verify.
- Two-plus Opus instances is intended. A reviewer Opus must be a separate subagent from any implementer, and the orchestrator never reviews or writes a track itself.
- **Scope is one task.** If the request is a whole feature (many independent pieces, a plan, or a task list), use `implement-feature` — it decomposes and calls this skill per task.
