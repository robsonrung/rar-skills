# The workflow

The authoritative description of how these skills compose. `ship` is the conductor; every step below is also usable standalone.

## Design principles

1. **Compose, don't duplicate.** Conductor skills are thin routers. Each behavior lives in exactly one skill and is referenced, never copied. When two skills wanted the same knowledge, one of them was merged away.
2. **Front-load judgment.** Every question an agent would otherwise ask mid-flight is answered while the human is still in the room, then encoded in an artifact. After the plan-approval gate the pipeline escalates to `models-consensus`, not to the user.
3. **The contract is the boundary.** A task marked `ready-for-agent` carries a machine-checkable acceptance contract and its gate flags — everything needed to finish it unattended.
4. **Vertical slices.** The unit of work cuts through every layer, is demoable alone, and ships with commands that prove it.
5. **One user-called skill per step.** Choosing among ten design lenses is itself a mid-flight question; `design-gate` turns that choice into a table lookup.
6. **Hand off the path, not the payload.** The conductor is thin: every phase that does not need the user runs in its own subagent, and what crosses between phases is a markdown report on disk plus a short envelope — never a pasted body. Contract in `_shared/references/handoff-contract.md`, per-station binding in `ship/references/station-dispatch.md`. This is what keeps a run's reasoning recoverable after a compaction, and the conductor's context flat across a seven-station run.

## The seven steps

```
 INTERACTIVE                                    │  AUTONOMOUS (per slice, in a worktree)
 0. Frame     1. Specify        2. Plan         │  3. Design gate  4. Build      5. Verify        6. Deliver
 brainstorm   interview →       to-tasks        │  coding-design-  implement-    coding-review-   open-pr →
 (prototype)  to-spec           → APPROVAL ◄────┤  plan →          and-review    simplify →       resolve-pr-
                                   GATE         │  design-gate     (tdd)         full-review →    feedback
                                                │                                browser-smoke
```

**Step 0 — Frame.** Optional; skip when the request is concrete. `brainstorm` digs into the motivation before the mechanism, expands the solution space, and closes with a BUILD / DEFER / REDUCE SCOPE / REJECT verdict. Its panel mode fans divergence and cross-critique out to real model seats. `prototype` settles a design unknown that only running code can answer, then throws the code away.

**Step 1 — Specify.** `interview` grounds itself in `CONCEPTS.md`, `docs/adr/`, and the code *before* asking anything, then grills the angles that change what gets built — actors and permissions, edge cases, scope boundaries, data lifecycle, migration and rollback — runs the `security-gate` threat-model-lite checklist, and names the test seams. Exit test: every question the autonomous phases would have to ask is answered, recorded as an assumption with a default, or descoped. `to-spec` then synthesizes the PRD without a second interview.

**Step 2 — Plan.** `to-tasks` cuts the PRD into tracer-bullet vertical slices. Each carries the **Slice Contract**: `acceptance` (exact commands, verified to exist, plus observable behaviors), `gates` (which design lenses apply and whether the deep security pass is required — lifted from `design-gate`'s table and `security-gate`'s trigger list, never re-derived), HITL/AFK classification with human-in-the-loop slices scheduled first, a rollback note, an expected review focus, and a merge-safety statement. The user approves the breakdown. **This is the last required human touchpoint.**

**Step 3 — Design gate.** `coding-design-plan` shapes the plan and names the test scenarios; `design-gate` reads the slice's flags and runs at most three lenses as parallel read-only reviewers, merging them into one `proceed` / `revise` verdict. Only load-bearing findings block.

**Step 4 — Build.** `implement-and-review` builds one slice test-first across a frontend and a backend track in isolated worktrees, where the implementer never reviews its own work. `tdd` is the loop itself (Iron Law: no production code without a failing test first); `safe-incremental-coding` builds a characterization net first when the code has no tests to stand on; `diagnose` root-causes bugs found mid-work. For a whole feature, `implement-feature` executes the slice DAG, rebasing each slice onto the current integration head.

**Step 5 — Verify.** Ordered, fail-fast: run the acceptance contract → `coding-review-simplify` (self-simplify while the context is fresh) → `full-review` (parallel specialists, multi-model triangulation, execution-based bug verification, deep security pass when flagged) → drive the real app, via `browser-smoke` for web-facing changes. The order matters: the multi-model gate reviews **final** code, so no mutating pass may follow it unreviewed.

**Step 6 — Deliver.** `open-pr` composes the PR; `ship` adds acceptance evidence, lens verdicts, the decision log, and remaining risks. Unapplied review findings are made durable rather than dropped. `session-handoff` stores the continuity note, `capture-learning` records a non-obvious solution, and `resolve-pr-feedback` closes the loop when review comments arrive.

## What replaces asking the user

After the step-2 gate, a contested or irreversible decision escalates:

1. `models-consensus` in `poll` mode with `--auto` — blind fan-out, five-dimension reconciliation, one gated gap-repair round, two judges, a dedicated synthesizer. Read-only, no user interaction, deterministic termination.
2. Unresolved: take the most reversible default and record the assumption in the decision log carried into the PR.
3. Hard-stop for the human **only** on destructive or irreversible operations.

## Cross-cutting

- **Design lenses** — `architecture-lens` (trade-offs, connascence, layer placement, cohesion, dependency direction, scope), `macro-architecture` (macro style + decomposition), `domain-driven-design`, `software-design-philosophy` (deep modules, complexity, conceptual integrity), `design-patterns`, `data-systems-coding-lens`, `agent-architecture-lens`, `react-performance`. Reached through `design-gate`; each returns the same reviewer contract.
- **Multi-model** — `models-consensus` (answer/decide, three modes), `diverse-plan` (multi-model planning), `collaborative-delivery` (panel-audited delivery), `dynamic-harness` (agent orchestration patterns and manager mode), and the `*-runner` seat family.
- **Knowledge** — `CONCEPTS.md` is the glossary the interview and spec speak; `docs/adr/` holds decisions; `capture-learning` accretes solved problems; `skill-expert` and `agents-md-craft` maintain the skills and the agent-memory files.
- **Posture** — `fable-mindset` covers the five moments of a working turn (intake, diagnosis, decision, implementation, reporting). It governs *how* an agent reads a request and reports a result; the procedural skills govern *what* it does.

## Conventions

- **Leitwörter.** Distinctive phrases an agent repeats while acting (`smallest reversible move`, `connascence`, `observable behavior`, `act or assess`). Registered in `leitworter.json`, guarded by `scripts/check_leitworter.py` — deleting one from its owning skill fails the build. See `LEITWORTER.md`.
- **New skills need an audit row.** `docs/porting-trigger-audit.md` records the trigger-collision check; a skill may not land without one.
- **Model ids live in one file.** `_shared/references/model-roster.md`. Skills name seats, not versions.
- **Entry points are user-invocable only.** Skills no other skill calls mid-workflow carry `disable-model-invocation: true`.
