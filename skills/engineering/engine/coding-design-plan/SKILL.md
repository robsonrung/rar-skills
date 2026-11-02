---
name: coding-design-plan
description: Plan the implementation shape of one approved coding task. Use when a module, data, API, component, or deployment boundary still needs a design decision; use to-tasks for task decomposition.
---

# Coding Design Plan

Turn one approved task into the **smallest coherent shape** an implementer can build without making a new product or architecture decision. Choices settled in the PRD or task are **already decided**; build on them.

## Workflow

1. Read the task, its acceptance contract, and the project's conventions. Inspect the relevant code, tests, and current behavior.
2. State the design problem in one sentence: the behavior that changes and its owner.
3. Map only the affected boundary: module, component, service, data store, public contract, or deployment path. Use **change ownership** to place each responsibility where its next change belongs.
4. Choose the smallest coherent shape that fits the existing code. When a real alternative exists, state the one trade-off that decides it. When the code makes one local move clear, take it.
5. Add a check only when its trigger applies:
   - The task crosses a nonlocal boundary and has no lens conclusions yet: run `design-gate`.
   - The task already carries lens conclusions: apply them as constraints.
   - One uncertainty only running code can answer: use `to-prototype`. Prototype code never graduates.
6. Name a test or direct check for every changed behavior. For a nonbehavior change, say why a test does not help and name the replacement check.
7. Put adjacent work you discover in `deferred`. Widening scope needs a new task or the user's instruction.

Use a safe default for nonmaterial details and state the assumption. Ask the user only when a fact you cannot inspect would change the shape, public behavior, risk, scope, or cost.

## Output

The plan is done when every field is filled and every changed behavior has its check.

1. `design_problem`: one sentence.
2. `chosen_shape`: the smallest coherent shape.
3. `boundaries`: affected owners, modules, contracts, or runtime paths.
4. `constraints`: task decisions and lens conclusions that apply.
5. `verification`: the command, test, or direct check for each changed behavior.
6. `test_scenarios`: input, action, and expected outcome per changed behavior, or `Test expectation: none` with its reason and replacement check.
7. `deferred`: adjacent work kept out of this task.
8. `blocker_or_assumption`: only an unresolved fact that could change the plan.

Write an ADR only when **all three or no ADR** holds: the decision is hard to reverse, surprising without context, and a real trade-off. **Record on settle**, not at the end of implementation.
