# The workflow

The authoritative description of how these skills compose. Four steps, four skills you type, one orchestrator, one build engine. Every step is also usable standalone.

```
 INTERACTIVE (you are in the room)                  │  AUTONOMOUS (nothing asks you)
 1. interview-me  →  2. to-prd  →  3. to-tasks ────┤→ 4. implement-tasks
    grill the idea      write the PRD   cut slices  │      └─ implement-and-review, per slice
                                        APPROVAL    │         design gate → tdd → cross-review →
                                        GATE        │         simplify → full-review
                                                    │      seam review → residuals → open-pr
```

## Design principles

1. **Compose, don't duplicate.** Orchestrators are thin routers. Each behavior lives in exactly one skill and is referenced, never copied. When two skills wanted the same knowledge, one of them was merged away.
2. **Front-load judgment.** Every question an agent would otherwise ask mid-flight is answered while the human is still in the room, then encoded in an artifact. After the step-3 approval the pipeline escalates to `models-consensus`, not to the user.
3. **The contract is the boundary.** A slice marked `ready-for-agent` carries a machine-checkable acceptance contract and its gate flags — everything needed to finish it unattended.
4. **Vertical slices.** The unit of work cuts through every layer, is demoable alone, and ships with commands that prove it.
5. **One user-called skill per step.** Choosing among ten design lenses is itself a mid-flight question; `design-gate` turns that choice into a table lookup.
6. **Hand off the path, not the payload.** `implement-tasks` is thin: each slice builds in its own `implement-and-review` run, and what crosses back is a report on disk plus a short envelope — never a pasted body. Contract in `shared/references/handoff-contract.md`. Progress lives in **the ledger, not the transcript** (`shared/references/run-state-contract.md`), so a run survives compactions and restarts.
7. **Each gate runs once.** The design gate, the self-simplify pass, and the multi-model review each run at one defined point inside the build engine. No orchestrator re-runs them on code that has not changed.

## The four steps

| Step | Skill | Reads | Writes | Accessory skills that run inside it |
| --- | --- | --- | --- | --- |
| 1. Interview | `interview-me` | `CONCEPTS.md`, `docs/adr/`, the code | glossary entries, ADRs | `security-gate` (threat-model-lite checklist), `test-lens` (naming the test seams), `to-prototype` (detour: one question only running code can settle, answered by a throwaway spike) |
| 2. PRD | `to-prd` | the step-1 conversation | `.ai-workflow/work/<slug>/prd.md` | `security-gate` (Security Decisions section); optional panel mode |
| 3. Tasks | `to-tasks` | the PRD | one file per slice under `.ai-workflow/work/<slug>/tasks/` | `design-gate`'s routing table and `security-gate`'s trigger list, to set the slice flags. No lens runs here. **The last human gate.** |
| 4. Implement | `implement-tasks` → `implement-and-review` per slice | the slice queue | integrated branch, residual record, PR | see below |

**Step 1 — Interview.** `interview-me` grounds itself in `CONCEPTS.md`, `docs/adr/`, and the code _before_ asking anything, then grills the angles that change what gets built — actors and permissions, edge cases, scope boundaries, data lifecycle, migration and rollback — in frontier rounds, each question with a recommended answer. It runs the `security-gate` checklist, names the test seams per `test-lens`, and records on settle: glossary entries for terms that resolve, an ADR only for a decision that clears the bar. A frontier question that only running code can settle, and whose answer changes the spec, detours to `to-prototype`: the spike returns one decision (plus the decision-rich snippets the PRD may carry), the interview records it as settled and resumes. Exit test: every question the autonomous step would have to ask is answered, recorded as an assumption with a default, or descoped. Closes with "run `to-prd`".

**Step 2 — PRD.** `to-prd` synthesizes the PRD without a second interview. Two sections are load-bearing downstream: **Security Decisions** (the checklist answers, pre-marking security-sensitive surfaces) and **Testing Decisions** (the named seams, which become the acceptance behaviors). Closes with "run `to-tasks`".

**Step 3 — Tasks.** `to-tasks` cuts the PRD into tracer-bullet vertical slices. Each carries the **Slice Contract**: `acceptance` (exact commands, verified to exist, plus observable behaviors), `gates` (which design lenses apply and whether the deep security pass is required — lifted from `design-gate`'s table and `security-gate`'s trigger list, never re-derived), HITL/AFK classification with human-in-the-loop slices scheduled first, a rollback note, an expected review focus, and a merge-safety statement. You approve the breakdown. **After this, nothing asks you anything.**

**Step 4 — Implement.** `implement-tasks` builds the dependency DAG from the slices and runs `implement-and-review` per slice, in parallel isolated worktrees, each rebased on the current integration head. Inside each slice build, in order:

