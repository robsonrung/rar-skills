---
name: coding-implementation-guard
description: Keep implementation work safe, local, and verifiable. Use when an agent is actively editing nontrivial code, changing behavior, touching stored state, APIs, async work, retries, migrations, or refactoring while preserving the chosen design.
---

# Coding Implementation Guard

Use this skill while editing code. The goal is to make the intended change with the least necessary structure, clear behavior, and concrete verification.

## Workflow

1. Reconfirm the requested behavior, current behavior, relevant tests, and the design shape if one was chosen.
2. Keep edits scoped to the requested path and the files required by the change.
3. Preserve external behavior unless the request explicitly changes it.
4. Match local patterns, naming, framework conventions, and helper APIs before adding a new abstraction.
5. Separate concerns only where the code is already mixing parsing, validation, business rules, persistence, formatting, orchestration, or side effects.
6. Make side effects visible and keep error behavior, data shapes, and public contracts stable unless intentionally changed.
7. Keep strong coupling close. Weaken coupling that crosses modules, services, public contracts, or many call sites.
8. Add or update focused tests and checks near the behavior being changed.
9. Stop for redesign only when the current plan cannot be implemented safely.

## State And Data Checks

Apply this pass when the edit touches databases, files, queues, caches, search indexes, event streams, jobs, external APIs, or production records:

1. Source of truth: what data is created, read, updated, deleted, cached, derived, or emitted?
2. Invariant: what must remain true for the feature to be correct?
3. Compatibility: can old readers, old writers, new readers, and new writers coexist during deploy and rollback?
4. Idempotency: can retry, replay, or duplicate delivery create duplicate records, emails, money movement, jobs, or notifications?
5. Concurrency: can two actors update the same entity or run the same operation at once?
6. Consistency: what needs strong consistency, and what can be reconciled later?
7. Observability: how would an operator detect and repair a silent or partial failure?

## Code Quality Checks

Use these as editing pressure, not as a rewrite license:

1. Names express intent and domain language.
2. Functions and modules have one clear responsibility at the current granularity.
3. Control flow is simple enough to review.
4. Duplication is removed only when it represents the same concept and same reason to change.
5. Comments explain business rules, external constraints, security, performance, or history.
6. Positional arguments, magic values, hidden ordering, shared mutable state, and duplicated algorithms are weakened when they are distant or high risk.
7. New helpers reduce real complexity instead of hiding it.

## Output Contract

When this skill shaped the implementation, include:

1. `changed`: what was edited.
2. `behavior`: whether behavior changed or was preserved.
3. `risk_guarded`: the main design, data, or code quality risk addressed.
4. `verification`: tests or checks run, or why they could not run.

## Gotchas

1. Do not expand scope to clean unrelated code.
2. Do not add layers, services, helpers, or dependencies because they sound tidy.
3. Do not hide domain rules behind generic utilities.
4. Do not leave architecture or data concerns as commentary when a test or check can guard them.
5. Do not weaken harmless local coupling if the cure adds more indirection than clarity.
