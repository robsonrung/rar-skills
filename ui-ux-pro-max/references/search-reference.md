# Search Reference

Full lookup tables for the `search.py` `--domain` and `--stack` flags. Load this when you need the complete list of available domains or stacks; the step-by-step workflow lives in `SKILL.md`.

## Available Domains

| Domain | Use For | Example Keywords |
|--------|---------|------------------|
| `product` | Product type recommendations | SaaS, e-commerce, portfolio, healthcare, beauty, service |
| `style` | UI styles, colors, effects; results include AI prompt keywords and CSS/technical keywords per style | glassmorphism, minimalism, dark mode, brutalism, (style name) |
| `typography` | Font pairings, Google Fonts | elegant, playful, professional, modern |
| `color` | Color palettes by product type | saas, ecommerce, healthcare, beauty, fintech, service |
| `landing` | Page structure, CTA strategies | hero, hero-centric, testimonial, pricing, social-proof |
| `chart` | Chart types, library recommendations | trend, comparison, timeline, funnel, pie |
| `ux` | Best practices, anti-patterns | animation, accessibility, z-index, loading |
| `icons` | SVG icon names, libraries, import code | menu, arrow, search, social, settings, chart |
| `react` | React/Next.js performance | waterfall, bundle, suspense, memo, rerender, cache |
| `web` | Web interface guidelines | aria, focus, keyboard, semantic, virtualize |

## Available Stacks

| Stack | Focus |
|-------|-------|
| `html-tailwind` | Tailwind utilities, responsive, a11y (DEFAULT) |
| `react` | State, hooks, performance, patterns |
| `nextjs` | SSR, routing, images, API routes |
| `astro` | Islands architecture, content, view transitions, SEO |
| `vue` | Composition API, Pinia, Vue Router |
| `nuxtjs` | File-based routing, data fetching, SSR, auto-imports |
| `nuxt-ui` | Nuxt UI components, theming, forms, dashboards |
| `svelte` | Runes, stores, SvelteKit |
| `swiftui` | Views, State, Navigation, Animation |
| `react-native` | Components, Navigation, Lists |
| `flutter` | Widgets, State, Layout, Theming |
| `shadcn` | shadcn/ui components, theming, forms, patterns |
| `jetpack-compose` | Composables, Modifiers, State Hoisting, Recomposition |

**Tip:** Be specific with keywords ("healthcare SaaS dashboard" > "app"). If results are weak, retry with more specific or different keywords — different keywords reveal different insights.
