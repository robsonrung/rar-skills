---
name: implement-and-review
description: Orchestrate a two-track, test-first implementation with cross-model review. A frontend track (a native Opus 4.8 subagent implements, Kimi reviews) and a backend track (Codex implements, an Opus 4.8 subagent reviews) run in parallel in isolated git worktrees, each building via TDD (red-green-refactor), applying the repo's quality and architecture lens skills, and improving the code it touches; each loops implement→cross-review→fix (max 3 cycles). The orchestrator then integrates both branches, runs the full-review skill on the result, applies its findings, and leaves the repo's tests/build green. Opus is the orchestrator. Use when the user wants to build/implement a feature with split frontend/backend work, TDD, cross-model code review, and a thorough final review. Distinct from model-roundtable (interpretation only, no code), collaborative_delivery (panel-gated TDD), and ship (single-model end-to-end pipeline).
---

# Implement And Review

Build a feature with two model tracks that implement in parallel and review each other's work, then converge on one integrated, reviewed, tested solution. You (the main agent, Opus 4.8) are the **orchestrator**: you plan, split the work, dispatch seats, gate writes, run the fix loops, integrate, and run the final review. You do not implement the tracks yourself — you delegate and coordinate.

Both tracks are **test-first (TDD)** and follow the **boy-scout rule** — leave the code they touch cleaner than they found it. The defining shape is **cross-model review**: the model that writes a track never reviews its own track.

| Track | Implementer | Reviewer |
|-------|-------------|----------|
| Frontend | native Opus 4.8 subagent (`Agent`, `model:"opus"`, write-enabled) | Kimi (`kimi-runner --role codereviewer`, read-only) |
| Backend | Codex (`codex-runner --role implementer`, write-enabled) | native Opus 4.8 subagent (read-only) |
| Final review | the **`full-review`** skill on the integrated diff (multi-model: Codex + Claude + bug finders + verification), then apply findings | — |

There are several independent Opus contexts here (orchestrator, FE implementer, BE reviewer). Keep them separate; never let one act as another.

Exact launch commands and the worktree/integration git flow live in
[references/runner-invocations.md](references/runner-invocations.md) and
[references/worktree-and-integration.md](references/worktree-and-integration.md). Read both before Phase 1.

## Hard Rules

