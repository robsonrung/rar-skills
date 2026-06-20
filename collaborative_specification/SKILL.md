---
name: collaborative_specification
description: Multi-model PRD and technical specification workflow. Use after discovery, or when the user asks for a PRD, product spec, technical spec, acceptance criteria, codebase fit analysis, or feature definition before task planning.
---

# Collaborative specification

Create a PRD and codebase fit analysis from a clarified idea with real multi-model product, domain, interface, security, and delivery review.

Shared scaffolding (inputs, routing and configurability, local panel runner and flags, native response helper, panel status taxonomy, completion gate) lives in `../_shared/collaborative-panel-runner.md`. Read it before running any panel phase. This file keeps only what is specific to specification.

## Roles

Specification uses the role names `synthesis_anchor`, `adversarial_anchor`, `product`, `domain`, `interface`, `backend`, `security`, and `delivery_review`. The mapping to models is editable in `assets/routing.toml`.

## Phases

Run the configured panel phases in order: `repo_read`, `product_definition`, `domain_definition`, `interface_definition`, `backend_definition`, `risk_review`, and `convergence`. Artifacts and prompts live under `.codex_workflow/specification`.

## Workflow

Use this skill to produce the specification that future coding work must obey. It must connect the user request to the existing repository before tasks are created.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete (see the shared Core rule). The interface definition phase must include the interface role and the adversarial anchor together. The backend definition phase must include the backend role and synthesis anchor together. If a specialist role is not relevant to the current spec, it still participates and states why it has no material concern.

### Steps

1. Read the user request, any discovery brief, and the relevant repository files in read only mode.
2. Map existing patterns before inventing new ones. Look for similar routes, components, services, use cases, repositories, tests, permissions, validators, migration patterns, and error handling.
3. Run the configured panel phases in order: `repo_read`, `product_definition`, `domain_definition`, `interface_definition`, `backend_definition`, `risk_review`, and `convergence`. Read `references/engineering_rules.md` before the `domain_definition` and `backend_definition` phases so the contracts follow the spec driven, domain driven design, clean architecture, and test driven development rules.
4. Reconcile the outputs into one specification. Record disagreements in decision_log.md rather than hiding them.
5. Define acceptance criteria as testable statements.
6. Define non goals and out of scope behavior.
7. Define data contracts, permissions, validations, observability, rollout, migration, and rollback expectations where relevant.
8. Stop before task breakdown. Link to the task design skill as the next step.

### Quality bar

The PRD must be detailed enough that a separate agent can create a task plan without asking what the feature means. It must be constrained by the repository, not only by ideal product design.

Do not produce implementation patches in this skill. If code snippets are needed, keep them illustrative and mark them as non authoritative.

## Required outputs

Read `references/output_contract.md` when writing these phase artifacts or interpreting `panel_summary.json` statuses.

Create these files under `.codex_workflow/specification` unless the user asks for another path:

1. `prd.md`
2. `codebase_fit.md`
3. `domain_notes.md`
4. `interface_contract.md`
5. `backend_contract.md`
6. `risk_register.md`
7. `decision_log.md`
8. `panel_summary.json`
