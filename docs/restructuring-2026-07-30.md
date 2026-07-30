# Restructuring — 2026-07-30

A repo-wide consolidation pass. Goal: one workflow, the fewest user-called skills per step, no duplicated knowledge, and a pipeline that runs entirely on skills in this collection.

**Net: 68 → 56 skills.** 17 removed, 5 added, 165 files changed (+3,211 / −7,987). Decision rationale per merge is in [porting-trigger-audit.md](porting-trigger-audit.md); the workflow narrative is in [workflow.md](workflow.md).

---

## Why anything changed

Three problems blocked the "one workflow" goal:

1. **The pipeline was not self-contained.** `ship` invoked `grill-with-docs` (the specify-phase interview) and `tdd` (the execution loop) — neither existed in this repo. `prototype`, `diagnose`, and `handoff` were also dangling, and phase 5 called a `verify` skill documented as a Claude Code builtin that isn't one. The first and fourth steps of the pipeline routed into holes.
2. **Multiple skills competed at the same step.** Five delivery pipelines, six multi-model councils, two spec skills, two task-breakdown skills, two interview skills, and eleven design lenses in a repo whose `design-gate` existed precisely so lens choice would be a lookup rather than a judgment call.
3. **Order-of-operations bug in the conductor.** `ship` phase 5 ran the expensive multi-model `full-review` *first*, then let the mutating `coding-review-simplify` rewrite the reviewed code, with no re-review.

---

## Added (5)

| Skill | Fills |
|---|---|
| `interview` | The specify-phase requirements interview (the role `grill-with-docs` was supposed to play). Grounds in `CONCEPTS.md`, `docs/adr/`, and the code before asking anything; runs the `security-gate` checklist; names test seams; exits on a spec-ready test. |
| `tdd` | The execution loop. The Iron Law (no production code without a failing test first), the red-green-refactor cadence built on the **smallest reversible move**, the test-writing bar, and a per-step output contract. |
| `diagnose` | Procedural debugging — reproduce, minimize, differential hypotheses, instrument, fix the cause, regression-test. Carries a non-interactive `mode:pipeline` contract so autonomous phases can call it. |
| `prototype` | Throwaway spike discipline for a design unknown only running code can settle, including the throw-it-away rule. |
| `fable-mindset` | The five `fable-*` skills merged into one: intake, diagnosis, decision, implementation, reporting. Governs posture; the procedural counterparts stay separate. |

## Removed (17)

**Merged into a survivor** — no knowledge lost, only the extra trigger surface:

| Removed | Merged into | Why |
|---|---|---|
| `models-roundtable`, `council`, `decision-council` | `models-consensus` (modes `poll` / `debate` / `personas`) | Four skills ran the same five-stage pipeline differing in six knobs, with four copies of the seat roster and a trigger collision on "council this". |
| `collaborative_discovery` | `brainstorm` (panel mode) | Same step, same artifact; only the seat count differed. |
| `collaborative_specification` | `to-spec` (panel mode) | Same. The multi-model path also gained the security-gate handshake it never had. |
| `collaborative_task_design` | `to-tasks` (panel mode) | Its output could not drive the autonomous phases — no gate flags, no stable IDs, no approval gate. `ship` was patching that by hand. |
| `design-integrity` | `software-design-philosophy` | Every step had a stronger owner in the Ousterhout lens; the vocabulary moved verbatim with its CI guard. |
| `feature-models-roundtable` | `implement-feature` | 33 lines of glue for a handoff the callee already documented. |
| `codex-mission-control` | `dynamic-harness` | Shared preflight, agent contract, write-scope rules, and ledger discipline. |
| the five `fable-*` | `fable-mindset` | One body of thought wearing five frontmatters, cross-citing each other. |

**Dissolved or deleted outright:**

