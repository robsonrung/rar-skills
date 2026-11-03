---
name: data-systems-coding-lens
description: "Review implementation risks in persistent state and asynchronous data paths. Use for schemas, migrations, queues, caches, retries, or concurrent writes; use architecture-lens to decide service and data ownership."
---

# Data Systems Coding Lens

Catch data failure modes before they reach production. Apply it when a change touches persistent data, background work, or production operational risk; UI copy, styling, and throwaway scripts do not need it.

Two leitwörter anchor every pass. Say them by name as you work:

- **Source of truth**: the one place that durably owns each fact. Caches, indexes, and read models are derived and must be rebuildable from it.
- **Idempotent**: a retried or replayed write produces the same result the second time: no duplicate money, emails, jobs, or records.

## First pass: the state boundary

1. What data is created, updated, deleted, cached, derived, or emitted, and what is its **source of truth**?
2. Which paths are asynchronous, retried, replayed, or user-visible?
3. Which invariant makes the feature wrong if it breaks, and where does the code enforce it?
4. Which failure would be silent, expensive, or hard to repair?

On a small change, fold this into the work. When shared data contracts or production records are involved, write the answers down before editing.

## Checks

Work through the areas the change touches.

**Contracts and evolution.** Old writers with new readers, and new writers with old readers, must both work. Look at nullability, enum growth, identifier stability, time zones, and migration defaults on existing rows. State the deploy order. Prefer a change that ships across several deploys, a migration that can pause and resume, and a rollback path. Name the flag, column, or job that needs cleanup afterward.

**Query and storage.** Find what grows with users, tenants, rows, events, or time. Look for N+1 round trips, missing index coverage, unstable pagination sorts, and transaction or lock scope. For a cache, name the key shape and its cardinality, the invalidation trigger, and how much staleness the flow tolerates.

**Reliability.** Trace a crash between two writes, an external call that succeeds while the local write fails, and a local write that succeeds while the external call times out. Every retry path is **idempotent**: an idempotency key, a unique constraint, or a version check. Poison messages have a dead-letter destination. Every file, lock, transaction, subscription, timer, and socket has one owner and is released on success, failure, and cancellation. When correctness depends on hidden timing, make the sequencing explicit with state, a queue, a lock, a transaction, or a version check.

**Concurrency and distribution.** When more than one process, worker, region, store, or external system is involved, state which operations need strong consistency and which can reconcile later. Check two actors updating one entity, read-after-write needs, clock dependence, leases, and any assumption of a global order. Derived state must be rebuildable from the **source of truth**. Process topology itself belongs to `distributed-systems-patterns`.

**Operability.** An operator can detect and repair the failure from the logs, metrics, and traces of the real production path.

## Verification

Test at the real boundary the risk lives on: invariant and idempotency unit tests, integration tests against the database, queue, cache, or external API, migrations run against existing data shapes, concurrency tests for races and duplicate work, and query-plan or load checks when cardinality is the risk.

Report each finding as the failure case, why it matters, the fix, and how to verify it. When the lens changes the work, name the state or invariant, the mitigation, and its verification in one line of the final response.
