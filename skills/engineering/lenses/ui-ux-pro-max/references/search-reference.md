# Search Reference

Use the relevant section when generating a system, saving it, searching the database, or resolving a visual detail. Review and implementation routes are in [SKILL.md](../SKILL.md).

## Command setup

The scripts need Python 3.10 or later. Check the available version before the first database command. If Python is missing, report the blocked lookup and continue work that can use the existing system. Do not install Python from this skill.

Each example sets `SKILL_DIR` to the absolute directory containing the loaded `SKILL.md`. Replace the placeholder before running it. Keep the assignment in each invocation because shell state may not persist. The script finds its data relative to its own path, so commands can run from any working directory.

Use specific English search terms for the product, industry, and style. Interpret requests in other languages before choosing those terms. Retry with different terms only when weak results leave the question unresolved.

## Generate recommendations

Generate a system when one is missing or the user requests a new direction:

```bash
SKILL_DIR="<absolute path of the loaded skill directory>";
python3 "$SKILL_DIR/scripts/search.py" "beauty spa wellness service elegant" --design-system -p "Serenity Spa" -f markdown
```

The generator searches `product`, `style`, `color`, `landing`, and `typography`. It uses `data/ui-reasoning.csv` to select recommendations. Results include a page pattern, style, colors, typography, effects, and practices to avoid.

`--project-name` or `-p` sets the project name. `--format` or `-f` accepts `ascii` or `markdown`; `ascii` is the default. `-ds` is an alias for `--design-system`.

Use the output to select rules that fit the request. Generated values and checklists do not override the selected system, project conventions, or accessibility requirements.

## Save a system

Use `--persist` when the system belongs in the project's files. Set the output directory deliberately:

```bash
SKILL_DIR="<absolute path of the loaded skill directory>";
python3 "$SKILL_DIR/scripts/search.py" "beauty spa wellness service elegant" --design-system --persist -p "Serenity Spa" -o "<absolute target directory>"
```

This writes:

1. `<target directory>/design-system/serenity-spa/MASTER.md`
2. `<target directory>/design-system/serenity-spa/pages/`

`--output-dir` or `-o` sets the directory that will contain `design-system/`. Without it, files go under the current working directory.

Pass `-p` when saving so the destination has a stable name. The script makes the project folder name lowercase and replaces spaces with hyphens. Without `-p`, it derives the name from the query; the terminal confirmation can show a different path.

To generate a system with a page override:

```bash
SKILL_DIR="<absolute path of the loaded skill directory>";
python3 "$SKILL_DIR/scripts/search.py" "beauty spa booking dashboard" --design-system --persist -p "Serenity Spa" --page "dashboard" -o "<absolute target directory>"
```

This also writes `design-system/serenity-spa/pages/dashboard.md`. Page filenames are lowercase with spaces replaced by hyphens.

Each persistence run replaces `MASTER.md` and the named page file, if supplied. `--page` does not update a page alone. For a page change within an existing system, edit its override file directly instead of regenerating the master.

For page retrieval, use both files inside the same project folder:

1. Read `design-system/<project-slug>/MASTER.md`.
2. Check `design-system/<project-slug>/pages/<page-slug>.md`.
3. Apply page rules where they differ. Use master rules for everything else.

Generated headers can omit the project folder from example paths. Resolve the files using the full paths above.

## Search unresolved details

A domain search returns up to three results by default:

```bash
SKILL_DIR="<absolute path of the loaded skill directory>";
python3 "$SKILL_DIR/scripts/search.py" "animation accessibility" --domain ux -n 3
```

Use `--domain` or `-d` to select a domain. Without it, the script chooses a domain from the query and falls back to `style`.

Available domains:

1. `product`: Product type recommendations. Example terms: `saas ecommerce portfolio healthcare beauty service`.
2. `style`: Visual styles, colors, effects, and CSS guidance. Example terms: `glassmorphism minimalism dark mode brutalism`.
3. `typography`: Font pairings, sources, and imports. Example terms: `elegant playful professional modern`.
4. `color`: Palettes by product type. Example terms: `saas ecommerce healthcare beauty fintech service`.
5. `landing`: Page structure and calls to action. Example terms: `hero testimonial pricing social proof`.
6. `chart`: Chart types, libraries, and accessibility. Example terms: `trend comparison timeline funnel pie`.
7. `ux`: Interaction guidance and practices to avoid. Example terms: `animation accessibility loading`.
8. `icons`: SVG icon names, libraries, and imports. Example terms: `menu arrow search social settings chart`.
9. `react`: Rendering and performance reference data. Example terms: `waterfall bundle suspense memo rerender cache`.
10. `web`: Web interface guidance. Example terms: `aria focus keyboard semantic virtualize`.

Search the selected project stack when a specific implementation decision needs guidance:

```bash
SKILL_DIR="<absolute path of the loaded skill directory>";
python3 "$SKILL_DIR/scripts/search.py" "layout responsive form" --stack html-tailwind
```

Use `--stack` or `-s` with one of these values:

1. `html-tailwind`: Utility classes, responsive layout, and accessibility.
2. `react`: State, hooks, performance, and patterns.
3. `nextjs`: Server rendering, routing, images, and API routes.
4. `astro`: Islands, content, view transitions, and search visibility.
5. `vue`: Composition API, state, and routing.
6. `nuxtjs`: File routing, data fetching, server rendering, and imports.
7. `nuxt-ui`: Components, themes, forms, and dashboards.
8. `svelte`: Runes, stores, and application structure.
9. `swiftui`: Views, state, navigation, and animation.
10. `react-native`: Components, navigation, and lists.
11. `flutter`: Widgets, state, layout, and themes.
12. `shadcn`: Components, themes, forms, and patterns.
13. `jetpack-compose`: Composables, modifiers, state, and recomposition.

`html-tailwind` is a skill default only for new artifacts with no selected stack. The script has no default stack.

Use `--max-results` or `-n` to change the result limit. Add `--json` for structured domain or stack results. Choose one command mode: `--design-system` takes priority over `--stack`, which takes priority over `--domain`. Search limits and JSON output apply to searches. Persistence options apply to generation; `--page` and `-o` take effect only with `--persist`.

## Optional visual examples

Use these examples only when they fit the selected system. Reuse project tokens before introducing literal values.

1. **Icons:** An SVG icon with a `24 × 24` viewBox and `w-6 h-6` is one size convention. Match the project's icon family and optical size. Use emoji only when the selected visual direction calls for it.
2. **Feedback and motion:** `transition-colors duration-200` is one transition example. Select duration and easing from project tokens, keep hover effects from shifting layout, and respect reduced motion.
3. **Light mode:** `#0F172A` for body text, `#475569` for secondary text, `bg-white/80` for a translucent card, and `border-gray-200` are palette examples. Check actual foreground and background contrast in each supported theme.
4. **Spacing and layout:** `top-4 left-4 right-4` can fit a floating navigation bar. `max-w-6xl` or `max-w-7xl` can fit a shared container. Use the selected layout and spacing scale, and account for fixed elements so they do not cover content.
