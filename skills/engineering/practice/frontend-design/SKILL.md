---
name: frontend-design
description: "Build or review a frontend interface within an existing design system or a new visual direction. Use for a bespoke page, component, or site, or a new or reworked user-facing flow; use advanced-react for React behavior."
license: Complete terms in LICENSE.txt
---

# Frontend Design

Build distinctive, production-grade interfaces as real working code.

The load-bearing idea is **conceptual integrity**: the interface commits to one design idea, and every typographic, color, motion, and layout choice serves it. Name that idea before coding and hold to it. A striking but incoherent screen fails.

## Existing product or new direction

In an existing product, its components, theme, density, and interaction conventions are the direction. Extend them, and change an established font, control, or layout only when the user asks for a redesign. When the project keeps a design system (tokens, a master rules file, component library), it governs: a page-level rules file overrides the master for that page, and the master supplies everything else.

For a new direction, decide:

- **Purpose**: the problem the interface solves and for whom.
- **Tone**: one committed extreme (brutally minimal, maximalist, retro-futuristic, editorial, brutalist, art deco, soft, industrial, or your own), never a blend that hedges.
- **Constraints**: framework, performance, accessibility.
- **Differentiation**: the one thing someone will remember.

## Aesthetics

- **Typography**: a characterful display face paired with a refined body face, chosen for this context.
- **Color**: a dominant palette with sharp accents, held in CSS variables.
- **Motion**: a few high-impact moments, such as one orchestrated load with staggered reveals, over scattered micro-interactions. CSS first for HTML; Motion for React when available.
- **Composition**: asymmetry, overlap, diagonal flow, grid-breaking elements, and either generous negative space or controlled density.
- **Atmosphere**: backgrounds and texture with depth, such as gradient meshes, noise, patterns, layered transparency, and grain, matched to the tone.

Each new direction gets its own fonts, palette, and layout, unlike the templated defaults: Inter, Roboto, Arial, system stacks, Space Grotesk, purple-on-white gradients, card grids.

Match code complexity to the vision. Maximalism earns elaborate animation and effects; minimalism earns precision in spacing, type, and detail.

## Verify

Check the changed surfaces once, in every mode they support (light, dark): readable contrast, visible keyboard focus, labels and image alternatives, cues beyond color, reduced-motion support, and a responsive layout with no stray horizontal scroll on mobile and no content hidden behind fixed elements. Recheck only what a correction touched, and report what went untested. Under `design-gate`, review against the direction and this check set without editing, and return the caller's gate result.

## Delivery

Ship runnable code with a note on accessibility, how desktop and mobile differ, the trade-offs the direction forced, and how to run it. When the requested framework is unavailable, ship plain HTML/CSS/JS and say so.
