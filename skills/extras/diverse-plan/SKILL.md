---
name: diverse-plan
description: Compare independent implementation approaches and produce one reviewed plan. Use when the user explicitly requests a diverse plan or several model-generated approaches; it does not implement the plan.
disable-model-invocation: true
---

# Diverse Plan

Use this only when alternative designs can change the implementation decision. It is a planning exercise, not a council; never invoke `models-consensus` from here. The result is one executable plan.

## Plan

1. Write one neutral brief: goal, scope, constraints, acceptance contract, relevant files, and what a plan must decide. Ask one question only when different answers would produce different plans.
2. Choose the branches. Two by default; add a third only when an unresolved boundary, failure case, or delivery tradeoff needs its own approach. Each branch gets one **premise**: smallest viable change, cleanest design, or most robust failure handling. A branch that repeats another's brief at higher effort is not a branch.
3. Resolve each branch with `python3 shared/scripts/model_routing.py resolve <route>`, using `deep-analysis`, `architecture`, or `technical-analysis` (defined in `shared/model-routing.json`; shapes in `shared/references/task-shaped-model-routing.md`), and `precision-review` only for a named semantic risk. Branches run on distinct models.
4. Show the branches with their premise, model, effort, and host route, plus the synthesis and completeness-check roles. Ask: **"Approve this plan, or specify changes."**

Route each role by host: T3 Code `delegate_task`, continued with `t3_thread_send`; Claude Code or Codex, a native subagent; otherwise the matching `*-runner` skill. Each branch keeps one context for its later critique and reply; synthesis gets its own. **Seat fidelity**: an unavailable branch is reported, never replaced. With fewer than two distinct branches, stop and offer the single-model `to-prd` path.

## Run

1. **Branches**, blind and in parallel, from the same brief. Each returns approach, files, tradeoff, risks, tests, and rollback point.
2. **Critique** against the acceptance contract, using only the lenses that apply: the strongest point, the material weakness, and a concrete check for each branch.
3. **Synthesis.** Choose the plan spine and fold in verified improvements. Every adopted element traces to a branch or a resolved critique; record why the strongest alternative lost, and keep a material unresolved disagreement as a risk or open question.
4. **Completeness check**, once: could an implementer follow the plan without inventing a design decision? Check scope, file placement, acceptance criteria, commands, tests, rollout risk, and rollback. Patch one material gap, then stop.

## Output

1. The change and chosen approach.
2. The approaches considered and the deciding tradeoff.
3. Ordered steps, files, tests, and verification.
4. Risks, rollback, and open questions.
5. Each role's model and route, and any unavailable branch.

Write an artifact only when the user asks. Hand the approved plan to `to-prd`, and `to-tasks` slices that PRD. Do not implement it here.
