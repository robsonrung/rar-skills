---
name: implement-and-review
description: "Implement ONE scoped task end-to-end with cross-model review. Given a task prompt, decide the frontend/backend split and route each track by task shape: the default Codex seat executes explicit backend and standard product-interface work, while the Opus seat handles visual or highly creative interfaces and unresolved root-cause diagnosis; the other seat reviews. Build test-first in parallel isolated git worktrees, apply the repo's lens skills, loop implement→cross-review→fix (max 3), integrate, self-simplify, then gate the final code with full-review. Use to implement/build/fix a single scoped task with TDD and cross-model review. For a whole task queue, use implement-tasks."
---

# Implement And Review

Implement **one scoped task** with two model tracks that build in parallel and review each other's work, then converge on one integrated, reviewed, tested change. You (the main agent — model ids live only in `shared/references/model-roster.md`) are the **orchestrator**: you decide the split, dispatch seats, gate writes, run the fix loops, integrate, and run the final review. You never implement a track yourself — you delegate and coordinate.

This skill builds **one task**. To build a whole task queue, use **`implement-tasks`**, which calls this skill per task. Keep this skill simple and self-contained.

**Runs standalone on any input grade.** The task can arrive as a one-line prompt, a tracker-issue brief, or a full `to-tasks` Slice Contract — the engine is the same; only how much it has to derive changes. It needs no pipeline around it: invoke it directly on a bare prompt and it derives the split, lenses, and done-gate itself. For unattended / looped use, pass `--auto` to skip the Phase 0 approval gate (never for a slice typed `HITL` — see Phase 0). A richer input (a Slice Contract) is an enrichment it _lifts_ (Phase 0, step 1), never a requirement.

Both tracks are **test-first (TDD)** and follow the **boy-scout rule** — leave touched code cleaner than found. The defining shape is **cross-model review**: the model that writes a track never reviews its own track. Read `shared/references/task-shaped-model-routing.md` before assigning seats.

| Track shape | Implementer | Reviewer |
| --- | --- | --- |
| Standard product interface from an explicit contract | default Codex seat (`codex-runner --role implementer`, write-enabled) | fresh Opus seat (read-only) |
| Visual reconstruction, games, animation, 3D, or highly creative interface | Opus seat (`Agent model:"opus"` or `claude-runner --model opus`, write-enabled) | fresh default Codex seat (read-only) |
| Backend after the contract or reproduction is explicit | default Codex seat (`codex-runner --role implementer`, write-enabled) | fresh Opus seat (read-only) |
| Difficult root-cause investigation without a reproduction or diagnostic plan | Opus seat, read-only diagnosis first | default Codex seat executes only after the chain is closed |
| Self-simplify | **`coding-review-simplify`** (standard mode) on the integrated diff, before the final gate | — |
| Final review | the **`full-review`** skill on the task's integrated diff — full-review's multi-model triangulation (seat roster per `shared/references/model-roster.md`) — then apply findings | — |

Kimi is the first fallback reviewer when the preferred cross-model reviewer is unavailable. Several independent contexts may use the same seat; keep them separate and never count them as model diversity.

Exact launch commands and the worktree/integration git flow are in [references/runner-invocations.md](references/runner-invocations.md) and [references/worktree-and-integration.md](references/worktree-and-integration.md); per-track methodology + skill snippets in [references/methodology.md](references/methodology.md). Read them before Phase 1.

## Hard Rules

