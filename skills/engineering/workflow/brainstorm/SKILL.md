---
name: brainstorm
description: Explore an uncertain idea and recommend whether to build, defer, reduce scope, or reject it. Use for brainstorming or a build decision; use interview-me next to settle requirements.
disable-model-invocation: true
---

# Brainstorm

Decide whether to build and which direction to take. Keep **the why before the how**: name the problem before choosing a mechanism. **Expand the solution space** with alternatives grounded in the user's needs and the project. Write no production code or tasks.

1. **Understand the problem.** Read the relevant code, docs, and prior decisions first. Ask only what research cannot answer: who is affected, what fails today, why it matters, and which constraints change the decision. Do not reopen a settled decision without new evidence.
2. **Compare directions.** Weigh the current approach, the smallest useful change, and a materially different option when one exists, each with its expected result, cost, and main risk. Claims about the project cite files read in this run; label assumptions and unverified outside claims. When the user wants generated ideas, follow [references/idea-basis-contract.md](references/idea-basis-contract.md). When the user cannot judge a territory, run [references/blindspot-pass.md](references/blindspot-pass.md).
3. **Choose.** Recommend one option, explain the trade-off that matters, and ask the user to confirm or change it. Resolve material objections; no fixed count of options or rounds.
4. **Return the verdict:** BUILD, DEFER, REDUCE SCOPE, or REJECT, with the reason, scope, exclusions, open decisions, and evidence. DEFER names the event that should reopen the question. Give no numerical confidence without a measured basis.

BUILD or REDUCE SCOPE hands the direction to `interview-me`, within the user's request. DEFER and REJECT stop here.
