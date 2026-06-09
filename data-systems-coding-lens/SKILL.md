---
name: data-systems-coding-lens
description: Use this skill whenever a coding task touches stored state, databases, queues, caches, search indexes, event streams, background jobs, migrations, external APIs, concurrency, retries, consistency, scalability, reliability, observability, or production data risk. This skill helps turn data systems design ideas into concrete implementation checks, review findings, and verification steps during coding sessions.
---

# Data Systems Coding Lens

Use this skill to add a practical data systems review pass to coding work. The goal is not to explain theory. The goal is to catch failure modes before they become production bugs.

<!-- Authoring note: do not quote or summarize any copyrighted source. This is an original engineering workflow. -->

## First Pass

Start by identifying the state boundary:

1. What data is created, read, updated, deleted, cached, derived, or emitted?
2. What is the source of truth?
3. Which paths are synchronous, asynchronous, retried, replayed, or user visible?
4. Which invariant would make the feature incorrect if it broke?
5. Which failure would be silent, expensive, or hard to repair?

If the task is small, keep this pass brief and fold it into the implementation. If the task touches shared data contracts or production records, write the answer down before editing.

Do not overcomplicate pure UI copy, styling, one off scripts, docs only edits, or local throwaway utilities. In those cases, only apply the lens if the change touches persistent data, background work, or production operational risk.

## Implementation Lens

When changing code, inspect these areas in order.

### Data Model And Contracts

Check schema shape, nullability, enum growth, identifier stability, time zones, ownership, uniqueness, and backward compatibility.

Ask:

1. Can old writers coexist with new readers?
2. Can new writers coexist with old readers?
3. Is there a rollback path?
4. Are migration defaults safe for existing data?
5. Is the API contract precise enough for clients and jobs?

### Query And Storage Path

Check query cardinality, index coverage, pagination, sort stability, cache keys, cache invalidation, transaction scope, and lock behavior.

Ask:

1. What grows with user count, tenant count, rows, events, or time?
2. Does the code accidentally turn one request into many database round trips?
3. Is the query plan likely to change badly as data grows?
4. Are writes idempotent when retried?
5. Can the same operation race with itself?

### Reliability And Failure

Check retries, duplicate messages, partial writes, timeout behavior, poison messages, dead letter handling, and user visible recovery.

Ask:

1. What happens after a crash between two writes?
2. What happens if the external service succeeds but the local write fails?
3. What happens if the local write succeeds but the external service times out?
4. Can a retry create duplicate money, emails, notifications, jobs, or records?
5. How does an operator detect and repair the failure?

### Distributed Behavior

Use this when there is more than one process, worker, region, database, queue, cache, or external system.

Check ordering assumptions, stale reads, read after write needs, leader election, leases, clock dependence, consistency level, transaction boundaries, and reconciliation.

Ask:

1. Does correctness require a single global order?
2. Is eventual consistency acceptable for this user flow?
3. Which operation needs strong consistency, and which can be reconciled later?
4. What happens when two actors update the same entity at the same time?
5. Is there a source of truth that can rebuild derived state?

### Evolution And Maintenance

Check deploy order, feature flags, versioned payloads, schema migrations, backfills, rebuilds, observability, and cleanup plans.

Ask:

1. Can this change ship in multiple deploys?
2. Can the migration be paused and resumed?
3. Can derived data be rebuilt from durable inputs?
4. Are logs, metrics, and traces enough to debug the real production path?
5. What old code, data, flag, or job needs cleanup after the rollout?

## Output Patterns

For implementation work, add a short note before coding when useful:

```text
Data systems lens:
State touched:
Invariant:
Main risk:
Verification:
```

For code review, lead with concrete findings:

```text
Finding:
Why it matters:
Failure case:
Suggested fix:
Verification:
```

For architecture or planning, use this compact decision record:

```text
Decision:
Source of truth:
Consistency requirement:
Failure handling:
Migration path:
Observability:
Open question:
```

## Verification Defaults

Prefer verification that exercises real boundaries:

1. Unit tests for invariants and idempotency.
2. Integration tests for database, queue, cache, and external API boundaries.
3. Migration checks with existing data shapes.
4. Concurrency tests for races and duplicate work.
5. Load or query plan checks when cardinality is the risk.
6. Observability checks for logs, metrics, traces, and repair signals.

## Final Response Contract

When this skill changes the work, mention the highest value check in the final response. Keep it short:

```text
I also checked the data systems risk: [state or invariant], [main mitigation], [verification].
```
