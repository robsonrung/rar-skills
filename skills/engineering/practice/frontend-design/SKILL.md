---
name: frontend-design
description: Build a custom frontend interface from a chosen visual direction. Use for a bespoke page, component, or site; use ui-ux-pro-max for reusable design systems and advanced-react for React behavior.
license: Complete terms in LICENSE.txt
---

# Frontend Design

Build distinctive, production-grade interfaces as real working code.

The load-bearing idea is **conceptual integrity**: the interface commits to one design idea, and every typographic, color, motion, and layout choice serves it. Name that idea before coding and hold to it. A striking but incoherent screen fails.

## Existing product or new direction

In an existing product, its components, theme, density, and interaction conventions are the direction. Extend them, and change an established font, control, or layout only when the user asks for a redesign.

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

## Delivery

Ship runnable code with a note on accessibility, how desktop and mobile differ, the trade-offs the direction forced, and how to run it. When the requested framework is unavailable, ship plain HTML/CSS/JS and say so.
