# Proposal: One Development Workflow from the Existing Skills

Goal: a single pipeline where **all human interaction happens in the first three phases**, and everything after the plan approval gate runs autonomously — while still optimizing architecture, design, simplicity, code quality, tests, and security.

Design principles:

1. **Compose, don't duplicate.** The repo already contains every capability the pipeline needs. New skills are thin routers/conductors that reference existing skills; they contain no phase knowledge of their own.
2. **Front-load all judgment.** Every decision an agent would otherwise ask the user mid-flight is either (a) extracted during the interactive phases and encoded in the task contract, (b) resolved autonomously by multi-model consensus, or (c) recorded as a logged assumption surfaced in the PR.
3. **The issue tracker is the autonomy boundary** (adopted from mattpocock/skills): a task labeled `ready-for-agent` carries everything needed to complete it unattended. `CONTEXT.md` + `docs/adr/` are the durable memory that makes specs and reviews speak the project's language.
4. **Vertical slices are the unit of autonomous work.** Each slice cuts through all layers, is demoable alone, and carries a machine-checkable acceptance contract.

---

## The pipeline

```
 INTERACTIVE                                  │  AUTONOMOUS (per task, in a worktree)
                                              │
 0. FRAME      1. SPECIFY      2. PLAN        │  3. DESIGN GATE   4. IMPLEMENT     5. VERIFY        6. DELIVER
 brainstorm →  grill-with-docs to-tasks /     │  coding-design-   tdd +            full-review      PR + triage
 (prototype)   → to-prd /      collaborative_ │  plan + lens      safe-increment   (incl. security  label move +
               collaborative_  task_design    │  router →         implementation-  + execution      handoff note
               specification   → APPROVAL ◄───┤  (models-         guard            verification)
                                  GATE        │  consensus if     (refactor-to-    → diagnose on
                                              │  contested)       testability      failures
                                              │                   first if legacy) → coding-review-
                                              │                                     simplify → verify
```

The **approval gate at the end of Phase 2 is the last required human touchpoint** until PR merge.

---

## Phase-by-phase skill mapping

### Phase 0 — Frame (interactive, optional)

Skip when the request is already concrete.

| Situation | Skill |
|---|---|
| Half-baked idea, unclear if worth building | `brainstorm` → BUILD/DEFER/REDUCE-SCOPE/REJECT verdict |
| Design unknown that only running code can settle (state machine, data model, UI shape) | `prototype` — throwaway; decision-rich snippets feed the PRD |

### Phase 1 — Specify (interactive)

| Situation | Skill |
|---|---|
| Default | `grill-with-docs` (stress-test against `CONTEXT.md`/ADRs, updates them inline) → `to-prd` |
| High-stakes / contested feature | `collaborative_discovery` → `collaborative_specification` (multi-model PRD + tech spec via the runner family) |

**Security shifts left here**: the proposed `security-gate` skill (below) injects a threat-model-lite checklist into the grilling — auth/authz surface, untrusted input, secrets, data sensitivity, dependency additions. Answers land in the PRD's Implementation Decisions, so the autonomous phases never have to ask.

### Phase 2 — Plan (interactive — THE gate)

| Situation | Skill |
|---|---|
| Default | `to-tasks` — tracer-bullet vertical slices with the Slice Contract built in, HITL/AFK classification, dependency order, user approves breakdown |
| Complex delivery needing test plans + architecture decisions per task | `collaborative_task_design` |

Two fields in the slice template (carried natively by `to-tasks`):

- **Acceptance contract**: exact commands that must pass (test command, lint, build, app-level check `verify` can run), plus observable behaviors. Machine-checkable = autonomously verifiable.
- **Gate flags**: which design lenses apply (see router table) and whether the deep security pass is required. Set deterministically from the surfaces the slice touches.

HITL slices (rare: irreversible migrations, externally visible API contracts, design sign-off) are scheduled **first**, so the human's involvement clusters at the start. Everything labeled `ready-for-agent` after the approval gate runs unattended.

### Phase 3 — Design gate (autonomous, per task)

`coding-design-plan` shapes the implementation plan, then the proposed `design-gate` router runs only the lenses the slice's flags select:

| Slice touches | Lens skill(s) |
|---|---|
| New system/service/subsystem shape | `macro-architecture`, `design-integrity` |
| Module/service boundaries, cross-context calls | `domain-driven-design`, `macro-architecture` |
| Business-logic structure inside one context | `domain-driven-design`, `design-patterns` |
| Layering, "where does this code belong" | `architecture-lens` |
| Stored state, queues, caches, migrations, retries, concurrency | `data-systems-coding-lens` |
| React components/hooks/contexts | `react-performance` |
| Competing approaches with real trade-offs | `architecture-lens` |

Lenses run as parallel read-only subagents; each returns **proceed / revise-plan** with findings. Escalation ladder when a decision is contested or irreversible:

