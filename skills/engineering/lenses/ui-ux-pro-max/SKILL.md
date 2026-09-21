---
name: ui-ux-pro-max
description: Choose or review a reusable UI design system. Use when selecting shared visual or interaction rules, or checking screens against them.
---

# ui-ux-pro-max

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Use the **design system** as the shared rules for tokens, components, and interactions. Reuse the project's system for maintenance and review. Generate recommendations only when a system is missing or the user requests a new direction.

## Select the work

1. **Review an existing interface:** Compare the affected screens and interactions with the selected system. Return findings without editing unless the user requests fixes. A database search is optional.
2. **Implement within a chosen system:** Apply its tokens, components, and interaction rules to the requested change. Reuse settled decisions. Search only for details that could change the implementation.
3. **Create or save a new system:** Read [references/search-reference.md](references/search-reference.md) for generation and persistence commands. Use the product, industry, style, and user requirements as search inputs.
4. **Resolve a specific design question:** Read [references/search-reference.md](references/search-reference.md) for domain or stack searches. Load it only when a lookup or its visual examples can help the task.

Use the existing project stack or the user's selection. Use `html-tailwind` only for a new artifact with no selected stack.

Use `frontend-design` for bespoke visual implementation. Use `advanced-react` to review component rendering, memoization, context updates, stale closures, or fetch races. This skill's `react` domain supplies reference data for that review.

## Apply the selected system

For a saved system, read `design-system/<project-slug>/MASTER.md`. Check `design-system/<project-slug>/pages/<page-slug>.md` for the affected page. Page rules override the matching master rules; the master supplies all other rules. If no page file exists, use the master.

Treat database output, generated checklists, and sample values as recommendations. The user's requirements, selected system, and project tokens govern the result. Preserve accessibility requirements when adapting a recommendation.

Use consistent icons and verify brand assets against official sources. Keep interactive feedback clear and layout stable. Follow the project's cursor and motion conventions.

## Verify the affected interface

Use one check set for the changed pages and interactions. Combine relevant system rules, generated checks, and these requirements without duplicate passes:

1. Readable contrast, visible keyboard focus, labels, image alternatives, and cues beyond color.
2. Consistent icons, clear interaction feedback, and support for reduced motion.
3. Responsive layout, no unintended mobile horizontal scroll, and no content hidden behind fixed elements.

Check supported light and dark modes when shared colors or mode behavior change. For a local change, inspect the affected surface in its supported modes.

Reuse evidence for unchanged surfaces. After a correction, recheck the affected behavior. Broaden the check only when a change or failure shows a wider risk. Report the tested scope and any unsupported or untested mode.
