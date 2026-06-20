---
name: ui-ux-pro-max
description: Searchable UI/UX design database (styles, color palettes, font pairings, UX guidelines, chart types, icons, stack best practices) that generates complete design systems. Use when designing or building any web/mobile UI — landing pages, dashboards, components — or when choosing styles, colors, typography, charts, or reviewing/fixing UI quality.
---
# ui-ux-pro-max

Comprehensive design guide for web and mobile applications. Contains 67 styles, 96 color palettes, 57 font pairings, 99 UX guidelines, and 25 chart types across 13 technology stacks. Searchable database with priority-based recommendations.

The load-bearing artifact is the **design system** — the output of `--design-system` (persisted as `MASTER.md`). Generate it first, then obey it: every page, component, and review decision cites the design system as the source of truth rather than improvising fresh choices.

For purely creative/bespoke aesthetic direction without the design-system database, see frontend-design.

## Prerequisites

Check if Python is available:

```bash
python3 --version || python --version
```

If Python is not available, stop and tell the user the prerequisite is missing. Do not install Python from this skill.

---

## How to Use This Skill

When user requests UI/UX work (design, build, create, implement, review, fix, improve), follow this workflow.

**Running commands:** all examples below use `<skill-dir>` as a placeholder for this skill's directory (the folder containing this SKILL.md). Substitute its actual path, e.g. `python3 <skill-dir>/scripts/search.py ...`. The script resolves its data files relative to itself, so it works from any working directory.

### Step 1: Analyze User Requirements

Extract key information from user request:
- **Product type**: SaaS, e-commerce, portfolio, dashboard, landing page, etc.
- **Style keywords**: minimal, playful, professional, elegant, dark mode, etc.
- **Industry**: healthcare, fintech, gaming, education, etc.
- **Stack**: React, Vue, Next.js, or default to `html-tailwind`

### Step 2: Generate Design System (REQUIRED)

**Always start with `--design-system`** to get comprehensive recommendations with reasoning:

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

After getting the design system, use domain searches when you need additional details:

```bash
python3 <skill-dir>/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

**When to use detailed searches:**

| Need | Domain | Example |
|------|--------|---------|
| More style options | `style` | `--domain style "glassmorphism dark"` |
| Chart recommendations | `chart` | `--domain chart "real-time dashboard"` |
| UX best practices | `ux` | `--domain ux "animation accessibility"` |
| Alternative fonts | `typography` | `--domain typography "elegant luxury serif"` |
| Landing structure | `landing` | `--domain landing "hero social-proof"` |

### Step 4: Stack Guidelines (Default: html-tailwind)

Get implementation-specific best practices. If user doesn't specify a stack, **default to `html-tailwind`**.

```bash
python3 <skill-dir>/scripts/search.py "layout responsive form" --stack html-tailwind
```

For the full list of `--domain` and `--stack` values, see `references/search-reference.md`.

**Then:** Synthesize the design system + detailed searches and implement the design, citing the design system for every choice.

---

## Common Rules for Professional UI

These are frequently overlooked issues that make UI look unprofessional:

### Icons & Visual Elements

| Rule | Do | Don't |
|------|----|----- |
| **No emoji icons** | Use SVG icons (Heroicons, Lucide, Simple Icons) | Use emojis like 🎨 🚀 ⚙️ as UI icons |
| **Stable hover states** | Use color/opacity transitions on hover | Use scale transforms that shift layout |
| **Correct brand logos** | Research official SVG from Simple Icons | Guess or use incorrect logo paths |
| **Consistent icon sizing** | Use fixed viewBox (24x24) with w-6 h-6 | Mix different icon sizes randomly |

### Interaction & Cursor

| Rule | Do | Don't |
|------|----|----- |
| **Cursor pointer** | Add `cursor-pointer` to all clickable/hoverable cards | Leave default cursor on interactive elements |
| **Hover feedback** | Provide visual feedback (color, shadow, border) | No indication element is interactive |
| **Smooth transitions** | Use `transition-colors duration-200` | Instant state changes or too slow (>500ms) |

### Light/Dark Mode Contrast

| Rule | Do | Don't |
|------|----|----- |
| **Glass card light mode** | Use `bg-white/80` or higher opacity | Use `bg-white/10` (too transparent) |
| **Text contrast light** | Use `#0F172A` (slate-900) for text | Use `#94A3B8` (slate-400) for body text |
| **Muted text light** | Use `#475569` (slate-600) minimum | Use gray-400 or lighter |
| **Border visibility** | Use `border-gray-200` in light mode | Use `border-white/10` (invisible) |

### Layout & Spacing

| Rule | Do | Don't |
|------|----|----- |
| **Floating navbar** | Add `top-4 left-4 right-4` spacing | Stick navbar to `top-0 left-0 right-0` |
| **Content padding** | Account for fixed navbar height | Let content hide behind fixed elements |
| **Consistent max-width** | Use same `max-w-6xl` or `max-w-7xl` | Mix different container widths |

---

## Pre-Delivery Checklist

The `--design-system` output appends the canonical checklist (emoji icons, consistent icon set, cursor-pointer, transitions 150-300ms, 4.5:1 contrast, visible focus states, responsive breakpoints, no content behind fixed navbars, no mobile horizontal scroll, `prefers-reduced-motion`). Treat that generated checklist as the source of truth and run it before delivery.

Also verify every **Do** column above, plus these items the generated checklist does not cover:

- [ ] Use theme colors directly (bg-primary) not `var()` wrapper
- [ ] Test both light and dark modes
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Color is not the only indicator
