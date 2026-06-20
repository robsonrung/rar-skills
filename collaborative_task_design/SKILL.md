---
name: collaborative_task_design
description: Multi-model engineering task design and test planning. Use when a PRD, technical spec, bug description, or accepted discovery brief must become implementation tasks, test plans, architecture decisions, or delivery phases.
---

# Collaborative task design

Convert a PRD into sequenced engineering tasks using real multi-model review, spec driven development, domain driven design, clean architecture, and test driven development.

Shared scaffolding (inputs, routing and configurability, local panel runner and flags, native response helper, panel status taxonomy, completion gate) lives in `../_shared/collaborative-panel-runner.md`. Read it before running any panel phase. This file keeps only what is specific to task design.

## Roles

Task design uses the role names `synthesis_anchor`, `adversarial_anchor`, `architecture`, `testing`, `interface`, `backend`, and `delivery`. The mapping to models is editable in `assets/routing.toml`.

## Phases

Run the configured panel phases in order: `architecture_mapping`, `test_strategy`, `task_slicing`, `dependency_review`, and `convergence`. Artifacts and prompts live under `.codex_workflow/task_design`.

## Workflow

Use this skill to convert specification into executable engineering work. The output is not a PRD and not a patch. It is the bridge between product intent and implementation. Every task must trace back to a spec item and must define tests before code.

Read `references/engineering_rules.md` before running `architecture_mapping` and `task_slicing`; it holds the spec driven development, domain driven design, clean architecture, and test driven development rules this skill applies.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete (see the shared Core rule). If a specialist role is not relevant to the current plan, it still participates and states why it has no material concern.

### Steps

1. Read the PRD and codebase fit artifacts. If they do not exist, create a minimal assumptions section and mark missing inputs.
2. Map the target architecture. Identify domain layer, application use cases, ports, adapters, infrastructure, presentation, data boundaries, and dependency direction.
3. Run the configured panel phases in order: `architecture_mapping`, `test_strategy`, `task_slicing`, `dependency_review`, and `convergence`.
4. Slice tasks into vertical slices (tracer bullets) by user visible value and architectural seam. Avoid tasks that are too broad, such as implement backend, and tasks that are too tiny, such as rename one variable, unless that variable is a blocking domain concept.
5. For each task, include goal, files likely touched, tests to write first, implementation notes, acceptance criteria, verification commands, dependencies, rollback note, and expected review focus.
6. Identify work that can be parallelized safely. Do not parallelize tasks that write the same files, migrations, shared contracts, or security sensitive paths unless there is an explicit merge plan.
7. Produce a task sequence that supports red, green, refactor execution.

### Quality bar

A task is ready only when another agent can execute it without reinterpreting the product requirement. Each task must have a clear test first entry point and a bounded diff surface.

Do not implement code in this skill. Do not change files outside the workflow artifact directory unless the user explicitly asks for repository scaffolding.

## Required outputs

Read `references/output_contract.md` before writing phase artifacts; it defines the per-phase presence audit structure each artifact must include.

Create these files under `.codex_workflow/task_design` unless the user asks for another path:

1. `architecture_plan.md`
2. `tasks.md`
3. `test_plan.md`
4. `parallelization_plan.md`
5. `risk_register.md`
6. `decision_log.md`
7. `panel_summary.json`