| Removed | Disposition |
|---|---|
| `architecture_session_review` | Its lens selection duplicated `design-gate`, its scope classifier duplicated `coding-design-plan`, and its only inbound reference was a fallback row it could not legally serve (it instructed *implementation* inside a read-only gate). References harvested into `architecture-lens` (risk pass, C4 guidance, verification menu), `macro-architecture` (Least Worst Rule, three missing styles), `coding-review-simplify` (team checklists). |
| `coding-implementation-guard` | A lossy recombination of four other skills with near-verbatim duplications. Output contract and scope gotchas → `tdd`. |
| `pragmatic-coding-session` | Six of seven phases handed off to the skill that owned them. Leitwort and loop rules → `tdd`; tracer/prototype and estimation → `coding-design-plan`; resource ownership and hidden time ordering → `data-systems-coding-lens`. |

Also removed: `SKILL_AUDIT_REPORT.md` and `DEV_WORKFLOW_PROPOSAL.md` (both described skills that no longer exist), replaced by [workflow.md](workflow.md).

## Bugs fixed along the way

- **`council --auto` started implementing** (`codex --full-auto`) while `ship` called it expecting deliberation only — a race against ship's own implementation phase. The merged skill never auto-executes.
- **`run_qwen.py` reported `auth_ok: false` on a missing CLI**, violating the envelope contract ("a missing CLI is untested auth, not failed auth"). Its `--output-file` pointer also omitted all five seat-identity keys. Both fixed; qwen is now in the parity test that was blind to it, and the gemma/minimax shims inherit the fix.
- **`--seat qwen` exited with an error** although `full-review` listed it as a backup seat. Seats now carry a `tier`, so backups resolve when named without enlarging any default fan-out.
- **Stale model ids in four routing files**, including `kimi-code/kimi-for-coding` — unresolvable *and* it rewrote the user's persisted cline config on every panel run.
- **`effective_provider` disagreed with itself** across exit paths (`z-ai` vs `zai`, `moonshot` vs `moonshotai`). Normalized across all runner scripts.
- **`panel_round.py` ignored `RUNNER_BASE_PATH`** despite the README promising it, and resolved runner scripts against paths that don't exist in a source checkout.
- Private application identifiers (service map, module names, domain rules) removed from four shared references.

---

## Developing a feature: the call order

`ship` runs all of this end to end. Each step is also usable alone — the chain below is what `ship` automates.

```
 INTERACTIVE  ─────────────────────────────────────┐  AUTONOMOUS (per slice)
 brainstorm → interview → to-spec → to-tasks ──────┤→ coding-design-plan → design-gate
   (prototype)                          ▲          │        → implement-and-review (tdd)
                              APPROVAL GATE        │        → coding-review-simplify
                                                   │        → full-review → browser-smoke
                                                   │        → open-pr → resolve-pr-feedback
```

### 0. `brainstorm` — should we build this?
Optional; skip when the request is already concrete. Digs into motivation before mechanism, explores the codebase, expands the solution space.
**Hands off:** a **BUILD / DEFER / REDUCE SCOPE / REJECT verdict** with confidence and recommended scope. On BUILD it names the next step: run `interview`. If a design unknown can only be settled by running code, it detours through `prototype`, whose decision-rich snippets are the one exception to the later no-file-paths rule.

### 1. `interview` — what exactly are we building?
Reads `CONCEPTS.md`, `docs/adr/`, and the code **before** asking anything (a question exploration could answer is not for the user). Grills actors and permissions, edge cases, scope boundaries, data lifecycle, migration and rollback. Runs the `security-gate` threat-model-lite rows the feature exposes, and names the observable behavior at the highest seam for each requirement (per `test-lens`).
**Hands off:** a **compact decision record in the conversation** — decisions, explicit assumptions with defaults, descoped items, security answers, and named seams. Exit test: every question the autonomous phases would have to ask is answered, recorded as an assumption, or descoped. Closes with "run `to-spec`".

### 2. `to-spec` — write it down
Does **not** interview; it synthesizes what step 1 already produced. This is the **autonomy contract** — the last artifact written while the human is in the room.
**Hands off:** a **PRD published to the issue tracker** with the `ready-for-agent` label (or a repo-root file if no tracker). Two sections are load-bearing downstream: **Security Decisions** (the checklist answers, pre-marking which surfaces are security-sensitive) and **Testing Decisions / named seams** (which become the acceptance behaviors). Panel mode optionally drafts this with a multi-seat panel.

