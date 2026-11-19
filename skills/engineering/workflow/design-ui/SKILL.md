---
name: design-ui
description: Take a product interface from visual direction to a verified build by comparing real alternatives, translating the chosen one, and inspecting the rendered result. Use for a UI redesign, image concept exploration, implementing a screenshot or design file, or raising an interface's visual quality; use build-ui to build a page or component directly when the direction is already chosen and to-prototype for one throwaway design question.
---

# Design UI

Make an interface that fits its product and users through concrete direction, compared alternatives, faithful implementation, and observed behavior. Keep four kinds of evidence apart: visual judgment, reference fidelity, functional correctness, and usability. A strong visual verdict never offsets a broken required action, and agent review is not a study with people.

## Establish the outcome

1. Identify the scope (exploration, audit, prototype, or implementation) and stay within it.
2. Inspect existing routes, components, tokens, content, and representative screens before inventing a visual language. Verify component paths in files, not from guessed names.
3. Name the primary user, task, and devices, and the **acceptance contract**: the journeys, states, viewports, and gates the result must pass ([references/evaluation.md](references/evaluation.md)). Infer routine details; ask only what changes the work and cannot be found.
4. For substantial work, keep a short record from [assets/designbrief.md](assets/designbrief.md), or extend the project's existing design documentation instead of starting a competing one.

## Choose the route

Route by the unresolved question. [references/routes.md](references/routes.md) holds each route's method and the honest fallbacks when image generation, a browser, or a reviewer is unavailable.

- **Existing product**: start from its components and observed problems; explore a new direction only when it resolves a real uncertainty.
- **New visual identity**: generate image concepts before building, and always when the user asks for images before code.
- **Interaction uncertainty**: compare executable alternatives through `to-prototype`, which sets their number. **Prototype code never graduates**, so the winner is rebuilt in the representative slice.
- **Selected reference**: the user already chose an image, screenshot, design file, or direction; skip divergent exploration and implement it.
- **Mixed**: images for direction, then a prototype for the consequential interaction.

A bitmap does not specify interaction. Never silently replace a required image deliverable with HTML.

## The mandate

Honor explicit checkpoints such as "show images before coding" or "let me choose": prepare the real alternatives and a recommendation, then stop. Approval to explore does not authorize a selection or implementation the user reserved. Otherwise choose directions yourself, record why, and keep the alternatives; routine design decisions get no approval step. Dispatching a reviewer model is a separate boundary, set under Inspect and refine.

Effort defaults are adjustable, not proven optima:

- Substantial exploration: three meaningfully different candidates of one representative screen or flow; five when requested or when the first set misses the brief.
- Up to three refinement passes after the first render and one structural pivot. A small fix gets one implementation and verification pass.
- These budgets cap optional aesthetic work, never a fixable defect in required behavior.

## Explore and select

1. Use real content or realistic samples with long labels, quantities, and units. Hold task, viewport, state, and data constant across candidates, and vary at least two meaningful axes, such as composition and hierarchy or typography and imagery.
2. Record each reference and the property it informs. Existing product screens are the strongest reference for an extension.
3. Render the actual candidates ([references/prompts.md](references/prompts.md)); a written description is not a candidate.
4. Compare under neutral labels as [references/evaluation.md](references/evaluation.md) describes. Adopt the user's pick when the choice is theirs.
5. Turn the winner into a compact design contract: hierarchy, type roles, spacing, color tokens, density, components, assets, responsive transformations, and required states. Separate what a screenshot shows from inferred behavior, and disclose adaptations made for usability or correctness.

## Build a representative slice

Build one representative screen and its primary interaction before spreading the direction. Follow `build-ui` for craft and its verify check set, building to the design contract as its direction: that skill's new-direction choices, including its list of templated defaults, apply only where the contract is silent.

- Reuse repository components and accessible primitives; add no second design system and no dependency only for decoration.
- Keep text, controls, tables, and charts native and editable, and generate isolated raster assets only for imagery. Never ship a screenshot with invisible click regions.
- Cover the loading, empty, error, success, disabled, and permission states that apply, plus long content and realistic volume.
- Adapt hierarchy and controls for narrow screens rather than shrinking the desktop layout.
- Label simulated behavior as simulated; never report it as integrated.
- Keep a recoverable best version before each substantial revision.

## Inspect and refine

Run the app and open its screenshots; a passing build or code review is not visual inspection. [references/evaluation.md](references/evaluation.md) owns capture conditions, journeys, the reviewer brief, and stop conditions.

Fix the highest-impact one to three findings, recapture, compare with the best previous version, and keep the better one. Stop when the acceptance contract holds and no significant in-scope issue remains, or when passes stop improving; report an unresolved gate as incomplete or blocked.

**Independent review.** Substantial work gets one fresh reviewer, resolved with `python3 shared/scripts/model_routing.py resolve review --provider <host>`, whose model differs from the builder's; a consequential or contested choice adds a second, resolved with `--risk high`. When the work is scoped, show each reviewer with model, effort, and host route, and ask: **"Approve this plan, or specify changes."** An inherited approved plan is already the approval. Route each reviewer as `shared/references/host-model-execution.md` says. An unavailable reviewer is reported as not performed, never replaced by another model; a self-review pass is labeled as self review.

## Deliver

Give the preview or deliverable, the selected direction and rationale, the checks actually run, and material limits, separating verified behavior from judgment, assumptions, and untested areas. For substantial work, hand off the design contract, selected reference, evidence tied to the checked version, and best checkpoint; [assets/evaluation.json](assets/evaluation.json) gives each gate its own status. Record explicit user preferences in project guidance and label inferred ones separately.

Deploy, publish, merge, send messages, or change shared settings only when authorized.

Provenance for these defaults, for editing this skill rather than running it: [references/research.md](references/research.md).
