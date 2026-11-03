---
name: to-prototype
description: Build a throwaway experiment to answer a design question that reading cannot settle. Use for technical spikes, state-model demos, or visual alternatives; use a tracer bullet when the code must ship.
---

# Prototype

Answer one decision-changing question with throwaway code. **Prototype code never graduates**: the production task rebuilds the chosen behavior under its own acceptance contract. A prototype yields evidence and a decision, not a feature.

## 1. State the question

Name the unknown, the observation that would answer it, and the time or scope limit. Read the code and docs first; a question they already answer needs no prototype. Pick the smallest form:

1. A visual decision: [references/ui.md](references/ui.md).
2. Logic or state behavior a person must explore: a standalone HTML demo, [references/logic.md](references/logic.md).
3. A technical property such as integration behavior, latency, or library support: a small script or harness that records input, output, and measurement, with no UI.

## 2. Run it

Work in a scratch location or local worktree, name it as a prototype, and give one command or path to run it. Use memory-backed or scratch data; touch real services only when authorized and necessary. Skip production scaffolding and polish, but keep enough checks and error output to trust the result. Record observations and failed attempts. Stop at the agreed limit even if the question stays open.

## 3. Return the decision

Return:

1. `question`: the one question tested.
2. `answer`: the decision, its evidence and limits, or the open result.
3. `snippets`: only decision-bearing state, schema, or type shapes.
4. `disposition`: the artifact path, and whether it is kept or removed.

Save the evidence beside the caller's decision record or task plan, with the decision revision it answers; a later decision change marks it superseded. A visual decision needs an actual browser review; a model or DOM check does not prove usability, so without one the decision stays open. Commit a throwaway branch or update a tracker only when authorized, and delete only what the prototype created.

Return to `interview-me` or `coding-design-plan` with the answer. An unresolved result comes back as an open decision, never a fabricated answer.