1. **Orchestrator coordinates, never implements a track.** Delegate FE to the Opus subagent and BE to Codex.
2. **Cross-model review is mandatory.** Kimi reviews FE (Opus's work); Opus reviews BE (Codex's work). An implementer never reviews its own track.
3. **Test-first (TDD).** Both tracks build via red-green-refactor — a failing test before the code that passes it, vertical slices (one test → one minimal change), refactor only on green. No implementation without a test first.
4. **Good code, boy-scout rule.** Produce clean code (clear names, small focused units, no duplication or dead code) and leave every file touched cleaner than found — but scope improvements to the code the task changes; never rewrite unrelated areas or change behavior beyond the task.
5. **Apply the repo's lens skills.** Each track works through the relevant quality/architecture skills (see [Methodology & Per-Track Skills](#methodology--per-track-skills)); the final review uses **`full-review`**.
6. **Writes are gated.** Do not write code until the user approves the plan + FE/BE split in Phase 0 (skip the gate only when `--auto` is set). Implementers run unattended-write only after that approval.
7. **Isolated parallelism.** Each track builds in its own git worktree/branch so the tracks cannot clobber each other. Fall back to sequential same-tree execution only when the project is not a git repo.
8. **Bounded fix loop.** At most **3** review→fix cycles per track. If a reviewer still blocks after 3, stop that track and escalate to the user with the open findings.
9. **Definition of done = green.** The integrated solution, and again after applying the final-review findings, must pass the project's tests/build (including the new test-first tests). If none exist, say so explicitly; never claim "tests pass" when none ran.
10. **Never fabricate or silently swap a seat.** Pass `--disable-fallback` to every runner. If a required seat is missing, degrade per [Degrade Gracefully](#degrade-gracefully) and say so.

## Methodology & Per-Track Skills

These are Claude Code skills. The **orchestrator** can invoke them directly — use them in Phase 0 planning, when reviewing, and for the final `full-review`. Runner/subagent implementers (Codex, the Opus FE subagent, Kimi) **cannot load skills**, so **embed each track's methodology into its brief** using the ready-made snippets in [references/methodology.md](references/methodology.md).

| Scope | Skills to apply |
|-------|-----------------|
| Both tracks | `tdd` (+ `small-steps`), `clean-code`, `refactor-to-testability` (when touching untested/legacy code, add a characterization-test net first), `coding-design-plan` (Phase 0), `coding-implementation-guard`, `test-lens` |
| Frontend | `frontend-design`, `react-performance` (when React — 17 + MUI + Redux Toolkit: re-renders, memo, context, stale closures, fetch races), `ui-ux-pro-max` |
| Backend | `data-systems-coding-lens` (stored state, transactions, idempotency/retries, concurrency, migrations, observability), `ddd-tactical` (business-logic pattern + aggregate invariants), `ddd-strategic` / `architect-lens` (when crossing a service/context boundary) |
| Final review | `full-review` (Phase 4); `security-gate` / full-review `security_focus=true` when the change is security-sensitive |

Pick only the lenses that fit the actual change; do not force every skill onto every task. The detailed per-track checklists and the exact brief snippets to paste live in [references/methodology.md](references/methodology.md).

## Preflight

1. **Host & git.** Confirm the `Agent` tool exists (native Opus subagents). Confirm `git rev-parse --is-inside-work-tree`. No git → use the sequential fallback in the worktree reference.
2. **Seats.** `codex` in `PATH` (BE implementer + a full-review external runner); `kimi-cli` in `PATH` (FE reviewer). Mark missing seats and apply degradation.
3. **Verification commands.** Detect how this project tests/builds (e.g. `package.json` scripts, `Makefile`, `pytest`, `cargo`, etc.) and how it runs a single test (TDD needs a fast inner loop). Record the exact commands; you will run them inside each track's TDD loop, at integration, and after applying the final-review findings.
4. **Base commit.** Record current `HEAD` as `<base>`; all branches fork from it.
5. **Artifacts.** When `.ai-workflow/` is writable, use `.ai-workflow/impl-review/<session_id>/` for briefs, review outputs, and the report; otherwise keep state inline and return paths as `null`.

## Phase 0 — Plan & Decompose (gate)

1. Understand the task. If it is ambiguous, clarify first (or run `model-roundtable` if the user wants a shared interpretation before building).
2. Shape the approach with the planning/design skills as warranted — `coding-design-plan` for non-trivial work, and the relevant architecture lenses (`design-gate`, `architect-lens`, `model-lens`, `ddd-tactical` to pick the backend business-logic pattern). Keep this lightweight; it informs the briefs, it is not a deliverable.
3. Split the work into a **frontend task set** and a **backend task set** with **disjoint file scopes** (e.g. `client/**` vs `server/**`). For each track, list the **behaviors to test first** (TDD drives off these). List shared contracts (API shapes, types) both tracks must honor — capture these in the shared brief so the tracks stay compatible without editing each other's files.
4. A track may be empty (pure-FE or pure-BE task); skip the empty track and still run the final review on whatever was built.
5. Present: the plan, the FE/BE split, which model does what, the behaviors-to-test, the shared contracts, and the verification commands. **Get approval before any code is written**, unless `--auto`.

## Phase 1 — Parallel Implementation (isolated worktrees)

Fastest path: the bundled launcher does worktree creation + firing the runner-backed implementer(s) + a consolidated poll in one call —
`python3 .agents/skills/implement-and-review/scripts/launch.py launch --session-id <id> --fe-brief <f> --be-brief <f>` (then `poll --session-id <id> --wait`). With its default `--fe-mode subagent` it sets up the frontend worktree+brief and fires only the backend (Codex) job, leaving you to spawn the native Opus FE subagent; `--fe-mode runner` fires both implementers as background jobs. See [references/runner-invocations.md#launcher-script-one-call-setup](references/runner-invocations.md#launcher-script-one-call-setup). The manual path below is the fallback.

Create one worktree+branch per non-empty track off `<base>` (commands in the worktree reference), then launch both implementers **concurrently** (issue the Codex `Bash` call and the Opus `Agent` call in one message).

Every brief must embed the track's methodology (paste from [references/methodology.md](references/methodology.md)): the **TDD loop** (failing test first, vertical slices, refactor on green), the **good-code / boy-scout** instruction, and the track's **lens checklist**. Tell each implementer to commit in small red→green→refactor steps.

- **Frontend:** spawn a named Opus subagent (`Agent`, `model:"opus"`, write-enabled, addressable so you can send fix rounds via `SendMessage`). Instruct it to operate **only inside the frontend worktree**, implement the FE task set test-first, honor the shared contracts, apply the frontend lenses (`frontend-design`, and `react-performance` when React), run FE-local tests after each step, and return a compact summary (files changed, tests added, how to test, self-noted risks). Do not paste its full diff into your context — you will read the diff from the worktree.
- **Backend:** run `codex-runner --role implementer` in the backend worktree with write access; the brief = the BE task set + behaviors-to-test + shared contracts + the embedded TDD/boy-scout/backend-lens snippets (`data-systems-coding-lens`, `ddd-tactical`). Use `--background`/`--output-file` so its transcript stays out of your context. Keep the returned `session_id` — you will `--resume` it for fixes.

Each implementer commits its work on its branch, with tests and code interleaved (not all tests, then all code).

## Phase 2 — Cross-review + fix loop (≤3 cycles per track)

Run both tracks' loops independently (they can proceed in parallel).

For each cycle:
1. **Review the diff** (`git -C <worktree> diff <base>..HEAD`) with the cross-model reviewer, read-only, against the track's task set + shared contracts, and **through the track's lens checklist** (FE: `react-performance`/`frontend-design`; BE: `data-systems-coding-lens`/`ddd-tactical`). The reviewer must also check that changed behavior is covered by test-first tests and that touched code was left clean. Require the review-output contract (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation): reuse `.agents/skills/codex-runner/schemas/review-output.schema.json` for Kimi (`--output-schema`) and embed the same shape in the Opus reviewer's prompt.
2. **Stop** the loop when the reviewer returns `approve` with no high-severity findings.
3. **Else fix:** send the findings back to the **same implementer** to preserve context — FE via `SendMessage` to the Opus subagent; BE via `codex-runner --resume <session_id> --role implementer`. The implementer addresses findings and re-commits.
4. After **3** cycles without approval, stop that track and record the unresolved findings for escalation.

Never apply review findings yourself; the implementer applies its own fixes. Never auto-accept — the reviewer must actually re-check after each fix.

## Phase 3 — Integration

1. Create an integration branch off `<base>` and merge both track branches into it (commands in the worktree reference). Phase 0's disjoint scopes should make this clean; resolve any conflict yourself using both diffs, preserving each track's intent.
2. Run the full verification commands. If red, run a bounded integration-fix loop (≤3): route the failure to the track whose code caused it (FE→Opus subagent, BE→Codex `--resume`), re-merge, re-test.
3. Proceed only when the integrated branch is **green** (or escalate if it cannot be made green within the loop).

## Phase 4 — Final Review (full-review) & Apply

Run the **`full-review`** skill on the integrated change. full-review is itself multi-model (Codex + Claude + Gemini external runners, six bug finders, personas, conditional specialists, execution-based verification, and a structural-maintainability pass), so it fulfills "Opus and Codex review together" and goes further — verified bugs, security, compatibility, and simplification/maintainability findings — than a hand-rolled joint pass.

1. **Invoke** `full-review` against the integration branch, scoped to this change — a local diff against `<base>` (or the commit range `<base>..<integration>`). Pass `security_focus=true` when the change is security-sensitive. full-review is **read-only**; it returns a verdict (`APPROVE`/`COMMENT`/`REQUEST_CHANGES`), severity-ranked findings, and `tests_to_run`.
2. **Triage** the findings as orchestrator: every CRITICAL/HIGH must be fixed; apply MEDIUM maintainability/simplification findings that are safe and behavior-preserving; record anything deliberately deferred with a reason. Treat full-review's machine JSON as the source of truth.
3. **Apply** fixes/simplifications via the responsible implementer (BE → Codex `--resume`; FE → `SendMessage` the Opus subagent), preserving TDD — add/adjust a test for any behavioral fix. Keep each fix scoped to the finding.
4. **Re-verify:** re-run the verification commands — must be **green** — and re-run `full-review` (or `quick_mode`) when CRITICAL/HIGH were fixed, until the verdict is `APPROVE` or only accepted findings remain.

## Phase 5 — Report & Handoff

Deliver inline, and write `.ai-workflow/impl-review/<session_id>/report.md` in persisted mode:

1. **Task** and final status (`done` / `partial` / `escalated`).
2. **Seats** used and any degraded/unavailable seats with reasons.
3. **Frontend** — what was built, tests added (test-first), lenses applied, review cycles used, findings resolved vs. outstanding.
4. **Backend** — same.
5. **Integration** — merge notes, conflicts resolved.
6. **Final review (full-review)** — the verdict, count of findings by severity, what was fixed/simplified, and anything deliberately deferred with the reason.
7. **Verification** — exact commands run and their result (green/red); confirm the new test-first tests pass; state plainly if no tests existed.
8. **Branch/worktree** — the integration branch name and how to inspect or land it. Do not push, open a PR, or delete worktrees unless the user asks.
9. **Escalations** — any track stopped at the 3-cycle cap, with the open findings.

## Degrade Gracefully

- **Kimi missing (FE reviewer):** use Codex as the FE reviewer instead (still cross-model, since FE is implemented by Opus); note the substitution and lowered diversity.
- **Codex missing (BE implementer):** cannot run the intended backend track. With approval, have an Opus subagent implement BE and use Kimi (or, if absent, the orchestrator is *not* allowed — pick a different model) as its reviewer; flag the loss of cross-vendor diversity. If neither a write-capable seat nor a distinct reviewer remains for a non-empty track, stop and report.
- **Not a git repo:** run tracks **sequentially** in the working tree (backend fully, then frontend), per the worktree reference's fallback; no merge step. full-review then runs against the local diff.
- **No tests/build found:** TDD still drives design where a test harness can be introduced; if truly none exists, complete the build and reviews, run `full-review`, and report that verification could not run — never imply it passed.
- **full-review external runners unavailable:** full-review degrades on its own (it lowers its confidence cap and notes lost triangulation) — let it; still apply its findings. Do not skip the final review.
- Lower overall confidence one band for each degradation and surface it in the report.

## Output Contract

Return:
1. `report_path` (or `null`)
2. final status + per-track summary (built / cycles / outstanding)
3. integration branch name and verification result
4. a concise inline rendering of the report

## Gotchas

- BE implementer needs write + command execution; pass the write flag only after the Phase 0 approval (or `--auto`). Reviewers and `full-review` are always read-only (`--restrict-tools`, no `--role` overrides that would grant writes).
- **Skills don't load inside runner/subagent seats.** The orchestrator invokes skills it can (`full-review`, planning/lens skills); for implementer seats, embed the methodology from `references/methodology.md` into the brief.
- **`full-review` is read-only** — it never edits. Applying its findings is a separate step by an implementer seat, followed by re-verification.
- Read implementer/reviewer results from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript).
- Keep state in the orchestrator: read diffs from worktrees rather than pulling full implementer transcripts into context, so the seats across multiple phases don't blow the budget.
- `--resume <session_id>` continues the *same* Codex thread for fixes; `SendMessage` continues the *same* Opus subagent. Use them — re-spawning loses the implementer's context.
- Fixes and simplifications must not regress behavior, and TDD still applies — add or adjust a test for every behavioral fix, and re-run verification after each change.
- Two-plus Opus instances is intended. The reviewer Opus must be a separate subagent from any implementer, and the orchestrator never reviews or writes a track itself.
