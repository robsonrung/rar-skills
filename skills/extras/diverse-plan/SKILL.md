---
name: diverse-plan
description: Compare independent implementation approaches and produce one reviewed plan. Use when the user explicitly requests a diverse plan or several model-generated approaches; it does not implement the plan.
disable-model-invocation: true
---

# Diverse Plan

Use this only when alternative designs can change the implementation decision. It is separate from `models-consensus`: the user chose a planning exercise, not a council. Never invoke the council from this skill.

## Outcome

Return one executable plan. It names the chosen approach, rejected alternatives, files, tests, risks, and the effective seats used. A branch is useful only when it explores a materially different premise.

## Routing

Read `shared/references/task-shaped-model-routing.md` and `shared/references/model-roster.md` from the collection's sanctioned shared directory before selecting seats. Use the semantic route selected there, not a legacy seat name or pinned model id. Astra is the default for system and cross-cutting synthesis. Fable is the default for repository-scale judgment. Opus is an explicitly selected focused precision perspective, not a default route.

Use two blind branch seats by default. Add a third branch only when a different boundary, failure mode, or delivery tradeoff is still unresolved. Select domain lenses only for surfaces the change touches:

| Need | Route |
| --- | --- |
| System shape, integration, or plan reconciliation | Astra planning route |
| Repository-scale design or codebase judgment | Fable planning route |
| Focused precision review | Opus only when the route explicitly selects it |
| Explicit implementation plan and execution gaps | Approved implementation route |
| Regression, concurrency, security, maintainability, or tests | Matching reviewer route from the shared routing |

Probe the selected seats once. Preserve **seat fidelity**: a missing seat is unavailable, never silently replaced. Continue only with two distinct available branch seats. If that quorum is unavailable, return the missing prerequisites and the single-model `to-prd` path instead.

## Route Approval

Before branch dispatch, present the exact route table: branch or lens, seat, current model, effort, role, transport, call count, and unavailable action. Ask the user to approve the table or name changes. Do not launch a branch or critique before that approval. Record the approved table with the plan artifacts and use only those routes.

## Workflow

1. Write one neutral brief with the goal, scope, constraints, acceptance contract, relevant files, and what a plan must decide. Ask one question only when different answers would produce different plans.
2. Launch the blind branches with the same brief. Give each one premise: smallest viable change, cleanest design, or most robust failure handling. Each returns approach, files, tradeoff, risks, tests, and rollback point.
3. Compare branches against the acceptance contract. Run only the relevant engineering lenses. Each critique must identify the strongest point, material weakness, and a concrete test or check.
4. Synthesize the record into one plan. Every adopted element traces to a branch or resolved critique. Preserve a material unresolved disagreement as a risk or open question.
5. Run one bounded execution-completeness check. Patch the plan once if it exposes a material omission. Do not create an open-ended planning loop.

## Synthesize and enrich

Use the approved synthesis route. It chooses the plan spine, incorporates verified improvements, and records why the strongest alternative lost. If the selected route is unavailable, stop and report the missing route or use only a user-approved alternate.

## Execution completeness check

Use the approved implementation-review route to test whether an implementer can follow the plan without inventing a design decision. Check scope, file placement, acceptance criteria, commands, tests, rollout risk, and rollback. One material gap gets one targeted correction round; otherwise stop.

## Output

Present:

1. the change and chosen approach;
2. approaches considered and the deciding tradeoff;
3. ordered implementation steps, files, tests, and verification;
4. risks, rollback, and open questions;
5. the seat and lens table, including effective receipts, unavailable seats, and fallbacks.

Write an artifact only when the user asks. Hand the approved plan to `to-prd` so it becomes the workflow's approved product record; then `to-tasks` slices that PRD. Do not implement it here.
