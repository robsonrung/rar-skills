---
name: ui-ux-pro-max
description: Choose a reusable UI design system or review cross-screen UX using a design database. Use for visual systems, interaction rules, or UI quality; use frontend-design for bespoke visual implementation.
---

# ui-ux-pro-max

Comprehensive design guide for web and mobile applications. Contains 67 styles, 96 color palettes, 57 font pairings, 99 UX guidelines, and 25 chart types across 13 technology stacks. Searchable database with priority-based recommendations.

The load-bearing artifact is the **design system**. Reuse the project's existing tokens, components, and design rules for maintenance or review. Generate a system with `--design-system` only when one is missing or the user requests a new direction. The selected system guides each page and component.

For purely creative/bespoke aesthetic direction without the design-system database, see frontend-design.

## Prerequisites

When a database search or design-system generation is needed, check if Python is available. Reviewing an existing system without a database lookup does not require Python:

```bash
python3 --version || python --version
```

If Python is not available, stop and tell the user the prerequisite is missing. Do not install Python from this skill.

---

## How to Use This Skill

Select the work from the request: create a missing system, implement within the chosen system, or review the affected interface. Reuse existing decisions and skip searches or generation that would not change the result.

**Running commands:** all examples below use `<skill-dir>` as a placeholder for this skill's directory (the folder containing this SKILL.md). Substitute its actual path, e.g. `python3 <skill-dir>/scripts/search.py ...`. The script resolves its data files relative to itself, so it works from any working directory.

### Step 1: Analyze User Requirements

Extract key information from user request:

- **Product type**: SaaS, e-commerce, portfolio, dashboard, landing page, etc.
- **Style keywords**: minimal, playful, professional, elegant, dark mode, etc.
- **Industry**: healthcare, fintech, gaming, education, etc.
- **Stack**: use the existing project stack or the user's selection; use `html-tailwind` only for a new unconfigured artifact.

### Step 2: Select or generate the design system

Use an existing system for a review or scoped fix. When the system is missing or a new direction is requested, use `--design-system` to obtain recommendations:

```bash
python3 <skill-dir>/scripts/search.py "<product_type> <industry> <keywords>" --design-system [-p "Project Name"]
```

This command:

1. Searches 5 domains in parallel (product, style, color, landing, typography)
2. Applies reasoning rules from `ui-reasoning.csv` to select best matches
3. Returns complete design system: pattern, style, colors, typography, effects
4. Includes anti-patterns to avoid

Add `-f markdown` for documentation-friendly output (default: `ascii` box, best for terminal display).

**Example** — user asks "Làm landing page cho dịch vụ chăm sóc da chuyên nghiệp" (non-English requests work: analyze the request, then search with English keywords):

```bash
python3 <skill-dir>/scripts/search.py "beauty spa wellness service elegant" --design-system -p "Serenity Spa"
```

### Step 2b: Persist Design System (Master + Overrides Pattern)

To save the design system for hierarchical retrieval across sessions, add `--persist`:

```bash
python3 <skill-dir>/scripts/search.py "<query>" --design-system --persist -p "Project Name"
```

This creates (where `<project-slug>` is the lowercased, hyphenated project name, or `default` if no `-p` given):

- `design-system/<project-slug>/MASTER.md` — Global Source of Truth with all design rules
- `design-system/<project-slug>/pages/` — Folder for page-specific overrides

Persisted files land under the **current working directory** by default. Pass `--output-dir` (short form `-o`) to write the `design-system/` tree somewhere else — the repo root, a `docs/` folder, or a scratch directory:

```bash
python3 <skill-dir>/scripts/search.py "<query>" --design-system --persist -p "Project Name" -o <target-dir>
```

Set it deliberately when the shell's working directory is not where the design system belongs; the confirmation output prints paths relative to the chosen directory.

**With page-specific override:**

```bash
python3 <skill-dir>/scripts/search.py "<query>" --design-system --persist -p "Project Name" --page "dashboard"
```

This also creates:

- `design-system/<project-slug>/pages/dashboard.md` — Page-specific deviations from Master

**How hierarchical retrieval works:**

1. When building a specific page (e.g., "Checkout"), first check `design-system/<project-slug>/pages/checkout.md`
2. If the page file exists, its rules **override** the Master file
3. If not, use `design-system/<project-slug>/MASTER.md` exclusively

