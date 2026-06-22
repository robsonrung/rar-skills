---
name: clean-code
description: Improve existing code through safe, behavior-preserving Clean Code refactoring. Use when the user asks to refactor code, clean up messy code, improve readability, simplify structure, reduce duplication, improve naming, review maintainability, or apply Clean Code principles. Do not use for broad architecture redesign unless the user asks for redesign.
---

# Clean Code

Improve existing code so it is easier to read, safer to change, and simpler to test while preserving behavior by default.

## Operating Rules

- Stay behavior-preserving unless the user explicitly asks for a behavior change: keep public APIs, side effects, error behavior and messages, performance characteristics, observable timing assumptions, edge cases, and data shapes stable unless changing them is part of the request.
- Prefer the smallest useful change over a broad rewrite.
- Improve names before adding comments or abstractions.
- Keep domain language visible. Do not hide business rules behind generic helpers.
- Remove duplication only when duplicated code represents the same concept and has the same reason to change.
- Avoid new patterns, dependencies, formatting churn, and module moves unless they clearly reduce real complexity.
- If tests are missing or weak and the refactor is risky, improve existing tests, or add or suggest focused characterization tests as the behavior-preserving net, before changing structure deeply. For legacy code with no net to stand on, build that net first via `safe-incremental-coding`, then return here.

## Workflow

1. Understand the code.
   - Identify the code's purpose, public interfaces, inputs, outputs, side effects, invariants, framework constraints, and existing tests.
   - If the user asked for review only, report findings without editing.

2. Classify the work.
   - Use `local cleanup` for naming, constants, simple extraction, and control-flow clarity.
   - Use `refactor` for behavior-preserving structural changes.
   - Use `bug fix plus cleanup` only when the user allowed a behavior change or the requested bug is clear.
   - Treat `redesign` as out of scope unless the user explicitly asked for it.
   - If the safe path requires redesign, dependency changes, or behavior changes beyond the request, stop and report the option to the user instead of proceeding.

3. Choose improvements.
   - Rename unclear identifiers.
   - Extract meaningful constants for magic values.
   - Extract small helpers when they name a real step in the domain.
   - Flatten nested control flow with guard clauses.
   - Separate parsing, validation, business rules, persistence, formatting, orchestration, and side effects when they are tangled.
   - Improve error handling consistency without weakening existing errors.

4. Edit safely.
   - Keep changes scoped to the requested code path.
   - Make one logical improvement at a time when possible.
   - Re-verify the change is behavior-preserving per the rule above.
   - Do not replace clear code with clever code.

5. Validate.
   - Run the most relevant existing tests or checks when available.
   - If tests cannot be run, say why.
   - Re-check that names express intent, functions are focused, abstraction levels are consistent, comments remain accurate, and side effects are visible.

## Smell Checklist

Diagnose by name. Before you change anything, say which smell you see — naming the smell is what makes the fix obvious and keeps the change behavior-preserving. Each smell below is a term of art; use the term, don't paraphrase it.

- **Naming smells**: unclear names, magic values.
- **Function smells**: long functions, deep nesting, complex booleans, flag arguments, inconsistent abstraction levels.
- **Responsibility smells**: mixed responsibilities, large classes, hidden mutations.
- **Data smells**: primitive obsession, data clumps, long parameter lists.
- **Duplication smells**: duplicated logic (only when it is the same concept with the same reason to change).
- **Comment smells**: noisy comments that repeat or excuse the code.
- **Safety smells**: inconsistent error handling, brittle or missing tests.

State the smell, then apply the matching improvement. "This has **primitive obsession** and a **data clump** in the parameters" is the kind of sentence that should precede each edit.

## Naming Guide

- Prefer intent-revealing names such as `elapsedTimeInDays`, `customerRepository`, `isEligibleForDiscount`, `calculateInvoiceTotal`, and `parsePaymentRequest`.
- Avoid vague names such as `data`, `info`, `manager`, `processor`, and `helper` unless the domain really uses that term.
- Name booleans so they read naturally: `isActive`, `hasPermission`, `canRetry`, `shouldNotifyCustomer`.
- Name functions with verbs when practical: `calculateTotal`, `validateRequest`, `loadCustomer`, `sendReceipt`, `formatCurrency`.

## Comments

Diagnose every comment as an **earned comment** or noise. A comment is earned only when it carries what the code cannot — a business rule, external constraint, security concern, performance tradeoff, historical context, or non-obvious decision. Say it while editing: "this is an **earned comment** — it records the auth constraint the parameter name can't." Everything else is noise: comments that repeat the code, restate the obvious, excuse code that should be renamed or extracted, or read like AI slop (apologetic, placeholder, or narrate-the-diff lines a senior would never leave).

- Keep **earned comments**: business rules, external constraints, security concerns, performance tradeoffs, historical context, non-obvious decisions.
- Cut the unearned: code-restating, obvious, outdated, or AI-slop comments.

## Output Contract

When returning results, include:

- `summary`: what was improved.
- `key_improvements`: the most important readability, maintainability, safety, or testability changes.
- `behavior_changes`: state `none` when behavior was preserved; otherwise explain exactly what changed and why.
- `validation`: tests or checks run, with results.
- `risks`: missing tests, unclear requirements, framework constraints, or areas needing extra review.

For review-only tasks, lead with findings ordered by severity and include file and line references where possible.
