# Evidence strategy and safety checks for implementation tracks

Contract-level guidance for the implementer seats (both tracks) and the orchestrator. The load-bearing rule: **red-before-implementation evidence exists only in the worker's report** — it cannot be reconstructed from the tree after the fact, so every implementer must capture it as it goes and return it in the `verification_evidence` field of its report (schema: `_shared/runner-envelope.schema.json`).

## verification_evidence report contract

Every implementation run that changes behavior reports:

- `behavior_changed` — true unless the change was a pure refactor/analysis.
- `existing_tests_inspected` — tests read to locate coverage for the touched behavior.
- `tests_added_or_changed` — tests this run created or modified.
- `red_baseline` — the observed failing output (or characterization baseline) captured **before** production code changed: a verbatim excerpt or file:line pointer.
- `evidence_strategy` — which route below was taken.
- `no_test_reason` — required for the no-test exception: why no automated test was meaningful plus the replacement verification performed. Never invent a hollow test to avoid writing this.

The orchestrator persists these with the track results; a report claiming `behavior_changed: true` with no coherent evidence gets one recovery re-invocation to reconcile evidence without reimplementing, then blocks.

## Evidence Strategy — test discovery decides where proof belongs

| Situation | Action |
|-----------|--------|
| Existing test already fails for the intended behavior | Use it as the red evidence; do not add a duplicate test |
| Existing test covers the contract but asserts the old/wrong expectation | Update that test, run it, verify the expected failure before implementation |
| Existing test is over-mocked or misses the real chain | Strengthen/refactor it narrowly, then verify it fails for the right reason |
| No existing test covers the behavior | Add the smallest focused failing test or characterization test proving the behavior slice |
| Testing is inappropriate for the task | Record the no-test exception and replacement verification before marking done |

## System-Wide Test Check — before marking a task done

| Question | What to do |
|----------|------------|
| **What fires when this runs?** Callbacks, middleware, observers, event handlers — trace two levels out. | Read the actual code (not docs) for callbacks on touched models, middleware in the request chain, `after_*` hooks. |
| **Do my tests exercise the real chain?** All-mocked tests prove isolation, not interaction. | At least one integration test through the full callback/middleware chain with real objects. |
| **Can failure leave orphaned state?** State persisted before an external call that can fail. | Trace the failure path with real objects; test cleanup or idempotent retry. |
| **What other interfaces expose this?** Mixins, DSLs, alternative entry points. | Grep for the behavior in related classes; add parity now, not as a follow-up. |
| **Do error strategies align across layers?** Retry middleware + app fallback + framework handling. | List the error classes per layer; verify the rescue list matches what the lower layer raises. |

Skip only for leaf-node changes with no callbacks, no state persistence, no parallel interfaces.

## Parallel Safety Check — before dispatching tracks/waves concurrently

File overlap is necessary but not sufficient. Before running implementers in parallel:

1. Dependencies of each unit already committed; peers in the layer don't depend on each other.
2. Reason beyond declared files: shared types/APIs/interfaces, migrations, lockfiles, generated artifacts/clients, registry/config/schema surfaces, and environment singletons (one dev server/port, shared DB, browser session, package install, rate limit) all create contention.
3. Estimate expected merge + verification cost — isolated workers still serialize when they share a contract or when reconciling outputs isn't obviously cheaper than serial authoring.
4. **Decline parallelism on uncertainty.** Speed is optional; every concurrent worker needs an isolated workspace (this skill's worktree flow); a shared-workspace worker runs serially regardless of file disjointness.
5. Cap concurrency at ~3–5 workers. Abort criteria: broad unplanned edits, semantic overlap, out-of-scope failures, or repeated collisions disable further waves — finish affected work serially.

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
