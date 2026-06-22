---
name: pragmatic-coding-session
description: Apply a Pragmatic Programmer inspired coding session lens across planning, design, implementation, debugging, review, and handoff. Use when the user wants a pragmatic, phase-by-phase operating lens for a coding session, when work feels vague, risky, overdesigned, brittle, accidental, hard to test, hard to change, or when the user asks for pragmatic programming guidance.
---

# Pragmatic Coding Session

Use this skill as a phase by phase operating lens for real coding work. The goal is practical mastery in the current repo: take responsibility, make the system easier to change, prefer feedback over speculation, and leave a clear trail.

The through-line for every phase is the **smallest reversible move**: the cheapest action that creates real learning and can be undone if it teaches you something unwelcome. Say it by name when you choose what to do next — naming the move keeps you from over-committing to speculation. Speed comes from feedback and reversibility, never from skipping them.

This is not a book summary. Apply the durable practices from *The Pragmatic Programmer* as decisions, checks, and verification.

## Session Loop

1. Locate the current phase: planning, design, implementation, debugging, review, or handoff. Apply the Reliability And Safety pass whenever the change touches state, resources, or trust boundaries, regardless of phase.
2. Inspect the real code, tests, docs, runtime behavior, and repo guidance before giving advice.
3. Name the practical problem in one sentence.
4. Find the smallest reversible move that can create learning.
5. Turn uncertainty into a tracer, prototype, test, assertion, log, or explicit question.
6. Keep the code easier to change than when you arrived.
7. Verify with the cheapest check that proves the behavior, contract, or risk.
8. Record decisions, assumptions, and follow ups briefly when they would help the next session.

## Planning

Use this pass when the goal, requirements, estimate, or first move is unclear.

1. Separate the user outcome from the requested mechanism.
2. Identify the people, callers, systems, and data that experience the change.
3. Capture unknowns as questions that code, logs, docs, a prototype, or the user can answer.
4. Prefer a thin end to end tracer when integration risk is higher than design risk.
5. Prefer a throwaway prototype when learning is needed but production shape is still unclear.
6. Estimate by decomposing into observable deliverables and naming the uncertainty, not by padding.
7. Define done as behavior plus verification, not as files touched.

Hand off to `coding-design-plan` when boundaries, public contracts, persistence, async flow, or cross module ownership matter.

## Design

Use this pass before adding abstractions, changing data flow, or touching module boundaries.

1. Optimize for ease of change in this codebase, not for a generic ideal.
2. Treat knowledge duplication as the real duplication risk. Repeated text is not always repeated knowledge.
3. Keep independent concerns independent. A change in one concept should not force edits in distant concepts.
4. Make decisions reversible where the future is uncertain. Hide volatile choices behind small boundaries.
5. Use the project language directly in names, data shapes, tests, and errors.
6. Define contracts at important boundaries: expected inputs, outputs, invariants, errors, and ownership.
7. Choose configuration for values that vary by environment, deployment, tenant, or operator choice.
8. Delete or postpone abstractions that do not protect a real variation point.

Hand off to `design-integrity`, `architecture-lens`, or `domain-driven-design` when the design problem needs deeper treatment.

## Implementation

Use this pass while editing.

1. Work in small steps. Change one meaningful thing at a time.
2. Avoid programming by coincidence. If the code passes, know why.
3. Keep feedback fast through focused tests, type checks, linters, local runs, or narrow smoke checks.
4. Put policy, parsing, validation, orchestration, persistence, and side effects in clear places.
5. Use plain data and plain text formats where they improve inspectability, diffs, testing, or automation.
6. Version every meaningful source of behavior: code, tests, config, scripts, schemas, and migrations.
7. Strengthen names before adding comments. Add comments only for constraints, intent, history, or tradeoffs.
8. When discomfort appears, pause and identify the smell: unclear name, mixed responsibility, hidden state, weak test seam, distant coupling, timing dependence, or unknown behavior.

