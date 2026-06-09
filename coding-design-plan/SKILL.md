---
name: coding-design-plan
description: Shape coding plans before implementation. Use when a coding task is ambiguous, broad, touches module or service boundaries, changes public interfaces, alters persistence or data flow, introduces an abstraction, or needs a design decision before edits. Also use when the user asks for an implementation plan, design plan, or approach before coding.
---

# Coding Design Plan

Use this skill before coding when the implementation shape matters. The goal is a small coherent plan that makes the edit safer, not an architecture essay.

## Workflow

1. Inspect the live code, repo guidance, current behavior, and tests before naming the design.
2. State the real design problem in one sentence.
3. Classify the scope as local code, module, component, service, data boundary, public contract, or deployment behavior.
4. Name the main boundary, owner, invariant, or interface that must stay coherent.
5. Pick at most three quality concerns that are in tension for this task, such as correctness, maintainability, reliability, performance, security, deployability, or observability.
6. Compare alternatives only when the choice is meaningful. Include keeping the current shape as an option when it is realistic. For small tasks, state why the obvious local shape is enough.
7. Choose the smallest coherent shape that fits the current codebase and avoids unrelated redesign.
8. Convert the main concern into verification before editing: a cheap objective test, static check, contract check, migration check, or smoke check that proves the design holds.

## Decision Checks

Use these checks when the task is larger than a local edit:

1. Boundaries: what module, component, service, data owner, or public contract changes?
2. Coupling: what new dependency or shared knowledge appears, and is it local or distant?
3. Concept: does the plan have one central idea with consistent names and interfaces?
4. Data: what source of truth, consistency need, migration path, or rollback risk exists?
5. Runtime: does sync, async, retry, queue, cache, or external API behavior affect correctness?
6. Reversibility: would this decision be expensive to undo?

## Escalation

Draft a short decision note or ADR only when the change sets long lived direction, changes data ownership, changes a public contract, introduces a platform or vendor, affects more than one team, or resolves a repeated debate.

## Output Contract

When planning, return:

1. `design_problem`: the real problem to solve.
2. `chosen_shape`: the smallest coherent implementation shape.
3. `boundaries`: files, modules, data owners, contracts, or runtime paths likely touched.
4. `tradeoff`: the decisive benefit, accepted cost, and quality concern being prioritized.
5. `verification`: the checks that should prove the plan.
6. `escalation`: whether a decision note or ADR is needed.

When implementing in the same turn, keep the plan short and move into the edit.

## Gotchas

1. Do not turn routine bug fixes into architecture reviews.
2. Do not preserve existing patterns when the existing model is the problem.
3. Do not choose a new abstraction until the current code shows a real pressure.
4. Do not ask the user to choose among options until the practical tradeoff is clear.
5. Do not present an option as free. If no cost is visible, keep looking.
