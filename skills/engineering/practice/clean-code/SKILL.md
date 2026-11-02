---
name: clean-code
description: Refactor existing code with behavior-preserving Clean Code practices. Apply it to local naming, readability, duplication, or structure problems; use architecture-lens for module boundary decisions.
---

# Clean Code

Make existing code easier to read, change, and test. Every edit is **behavior-preserving** unless the request changes behavior: public APIs, side effects, errors and their messages, performance, edge cases, and data shapes all stay put. Code with no test net goes through `safe-incremental-coding` first.

**Act or assess**: a review request gets findings ordered by severity with `file:line`, and no edits.

## Classify the work

- **Local cleanup**: names, constants, simple extraction, control-flow clarity.
- **Refactor**: behavior-preserving structural change.
- **Bug fix plus cleanup**: only when a behavior change is allowed or the requested bug is clear.
- **Redesign** is out of scope unless requested. If the safe path needs redesign, new dependencies, or behavior change beyond the request, stop and report that option.

Keep the change to the **smallest coherent shape** on the requested path, one logical improvement at a time.

## Smell catalogue

**Diagnose by name.** Name the smell before you change anything; the name picks the fix and keeps the change honest. Use the term of art, never a paraphrase.

- **Naming**: unclear names, magic values.
- **Function**: long functions, deep nesting, complex booleans, flag arguments, inconsistent abstraction levels.
- **Responsibility**: mixed responsibilities, large classes, hidden mutations.
- **Data**: primitive obsession, data clumps, long parameter lists.
- **Duplication**: duplicated logic, merged only when it is the same concept with the same reason to change.
- **Comment**: noise that repeats or excuses the code.
- **Safety**: inconsistent error handling, brittle or missing tests.

Model sentence: "This has **primitive obsession** and a **data clump** in the parameters." Then apply the matching move: rename, extract a named constant, extract a helper that names a real domain step, flatten with guard clauses, or separate tangled parsing, validation, rules, persistence, formatting, and side effects.

## Names

Choose intent-revealing names in the **ubiquitous language**: `isEligibleForDiscount`, `calculateInvoiceTotal`. Use verbs for functions and predicates for booleans (`canRetry`). Keep business rules visible rather than hidden behind generic helpers. Treat `data`, `manager`, and `helper` as smells unless the domain uses the word.

## Comments

Judge every comment as an **earned comment** or noise. A comment is earned when it carries what the code cannot: a business rule, an external constraint, a security concern, a performance tradeoff, historical context, or a non-obvious decision. Say it while editing: "this is an **earned comment**: it records the auth constraint the parameter name can't." Cut the rest: comments that restate the code, are outdated, excuse code you should rename or extract, or narrate the diff.

## Report

Report what improved, any behavior changes (`none` when preserved), the checks run with their results, and the remaining risks.

Do not quote or reconstruct source text from the book this skill distills.