- _Design:_ `coding-design-plan` shapes the plan and names test scenarios (and may detour to `to-prototype` when one slice hides a question only running code can settle); `design-gate` runs at most three lenses selected by the slice's flags as parallel read-only reviewers and returns one `proceed` / `revise` verdict.
- _Build:_ two model tracks (frontend and backend) build test-first with `tdd`; `safe-incremental-coding` puts untested legacy code under a characterization net first; `clean-code` and `test-lens` supply the refactor and test vocabulary; `diagnose` root-causes a failure not understood at a glance; the implementer never reviews its own track.
- _Verify:_ `coding-review-simplify` tightens the integrated diff while context is fresh, then `full-review` gates the final code. No mutating pass follows it unreviewed.

`implement-tasks` then integrates slices in dependency order, runs one feature-wide `full-review` on the seams, makes every unapplied finding durable (tracker ticket plus a committed record, never a PR-body ledger), and delivers through `open-pr` with acceptance evidence, gate verdicts, the decision log, and remaining risks. `capture-learning` records a non-obvious solution; `session-handoff` stores a continuity note when a run outgrows its session; `resolve-pr-feedback` closes the loop when review comments arrive.

## What replaces asking the user

After the step-3 gate, a contested or irreversible decision escalates:

1. `models-consensus` in `poll` mode with `--auto` — blind fan-out, five-dimension reconciliation, one gated gap-repair round, two judges, a dedicated synthesizer. Read-only, no user interaction, deterministic termination.
2. Unresolved: take the most reversible default and record the assumption in the decision log carried into the PR.
3. Hard-stop for the human **only** on destructive or irreversible operations.

## The toolbox

`engineering/workflow/` is the engineer's toolbox, not a fixed sequence: the four steps above, plus `brainstorm` (before step 1, when it is not yet clear whether or what to build — closes with a BUILD / DEFER / REDUCE SCOPE / REJECT verdict and hands to `interview-me`), `to-prototype` (the detour from step 1 or from a slice, when only running code can settle a question), and `models-consensus` (a contested decision at any point, and what step 4 escalates to). Which tool you reach for depends on the task; each one names the next.

## Cross-cutting

- **Design lenses** — `architecture-lens` (trade-offs, connascence, layer placement, cohesion, dependency direction, scope), `macro-architecture` (macro style + decomposition), `domain-driven-design`, `software-design-philosophy` (Ousterhout 2nd ed. plus conceptual integrity), `design-patterns`, `data-systems-coding-lens`, `distributed-systems-patterns` (Burns container and multi-node patterns, plus the Bellemare event-driven route: adopt/hold, event contracts, single writer, data liberation), `agent-architecture-lens`, `advanced-react` (Makarevich: composition-first React, plan/implement/review), `ui-ux-pro-max`. Reached through `design-gate`; each returns the same reviewer contract.
- **Practice** — `tdd`, `safe-incremental-coding`, `clean-code`, `test-lens`, `diagnose`. Wired together by `implement-and-review`; each also runs on its own.
- **Multi-model** — `models-consensus` (answer/decide, three modes), `diverse-plan` (multi-model planning), `collaborative-delivery` (panel-audited delivery), `dynamic-harness` (agent orchestration patterns and manager mode), and the runner seats: `claude-runner`, `codex-runner`, `gemini-runner`, `grok-runner`, `pi-runner` (`--seat kimi|glm|qwen|gemma`), `cline-runner` (`--seat muse|minimax`).
- **Knowledge** — `CONCEPTS.md` is the glossary the interview and spec speak; `docs/adr/` holds decisions, written by `interview-me` on settle; `capture-learning` accretes solved problems; `skill-expert` and `agents-md-craft` maintain the skills and the agent-memory files.
- **Posture** — `fable-mindset` covers the five moments of a working turn (intake, diagnosis, decision, implementation, reporting). It governs _how_ an agent reads a request and reports a result; the procedural skills govern _what_ it does.

## Conventions

- **Leitwörter.** Distinctive phrases an agent repeats while acting (`smallest reversible move`, `connascence`, `observable behavior`, `act or assess`). Registered in `leitworter.json`, guarded by `scripts/check_leitworter.py` — deleting one from its owning skill fails the build. See `LEITWORTER.md`.
- **New skills need an audit row.** `docs/porting-trigger-audit.md` records the trigger-collision check; a skill may not land without one.
- **Model ids live in one file.** `shared/references/model-roster.md`. Skills name seats, not versions; a seat is `<runner> --seat <name>` where the runner serves several.
- **Entry points are user-invocable only.** Skills no other skill calls mid-workflow carry `disable-model-invocation: true` (and `allow_implicit_invocation: false` in `agents/openai.yaml`); a host hides them from the model, so they are typed by the user or reached by reading their file path. In the toolbox that is `brainstorm`, `interview-me`, `to-prd`, and `implement-tasks`; `to-tasks`, `to-prototype`, and `models-consensus` stay invocable because other skills call them.
