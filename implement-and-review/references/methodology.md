# Methodology & Per-Track Skills

How the implement-and-review tracks use the repository's skills, and the exact text to embed in each implementer/reviewer brief.

## How skills apply here

- The **orchestrator** is Claude Code and can invoke any of these skills directly. Use them in Phase 0 (planning/design), when constructing review prompts, and for the Phase 4 `full-review`.
- The **implementer/reviewer seats** are runner CLIs (Codex, Kimi) and native subagents — they **cannot load Claude Code skills**. So you carry the *methodology* to them: paste the relevant snippets below into each track's brief. Don't tell a seat to "use the tdd skill" — give it the TDD instructions.
- Pick only what fits the change. A small CSS tweak doesn't need `ddd-tactical`; a queue consumer doesn't need `frontend-design`. Over-applying lenses wastes budget and muddies briefs.

## Skill map

### Both tracks
- **`tdd`** — red-green-refactor, vertical slices (one failing test → minimal code → refactor on green). Tests verify behavior through public interfaces and survive refactors.
- **`small-steps`** — keep each increment tiny and committed.
- **`clean-code`** — naming, small focused units, no duplication/dead code; the "good code" bar.
- **`refactor-to-testability`** — when the code you must change is untested/legacy, add a characterization-test safety net *before* changing it, then TDD on top.
- **`coding-design-plan`** — shape non-trivial work in Phase 0 before briefing.
- **`coding-implementation-guard`** — keep changes safe, local, and verifiable (stored state, APIs, async, retries, migrations).
- **`test-lens`** — sanity-check test quality/coverage of the changed behavior.

### Frontend track
- **`frontend-design`** — distinctive, production-grade UI; avoid generic AI aesthetics; accessibility and polish.
- **`react-performance`** — **when the frontend is React (17 + MUI + Redux Toolkit)**: unnecessary re-renders, composition-before-memoization, `memo`/`useMemo`/`useCallback` correctness, Context value stability, refs & stale closures, effect cleanup/`useLayoutEffect` flicker, data-fetching waterfalls & race conditions, error boundaries.
- **`ui-ux-pro-max`** — deeper UI/UX work when the task is design-heavy.

### Backend track
- **`data-systems-coding-lens`** — stored state and integration points: transactions/atomicity, idempotency & safe retries, concurrency, migration safety & backfill, pagination, timeouts/circuit-breaking, observability, production-data risk.
- **`ddd-tactical`** — pick the business-logic pattern (transaction script / active record / domain model / event-sourced) and keep aggregate invariants, value-object immutability, and reliable event publishing.
- **`ddd-strategic`** — when the change crosses a service/bounded-context boundary or integrates a third party (anticorruption layer, open-host service, outbox/saga).
- **`architect-lens` / `model-lens`** — coupling/connascence and layer-placement checks when restructuring.

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

### Reviewer overlay (cross-model review prompts)

Add to the FE review (Kimi) or BE review (Opus) prompt, on top of the review-output schema:

```text
Review through these lenses: <frontend: react-performance + frontend-design | backend:
data-systems-coding-lens + ddd-tactical>. Confirm the changed behavior is covered by
behavior-level tests written test-first, and that touched code was left clean (no new
duplication, dead code, or naming drift). Flag any behavior change beyond the task scope.
```
