---
name: coding-design-plan
description: Shape coding plans before implementation. Use when a coding task is ambiguous, broad, touches module or service boundaries, changes public interfaces, alters persistence or data flow, introduces an abstraction, or needs a design decision before edits. Also use when the user asks for an implementation plan, design plan, or approach before coding.
---

# Coding Design Plan

Use this skill before coding when the implementation shape matters. The goal is a small coherent plan that makes the edit safer, not an architecture essay.

## Workflow

1. Inspect the live code, repo guidance, current behavior, and tests before naming the design.
2. State the real design problem in one sentence.
3. Scope gate: before spending effort on deeper research or plan writing, state the scope claim in one or two sentences — what the plan will target and what it will not — and wait for the user to affirm or redirect. Auto-proceed, announcing instead of waiting, only when the task is small and unambiguous with no fork where user input would change the plan. In headless or pipeline runs, never block: proceed and record inferred scope as explicit assumptions in the plan.
4. Classify the scope as local code, module, component, service, data boundary, public contract, or deployment behavior.
5. Name the main boundary, owner, invariant, or interface that must stay coherent.
6. Pick at most three quality concerns that are in tension for this task, such as correctness, maintainability, reliability, performance, security, deployability, or observability.
7. Compare alternatives only when the choice is meaningful. Include keeping the current shape as an option when it is realistic. For small tasks, state why the obvious local shape is enough.
8. Choose the smallest coherent shape that fits the current codebase and avoids unrelated redesign.
9. Convert the main concern into verification before editing: a cheap objective test, static check, contract check, migration check, or smoke check that proves the design holds.

## Test Scenarios

Every feature-bearing unit of the plan enumerates its test scenarios — specific enough that the implementer never invents coverage. Each scenario names the input, the action, and the expected outcome. Draw from every category that applies to the unit:

1. Happy path: core behavior with expected inputs and outputs.
2. Edge cases: boundary values, empty inputs, nil states, concurrent access.
3. Error and failure paths: invalid input, downstream failure, timeout, permission denial.
4. Integration: cross-layer behavior that mocks alone cannot prove.

Right-size to the unit: a config tweak may need one scenario, a payment flow a dozen. A unit with no behavioral change (pure config, scaffolding, styling) carries the mandatory line `Test expectation: none — [reason]` instead. A feature-bearing unit with blank or missing scenarios flags the plan incomplete — the none-annotation is never valid there.

## Scope Discipline

"While we're here" work never enters scope. When planning surfaces an adjacent refactor, tangential cleanup, or scope-adjacent nice-to-have, route it to a `Deferred` subsection of the plan, not into the active shape. The user's explicit ask overrides this: an explicitly requested refactor is in scope, not deferred.

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
6. `test_scenarios`: per feature-bearing unit, the enumerated scenarios; per non-feature unit, the `Test expectation: none — [reason]` line.
7. `deferred`: out-of-scope work noticed while planning, kept out of the active shape.
8. `escalation`: whether a decision note or ADR is needed.

When implementing in the same turn, keep the plan short and move into the edit.

## Confidence Check and Deepening

After drafting, score each plan section: is it grounded in inspected code, or resting on assumption? Two triggers force a deepening pass even when the plan looks solid:

1. Thin local grounding — fewer than three direct local examples of the pattern the plan relies on, or only adjacent-domain examples.
2. Load-bearing external research — an external finding shaped a decision the local codebase cannot verify.

Deepening during initial plan generation runs in auto mode: strengthen the flagged sections and synthesize directly, without asking. When the user asks to deepen an existing plan, run interactive mode: present findings individually and integrate only what they accept. If neither trigger fires and no section scores low, report the check passed and stop.

## Gotchas

1. Do not turn routine bug fixes into architecture reviews.
2. Do not preserve existing patterns when the existing model is the problem.
3. Do not choose a new abstraction until the current code shows a real pressure.
4. Do not ask the user to choose among options until the practical tradeoff is clear.
5. Do not present an option as free. If no cost is visible, keep looking.
6. Do not fold "while we're here" work into scope — route it to `deferred`.
7. Do not leave a unit's test scenarios blank — enumerate them or write the test-expectation line.

---
*Test-scenario, scoping-gate, anti-expansion, and deepening contracts adapted from Every's compound-engineering-plugin (`ce-plan`).*
