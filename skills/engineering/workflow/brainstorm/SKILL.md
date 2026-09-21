---
name: brainstorm
description: Explore an uncertain idea and recommend whether to build, defer, reduce scope, or reject it. Use for brainstorming or a build decision; use interview-me next to settle requirements.
disable-model-invocation: true
---

# Brainstorm

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Decide whether to build and which direction to explore. Keep **the why before the how**: identify the problem before choosing a mechanism. **Expand the solution space** with alternatives supported by the user's needs and the project. Do not write production code or implementation tasks.

## 1. Understand the problem

Use existing context and inspect relevant code, docs, and prior decisions. Ask only what research cannot answer: who is affected, what fails today, why it matters, and the constraints that change the decision. Do not reopen a settled decision without new evidence.

## 2. Compare viable directions

Compare the current approach, the smallest useful change, and a materially different option when one exists. State the expected result, cost, and principal risk. Claims about the project must cite files inspected in this run; label assumptions and unverified external claims.

For generated ideas, read `references/idea-basis-contract.md`: each idea needs a source or an explicit reasoning basis. If the user cannot assess an unfamiliar area, read `references/blindspot-pass.md` and explain its decision points before asking for a choice.

Use `models-consensus` only when the user asks for additional opinions. That skill owns model selection, approval, dispatch, and council artifacts. Pass a neutral problem statement and then use its report here. Do not start a separate brainstorming panel.

## 3. Choose a direction

Recommend an option and explain the trade-off that matters. Ask the user to confirm or change the direction. Resolve material objections; do not require a fixed count of options or rounds.

## 4. Return the verdict

State BUILD, DEFER, REDUCE SCOPE, or REJECT, with the reason, proposed scope, exclusions, unresolved decisions, and evidence. For DEFER, name the event that should reopen the question. Avoid numerical confidence without a measured basis.

For BUILD or REDUCE SCOPE, hand the agreed direction to `interview-me`, which settles the requirements before `to-prd`. Continue into that stage only within the user's request. For DEFER or REJECT, stop. The verdict is the acceptance contract; an implementation plan is not required here.
