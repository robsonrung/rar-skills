---
name: collaborative_discovery
description: Multi-model discovery interview and brainstorming. Use for product ambiguity, feature exploration, scenario discovery, tradeoff exploration, or when the user is not yet sure what should be built.
---

# Collaborative discovery

Turn an ambiguous idea into a clear problem frame through real multi-model brainstorming and user interview.

Shared scaffolding (inputs, routing and configurability, local panel runner and flags, native response helper, panel status taxonomy, completion gate) lives in `../_shared/collaborative-panel-runner.md`. Read it before running any panel phase. This file keeps only what is specific to discovery.

## Roles

Discovery uses the role names `synthesis_anchor`, `adversarial_anchor`, `broad_context`, `feasibility`, and `user_advocate`. The mapping to models is editable in `assets/routing.toml`.

## Phases

Run the configured panel phases in order: `intake`, `divergence`, `user_interview`, `cross_critique`, and `convergence`. Artifacts and prompts live under `.codex_workflow/discovery`.

## Workflow

Use this skill as a dialogue loop, not as a one shot planner. The goal is to make the problem crisp before any PRD, task plan, or implementation begins.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete (see the shared Core rule). If a specialist role is not relevant to the current idea, it still participates and states why it has no material concern.

### Steps

1. Capture the user idea exactly, then rewrite it as a neutral problem statement.
2. Identify ambiguity categories, users, jobs to be done, constraints, known non goals, and likely missing decisions.
3. Run the configured panel phases in order: `intake`, `divergence`, `user_interview`, `cross_critique`, and `convergence`. Use `user_interview` to decide which questions matter; it may conclude that no more questions are needed. Treat every role response as advisory until reconciled.
4. Ask the user only the questions that would materially change the direction. Group questions by product risk, user workflow, data, permissions, user interface, and delivery constraints.
5. Repeat the interview loop until the remaining ambiguity is explicit and acceptable.
6. Run a cross critique round. Each role should critique the strongest option, not the weakest option.
7. Produce a converged discovery brief with options preserved. Do not erase minority views. Mark each unresolved point as decision needed, assumption accepted, or deferred.

### Quality bar

The final brief must be usable as input to the specification skill without the user repeating context. It must include the problem, target users, value proposition, constraints, non goals, scenarios, key tradeoffs, accepted assumptions, rejected options, risks, and recommended next step.

Do not write production code in this skill. Do not create implementation tasks in this skill. If implementation details appear, keep them as feasibility notes only. The feasibility role may consult `references/engineering_rules.md` when judging implementation risk.

## Required outputs

Read `references/output_contract.md` before writing phase artifacts (audit fields, status taxonomy, transcript handling).

Create these files under `.codex_workflow/discovery` unless the user asks for another path:

1. `discovery_brief.md`
2. `option_map.md`
3. `open_questions.md`
4. `decision_log.md`
5. `panel_summary.json`

This list is mirrored in `assets/routing.toml` `required_outputs`, the machine-read source consumed by `scripts/validate_artifacts.py`.