1. `models-consensus` (or the lighter `council`) — multi-model deliberation **substitutes for asking the user**.
2. Still unresolved → record the assumption + chosen default in a decision log, proceed, flag prominently in the PR.
3. Hard-stop (pause for human) only for destructive/irreversible operations — the same rule the harness already enforces.

### Phase 4 — Implement (autonomous, per task, isolated worktree)

- Touching untested/legacy code → `safe-incremental-coding` **first** (characterization net before change).
- New behavior → `tdd` red-green-refactor, paced by `safe-incremental-coding`.
- `coding-implementation-guard` active throughout (safe, local, verifiable changes; stored-state/API/async/retry/migration checks).
- Bugs found mid-implementation → `diagnose` (reproduce → minimise → hypothesise → instrument → fix → regression-test).
- Context economy on long tasks: `codex-mission-control` / `handoff` for compact continuation instead of degrading in a bloated context.

### Phase 5 — Verify (autonomous)

Ordered, fail-fast:

1. **Acceptance contract** — run the slice's commands. Failures loop back to Phase 4 via `diagnose`.
2. **`full-review`** — parallel specialists + multi-model triangulation + execution-based bug verification; includes the security dimension. Slices flagged by `security-gate` get the deep security pass (auth flows, injection surfaces, secrets handling, dependency diff).
3. **`coding-review-simplify`** — remove unnecessary abstraction, tighten, check architecture fit on the final diff.
4. **`verify`** — run the actual app and observe the behavior the slice promised.

Review findings are fixed autonomously and re-verified; only contested findings use the same escalation ladder as Phase 3.

### Phase 6 — Deliver (autonomous)

Commit in the worktree, open the PR (body: acceptance evidence, lens verdicts, decision log, flagged assumptions), move the issue's triage label, write a `summarize`/`handoff` continuity note. **The human's only late-phase job is merging the PR.**

Cross-cutting: `clean-code` and `pragmatic-coding-session` are standing lenses available in phases 4–5; the runner family (claude/codex/gemini/gemma/glm/kimi/minimax/opencode/qwen) is pure infrastructure consumed by the multi-model skills; `explain-architecture` onboards an agent dropped into an unfamiliar repo before Phase 3.

---

## Proposed new skills (3 — all thin)

### 1. `ship` — pipeline conductor (the only new entry point)

A ~150-line SKILL.md that encodes the table above: phase routing ("in situation X invoke skill Y"), the slice template additions (acceptance contract + gate flags), the escalation ladder, and the autonomous loop ("pull next `ready-for-agent` issue → worktree → phases 3–6 → PR → next"). Contains **zero** phase knowledge of its own — every behavior is a reference to an existing skill. Optionally ships a Workflow script for running independent slices in parallel worktrees.

### 2. `design-gate` — deterministic lens router

Today, choosing among ~10 overlapping architecture/design lenses is itself a judgment call — a mid-flight question waiting to happen. This skill makes it a lookup: the touched-surfaces → lens table above, the parallel read-only subagent invocation pattern, and the proceed/revise output contract. Also independently useful interactively ("review this design" → right lenses, automatically).

### 3. `security-gate` — shift-left checklist + deep-pass trigger

Two small parts: (a) the threat-model-lite question set merged into Phase 1 grilling, (b) deterministic trigger conditions for the Phase 5 deep security pass (slice touches auth/authz, parses untrusted input, handles secrets/PII, adds dependencies, changes CORS/headers/serialization, writes migrations). Keeps `full-review` unchanged; just controls when its security dimension goes deep and guarantees security questions are answered while the human is still in the room.

Deliberately **not** proposed: a task-contract skill (it's a template inside `ship`), a test-strategy skill (`tdd` + `safe-incremental-coding` + `test-lens` + the contract cover it), or any mega-skill duplicating phase content.

---

## Overlap policy (designate, don't delete)

Several skill clusters overlap; the pipeline picks **canonical defaults** and keeps the rest as reachable alternatives — no knowledge is removed:

| Cluster | Pipeline default | Alternatives (when) |
|---|---|---|
| Interview/clarify | `grill-with-docs` | `grill-me` (no domain docs), `council` (wants a plan out, not just clarity), `collaborative_discovery` (multi-model stakes) |
| Spec | `to-prd` | `collaborative_specification` (high stakes) |
| Task breakdown | `to-tasks` | `collaborative_task_design` (needs per-task test plans), `to-issues` (human-executed tickets, no contracts) |
| Implementation rhythm | `tdd` + `safe-incremental-coding` | `collaborative_delivery` (panel-gated, audit trail required), `pragmatic-coding-session` (lens, not loop) |
| Review | `full-review` | `review` (standards+spec axes), `code-review` (quick) |

## Rollout

1. Author `ship`, `design-gate`, `security-gate` (use `skill-expert` to validate triggers/structure).
2. Done via the local `to-tasks` skill, which carries the acceptance-contract + gate-flags fields natively (supersedes editing the external `to-issues`).
3. Pilot one feature end-to-end; measure user touchpoints after the Phase 2 gate (target: zero) and verify-phase pass rate.
4. Tune the lens-router table from pilot misroutes.
