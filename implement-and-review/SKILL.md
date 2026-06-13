---
name: implement-and-review
description: Orchestrate a two-track implementation with cross-model review. A frontend track (a native Opus 4.8 subagent implements, Kimi reviews) and a backend track (Codex implements, an Opus 4.8 subagent reviews) run in parallel in isolated git worktrees, each looping implement→cross-review→fix (max 3 cycles), then the orchestrator integrates both branches and runs a joint Opus+Codex review-and-simplify pass, leaving the repo's tests/build green. Opus is the orchestrator. Use when the user wants to build/implement a feature with split frontend/backend work, cross-model code review, and a final simplification pass, or asks for a multi-model implementer / build pipeline. Distinct from model-roundtable (interpretation only, no code), collaborative_delivery (panel-gated TDD), and ship (single-model end-to-end pipeline).
---

# Implement And Review

Build a feature with two model tracks that implement in parallel and review each other's work, then converge on one integrated, simplified, tested solution. You (the main agent, Opus 4.8) are the **orchestrator**: you plan, split the work, dispatch seats, gate writes, run the fix loops, integrate, and run the final joint pass. You do not implement the tracks yourself — you delegate and coordinate.

The defining shape is **cross-model review**: the model that writes a track never reviews its own track.

| Track | Implementer | Reviewer |
|-------|-------------|----------|
| Frontend | native Opus 4.8 subagent (`Agent`, `model:"opus"`, write-enabled) | Kimi (`kimi-runner --role codereviewer`, read-only) |
| Backend | Codex (`codex-runner --role implementer`, write-enabled) | native Opus 4.8 subagent (read-only) |
| Final joint pass | Opus + Codex together review **and simplify** the integrated solution | — |

There are several independent Opus contexts here (orchestrator, FE implementer, BE reviewer, joint-pass reviewer). Keep them separate; never let one act as another.

Exact launch commands and the worktree/integration git flow live in
[references/runner-invocations.md](references/runner-invocations.md) and
[references/worktree-and-integration.md](references/worktree-and-integration.md). Read both before Phase 1.

## Hard Rules

