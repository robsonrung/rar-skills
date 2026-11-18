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

**Contracts and evolution.** Old writers with new readers, and new writers with old readers, must both work. Look at nullability, enum growth, identifier stability, time zones, and migration defaults on existing rows. State the deploy order. Prefer a change that ships across several deploys, a migration that can pause and resume, and a rollback path. Name the flag, column, or job that needs cleanup afterward. Before a retry treats an existing database object as complete, check its identity, schema, and validity. Check transaction restrictions in both forward and rollback phases.

**Schema.** A new table justifies itself against a column on its parent. Name it after the thing it holds, not the screen that shows it. One fact has one **source of truth**: a copied column names the job that refreshes it, and two tables that can answer one question state the rule that separates them. A table has a primary key and a named reader (code in this change, a later slice the description names, or an outside consumer that a comment names), and a table that only grows has a retention rule.

**Query and storage.** Find what grows with users, tenants, rows, events, or time. Look for N+1 round trips, missing index coverage, unstable pagination sorts, and transaction or lock scope. For a cache, name the key shape and its cardinality, the invalidation trigger, and how much staleness the flow tolerates.

**Reliability.** Trace a crash between two writes, an external call that succeeds while the local write fails, and a local write that succeeds while the external call times out.

- **Retries.** Every retry path is **idempotent**: an idempotency key, a unique constraint, or a version check. Poison messages have a dead-letter destination. Publishing and recording the publish fail separately, and each event carries a stable key the consumer can drop duplicates on.
- **Replays.** A replay returns the first result only to a caller who may still see it: check the current identity and permission for the result's scope first. The replay contract may skip only mutable business checks, such as a flag, stage, or limit. The fingerprint covers every field that changes the result.
- **Unknown is not empty.** A failed, partial, or omitted result never clears stored data. Only an explicit clear or a complete rebuild does. Read `null` from the field contract, and never let an error default select the destructive branch.
- **Budgets.** Retries, backoff, and per-call timeouts add up to less than the timeout of whoever waits. A job that costs money or minutes refuses a duplicate for the same scope while one is pending, on the server, and treats an empty selector as nothing, never as everything.
- **Owned resources.** Every file, lock, transaction, subscription, timer, and socket has one owner and is released on success, failure, and cancellation. When correctness depends on hidden timing, make the sequencing explicit with state, a queue, a lock, a transaction, or a version check.

**Concurrency and distribution.** When more than one process, worker, region, store, or external system is involved, state which operations need strong consistency and which can reconcile later. Check two actors updating one entity, read-after-write needs, clock dependence, leases, and any assumption of a global order.

- **Lock order.** Commands that can contend on the same records take their locks in one order, derived from the actual store, records, and constraints, implicit foreign-key locks included. Share the locking code where sharing prevents drift. Take the weakest lock that protects the invariant.
- **Decide under the lock.** A lock does not refresh an object read before it. Read or revalidate the decision state inside the protected operation.
- **Claims.** When a worker claim can expire, renew, or move, bind completion, failure, release, and takeover to the current claim identity or generation, compared inside the protected write. An expiry time alone does not prove ownership.
- **Every write path.** A rule the create path enforces, such as a required field or a guard on an archived record, holds on edit, bulk, and import too.

Derived state must be rebuildable from the **source of truth**. Process topology itself belongs to `distributed-systems-patterns`.

**Operability.** An operator can detect and repair the failure from the logs, metrics, and traces of the real production path. A one-off script that skips a record says so and why, never printing success for a case it did not handle, and it checks a required run order itself.

## Verification

Test at the real boundary the risk lives on: invariant and idempotency unit tests, integration tests against the database, queue, cache, or external API, migrations run against existing data shapes, concurrency tests for races and duplicate work, and query-plan or load checks when cardinality is the risk.

Report each finding as the failure case, why it matters, the fix, and how to verify it. When the lens changes the work, name the state or invariant, the mitigation, and its verification in one line of the final response.
