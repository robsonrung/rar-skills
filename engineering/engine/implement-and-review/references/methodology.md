# Methodology & Per-Track Skills

How the implement-and-review tracks use the repository's skills, and the exact text to embed in each implementer/reviewer brief.

## How skills apply here

- The **orchestrator** is Claude Code and can invoke any of these skills directly. Use them in Phase 0 (planning/design), when constructing review prompts, and for the Phase 4 `full-review`.
- The **implementer/reviewer seats** are runner CLIs (Codex, Kimi) and native subagents — they **cannot load Claude Code skills**. So you carry the _methodology_ to them: paste the relevant snippets below into each track's brief. Don't tell a seat to "use the tdd skill" — give it the TDD instructions.
- Pick only what fits the change. A small CSS tweak doesn't need `domain-driven-design`; a queue consumer doesn't need `frontend-design`. Over-applying lenses wastes budget and muddies briefs.

## Skill map

### Both tracks

- **`tdd`** — red-green-refactor, vertical slices (one failing test → minimal code → refactor on green). Tests verify behavior through public interfaces and survive refactors.
- **`safe-incremental-coding`** — keep each increment tiny and committed; for untested/legacy code, build a characterization-test net _before_ changing it, then TDD on top.
- **`clean-code`** — naming, small focused units, no duplication/dead code; the "good code" bar.
- **`coding-design-plan`** — shape non-trivial work in Phase 0 before briefing.
- **`data-systems-coding-lens`** — keep changes safe, local, and verifiable wherever they touch stored state, APIs, async work, retries, or migrations.
- **`test-lens`** — sanity-check test quality/coverage of the changed behavior.
- **`architecture-lens`** — coupling/connascence and layer-placement/cohesion checks when restructuring (applies to both tracks, not just backend).

### Frontend track

- **`frontend-design`** — distinctive, production-grade UI; avoid generic AI aesthetics; accessibility and polish.
- **`advanced-react`** — **when the frontend is React (17 + MUI + Redux Toolkit)**: unnecessary re-renders, composition-before-memoization, `memo`/`useMemo`/`useCallback` correctness, Context value stability, refs & stale closures, effect cleanup/`useLayoutEffect` flicker, data-fetching waterfalls & race conditions, error boundaries.
- **`ui-ux-pro-max`** — deeper UI/UX work when the task is design-heavy.

### Backend track

- **`data-systems-coding-lens`** — stored state and integration points: transactions/atomicity, idempotency & safe retries, concurrency, migration safety & backfill, pagination, timeouts/circuit-breaking, observability, production-data risk.
- **`agent-architecture-lens`** — **when the thing being built is an agent**: whether the task needs a plain loop or an explicit state graph, typed state vs message history, a retry bound counted outside the model, three exits (success / retries-exhausted / hard ceiling), idempotent steps, and human gates that survive a restart.
- **`domain-driven-design`** — pick the business-logic pattern (transaction script / active record / domain model / event-sourced) and keep aggregate invariants, value-object immutability, and reliable event publishing (tactical); and when the change crosses a service/bounded-context boundary or integrates a third party, the bounded-context & integration patterns (anticorruption layer, open-host service, outbox/saga) (strategic).

### Planning lenses (only when a slice's `gates` flag them)

`design-gate` can route a slice to four lenses that have no natural home in a track brief. The **orchestrator** runs them in Phase 0 and turns their conclusions into constraints in the briefs; the compact snippets below let a seat honor those constraints without loading the skill.

- **`macro-architecture`** — the overall style and decomposition of a system or subsystem: service granularity, data ownership, distributed transactions and sagas, orchestration vs choreography, contracts and ADRs.
- **`software-design-philosophy`** — deep modules and information hiding (Ousterhout): interfaces much simpler than their implementations, complexity pulled down rather than pushed to callers, comments as design.
- **`design-patterns`** — a Gang-of-Four pattern only where it genuinely fits (sprawling conditionals, duplicated behavior, tangled notifications); name it, don't over-engineer it.
- **`distributed-systems-patterns`** — container and multi-node topology: sidecar/ambassador/adapter, replicated serving, sharding, scatter/gather, ownership election, work queues, batch — reviewed against each pattern's failure modes.

### Final review (Phase 4)