1. **Orchestrator coordinates, never implements.** Classify the task shape and dispatch the assigned seat from the table above.
2. **Cross-model review is mandatory.** The preferred reviewer is the other primary seat: Opus reviews Codex work and Codex reviews Opus work. Kimi is a fallback reviewer, never the first default. An implementer never reviews its own track.
3. **Test-first (TDD).** Both tracks build via red-green-refactor — a failing test before the code that passes it, one test → one minimal change, refactor only on green. One exception: a Slice Contract whose acceptance states `Test expectation: none — [reason]` pre-authorises the no-test route in [references/evidence-strategy.md](references/evidence-strategy.md) — the implementer reports the slice's reason as `no_test_reason` and the acceptance commands as the replacement verification, and the reviewer confirms no behavioral change slipped in under it.
4. **Good code, boy-scout rule.** Produce clean code (clear names, small focused units, no duplication/dead code) and leave touched files cleaner than found — but scope improvements to what the task changes; never rewrite unrelated areas or change behavior beyond the task.
5. **Apply the repo's lens skills.** Each track works through the relevant quality/architecture skills (see [Methodology & Per-Track Skills](#methodology--per-track-skills)); the integrated diff gets a **`coding-review-simplify`** pass, and the final gate is **`full-review`** on the code that ships.
6. **Writes are gated.** No code until the user approves the plan + FE/BE split in Phase 0 (skip only when `--auto`, and never for a `HITL` slice). Implementers run unattended-write only after that approval.
7. **Isolated parallelism.** Each track builds in its own git worktree/branch so they cannot clobber each other. Fall back to sequential same-tree execution when the project is not a git repo.
8. **Bounded fix loop.** At most **3** review→fix cycles per track. Still blocking after 3 → stop and escalate with the open findings.
9. **Definition of done = green.** The integrated task — after applying full-review findings — passes the project's tests/build (including the new test-first tests). If none exist, say so; never claim "tests pass" when none ran. Green must be earned: never delete, skip, weaken, or mock-away tests — or loosen acceptance checks — to reach it (`shared/references/engineering-rules.md`, Contract integrity); a wrong contract is escalated, not edited around.
10. **Never fabricate or silently swap a seat.** Pass `--disable-fallback` to every runner. Missing seat → degrade per [Degrade Gracefully](#degrade-gracefully) and say so.

## Methodology & Per-Track Skills

These are Claude Code skills. The **orchestrator** invokes them directly — in Phase 0 (design with the lenses) and for the final `full-review`. Runner/subagent implementers (Codex, the Opus FE subagent, Kimi) **cannot load skills**, so **embed each track's methodology into its brief** using the ready-made snippets in [references/methodology.md](references/methodology.md).

| Scope | Skills to apply |
| --- | --- |
| Both tracks | `tdd` (+ `safe-incremental-coding`), `clean-code`, `safe-incremental-coding` (untested/legacy code → characterization-test net first), `architecture-lens` (coupling, layer placement, cohesion, trade-offs when restructuring), `coding-design-plan`, `test-lens` |
| Frontend | `frontend-design`, `advanced-react` (when React — 17 + MUI + Redux Toolkit: re-renders, memo, context, stale closures, fetch races), `ui-ux-pro-max` |
| Backend | `data-systems-coding-lens` (stored state, transactions, idempotency/retries, concurrency, migrations, observability), `domain-driven-design` (business-logic pattern + aggregate invariants; bounded-context boundaries & integration when crossing a service/context boundary), `agent-architecture-lens` (when the thing being built is an agent — loop vs graph, agent state, bounded retries, termination ceilings) |
| Planning lenses (only when a slice's `gates` flag them) | `macro-architecture`, `software-design-philosophy`, `design-patterns`, `distributed-systems-patterns` — the orchestrator runs them in Phase 0 and their conclusions go into the briefs as constraints; compact seat snippets in [references/methodology.md](references/methodology.md) |
| Integrated diff | `coding-review-simplify` (standard mode) — behavior-preserving tightening before the final gate |
| Final review | `full-review`; `security-gate` / full-review `security_focus=true` when the change is security-sensitive |

Apply only the lenses that fit the task; don't force every skill onto every change. Checklists + paste-in snippets: [references/methodology.md](references/methodology.md).

## Preflight

1. **Host & git.** Confirm the `Agent` tool exists (native Opus subagents). Confirm `git rev-parse --is-inside-work-tree`. No git → sequential fallback (worktree reference).
2. **Seats.** Use the shared probe: `python3 .agents/skills/shared/scripts/discover_runners.py probe --native-agent yes --seat codex --seat opus --seat kimi --seat grok --format json`. Require the default Codex seat and either a native or runner-backed Opus seat. Kimi is the first fallback reviewer; Grok matters only as the fallback backend implementer when Codex is missing. Mark missing seats and degrade.
3. **Verification commands.** Detect how this project tests/builds and runs a _single_ test (TDD needs a fast inner loop). These back the done gate — unless the task carries a Slice Contract, whose `acceptance` commands are the authoritative done gate (confirm they exist and run; reconcile with the user if they don't, never silently swap).
4. **Base & artifacts.** Record the current head as `<base>` (when called by `implement-tasks`, this is the task's assigned base). When `.ai-workflow/` is writable, use `.ai-workflow/impl-review/<session_id>/`; else keep state inline.
5. **Queue entry.** When the task was published by `to-tasks` — a file `.ai-workflow/work/<feature-slug>/tasks/T<N>-<slug>.md` headed `# T<N>: …` — record its T-ID and path. Its `Status` line flips (`in-progress` at Phase 1, `done` or `blocked` at Phase 5) are side effects keyed `status:<T-ID>:<state>` in the run state; never edit the parent PRD or another slice's file.

## Phase 0 — Plan the Task (gate)

1. **Understand the task.** The default input is just a task description (often a bare prompt) — read it, and if it's ambiguous, clarify first (or, under `--auto`, record an assumption and proceed). **Lift a Slice Contract when one is present** — a task from `to-tasks` carries more than a description, and every field below was approved by the user, so **lift them, don't re-derive them**; re-deriving what an approved contract already states invites drift between what was approved and what gets built:
   - **T-ID and type.** Cite the T-ID in the run state and the report (and in `--slice` when a caller namespaces the build). `Type: HITL` means the slice needs a human decision — an irreversible migration, external contract sign-off, design approval — so **`--auto` never applies to it**: run the Phase 0 gate and park at `awaiting_human` (run-state contract) until the decision is recorded in `gates`.
   - **`acceptance`.** The commands ARE the done gate (Hard Rule 9); the behaviors are the test-first targets. `Test expectation: none — [reason]` pre-authorises the no-test route (Hard Rule 3).
   - **`gates`.** The lens flags select which lenses each track applies (step 2; when flags were set at planning time `design-gate` says use them as-is, capped at 3). `security: deep` means Phase 4 runs `full-review` with `security_focus=true` against the parent PRD's recorded security decisions; `standard` adds nothing.
   - **Expected review focus.** The slice's named risk goes into every Phase 2 review prompt and the Phase 4 `full-review` invocation, on top of the lens checklist.
   - **Rollback note.** Carried into the briefs as a boundary — a slice declared "plain revert, no side effects" must not grow a migration, data write, external call, or published contract — and checked against the integrated diff in Phase 4.

   **Ambiguity in a Slice Contract is a contract defect, not a judgment call.** A decision the contract does not answer, and that changes what gets built, is escalated with the gap named (`status: escalated`) — even under `--auto`; the assumption-and-proceed path above is for bare prompts only (`shared/references/engineering-rules.md`, Contract integrity — a corrected contract is a user decision). With no contract, derive all of this yourself in the steps below.

2. **Design pass** (lightweight) running the lenses the `gates` flags select when a contract is present, otherwise the planning/architecture lenses as warranted — `coding-design-plan`, `design-gate`, `domain-driven-design` (BE business-logic pattern). Informs the briefs, not a deliverable.
3. **Split and route the task** into a **frontend** part and a **backend** part with **disjoint file scopes** (e.g. `client/**` vs `server/**`), the **behaviors to test first**, and the **shared contracts** (API shapes, types) both tracks must honor. Classify frontend as `standard_product` or `visual_creative`; use `standard_product` unless the task explicitly requires visual reconstruction, games, animation, 3D, or original creative direction. If a difficult bug lacks a reproduction or diagnostic plan, run an Opus diagnosis before assigning implementation. A task may be single-track (pure-FE or pure-BE).
4. **Present** the split, which model does what, the behaviors-to-test, the shared contracts, and the verification commands. **Get approval before any code is written**, unless `--auto`.
5. **Record the approval.** Append `{"gate": "phase0_plan_approval", "decision": "approved"}` (or `"auto"` under `--auto`) to `gates` in the run state before Phase 1. On resume, a gate already in `gates` is **already decided** — do not re-ask. A gate _absent_ from `gates` was never granted, whatever the transcript appears to say, so a resumed run that cannot find it stops and asks.

### Run state

This skill follows `shared/references/run-state-contract.md`. Extend the launcher's `launch-manifest.json` with the contract's keys rather than adding a second file — it already persists session, tracks, worktrees, and job ids, but nothing about _where the run is_. Carry at minimum: `status`, `phase`, `attempts` (the per-track fix-cycle counters), `ceilings` (`max_cycles: 3`), `gates`, and `steps`. Progress lives in **the ledger, not the transcript**: after a compaction, `poll` can tell you the Codex job finished, but only the manifest can tell you it was fix-cycle 2 of 3.

## Phase 1 — Implement (FE + BE, test-first, parallel)

Fast path: the bundled launcher creates the worktrees, fires the runner-backed implementer(s), and polls — `python3 .agents/skills/implement-and-review/scripts/launch.py launch --session-id <id> --fe-brief <f> --be-brief <f>`. The default frontend seat is Codex for `standard_product`; pass `--fe-seat opus` for `visual_creative`, and add `--fe-mode runner` when no native Opus subagent is available. See [the launcher section](references/runner-invocations.md#launcher-script-one-call-setup). Manual git is the fallback.

When the task came from a published queue (Preflight step 5), flip its status to `in-progress` first — side-effect key `status:<T-ID>:in-progress`, skipped on resume if already recorded.

Create one worktree+branch per non-empty track off `<base>`, then build both tracks **concurrently**. Every brief embeds the track methodology from [references/methodology.md](references/methodology.md): the **TDD loop**, the **good-code / boy-scout** rule, the track's **lens checklist**, the explicit scope, the acceptance contract, the commands that must pass, and — when the task carries a Slice Contract — the **Slice Contract snippet** (expected review focus, rollback boundary, and the no-test route when the contract states it).

- **Standard frontend:** run the default Codex seat with write access in the FE scope. It implements test-first, honors shared contracts, applies FE lenses, and continues until the FE acceptance commands pass or a configured exit fires.
- **Visual or creative frontend:** spawn a named Opus subagent (`Agent`, `model:"opus"`, write-enabled, addressable for fix rounds via `SendMessage`) or use `claude-runner --model opus --allow-write`. Give it the complete specification and an explicit boundary around unchanged behavior.
- **Backend:** run the default Codex seat with write access in the BE scope. Give it the BE work, behaviors-to-test, shared contracts, exact scope, acceptance commands, and embedded methodology. Use `--background`/`--output-file`; keep the `session_id` for `--resume` fixes.

Commit tests and code interleaved (not all tests then all code).

**Evidence contract (mandatory in every implementer brief):** each track chooses its evidence route and captures the red failure/characterization baseline **before** changing production code, then reports it as `verification_evidence` (fields per `shared/runner-envelope.schema.json`) — the worker is the only party that witnesses red-before-implementation, so a report without it cannot be reconstructed later. Routes, the System-Wide Test Check, and the Parallel Safety Check (semantic contention beyond file overlap; decline parallelism on uncertainty) live in [references/evidence-strategy.md](references/evidence-strategy.md) — read it before writing briefs and apply the safety check before dispatching tracks concurrently. A track reporting `behavior_changed: true` without coherent evidence gets one recovery re-invocation to reconcile evidence (not reimplement); a second failure blocks integration.

## Phase 2 — Cross-review + Fix (≤3 cycles per track)

For each track, each cycle: read `attempts.<track>_fix_cycle` from the run state (absent = `0`), increment and write it back **before** starting the cycle — a cycle that crashes mid-review has still been spent — then compare against `ceilings.max_cycles`. At or over the bound, go straight to step 4 without starting another review. **The model never decides the retry**: the cap is the counter on disk, not a recollection of how many rounds have happened.

1. **Review the diff** (`git -C <worktree> diff <base>..HEAD`) with the other primary seat, read-only, against the task + shared contracts, **through the track's lens checklist** and, when the task carries a Slice Contract, its **expected review focus** (the slice's named risk is where the reviewer spends attention first). Opus reviews Codex work; the default Codex seat reviews Opus work. The reviewer also checks that changed behavior is covered by test-first tests and that touched code was left clean. Require the review-output contract (verdict `approve`/`needs-attention`, severity-ordered findings with file/line/recommendation). Kimi may fill either reviewer role only when the preferred reviewer is unavailable.
2. **Stop** when the reviewer returns `approve` with no high-severity findings.
3. **Else fix** via the **same implementer** using its saved subagent or runner session; re-review.
4. After **3** cycles without approval, stop and escalate the open findings, and set `status` to `ceiling_hit` naming the track that exhausted its cycles.

Never apply review findings yourself; the implementer fixes its own track. Never auto-accept — the reviewer re-checks after each fix.

## Phase 3 — Integrate the Two Tracks

1. Merge both track branches into an integration branch off `<base>` (commands in the worktree reference). Disjoint scopes should make this clean; resolve any conflict using both diffs, preserving each track's intent and the shared contracts. The merge is a side effect: append `merge:<track>-><integration>` to `side_effects` before running it, and skip a merge whose key is already recorded — a resumed run must not re-merge a branch it already merged.
2. Run the full verification commands. Red → bounded integration-fix loop (≤3), counted in `attempts.integration_fix` on the same read-increment-write rule as Phase 2: route the failure to the responsible track, re-merge, re-test.
3. Proceed only when **green** (or escalate).
4. **Self-simplify before the gate.** With the integration green, run **`coding-review-simplify`** (standard mode) on the integrated diff — a behavior-preserving tightening pass (reuse, dedupe, dead code, unnecessary abstraction, the FE/BE seam) run while the context is still fresh and _before_ the review gate. Apply its safe findings through the responsible implementer's saved runner or subagent session, re-verify **green**, then enter Phase 4. Ordering is load-bearing: `full-review` gates the **final** code, so never let a mutating pass follow it unreviewed.

## Phase 4 — Final Review (full-review) & Apply

Run the **`full-review`** skill on the task's integrated diff — full-review's multi-model triangulation (seat roster per `shared/references/model-roster.md`) plus bug finders, personas, specialists, execution-based verification, and a structural-maintainability pass, so it goes well beyond the per-track review.

1. **Invoke** `full-review` (local diff vs `<base>`, or range `<base>..<integration>`), passing the slice's expected review focus as the review focus when there is one. `security_focus=true` when the slice is `security: deep` or the change is otherwise security-sensitive; for `deep`, hand it the parent PRD's recorded security decisions as what the implementation must match (`security-gate`). If the build grew beyond the slice's declared scope, re-check `security-gate`'s trigger list before invoking — flags only escalate, never downgrade. It is **read-only**.
2. **Triage:** fix every CRITICAL/HIGH; apply safe, behavior-preserving MEDIUM simplification/maintainability findings; record deferrals with a reason. The machine JSON is the source of truth. For a slice, also confirm the integrated diff matches its **rollback note** — no undeclared migration, data write, external call, or published contract; a mismatch is a HIGH finding routed to the responsible implementer, or escalated when the note itself was wrong.
3. **Apply** through the responsible implementer's saved runner or subagent session, preserving TDD — add/adjust a test for any behavioral fix.
4. **Re-verify:** **green**; re-run `full-review` (or `quick_mode`) when CRITICAL/HIGH were fixed, until `APPROVE` or only accepted findings remain.

## Phase 5 — Report

Deliver inline and write `.ai-workflow/impl-review/<session_id>/report.md` (persisted mode):

1. **Task** (T-ID when present) and final status (`done` / `escalated`).
2. **Seats** used and any degraded/unavailable seats with reasons.
3. **Frontend** — what was built, tests added (test-first), lenses applied, review cycles, findings resolved vs. outstanding.
4. **Backend** — same.
5. **Integration** — merge notes, conflicts resolved.
6. **Self-simplify (coding-review-simplify)** — what was tightened on the integrated diff, and what was left alone.
7. **Final review (full-review)** — verdict, findings by severity, what was fixed/simplified, deferrals with reasons.
8. **Verification** — exact commands run and results (green/red); for a Slice Contract, a checklist of every acceptance command and every behavior with the test that proves it (or the `Test expectation: none` reason and the replacement verification performed); confirm the new test-first tests pass; state plainly if none existed.
9. **Rollback** — for a slice, confirm the shipped change matches its rollback note, or state exactly what differs.
10. **Branch/worktrees** — the integration branch name and how to inspect/land it. Do not push, open a PR, or delete worktrees unless asked.
11. **Escalations** — any track stopped at the 3-cycle cap, with open findings.
12. **Queue status** — when the task came from a published queue, set its status to `done` (or `blocked` on escalation) — side-effect key `status:<T-ID>:<state>` — and say so; never close or edit the parent issue.

When called by `implement-tasks`, return this report compactly so the orchestrator can integrate the task and move on.

## Degrade Gracefully

- **Preferred reviewer missing:** use Kimi as the first fallback, then another available model distinct from the implementer; note the substitution.
- **GPT 5.6 Sol / Codex missing (BE implementer):** first try **Grok 4.6** as the fallback BE implementer (`grok-runner --role implementer --effort high`, write-enabled; Opus still reviews — cross-vendor diversity is preserved) and note the substitution. If `grok` is also missing, with approval have an Opus subagent implement BE and a _different_ model review it; flag lost cross-vendor diversity. If no write-capable seat + distinct reviewer remain for a non-empty track, stop and report.
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
- `--resume <session_id>` continues the _same_ Codex thread; `SendMessage` continues the _same_ Opus subagent. Re-spawning loses context.
- Fixes/simplifications must not regress behavior; TDD still applies — add/adjust a test per behavioral fix and re-verify.
- Two-plus Opus instances is intended. A reviewer Opus must be a separate subagent from any implementer, and the orchestrator never reviews or writes a track itself.
- **A Slice Contract is lifted whole.** Type, acceptance, gates, expected review focus, and rollback note each have a consumer in this skill (Phase 0 step 1); dropping one silently is exactly the drift `to-tasks` exists to prevent.
- **Scope is one task.** If the request is a whole feature (many independent pieces, a plan, or a task list), use `implement-tasks` — it schedules the queue and calls this skill per task.
