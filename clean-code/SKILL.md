---
name: clean-code
description: Improve existing code through safe, behavior-preserving Clean Code refactoring. Use when the user asks to refactor code, clean up messy code, improve readability, simplify structure, reduce duplication, improve naming, review maintainability, or apply Clean Code principles. Do not use for broad architecture redesign unless the user asks for redesign.
---

# Clean Code

Improve existing code so it is easier to read, safer to change, and simpler to test while preserving behavior by default.

## Operating Rules

- Preserve external behavior unless the user explicitly asks for a behavior change.
- Keep public APIs, side effects, error behavior, and performance characteristics stable unless changing them is part of the request.
- Prefer the smallest useful change over a broad rewrite.
- Improve names before adding comments or abstractions.
- Keep domain language visible. Do not hide business rules behind generic helpers.
- Remove duplication only when duplicated code represents the same concept and has the same reason to change.
- Avoid new patterns, dependencies, formatting churn, and module moves unless they clearly reduce real complexity.
- If tests are missing and the refactor is risky, add or suggest focused characterization tests before changing structure deeply.

## Workflow

1. Understand the code.
   - Identify the code's purpose, public interfaces, inputs, outputs, side effects, invariants, framework constraints, and existing tests.
   - If the user asked for review only, report findings without editing.

2. Classify the work.
   - Use `local cleanup` for naming, constants, simple extraction, and control-flow clarity.
   - Use `refactor` for behavior-preserving structural changes.
   - Use `bug fix plus cleanup` only when the user allowed a behavior change or the requested bug is clear.
   - Treat `redesign` as out of scope unless the user explicitly asked for it.

3. Choose the smallest valuable improvements.
   - Rename unclear identifiers.
   - Extract meaningful constants for magic values.
   - Extract small helpers when they name a real step in the domain.
   - Flatten nested control flow with guard clauses.
   - Separate parsing, validation, business rules, persistence, formatting, orchestration, and side effects when they are tangled.
   - Improve error handling consistency without weakening existing errors.
   - Improve or add tests when risk justifies it.

4. Edit safely.
   - Keep changes scoped to the requested code path.
   - Make one logical improvement at a time when possible.
   - Preserve edge cases, error messages, observable timing assumptions, and data shapes.
   - Do not replace clear code with clever code.
   - Do not over-abstract code that is merely similar rather than conceptually duplicated.

5. Validate.
   - Run the most relevant existing tests or checks when available.
   - If tests cannot be run, say why.
   - Re-check that names express intent, functions are focused, abstraction levels are consistent, comments remain accurate, and side effects are visible.

## Smell Checklist

Look for unclear names, long functions, mixed responsibilities, duplicated logic, deep nesting, complex booleans, flag arguments, hidden mutations, large classes, primitive obsession, data clumps, long parameter lists, inconsistent abstraction levels, noisy comments, magic values, inconsistent error handling, and brittle or missing tests.

## Naming Guide

- Prefer intent-revealing names such as `elapsedTimeInDays`, `customerRepository`, `isEligibleForDiscount`, `calculateInvoiceTotal`, and `parsePaymentRequest`.
- Avoid vague names such as `data`, `info`, `manager`, `processor`, and `helper` unless the domain really uses that term.
- Name booleans so they read naturally: `isActive`, `hasPermission`, `canRetry`, `shouldNotifyCustomer`.
- Name functions with verbs when practical: `calculateTotal`, `validateRequest`, `loadCustomer`, `sendReceipt`, `formatCurrency`.

## Comments

- Keep comments that explain business rules, external constraints, security concerns, performance tradeoffs, historical context, or non-obvious decisions.
- Remove or rewrite comments that repeat the code, explain code that should be renamed or extracted, are outdated, or add noise.

## Output Contract

When returning results, include:

- `summary`: what was improved.
- `key_improvements`: the most important readability, maintainability, safety, or testability changes.
- `behavior_changes`: state `none` when behavior was preserved; otherwise explain exactly what changed and why.
- `validation`: tests or checks run, with results.
- `risks`: missing tests, unclear requirements, framework constraints, or areas needing extra review.

For review-only tasks, lead with findings ordered by severity and include file and line references where possible.
