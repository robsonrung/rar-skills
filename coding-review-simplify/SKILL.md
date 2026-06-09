---
name: coding-review-simplify
description: Final review-and-simplify pass on a just-completed implementation before handoff. Use after an agent finishes coding work, or when the user asks to tighten, audit maintainability, remove unnecessary abstraction, verify architecture fit, or check data risk in a concrete diff.
---

# Coding Review Simplify

Use this skill after code has been changed or when reviewing a concrete diff. The goal is to catch correctness risks and simplify the result before handoff.

## Workflow

1. Read the user request, changed files, diff, and verification already run.
2. Check whether the implementation matches the intended behavior and chosen design shape.
3. Review the smallest relevant surface first, then expand only if the diff crosses boundaries.
4. Run the Simplification Pass below.
5. Check names, responsibilities, interfaces, and edge cases for one coherent model.
6. If stored state or async behavior changed, review source of truth, invariants, retries, migrations, compatibility, observability, and repair path.
7. If the diff feels tangled or crosses a boundary, run the Coupling Pass below.
8. Turn important concerns into a focused fix, test, static check, contract check, migration check, or explicit follow up.
9. Finish with the shortest honest outcome.

## Review Modes

Choose one mode:

1. Light review for a narrow local change. Focus on behavior, naming, simple control flow, and verification.
2. Standard review for multiple files, shared helpers, APIs, persistence, or meaningful tests. Add boundary, data, and regression checks.
3. Deep review for service boundaries, public contracts, migrations, data ownership, deployment behavior, or long lived decisions. Add tradeoff and decision note checks.

## Coupling Pass

Use this only when the diff feels tangled or crosses a boundary:

1. Strength: is the coupling static and visible, or dynamic and runtime dependent?
2. Locality: is the coupling inside one cohesive unit, or across modules, services, contracts, or teams?
3. Degree: how many callers, files, records, or systems must change together?
4. Remedy: weaken the strongest distant coupling first, such as replacing magic values with names, positional arguments with named data, hidden order with explicit state, or duplicated algorithms with one owned implementation.
5. Restraint: leave local static coupling alone when extraction would add indirection without safety.

## Findings Bar

Report a finding only when it can cause a bug, regression, maintenance trap, architecture drift, data risk, weak verification, or meaningful reader confusion.

For each finding, include:

1. Where it is.
2. Why it matters.
3. The smallest useful fix.
4. The verification that would prove it.

## Simplification Pass

Before final delivery, ask:

1. Can any new abstraction be deleted or made local?
2. Can dead code, leftover indirection, broad helpers, or noisy comments be removed?
3. Can a name make a helper unnecessary?
4. Can control flow be flatter without changing behavior?
5. Can duplicated code stay duplicated because the concepts may diverge?
6. Can a test express the invariant better than a comment?
7. Does the final code still fit the repo style?

## Output Contract

For review only, lead with findings ordered by severity and include file and line references.

For completed implementation work, include:

1. `outcome`: safe as is, simplified, needs one focused fix, or needs design escalation.
2. `changes`: simplifications or fixes made.
3. `verification`: tests or checks run.
4. `remaining_risk`: what still needs attention, if anything.

## Gotchas

1. Do not perform a full architecture review by default.
2. Do not generate ADRs routinely.
3. Do not expand scope after implementation unless there is a correctness or safety issue.
4. Do not rewrite clear code into clever code.
