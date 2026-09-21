---
name: to-prototype
description: Build a throwaway experiment to answer a design question that reading cannot settle. Use for technical spikes, state-model demos, or visual alternatives; use a tracer bullet when the code must ship.
---

# Prototype

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Answer one decision-changing question with throwaway code. **Prototype code never graduates**: the next production task rebuilds the selected behavior under its acceptance contract. A prototype produces evidence and a decision, not a finished feature.

## 1. State the question

Identify the unknown, the observation that would answer it, and the time or scope limit. Read existing code and docs first. A question already answered by those sources does not need a prototype.

Choose the smallest useful form:

1. Visual alternatives: read `references/ui.md`. Compare layouts on a local route with safe data.
2. Logic or state behavior that a person must explore: read `references/logic.md`. Use a standalone HTML demo.
3. A technical property such as integration behavior, latency, or library support: write a small local script or harness that records the relevant input, output, and measurement. Do not add a UI that cannot help answer the question.

## 2. Run the experiment

Keep the work isolated in a scratch location or local worktree. Name it as a prototype and give one command or file path to run it. Use in-memory or scratch data. Use real services only when that access is authorized and necessary to the question.

Skip production scaffolding and unrelated polish. Keep enough checks and error output to trust the experiment. Record actual observations and failed attempts. Stop at the agreed limit if the question remains unresolved.

## 3. Return the decision

Return these four fields:

1. `question`: the single question tested.
2. `answer`: the decision, evidence, limitations, and any unresolved result.
3. `snippets`: only decision-bearing state, schema, or type shapes; no production-ready claim.
4. `disposition`: the artifact path and whether it is retained or removed. No prototype code is promoted to production.

Save the evidence beside the caller's decision record or task plan, with its decision revision or content hash. A later decision change marks the affected prototype superseded. For a visual decision, record an actual browser review before claiming the layout is verified; model or DOM checks do not prove visual usability. If browser review is unavailable, retain that open limit rather than claiming acceptance. Keep a local artifact when useful; commit a throwaway branch or update a tracker only when authorized. Do not delete unrelated files during cleanup.

Return to `interview-me` to settle its question, or to `coding-design-plan` to revise the slice plan. An unresolved result returns an open decision rather than a fabricated answer. This closes the prototype's acceptance contract.