### Step 3: Supplement with Detailed Searches

With the design system selected, use domain searches only for unresolved details:

```bash
python3 <skill-dir>/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

**When to use detailed searches:**

| Need | Domain | Example |
| --- | --- | --- |
| More style options | `style` | `--domain style "glassmorphism dark"` |
| Chart recommendations | `chart` | `--domain chart "real-time dashboard"` |
| UX best practices | `ux` | `--domain ux "animation accessibility"` |
| Alternative fonts | `typography` | `--domain typography "elegant luxury serif"` |
| Landing structure | `landing` | `--domain landing "hero social-proof"` |

### Step 4: Stack Guidelines (Default: html-tailwind)

Search stack-specific guidance when an implementation decision needs it. Use the existing project stack. Default to `html-tailwind` only for a new artifact with no selected stack.

```bash
python3 <skill-dir>/scripts/search.py "layout responsive form" --stack html-tailwind
```

For the full list of `--domain` and `--stack` values, see `references/search-reference.md`.

**React re-render and memoization review is not this skill's job.** `data/react-performance.csv` is a data lookup — rules you can search and cite. Auditing an actual component tree for unnecessary re-renders, memoization that buys nothing, Context provider churn, stale closures, or fetch race conditions belongs to the `advanced-react` skill, which is the reviewer. Use this skill for the design system; route the performance pass there.

For an implementation request, apply the selected system and relevant search results to the scoped change. For a review request, return findings against that system without editing.

---

## Common Rules for Professional UI

These are frequently overlooked issues that make UI look unprofessional:

### Icons & Visual Elements

| Rule | Do | Don't |
| --- | --- | --- |
| **No emoji icons** | Use SVG icons (Heroicons, Lucide, Simple Icons) | Use emojis like 🎨 🚀 ⚙️ as UI icons |
| **Stable hover states** | Use color/opacity transitions on hover | Use scale transforms that shift layout |
| **Correct brand logos** | Research official SVG from Simple Icons | Guess or use incorrect logo paths |
| **Consistent icon sizing** | Use fixed viewBox (24x24) with w-6 h-6 | Mix different icon sizes randomly |

### Interaction & Cursor

| Rule | Do | Don't |
| --- | --- | --- |
| **Cursor pointer** | Add `cursor-pointer` to all clickable/hoverable cards | Leave default cursor on interactive elements |
| **Hover feedback** | Provide visual feedback (color, shadow, border) | No indication element is interactive |
| **Smooth transitions** | Use `transition-colors duration-200` | Instant state changes or too slow (>500ms) |

### Light/Dark Mode Contrast

| Rule | Do | Don't |
| --- | --- | --- |
| **Glass card light mode** | Use `bg-white/80` or higher opacity | Use `bg-white/10` (too transparent) |
| **Text contrast light** | Use `#0F172A` (slate-900) for text | Use `#94A3B8` (slate-400) for body text |
| **Muted text light** | Use `#475569` (slate-600) minimum | Use gray-400 or lighter |
| **Border visibility** | Use `border-gray-200` in light mode | Use `border-white/10` (invisible) |

### Layout & Spacing

| Rule | Do | Don't |
| --- | --- | --- |
| **Floating navbar** | Add `top-4 left-4 right-4` spacing | Stick navbar to `top-0 left-0 right-0` |
| **Content padding** | Account for fixed navbar height | Let content hide behind fixed elements |
| **Consistent max-width** | Use same `max-w-6xl` or `max-w-7xl` | Mix different container widths |

---

## Verify the changed interface

Use one check set for the affected pages and interactions. Start from the selected design system and, when available, its generated checklist. Merge relevant rules from the tables above; do not run duplicate checklists.

Check supported light and dark modes when the change affects shared colors or mode behavior. For a local change, inspect the affected surface in the supported modes rather than retesting unrelated pages.

Preserve these checks where applicable: consistent icons, interaction feedback, readable contrast, visible focus, labels and image alternatives, text or shape in addition to color, responsive layout, no content hidden behind fixed elements, no mobile horizontal scroll, and reduced-motion support. Use theme tokens directly as required by the project's styling conventions.

Reuse evidence for unchanged surfaces. After a correction, recheck the affected behavior; broaden only if the correction or a failure exposes a wider risk. Report the tested scope and any unsupported or untested mode.