- **`full-review`** — the whole-change review; multi-model, verified, with a structural-maintainability pass.
- **`security-gate`** / full-review `security_focus=true` — when the change touches auth, validation, tenancy, secrets, or data exposure.

## Brief snippets to embed

Paste the cross-cutting snippets into **both** briefs, then add the matching track snippet.

### TDD (both)

```text
Build this test-first. Work in vertical slices: write ONE failing test for the next
behavior, then the minimal code to make it pass, then refactor on green — repeat.
Do NOT write all tests up front. Tests must assert observable behavior through public
interfaces (not implementation details) so they survive refactors. Run the single-test
command after each step; never refactor while red. Commit in small red→green→refactor steps.
If the code you must change has no tests, first add characterization tests that pin the
current behavior, then change it.
```

### Good code + boy-scout (both)

```text
Produce clean code: intention-revealing names, small focused functions, no duplication,
no dead code, errors handled the way this repo handles them. Apply the boy-scout rule —
leave every file you touch a little cleaner than you found it. BUT scope every improvement
to the code your task changes: do not rewrite unrelated modules, do not reformat whole
files, and do not change behavior beyond the task. When in doubt, prefer the smaller change.
```

### Frontend lens (frontend brief)

```text
Build accessible, polished UI — avoid generic/templated AI aesthetics. If this is React
(17 + MUI + Redux Toolkit): prevent unnecessary re-renders (prefer composition before
memoization; use memo/useMemo/useCallback only with correct deps; keep Context values
stable); avoid stale closures and clean up effects; guard data fetching against races and
out-of-order responses; avoid layout flicker. Cover user-facing behavior with
component/interaction tests, not snapshot-of-structure tests.
```

### Backend lens (backend brief)

```text
Treat stored state and integrations carefully: wrap multi-write operations in the right
transaction boundary; make handlers idempotent and retries safe; consider concurrency and
race conditions; keep migrations backward-compatible (expand/contract, safe backfill);
bound queries (pagination, timeouts) and add observability. Choose the simplest business-
logic pattern that fits (transaction script vs domain model); keep aggregate invariants in
one place and publish domain events reliably. Validate all input at the boundary; never
trust the client. When calling another service/context, isolate it behind an
anticorruption layer rather than leaking its model inward.
```

### Slice Contract (both, when the task came from `to-tasks`)

```text
This task is an approved slice; its contract is authoritative. ACCEPTANCE: the commands
listed must pass and every listed behavior must be proven by a test written before the
code (or, when the contract states "Test expectation: none — <reason>", take the no-test
route: report that reason as no_test_reason and the acceptance commands as your
replacement verification, and change no behavior). EXPECTED REVIEW FOCUS: <the slice's
named risk> — treat it as the place you are most likely to be wrong and test it first.
ROLLBACK BOUNDARY: <the slice's rollback note> — do not introduce any side effect it does
not declare (a migration, a data write, an external call, a published contract). Never
delete, skip, weaken, narrow, or mock-away tests, or loosen the acceptance checks, to
pass; if the contract cannot be satisfied as written, stop and report the gap instead of
choosing for the user.
```

### Planning-lens constraints (either brief, only when flagged)

```text
Honor these design constraints from the planning pass: <the orchestrator's conclusions —
e.g. which context owns the data, the module boundary and what it hides, the pattern
chosen and why, the topology pattern and its failure modes>. Keep interfaces simpler than
their implementations; do not introduce a pattern, service, or topology the constraints
do not name; if a constraint proves impossible, report it rather than working around it.
```

### Reviewer overlay (cross-model review prompts)

Add to every cross-model review prompt (Opus reviewing Codex work, Codex reviewing Opus work, Kimi only as the fallback reviewer), on top of the review-output schema:

```text
Review through these lenses: <the slice's `gates` lens flags when the task carries a Slice
Contract; otherwise frontend: advanced-react + frontend-design | backend:
data-systems-coding-lens + domain-driven-design>. Spend attention first on: <the slice's
expected review focus, or the orchestrator's named risk>. Confirm the changed behavior is
covered by behavior-level tests written test-first (or that a stated no-test route changed
no behavior), and that touched code was left clean (no new duplication, dead code, or
naming drift). Flag any behavior change beyond the task scope, and any side effect the
rollback note did not declare (migration, data write, external call, published contract).
```