1. **Orchestrator coordinates, never implements a track.** Delegate FE to the Opus subagent and BE to Codex.
2. **Cross-model review is mandatory.** Kimi reviews FE (Opus's work); Opus reviews BE (Codex's work). An implementer never reviews its own track.
3. **Writes are gated.** Do not write code until the user approves the plan + FE/BE split in Phase 0 (skip the gate only when `--auto` is set). Implementers run unattended-write only after that approval.
4. **Isolated parallelism.** Each track builds in its own git worktree/branch so the tracks cannot clobber each other. Fall back to sequential same-tree execution only when the project is not a git repo.
5. **Bounded fix loop.** At most **3** review→fix cycles per track. If a reviewer still blocks after 3, stop that track and escalate to the user with the open findings.
6. **Definition of done = green.** The integrated solution, and again after the joint simplify pass, must pass the project's tests/build. If none exist, say so explicitly; never claim "tests pass" when none ran.
7. **Never fabricate or silently swap a seat.** Pass `--disable-fallback` to every runner. If a required seat is missing, degrade per [Degrade Gracefully](#degrade-gracefully) and say so.

## Preflight

1. **Host & git.** Confirm the `Agent` tool exists (native Opus subagents). Confirm `git rev-parse --is-inside-work-tree`. No git → use the sequential fallback in the worktree reference.
2. **Seats.** `codex` in `PATH` (BE implementer + joint pass); `kimi-cli` in `PATH` (FE reviewer). Mark missing seats and apply degradation.
3. **Verification commands.** Detect how this project tests/builds (e.g. `package.json` scripts, `Makefile`, `pytest`, `cargo`, etc.). Record the exact commands; you will run them at integration and after the joint pass.
4. **Base commit.** Record current `HEAD` as `<base>`; all branches fork from it.
5. **Artifacts.** When `.ai-workflow/` is writable, use `.ai-workflow/impl-review/<session_id>/` for briefs, review outputs, and the report; otherwise keep state inline and return paths as `null`.

## Phase 0 — Plan & Decompose (gate)

1. Understand the task. If it is ambiguous, clarify first (or run `model-roundtable` if the user wants a shared interpretation before building).
2. Split the work into a **frontend task set** and a **backend task set** with **disjoint file scopes** (e.g. `client/**` vs `server/**`). List shared contracts (API shapes, types) both tracks must honor — capture these in the shared brief so the tracks stay compatible without editing each other's files.
3. A track may be empty (pure-FE or pure-BE task); skip the empty track and still run the joint pass on whatever was built.
4. Present: the plan, the FE/BE split, which model does what, the shared contracts, and the verification commands. **Get approval before any code is written**, unless `--auto`.

## Phase 1 — Parallel Implementation (isolated worktrees)

Create one worktree+branch per non-empty track off `<base>` (commands in the worktree reference), then launch both implementers **concurrently** (issue the Codex `Bash` call and the Opus `Agent` call in one message).

- **Frontend:** spawn a named Opus subagent (`Agent`, `model:"opus"`, write-enabled, addressable so you can send fix rounds via `SendMessage`). Instruct it to operate **only inside the frontend worktree**, implement the FE task set, honor the shared contracts, run FE-local tests, and return a compact summary (files changed, how to test, self-noted risks). Do not paste its full diff into your context — you will read the diff from the worktree.
- **Backend:** run `codex-runner --role implementer` in the backend worktree with write access, the BE task set + shared contracts as the brief, and `--background`/`--output-file` so its transcript stays out of your context. Keep the returned `session_id` — you will `--resume` it for fixes.

Each implementer commits its work on its branch.

## Phase 2 — Cross-review + fix loop (≤3 cycles per track)

Run both tracks' loops independently (they can proceed in parallel).

For each cycle:
1. **Review the diff** (`git -C <worktree> diff <base>..HEAD`) with the cross-model reviewer, read-only, against the track's task set + shared contracts. Require the review-output contract (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation): reuse `.agents/skills/codex-runner/schemas/review-output.schema.json` for Kimi (`--output-schema`) and embed the same shape in the Opus reviewer's prompt.
2. **Stop** the loop when the reviewer returns `approve` with no high-severity findings.
3. **Else fix:** send the findings back to the **same implementer** to preserve context — FE via `SendMessage` to the Opus subagent; BE via `codex-runner --resume <session_id> --role implementer`. The implementer addresses findings and re-commits.
4. After **3** cycles without approval, stop that track and record the unresolved findings for escalation.

Never apply review findings yourself; the implementer applies its own fixes. Never auto-accept — the reviewer must actually re-check after each fix.

## Phase 3 — Integration

1. Create an integration branch off `<base>` and merge both track branches into it (commands in the worktree reference). Phase 0's disjoint scopes should make this clean; resolve any conflict yourself using both diffs, preserving each track's intent.
2. Run the full verification commands. If red, run a bounded integration-fix loop (≤3): route the failure to the track whose code caused it (FE→Opus subagent, BE→Codex `--resume`), re-merge, re-test.
3. Proceed only when the integrated branch is **green** (or escalate if it cannot be made green within the loop).

## Phase 4 — Joint Review & Simplify (Opus + Codex)

Opus and Codex now work together on the **integrated** diff (`git diff <base>..<integration>`). This is a quality pass — reuse, simplification, efficiency, and consistency across the FE/BE seam — **not** new behavior.

1. Both review independently, read-only: Codex via `codex-runner --role codereviewer` with the review-output schema; an Opus subagent with the same shape. Ask each for simplifications that preserve behavior.
2. **Reconcile** as orchestrator: apply simplifications both agree on or that are clearly safe; for conflicting advice, keep the safer option and note the disagreement; drop anything that would change behavior.
3. Apply the agreed simplifications via one implementer (Codex `--resume` or an Opus subagent with write access), then **re-run the verification commands — must be green again**.

## Phase 5 — Report & Handoff

Deliver inline, and write `.ai-workflow/impl-review/<session_id>/report.md` in persisted mode:

1. **Task** and final status (`done` / `partial` / `escalated`).
2. **Seats** used and any degraded/unavailable seats with reasons.
3. **Frontend** — what was built, review cycles used, findings resolved vs. outstanding.
4. **Backend** — same.
5. **Integration** — merge notes, conflicts resolved.
6. **Joint simplify** — simplifications applied, disagreements noted, anything deliberately left.
7. **Verification** — exact commands run and their result (green/red); state plainly if no tests existed.
8. **Branch/worktree** — the integration branch name and how to inspect or land it. Do not push, open a PR, or delete worktrees unless the user asks.
9. **Escalations** — any track stopped at the 3-cycle cap, with the open findings.

## Degrade Gracefully

- **Kimi missing (FE reviewer):** use Codex as the FE reviewer instead (still cross-model, since FE is implemented by Opus); note the substitution and lowered diversity.
- **Codex missing (BE implementer):** cannot run the intended backend track. With approval, have an Opus subagent implement BE and use Kimi (or, if absent, the orchestrator is *not* allowed — pick a different model) as its reviewer; flag the loss of cross-vendor diversity. If neither a write-capable seat nor a distinct reviewer remains for a non-empty track, stop and report.
- **Not a git repo:** run tracks **sequentially** in the working tree (backend fully, then frontend), per the worktree reference's fallback; no merge step.
- **No tests/build found:** complete the build and reviews, run the joint simplify, and report that verification could not run — never imply it passed.
- Lower overall confidence one band for each degradation and surface it in the report.

## Output Contract

Return:
1. `report_path` (or `null`)
2. final status + per-track summary (built / cycles / outstanding)
3. integration branch name and verification result
4. a concise inline rendering of the report

## Gotchas

- BE implementer needs write + command execution; pass the write flag only after the Phase 0 approval (or `--auto`). Reviewers and the joint-pass analysis are always read-only (`--restrict-tools`, no `--role` overrides that would grant writes).
- Read implementer/reviewer results from `agent_message` / `--output-file`, never raw stdout (Kimi appends a resume hint; Codex emits a transcript).
- Keep state in the orchestrator: read diffs from worktrees rather than pulling full implementer transcripts into context, so five seats across multiple phases don't blow the budget.
- `--resume <session_id>` continues the *same* Codex thread for fixes; `SendMessage` continues the *same* Opus subagent. Use them — re-spawning loses the implementer's context.
- The joint pass simplifies; it must not regress behavior. Re-run verification after applying simplifications, every time.
- Two-plus Opus instances is intended. The reviewer Opus must be a separate subagent from any implementer, and the orchestrator never reviews or writes a track itself.