Hand off to `safe-incremental-coding`, `coding-implementation-guard`, or `clean-code` for deeper mechanics, or to `tdd` when that skill is installed.

## Debugging

Use this pass when behavior is surprising.

1. Reproduce first. Do not patch from a hunch.
2. State the expected behavior, actual behavior, and smallest known failing case.
3. Gather facts with logs, tests, traces, queries, breakpoints, or runtime inspection.
4. Change one variable at a time so the result can teach you something.
5. Treat impossible states as contract failures. Add assertions or guards where they reveal corrupted assumptions.
6. Fix the root cause, then add a regression check at the level where the behavior matters.
7. Remove temporary probes unless they become useful observability.

Hand off to `diagnose`, when that skill is installed, if the failure path is still unknown after the first reproduction pass; otherwise keep iterating this checklist, gathering one new fact per loop.

## Reliability And Safety

Use this pass when the change touches state, resources, concurrency, jobs, external services, security, money, private data, or production behavior.

1. Identify the source of truth and the invariant that must survive.
2. Check resource ownership: files, handles, locks, transactions, subscriptions, timers, sockets, and cleanup.
3. Design for retries, duplicate delivery, partial failure, cancellation, and rollback.
4. Break hidden time ordering. Make sequencing explicit through state, queues, locks, transactions, idempotency keys, or version checks.
5. Avoid shared mutable state across workers, requests, tasks, tests, and sessions unless ownership is explicit.
6. Make failure visible. Prefer clear errors, alerts, logs, repair scripts, or reconciliation checks over silent recovery.
7. Review security at the boundary where trust changes.

Hand off to `coding-design-plan` or `coding-review-simplify` when the risk is high. Prefer a dedicated security skill or command, such as `codex-security:security-scan` or `security-review`, when one is installed; if none is available, do a manual trust-boundary review using the checklist above.

## Review

Use this pass before final delivery or during code review.

1. Compare the diff to the stated outcome and chosen design.
2. Look for entropy introduced by the change: unclear ownership, duplicated knowledge, mixed concepts, hidden dependencies, broad helpers, accidental public API, and fragile tests.
3. Check that tests describe behavior and would survive a legitimate refactor.
4. Verify edge cases: invalid input, missing data, dependency failure, concurrency, permissions, and observability.
5. Simplify while the context is fresh. Delete speculative structure and tighten names.
6. Confirm the final answer says what changed, how behavior changed or stayed stable, and what was verified.

Hand off to `coding-review-simplify`, `full-review`, `test-lens`, or `architecture-lens` when the diff needs deeper review.

## Team And Handoff

Use this pass when the work affects other people or future sessions.

1. Communicate early when assumptions, risks, or tradeoffs matter.
2. Make the next action obvious through code, tests, issue notes, commit messages, or concise docs.
3. Keep local improvements visible but scoped. Do not surprise the team with unrelated cleanup.
4. Leave useful breadcrumbs: why this shape, what was deferred, how to verify, and where to look next.
5. Take pride in the delivered result without hiding uncertainty.

## Output Contract

When this skill shapes a coding session, include the relevant parts only:

1. `phase`: the phase or phases handled.
2. `pragmatic_frame`: the practical problem and chosen smallest useful move.
3. `decisions`: boundaries, contracts, reversibility, or tradeoffs that mattered.
4. `risk_checks`: state, concurrency, resource, security, or verification risks considered.
5. `verification`: checks run or the reason they could not run.
6. `handoff`: assumptions, next action, or follow up when useful.

## Gotchas

1. Do not turn this lens into a long checklist dump. Apply only the phase that matters.
2. Do not quote or reconstruct source text from the book, and do not embed chapter notes.
3. Do not confuse pragmatic with quick and dirty. Speed comes from feedback, clarity, and reversibility.
4. Do not use a prototype as production code unless it has been deliberately hardened.
5. Do not add abstractions before finding the variation they protect.
