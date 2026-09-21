---
name: coding-design-plan
description: Plan the implementation shape of one approved coding task. Use when a module, data, API, component, or deployment boundary still needs a design decision; use to-tasks for task decomposition.
---

# Coding Design Plan

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Turn a scoped task into the **smallest coherent shape** an implementer can build without making a new product or architecture decision. The next consumer is `implement-and-review` or the engineer making the change. The plan is done when it names the changed behavior, owner, boundary, verification, and any unresolved blocker.

Treat choices settled in the PRD or task as **already decided**. Do not reopen them through a new interview or option list.

## Workflow

1. Read the approved task, acceptance contract, and active project conventions. Inspect the relevant code, tests, and current behavior before proposing a shape.
2. State the design problem in one sentence. Name the behavior that changes and the owner of that behavior.
3. Map only the affected boundary: local code, module, component, service, data store, public contract, or deployment behavior. Use **change ownership** to place each responsibility where the next change belongs.
4. Choose the smallest coherent shape that fits the existing code. State one decisive tradeoff when a real alternative exists. Do not compare options when the code and task make one local move clear.
5. Use a targeted engineering check only when its trigger applies:

   1. Run `design-gate` when the task changes a nonlocal boundary and no task contract has already selected the applicable lenses.
   2. Apply the task's named lens conclusions when they already exist. Do not rerun a lens to restate the same conclusion.
   3. Use `to-prototype` for one uncertainty that only running code can answer. Prototype code never graduates.

6. Convert the plan into observable verification. For every changed behavior, name the test or direct check that proves it. For a nonbehavior change, record why an automated test is not useful and name the replacement check.
7. Keep discovered adjacent work in `deferred`. A scope expansion needs a new task or an explicit user instruction.

Ask the user only when a fact that cannot be inspected would change the selected shape, public behavior, or risk boundary. Otherwise state the assumption and continue.

## Output Contract

Return:

1. `design_problem`: one sentence.
2. `chosen_shape`: the smallest coherent implementation shape.
3. `boundaries`: affected owners, modules, contracts, or runtime paths.
4. `constraints`: applicable task decisions and lens conclusions.
5. `verification`: commands, tests, or direct checks for each changed behavior.
6. `test_scenarios`: input, action, and expected outcome for each changed behavior, or `Test expectation: none` with its reason and replacement check.
7. `deferred`: adjacent work kept out of this task.
8. `blocker_or_assumption`: only an unresolved fact that could change the plan.

Write an ADR only when **all three or no ADR** applies: the decision is hard to reverse, surprising without context, and a real tradeoff. **Record on settle** rather than at the end of implementation.

## Gotchas

1. Do not turn a routine fix into an architecture review.
2. Do not let a design lens add scope beyond the accepted task.
3. Do not plan a tracer bullet when a throwaway prototype is the needed learning move.
4. Do not call the plan complete without an acceptance contract and evidence route.
