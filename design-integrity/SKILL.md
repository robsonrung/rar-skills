---
name: design-integrity
description: Review and shape software designs for conceptual integrity before or during coding. Use when the user asks for architecture, API, data model, module, UI flow, feature, refactor, design review, Brooks, The Design of Design, tradeoffs, alternatives, system shape, or design before code. Do not use for tiny mechanical edits unless the design choice is the problem.
---

# Design Integrity

Use this skill to make software design work deliberate before implementation momentum hardens the wrong shape.

The core stance is Brooks inspired: real design discovers requirements, searches a space of alternatives, protects conceptual integrity, and relies on judgment under constraints.

## Operating Rules

1. Treat the stated request as a starting point, not the whole problem.
2. Preserve conceptual integrity: one clear model, consistent vocabulary, coherent boundaries, and predictable interfaces.
3. Prefer a small coherent design over a broad design with divided concepts.
4. Use the existing codebase as an exemplar source. Match its strongest local patterns unless they are part of the problem.
5. Compare alternatives before committing when the change affects architecture, data flow, public APIs, persistence, permissions, UI workflow, or cross module contracts.
6. Prototype only when uncertainty changes the decision. Throw the prototype away or clearly mark it as provisional.
7. Ask for user input only when a decision depends on product intent, operational risk, or a tradeoff the codebase cannot reveal.

## Workflow

1. Frame the real design problem.

   Identify the user goal, the affected users or callers, the current system behavior, the desired behavior, and the reason the current shape is insufficient.

2. Discover constraints.

   Look for invariants, existing contracts, data ownership, naming conventions, performance limits, security boundaries, migration cost, test seams, and deploy or rollback constraints.

3. Define design success.

   State what must be true for the design to be good. Include coherence, simplicity, testability, maintainability, and user visible behavior where relevant.

4. Search the design space.

   Produce at least two plausible solution shapes for meaningful changes. For each shape, state the central idea, what it simplifies, what it complicates, and how it fits or fights the existing system.

5. Choose the smallest coherent shape.

   Select the design that best preserves conceptual integrity under the known constraints. Explain the decisive tradeoff in one short paragraph before coding when the work is substantial.

6. Implement in the chosen shape.

   Keep names, boundaries, and data flow aligned with the chosen concept. Avoid adding side paths that solve local problems while weakening the central model.

7. Validate the design.

   Run relevant tests or checks. Then review whether the implementation still has one clear idea, whether edge cases follow the same model, and whether future maintainers can predict where changes belong.

## Review Checklist

Use this checklist before finalizing a design heavy change:

1. The real problem is named.
2. Hidden requirements and constraints were searched for.
3. At least two alternatives were considered, or the change was small enough to justify skipping that step.
4. The selected design has a single central concept.
5. Names match the concept.
6. Boundaries match ownership.
7. Public interfaces are predictable.
8. Error cases and edge cases follow the same model as the happy path.
9. The design is no larger than the problem requires.
10. Tests or verification exercise the main contract.

## Output Contract

When using this skill for planning or review, return:

1. `design_problem`: the real problem being solved.
2. `constraints`: the important constraints and assumptions.
3. `alternatives`: the viable solution shapes considered.
4. `recommendation`: the selected shape and decisive tradeoff.
5. `conceptual_integrity_check`: whether the result has one coherent model.
6. `validation`: tests, checks, prototypes, or evidence used.

When using this skill while implementing, keep the final answer concise and include the design decision, files changed, and validation performed.

## Gotchas

1. Do not turn every small bug fix into an architecture exercise.
2. Do not preserve existing patterns blindly when the request is about fixing a broken model.
3. Do not confuse consistency with conceptual integrity. Repeating an old mistake consistently is still a design problem.
4. Do not ask the user to choose among alternatives until you have explained the tradeoff in practical terms.