### 3. `to-tasks` — cut it into slices — **the last human gate**
Breaks the PRD into tracer-bullet vertical slices, each with a stable `T-ID` that is never renumbered.
**Hands off:** per slice, a **Slice Contract**: `acceptance` (exact commands verified to exist in the repo, plus observable behaviors *lifted* from the PRD's seams) and `gates` (which design lenses apply, read from `design-gate`'s routing table, and `security: deep|standard`, read from `security-gate`'s trigger list — lifted from the PRD's Security Decisions, never re-derived). Plus HITL/AFK classification with human-in-the-loop slices scheduled first, a rollback note, an expected review focus, and a merge-safety statement. You approve the breakdown in a five-question quiz; slices publish as tracker issues titled `T3: …` with `ready-for-agent`, or to `TASKS.md`. **After this, nothing asks you anything.**

### 4. `coding-design-plan` → `design-gate` — is the approach sound?
`coding-design-plan` shapes the implementation plan and names test scenarios. `design-gate` reads the slice's `gates` flags, selects at most three lenses from its table, and runs them as **parallel read-only subagents**.
**Hands off:** one merged **`proceed` / `revise`** verdict. Any `revise` carrying a concrete load-bearing finding blocks and returns a numbered list of required plan changes; cosmetic findings are listed but don't block. Lenses disagreeing about a real trade-off escalate to `models-consensus` rather than to you.

### 5. `implement-and-review` — build it
**Lifts** the Slice Contract rather than re-deriving it: `acceptance` commands *are* the done gate, the behaviors are the test-first targets, `gates` select each track's lenses. Splits the work into frontend and backend tracks in isolated worktrees where **the implementer never reviews its own track**, running `tdd` inside each. It also runs standalone on a bare prompt, deriving what a contract would otherwise supply.
**Hands off:** merged tracks plus `verification_evidence` — which tests were inspected, added, and run, and what they proved. `safe-incremental-coding` runs first when the code has no tests to stand on; `diagnose` handles bugs found mid-loop. For a whole feature, `implement-feature` runs this per slice across the dependency DAG, rebasing each onto the current integration head.

### 6. Verify — ordered, fail-fast
1. **The acceptance contract** — run the slice's own commands.
2. **`coding-review-simplify`** — self-simplify while the context is fresh (mutating).
3. **`full-review`** — parallel specialists, multi-model triangulation, execution-based bug verification; deep security pass when the slice's flag says so.
4. **`browser-smoke`** (`mode:pipeline`) for web-facing changes — drive the real pages the diff touches.

Order matters: the multi-model gate reviews **final** code, so no mutating pass may follow it unreviewed. Failures loop back to step 5 through `diagnose`.

### 7. `open-pr` → `resolve-pr-feedback` — ship it
`open-pr` composes and opens the PR; `ship` adds acceptance evidence, design-gate verdicts, the review summary, the decision log with flagged assumptions, and remaining risks. Unapplied review findings are made durable rather than dropped. `session-handoff` stores the continuity note; `capture-learning` records a non-obvious solution.
**Hands off:** a PR for you to merge. When review comments arrive, `resolve-pr-feedback` judges each against the actual code, fixes the valid ones, replies with quoted context, and resolves the threads.

### What replaces asking you, after the step-3 gate
1. `models-consensus` in `poll` mode with `--auto` — blind fan-out, five-dimension reconciliation, one gated gap-repair round, two judges, a dedicated synthesizer. Read-only, deterministic termination.
2. Unresolved: take the most reversible default and record the assumption in the decision log carried into the PR.
3. Hard-stop for a human **only** on destructive or irreversible operations.

---

## The through-line

Each step **lifts** what the previous one decided instead of re-deriving it. The interview names the security surface and the test seams; the spec records them as the autonomy contract; the planner turns them into a machine-checkable acceptance contract and gate flags; the builder treats that contract as its definition of done; the review gate checks the result against it. Re-deriving what an approved artifact already states is what lets the built thing drift from the approved thing.
